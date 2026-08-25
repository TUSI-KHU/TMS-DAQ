from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import numpy as np

from common.config import TmsConfig
from common.protocol import TelemetryBlock
from laptop.nano import NanoMessage, NanoSerialManager, NanoStatus
from laptop.ssh_client import SshConnectionError, SshFailureKind, SshTunnelManager
from laptop.telemetry import TelemetryClient, TelemetryError

ConnectionCallback = Callable[[str, str], None]
BlockCallback = Callable[[TelemetryBlock], None]
HealthCallback = Callable[[dict[str, Any]], None]
ErrorCallback = Callable[[str], None]

# USB-4704 acquisition and logging retain every 10 ms block.  The desktop does
# not need to repaint at that rate, though: limiting cross-thread Qt updates to
# 20 Hz keeps controls responsive while retaining a maximum display latency of
# one visual interval.
VISUAL_BLOCK_INTERVAL_SEC = 0.05


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
    ) -> None:
        self.config = config
        self.connection_callback = connection_callback
        self.block_callback = block_callback
        self.health_callback = health_callback
        self.error_callback = error_callback
        self.telemetry = telemetry_client or TelemetryClient()
        self.direct_telemetry = direct_telemetry
        self.ssh = ssh_manager or SshTunnelManager(
            config.system,
            config.ssh,
            status_callback=lambda status: self._connection("SSH", status),
        )
        self.nano = nano_manager or NanoSerialManager(
            config.nano,
            trigger_callback=self._nano_trigger,
            status_callback=self._nano_status,
        )
        self._stop_event = asyncio.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._block_task: asyncio.Task[None] | None = None
        self._health_task: asyncio.Task[None] | None = None
        self._daq_recovery_in_progress = False

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event.clear()
        self.nano.start()
        delays = (1.0, 2.0, 5.0, 10.0)
        attempt = 0
        try:
            while not self._stop_event.is_set():
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
                    attempt = 0
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
                    if not self.direct_telemetry:
                        await self.ssh.disconnect()
                    self._connection("Pi", "RECONNECTING")

                delay = delays[min(attempt, len(delays) - 1)]
                attempt += 1
                try:
                    await asyncio.wait_for(self._stop_event.wait(), delay)
                except asyncio.TimeoutError:
                    pass
        finally:
            self.nano.stop()

    async def stop(self) -> None:
        self._stop_event.set()
        await self.telemetry.disconnect()
        await self.ssh.disconnect()
        self.nano.stop()

    async def start_session(self, test_name: str) -> dict[str, Any]:
        result = await self.telemetry.start_session(test_name)
        session_id = str(result.get("session_id") or "")
        if not session_id:
            raise TelemetryError("agent did not return a session ID")
        self.nano.arm_session(session_id)
        return result

    async def stop_session(self) -> dict[str, Any]:
        return await self.telemetry.stop_session()

    async def capture_calibration_sample(self, duration_ms: int) -> dict[str, Any]:
        return await self.telemetry.capture_calibration_sample(duration_ms)

    async def set_thrust_calibration(
        self, *, scale_N_per_count: float, offset_N: float
    ) -> dict[str, Any]:
        return await self.telemetry.set_thrust_calibration(
            scale_N_per_count=scale_N_per_count,
            offset_N=offset_N,
        )

    async def reset_daq(self) -> dict[str, object]:
        # Deliberately do not preflight with telemetry.ping(). A wedged
        # USB-4704 can leave the agent's command path unable to answer PING,
        # which used to make the recovery button fail before it could run.
        # recover_usb4704() uses a separate SSH control connection and stops
        # the agent itself, so it remains usable precisely in that state.
        self._connection("DAQ", "INITIALIZING")
        self._daq_recovery_in_progress = True
        try:
            return await self.ssh.recover_usb4704()
        finally:
            self._daq_recovery_in_progress = False

    async def _consume_blocks(self) -> None:
        pending: list[TelemetryBlock] = []
        last_publish = time.monotonic()
        while True:
            block = await self.telemetry.wait_for_block()
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
        )

    async def _report_health(self) -> None:
        while True:
            if self.health_callback is not None and self.telemetry.latest_health:
                self.health_callback(self.telemetry.latest_health)
            await asyncio.sleep(0.2)

    def _nano_trigger(self, _message: NanoMessage) -> None:
        if self._loop is None or not self.telemetry.connected:
            return
        receive_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        future = asyncio.run_coroutine_threadsafe(
            self.telemetry.trigger(receive_time), self._loop
        )
        future.add_done_callback(self._trigger_done)

    def _trigger_done(self, future: asyncio.Future[int]) -> None:
        try:
            sample = future.result()
            self._connection("Trigger", f"SAMPLE {sample}")
        except Exception as exc:  # noqa: BLE001 - callback boundary reports task errors
            self._error(f"점화 Trigger 전송 실패: {exc}")

    def _nano_status(self, status: NanoStatus) -> None:
        self._connection("Nano", status.state)

    def _connection(self, component: str, status: str) -> None:
        if self.connection_callback is not None:
            self.connection_callback(component, status)

    def _error(self, message: str) -> None:
        if self.error_callback is not None:
            self.error_callback(message)
