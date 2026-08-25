from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from common.config import TmsConfig
from common.protocol import TelemetryBlock
from laptop.nano import NanoMessage, NanoSerialManager, NanoStatus
from laptop.ssh_client import SshConnectionError, SshFailureKind, SshTunnelManager
from laptop.telemetry import TelemetryClient, TelemetryError

ConnectionCallback = Callable[[str, str], None]
BlockCallback = Callable[[TelemetryBlock], None]
HealthCallback = Callable[[dict[str, Any]], None]
ErrorCallback = Callable[[str], None]


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
                    self._error(str(exc))
                    if exc.kind == SshFailureKind.AUTHENTICATION:
                        self._connection("SSH", "AUTHENTICATION_FAILED")
                        return
                except TelemetryError as exc:
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

    async def _consume_blocks(self) -> None:
        while True:
            block = await self.telemetry.wait_for_block()
            if self.block_callback is not None:
                self.block_callback(block)

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
