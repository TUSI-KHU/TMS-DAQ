from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import numpy as np

from common.config import TmsConfig
from common.protocol import TelemetryBlock
from laptop.local_daq import LocalDaqAccess
from laptop.nano import NanoMessage, NanoSerialManager, NanoStatus
from laptop.ssh_client import SshConnectionError, SshFailureKind, SshTunnelManager
from laptop.telemetry import RemoteCommandError, TelemetryClient, TelemetryError

ConnectionCallback = Callable[[str, str], None]
BlockCallback = Callable[[TelemetryBlock], None]
HealthCallback = Callable[[dict[str, Any]], None]
ErrorCallback = Callable[[str], None]

# USB-4704 acquisition and logging retain every 10 ms block.  The desktop does
# not need to repaint at that rate, though: limiting cross-thread Qt updates to
# 20 Hz keeps controls responsive while retaining a maximum display latency of
# one visual interval.
VISUAL_BLOCK_INTERVAL_SEC = 0.05
TRIGGER_DELIVERY_TIMEOUT_SEC = 8.0


class DashboardBackend:
    """Owns real Nano, SSH, and telemetry connections outside of the GUI layer."""

    def __init__(
        self,
        config: TmsConfig,
        *,
        connection_callback: ConnectionCallback | None = None,
        block_callback: BlockCallback | None = None,
        health_callback: HealthCallback | None = None,
        error_callback: ErrorCallback | None = None,
        nano_manager: NanoSerialManager | None = None,
        ssh_manager: SshTunnelManager | None = None,
        telemetry_client: TelemetryClient | None = None,
        direct_telemetry: bool = False,
        local_daq: bool = False,
    ) -> None:
        self.config = (
            replace(config, system=replace(config.system, pi_host="127.0.0.1"))
            if local_daq else config
        )
        self.connection_callback = connection_callback
        self.block_callback = block_callback
        self.health_callback = health_callback
        self.error_callback = error_callback
        self.telemetry = telemetry_client or TelemetryClient()
        self.local_daq = local_daq
        self.direct_telemetry = direct_telemetry or local_daq
        self.ssh = ssh_manager or SshTunnelManager(
            config.system,
            config.ssh,
            status_callback=lambda status: self._connection("SSH", status),
        )
        if local_daq and ssh_manager is None:
            self.ssh = LocalDaqAccess(config.logging.pi_directory)
        self.nano = nano_manager or NanoSerialManager(
            config.nano,
            trigger_callback=self._nano_trigger,
            level_callback=self._nano_level,
            status_callback=self._nano_status,
        )
        self._stop_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._block_task: asyncio.Task[None] | None = None
        self._health_task: asyncio.Task[None] | None = None
        self._daq_recovery_in_progress = False
        self._recovery_done = asyncio.Event()
        self._recovery_done.set()
        self._active_session_id: str | None = None
        self._trigger_task: asyncio.Task[int] | None = None
        self._nano_paused = False
        self._nano_levels: asyncio.Queue[tuple[NanoMessage, str, float, str]] = asyncio.Queue(maxsize=4096)
        self._nano_level_task: asyncio.Task[None] | None = None
        self._confirmed_trigger: int | None = None
        self._nano_overflow_reported = False

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event.clear()
        self.nano.start()
        delays = (1.0, 2.0, 5.0, 10.0)
        attempt = 0
        tunnel_failures = 0
        try:
            while not self._stop_event.is_set():
                await self._recovery_done.wait()
                if self._stop_event.is_set():
                    break
                try:
                    if self.direct_telemetry:
                        await self.telemetry.connect(
                            self.config.system.pi_host,
                            self.config.system.telemetry_port,
                        )
                        self._connection("SSH", "BYPASSED")
                    else:
                        local_port = await self.ssh.connect()
                        await self.telemetry.connect("127.0.0.1", local_port)
                    self._connection("Pi", "CONNECTED")
                    self._resume_nano_capture()
                    attempt = 0
                    tunnel_failures = 0
                    self._block_task = asyncio.create_task(self._consume_blocks())
                    self._health_task = asyncio.create_task(self._report_health())
                    await self.telemetry.wait_connection_lost()
                except SshConnectionError as exc:
                    if not self._daq_recovery_in_progress:
                        self._error(str(exc))
                    if exc.kind == SshFailureKind.AUTHENTICATION:
                        self._connection("SSH", "AUTHENTICATION_FAILED")
                        return
                except TelemetryError as exc:
                    tunnel_failures += 1
                    if not self._daq_recovery_in_progress:
                        self._error(str(exc))
                finally:
                    await self.telemetry.disconnect()
                    if self._block_task is not None:
                        self._block_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await self._block_task
                    self._block_task = None
                    if self._health_task is not None:
                        self._health_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await self._health_task
                    self._health_task = None
                    # Keep SSH alive across a tms-agent/DAQ restart.  A
                    # repeated failure on the same forward means the SSH
                    # transport itself is stale, so rotate it then.
                    if not self._daq_recovery_in_progress and not self.direct_telemetry and (
                        not self.ssh.connected or tunnel_failures >= 3
                    ):
                        await self.ssh.disconnect()
                    if not self._daq_recovery_in_progress:
                        self._connection("Pi", "RECONNECTING")

                if self._daq_recovery_in_progress:
                    # The agent is intentionally stopped. Repeated failed
                    # connects here used to rotate a perfectly healthy SSH
                    # tunnel and flood the operator with connection errors.
                    continue

                delay = delays[min(attempt, len(delays) - 1)]
                attempt += 1
                try:
                    await asyncio.wait_for(self._stop_event.wait(), delay)
                except asyncio.TimeoutError:
                    pass
        finally:
            self.nano.stop()

    async def stop(self) -> None:
        await self._finish_trigger_delivery(abort_on_timeout=True, clear_session=True)
        self._stop_event.set()
        self._recovery_done.set()
        await self.telemetry.disconnect()
        await self.ssh.disconnect()
        self.nano.stop()

    async def start_session(self, test_name: str) -> dict[str, Any]:
        self._require_not_recovering()
        self._loop = asyncio.get_running_loop()
        result = await self.telemetry.start_session(test_name)
        session_id = str(result.get("session_id") or "")
        if not session_id:
            raise TelemetryError("agent did not return a session ID")
        self._active_session_id = session_id
        self._trigger_task = None
        await self._close_level_worker()
        self._nano_levels = asyncio.Queue(maxsize=4096)
        self._nano_level_task = asyncio.create_task(self._consume_nano_levels())
        self._confirmed_trigger = None
        self._nano_overflow_reported = False
        self._nano_paused = False
        self.nano.arm_session(session_id)
        return result

    async def stop_session(self) -> dict[str, Any]:
        self._require_not_recovering()
        # A serial callback may arrive just before the operator presses Stop.
        # Persist that event before the agent closes the HDF5 logger.
        try:
            await self._finish_trigger_delivery()
            result = await self.telemetry.stop_session()
        except Exception:
            # A failed STOP may leave Pi recording. Do not silently disable
            # ignition capture for the remainder of that acquisition.
            self._connection("Nano", "CAPTURE_PAUSED")
            if self.telemetry.connected:
                with contextlib.suppress(TelemetryError, OSError):
                    status = (await self.telemetry.ping())["status"]
                    self._resume_nano_capture(status)
            raise
        self._active_session_id = None
        self._nano_paused = False
        await self._close_level_worker()
        return result

    async def capture_calibration_sample(self, duration_ms: int) -> dict[str, Any]:
        self._require_not_recovering()
        return await self.telemetry.capture_calibration_sample(duration_ms)

    async def set_thrust_calibration(
        self, *, scale_N_per_count: float, offset_N: float
    ) -> dict[str, Any]:
        return await self.telemetry.set_thrust_calibration(
            scale_N_per_count=scale_N_per_count,
            offset_N=offset_N,
        )

    async def set_pressure_calibration(
        self, *, scale_bar_per_count: float, offset_bar: float
    ) -> dict[str, Any]:
        return await self.telemetry.set_pressure_calibration(
            scale_bar_per_count=scale_bar_per_count,
            offset_bar=offset_bar,
        )

    async def reset_daq(self) -> dict[str, object]:
        # Deliberately do not preflight with telemetry.ping(). A wedged
        # USB-4704 can leave the agent's command path unable to answer PING,
        # which used to make the recovery button fail before it could run.
        # recover_usb4704() uses a separate SSH control connection and stops
        # the agent itself, so it remains usable precisely in that state.
        self._require_not_recovering()
        await self._finish_trigger_delivery(abort_on_timeout=True, clear_session=True)
        self._daq_recovery_in_progress = True
        self._recovery_done.clear()
        self._connection("DAQ", "INITIALIZING")
        self._connection("Pi", "INITIALIZING")
        try:
            await self.telemetry.disconnect()
            result = await self.ssh.recover_usb4704()
        finally:
            self._daq_recovery_in_progress = False
            self._recovery_done.set()
        # The helper verifies actual buffered AI acquisition, not just the
        # existence of a stale device node. Also wait for this UI's telemetry
        # connection before reporting that recovery is complete.
        if result.get("daq_ready"):
            async def reconnected() -> None:
                while not self.telemetry.connected:
                    await asyncio.sleep(0.1)
                await self.telemetry.ping()

            try:
                await asyncio.wait_for(reconnected(), timeout=20.0)
            except (asyncio.TimeoutError, TelemetryError) as exc:
                raise TelemetryError("DAQ 입력 검증 후 Pi 재연결 실패. DAQ 초기화를 다시 실행하십시오.") from exc
        return result

    def _require_not_recovering(self) -> None:
        if self._daq_recovery_in_progress:
            raise TelemetryError("DAQ 초기화가 진행 중입니다. 완료 후 다시 시도하십시오.")

    async def _consume_blocks(self) -> None:
        pending: list[TelemetryBlock] = []
        last_publish = time.monotonic()
        generation = self.telemetry.stream_generation
        while True:
            block = await self.telemetry.wait_for_block()
            if generation != self.telemetry.stream_generation:
                pending.clear()
                generation = self.telemetry.stream_generation
            if self.block_callback is None:
                continue

            # Never manufacture a continuous trace across a transport gap or
            # a changed DAQ configuration. Flush the preceding trace first so
            # the GUI can preserve the actual sample indices.
            if pending and not self._blocks_are_contiguous(pending[-1], block):
                self.block_callback(self._merge_blocks(pending))
                pending.clear()
                last_publish = time.monotonic()

            pending.append(block)
            now = time.monotonic()
            if now - last_publish >= VISUAL_BLOCK_INTERVAL_SEC:
                self.block_callback(self._merge_blocks(pending))
                pending.clear()
                last_publish = now

    @staticmethod
    def _blocks_are_contiguous(
        previous: TelemetryBlock, following: TelemetryBlock
    ) -> bool:
        return (
            following.first_sample_index
            == previous.first_sample_index + previous.sample_count
            and following.sample_rate == previous.sample_rate
            and following.channel_names == previous.channel_names
            and following.session_id == previous.session_id
        )

    @staticmethod
    def _merge_blocks(blocks: list[TelemetryBlock]) -> TelemetryBlock:
        if not blocks:
            raise ValueError("cannot merge an empty telemetry block list")
        if len(blocks) == 1:
            return blocks[0]
        first = blocks[0]
        last = blocks[-1]
        return TelemetryBlock(
            sequence=last.sequence,
            first_sample_index=first.first_sample_index,
            sample_rate=first.sample_rate,
            channel_names=first.channel_names,
            values=np.concatenate([block.values for block in blocks], axis=0),
            session_id=first.session_id,
        )

    async def _report_health(self) -> None:
        while True:
            if self.health_callback is not None and self.telemetry.latest_health:
                self.health_callback(self.telemetry.latest_health)
            await asyncio.sleep(0.2)

    def _nano_level(self, message: NanoMessage) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        received = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        self._loop.call_soon_threadsafe(
            self._queue_nano_level, message, received, time.monotonic()
        )

    def _queue_nano_level(self, message: NanoMessage, received: str, received_at: float) -> None:
        if message.session_id != self._active_session_id or self._active_session_id is None:
            return
        if self._nano_levels.full():
            # Bound memory during a long outage and explicitly break state
            # continuity rather than infer an edge across discarded samples.
            while not self._nano_levels.empty():
                self._nano_levels.get_nowait()
                self._nano_levels.task_done()
            self._nano_levels.put_nowait((
                replace(message, gpio_state=None, sequence=None, uptime_ms=None),
                received, received_at, uuid4().hex,
            ))
            if not self._nano_overflow_reported:
                self._error("Nano 상태 전송 대기열 초과: 일부 상태를 누락했고 해당 구간은 미확인으로 처리합니다.")
                self._nano_overflow_reported = True
        self._nano_levels.put_nowait((message, received, received_at, uuid4().hex))

    async def _consume_nano_levels(self) -> None:
        while True:
            message, received, received_at, event_id = await self._nano_levels.get()
            try:
                valid_for_ms = None
                while message.session_id == self._active_session_id:
                    if not self.telemetry.connected:
                        await asyncio.sleep(0.05)
                        continue
                    if self.telemetry.session_id != message.session_id:
                        raise TelemetryError("Pi 세션이 변경되어 이전 Nano 상태를 기록하지 않았습니다.")
                    if valid_for_ms is None:
                        age_ms = int((time.monotonic() - received_at) * 1000)
                        valid_for_ms = max(0, min(2000, int(self.config.nano.heartbeat_timeout_sec * 1000)) - age_ms)
                        if message.gpio_state is None:
                            valid_for_ms = 0
                    try:
                        result = await self.telemetry.nano_state(
                            session_id=message.session_id, gpio_state=message.gpio_state,
                            nano_sequence=message.sequence, nano_uptime_ms=message.uptime_ms,
                            receive_time=received, event_id=event_id,
                            valid_for_ms=valid_for_ms, timeout=2.0,
                        )
                        if result.get("trigger_sample") is not None:
                            self._confirm_trigger(int(result["trigger_sample"]))
                        break
                    except RemoteCommandError as exc:
                        if exc.error_type != "TriggerPendingError":
                            raise
                        await asyncio.sleep(0.05)
                    except (TelemetryError, OSError):
                        await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._error(f"Nano HIGH/LOW 상태 저장 실패: {exc}")
            finally:
                self._nano_levels.task_done()

    async def _close_level_worker(self) -> None:
        if self._nano_level_task is not None:
            self._nano_level_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._nano_level_task
            self._nano_level_task = None

    def _nano_trigger(self, message: NanoMessage) -> None:
        # Called on the serial reader thread. Capture receipt time there,
        # then do all session/transport bookkeeping on the backend loop.
        if self._loop is None or self._loop.is_closed():
            self._error("Nano 점화 신호를 받았지만 기록 backend가 준비되지 않았습니다.")
            return
        receive_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        self._loop.call_soon_threadsafe(self._queue_nano_trigger, message, receive_time)

    def _queue_nano_trigger(self, message: NanoMessage, receive_time: str) -> None:
        if not self._active_session_id or message.session_id != self._active_session_id:
            self._error("현재 측정 세션과 다른 Nano 점화 신호를 무시했습니다.")
            return
        if self._trigger_task is not None:
            return
        self._trigger_task = asyncio.create_task(
            self._deliver_trigger(message, receive_time)
        )
        self._trigger_task.add_done_callback(self._trigger_done)

    async def _deliver_trigger(self, message: NanoMessage, receive_time: str) -> int:
        self._connection("Trigger", "RECEIVED")
        while True:
            if message.session_id != self._active_session_id:
                raise TelemetryError("점화 신호의 측정 세션이 종료되었습니다.")
            if not self.telemetry.connected:
                self._connection("Trigger", "WAITING_FOR_PI")
                while not self.telemetry.connected:
                    await asyncio.sleep(0.05)
                continue
            if self.telemetry.session_id != message.session_id:
                raise TelemetryError("Pi 세션이 변경되어 이전 점화 신호를 기록하지 않았습니다.")
            try:
                return await self.telemetry.trigger(
                    receive_time, timeout=2.0,
                    session_id=message.session_id, source="nano",
                    nano_sequence=message.sequence, nano_uptime_ms=message.uptime_ms,
                )
            except RemoteCommandError as exc:
                if exc.error_type == "TriggerPendingError":
                    # START_ACK can precede the first sample; a slow logger
                    # can also need more than one ACK timeout to flush.
                    await asyncio.sleep(0.05)
                    continue
                if "already recorded" in str(exc):
                    status = (await self.telemetry.ping())["status"]
                    if (status.get("session_id") == message.session_id
                            and status.get("trigger_sample") is not None):
                        return int(status["trigger_sample"])
                # A rejection is authoritative, unlike a lost ACK. Never
                # silently retarget an old event to a different session.
                raise
            except (TelemetryError, OSError):
                self._connection("Trigger", "RETRYING")
                await asyncio.sleep(0.1)

    def _resume_nano_capture(self, status: dict[str, Any] | None = None) -> None:
        if not self._nano_paused or not self._active_session_id:
            return
        status = status if status is not None else self.telemetry.latest_health
        if (status.get("session_id") == self._active_session_id
                and status.get("state") in ("RECORDING", "TRIGGERED")):
            self.nano.arm_session(self._active_session_id)
            self._nano_paused = False

    async def _finish_trigger_delivery(
        self, *, abort_on_timeout: bool = False, clear_session: bool = False
    ) -> None:
        # disarm_session only gates reception; the Nano never drives ignition.
        disarm = getattr(self.nano, "disarm_session", None)
        if disarm is not None:
            disarm()
        self._nano_paused = True
        await asyncio.sleep(0)  # Drain serial callbacks queued before disarm.
        deadline = time.monotonic() + TRIGGER_DELIVERY_TIMEOUT_SEC
        if self._trigger_task is not None:
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._trigger_task), TRIGGER_DELIVERY_TIMEOUT_SEC
                )
            except asyncio.TimeoutError:
                if not abort_on_timeout:
                    raise TelemetryError(
                        "점화 신호 저장 확인을 기다리는 중입니다. Pi 재연결 후 종료를 다시 누르십시오."
                    ) from None
                self._trigger_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._trigger_task
                self._error("연결 종료/초기화로 미확인 점화 신호 전달을 중단했습니다. 로그의 ignition_recorded를 확인하십시오.")
            except Exception:
                # _trigger_done reports permanent rejection/write errors.
                pass
        try:
            await asyncio.wait_for(self._nano_levels.join(), max(0.001, deadline - time.monotonic()))
        except asyncio.TimeoutError:
            if not abort_on_timeout:
                raise TelemetryError(
                    "Nano HIGH/LOW 상태 저장 확인을 기다리는 중입니다. Pi 재연결 후 종료를 다시 누르십시오."
                ) from None
            self._error("연결 종료/초기화로 미확인 Nano 상태 전달을 중단했습니다.")
        if clear_session:
            self._active_session_id = None
            self._nano_paused = False
            await self._close_level_worker()
            while not self._nano_levels.empty():
                self._nano_levels.get_nowait()
                self._nano_levels.task_done()

    def _confirm_trigger(self, sample: int) -> None:
        if self._confirmed_trigger is None:
            self._confirmed_trigger = sample
            self._connection("Trigger", f"SAMPLE {sample}")

    def _trigger_done(self, future: asyncio.Future[int]) -> None:
        if future.cancelled():
            return
        try:
            sample = future.result()
            self._confirm_trigger(sample)
        except Exception as exc:  # noqa: BLE001 - callback boundary reports task errors
            self._connection("Trigger", "FAILED")
            reason = str(exc) or "Pi 저장 확인 시간 초과"
            self._error(f"점화 기록을 확인하지 못했습니다: {reason}. 로그의 ignition_recorded를 확인하십시오.")

    def _nano_status(self, status: NanoStatus) -> None:
        value = status.state
        if status.connected and status.state not in ("HEARTBEAT_TIMEOUT", "RECONNECTING"):
            level = "UNKNOWN" if status.gpio_state is None else "HIGH" if status.gpio_state else "LOW"
            value = f"{value} / {level}"
        self._connection("Nano", value)

    def _connection(self, component: str, status: str) -> None:
        if self.connection_callback is not None:
            self.connection_callback(component, status)

    def _error(self, message: str) -> None:
        if self.error_callback is not None:
            self.error_callback(message)
