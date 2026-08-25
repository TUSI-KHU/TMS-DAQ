from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any

from PySide6.QtCore import QObject, Signal

from common.config import TmsConfig
from laptop.backend import DashboardBackend
from laptop.system_test import SystemTestRunner


class BackendSignals(QObject):
    connection = Signal(str, str)
    block = Signal(object)
    health = Signal(object)
    error = Signal(str)
    session_started = Signal(object)
    session_stopped = Signal(object)
    calibration_sampled = Signal(object)
    calibration_saved = Signal(object)
    daq_reset_finished = Signal(object)
    system_test_finished = Signal(object)
    remote_log_downloaded = Signal(str)


class BackendRuntime:
    """Runs asyncio SSH/telemetry work on a background thread for Qt."""

    def __init__(
        self,
        config: TmsConfig,
        signals: BackendSignals,
        *,
        direct_telemetry: bool = False,
    ) -> None:
        self.config = config
        self.signals = signals
        self.direct_telemetry = direct_telemetry
        self._loop: asyncio.AbstractEventLoop | None = None
        self._backend: DashboardBackend | None = None
        self._thread = threading.Thread(
            target=self._thread_main, name="dashboard-backend", daemon=True
        )
        self._ready = threading.Event()

    def start(self) -> None:
        self._thread.start()
        self._ready.wait(timeout=3.0)

    def stop(self, timeout: float = 5.0) -> None:
        if self._loop is not None and self._backend is not None:
            future = asyncio.run_coroutine_threadsafe(self._backend.stop(), self._loop)
            try:
                future.result(timeout=timeout)
            except Exception:  # noqa: BLE001, S110 - shutdown is best effort
                pass
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread.is_alive():
            self._thread.join(timeout)

    def start_session(self, test_name: str) -> None:
        self._submit(
            self._require_backend().start_session(test_name),
            self.signals.session_started,
        )

    def stop_session(self) -> None:
        self._submit(
            self._require_backend().stop_session(), self.signals.session_stopped
        )

    def capture_calibration_sample(self, *, row: int, duration_ms: int) -> None:
        async def capture() -> dict[str, Any]:
            result = await self._require_backend().capture_calibration_sample(
                duration_ms
            )
            result["_ui_row"] = row
            return result

        self._submit(capture(), self.signals.calibration_sampled)

    def save_thrust_calibration(
        self, *, scale_N_per_count: float, offset_N: float
    ) -> None:
        self._submit(
            self._require_backend().set_thrust_calibration(
                scale_N_per_count=scale_N_per_count,
                offset_N=offset_N,
            ),
            self.signals.calibration_saved,
        )

    def reset_daq(self) -> None:
        self._submit(self._require_backend().reset_daq(), self.signals.daq_reset_finished)

    def run_system_test(self) -> None:
        backend = self._require_backend()
        runner = SystemTestRunner(
            backend.nano,
            backend.ssh,
            backend.telemetry,
            self.config.logging.directory,
        )
        self._submit(runner.run(), self.signals.system_test_finished)

    def fetch_latest_remote_log(self) -> None:
        async def fetch() -> str:
            backend = self._require_backend()
            remote_directory = str(self.config.logging.pi_directory)
            names = await backend.ssh.list_remote_logs(remote_directory)
            if not names:
                raise RuntimeError("Pi에 가져올 HDF5 로그가 없습니다.")
            name = names[-1]
            remote_path = f"{remote_directory.rstrip('/')}/{name}"
            local_path = self.config.logging.directory / name
            await backend.ssh.download_file(remote_path, local_path)
            return str(local_path)

        self._submit(fetch(), self.signals.remote_log_downloaded)

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._backend = DashboardBackend(
            self.config,
            connection_callback=self.signals.connection.emit,
            block_callback=self.signals.block.emit,
            health_callback=self.signals.health.emit,
            error_callback=self.signals.error.emit,
            direct_telemetry=self.direct_telemetry,
        )
        self._ready.set()
        loop.create_task(self._backend.run())
        try:
            loop.run_forever()
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            loop.close()

    def _submit(self, coroutine: Coroutine[Any, Any, Any], signal: Signal) -> None:
        if self._loop is None:
            self.signals.error.emit("Backend가 아직 준비되지 않았습니다.")
            coroutine.close()
            return
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)

        def done(completed: Any) -> None:
            try:
                signal.emit(completed.result())
            except Exception as exc:  # noqa: BLE001 - GUI task boundary
                self.signals.error.emit(str(exc))

        future.add_done_callback(done)

    def _require_backend(self) -> DashboardBackend:
        if self._backend is None:
            raise RuntimeError("Backend가 아직 준비되지 않았습니다.")
        return self._backend
