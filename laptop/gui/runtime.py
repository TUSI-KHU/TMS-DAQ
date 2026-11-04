from __future__ import annotations

import asyncio
import os
import tempfile
import threading
from collections.abc import Coroutine
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QObject, Signal

from common.config import TmsConfig
from laptop.backend import DashboardBackend
from laptop.logs import export_csv, read_session_summary
from laptop.system_test import SystemTestRunner


class BackendSignals(QObject):
    connection = Signal(str, str)
    block = Signal(object)
    health = Signal(object)
    error = Signal(str)
    operation_failed = Signal(str, str)
    session_started = Signal(object)
    session_stopped = Signal(object)
    calibration_sampled = Signal(object)
    calibration_saved = Signal(object)
    daq_reset_finished = Signal(object)
    system_test_finished = Signal(object)
    remote_log_downloaded = Signal(str)
    log_message = Signal(str)
    csv_exported = Signal(str)


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
        self._session_log_file: str | None = None
        self._retry_log_file: str | None = None
        self._session_recording = False
        self._remote_names_by_local_name: dict[str, str] = {}

    def start(self) -> None:
        self._thread.start()
        self._ready.wait(timeout=3.0)

    def stop(self, timeout: float = 12.0) -> None:
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
        async def start() -> dict[str, Any]:
            result = await self._require_backend().start_session(test_name)
            self._session_log_file = result.get("log_file")
            self._session_recording = True
            return result

        self._submit(
            start(),
            self.signals.session_started,
            operation="start",
        )

    def stop_session(self) -> None:
        self._submit(
            self._stop_and_save_session(), None,
            operation="stop",
        )

    async def _stop_and_save_session(self) -> None:
        result = await self._require_backend().stop_session()
        self._session_recording = False
        log_file = result.get("log_file")
        self._session_log_file = log_file
        # STOP success must be visible even when SFTP or CSV export fails.
        # Never turn a completed measurement into a DAQ recovery error.
        self.signals.session_stopped.emit(result)
        try:
            if not log_file:
                raise RuntimeError("Pi STOP 응답에 저장된 로그 파일명이 없습니다.")
            await self._download_and_export(log_file)
        except Exception as exc:  # noqa: BLE001 - separate acquisition/save outcomes
            self._retry_log_file = log_file
            self.signals.operation_failed.emit(
                "save", f"측정은 종료됐지만 로그 저장에 실패했습니다: {exc}\n"
                "Pi 원본 로그는 유지됩니다. 로그 화면에서 'Pi 로그 가져오기'로 다시 저장하십시오.",
            )

    def capture_calibration_sample(self, *, row: int, duration_ms: int) -> None:
        async def capture() -> dict[str, Any]:
            result = await self._require_backend().capture_calibration_sample(
                duration_ms
            )
            result["_ui_row"] = row
            return result

        self._submit(capture(), self.signals.calibration_sampled, operation="calibration")

    def save_thrust_calibration(
        self, *, scale_N_per_count: float, offset_N: float
    ) -> None:
        self._submit(
            self._require_backend().set_thrust_calibration(
                scale_N_per_count=scale_N_per_count,
                offset_N=offset_N,
            ),
            self.signals.calibration_saved,
            operation="calibration",
        )

    def save_pressure_calibration(
        self, *, scale_bar_per_count: float, offset_bar: float
    ) -> None:
        self._submit(
            self._require_backend().set_pressure_calibration(
                scale_bar_per_count=scale_bar_per_count,
                offset_bar=offset_bar,
            ),
            self.signals.calibration_saved,
            operation="calibration",
        )

    def reset_daq(self) -> None:
        self._submit(self._require_backend().reset_daq(), self.signals.daq_reset_finished,
                     operation="reset")

    def run_system_test(self) -> None:
        backend = self._require_backend()
        runner = SystemTestRunner(
            backend.nano,
            backend.ssh,
            backend.telemetry,
            self.config.logging.directory,
        )
        self._submit(runner.run(), self.signals.system_test_finished)

    def fetch_latest_remote_log(self, log_file: str | None = None) -> None:
        self._submit(self._fetch_remote_log(log_file), None, operation="save")

    async def _fetch_remote_log(self, log_file: str | None = None) -> None:
        # A failed automatic save takes priority over an older selection so
        # the retry button cannot silently retrieve the wrong measurement.
        name = self._retry_log_file or log_file or self._session_log_file
        name = self._remote_names_by_local_name.get(name, name)
        if not name:
            names = await self._require_backend().ssh.list_remote_logs(
                str(self.config.logging.pi_directory)
            )
            if not names:
                raise RuntimeError("Pi에 가져올 HDF5 로그가 없습니다.")
            name = names[-1]
        if self._session_recording and name == self._session_log_file:
            raise RuntimeError("현재 측정을 종료한 뒤 로그를 가져오십시오.")
        await self._download_and_export(name)

    async def _download_and_export(self, name: str) -> None:
        if PurePosixPath(name).name != name or not name.endswith(".h5"):
            raise ValueError(f"Pi 로그 파일명이 유효하지 않습니다: {name!r}")
        remote_path = str(PurePosixPath(str(self.config.logging.pi_directory)) / name)
        directory = self.config.logging.directory
        directory.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{name}.", suffix=".part", dir=directory)
        os.close(fd)
        partial_path = Path(temporary)
        try:
            await self._require_backend().ssh.download_file(remote_path, partial_path)
            summary = await asyncio.to_thread(read_session_summary, partial_path)
            local_path = directory / name
            # Keep existing H5/CSV files untouched, including files from a
            # previous attempt. Publish only the fully downloaded valid H5.
            while True:
                if local_path.with_suffix(".csv").exists():
                    local_path = directory / f"{Path(name).stem}-download-{uuid4().hex[:8]}.h5"
                    continue
                try:
                    os.link(partial_path, local_path)
                    break
                except FileExistsError:
                    local_path = directory / f"{Path(name).stem}-download-{uuid4().hex[:8]}.h5"
            self._remote_names_by_local_name[local_path.name] = name
            self.signals.remote_log_downloaded.emit(str(local_path))
            csv_path = await asyncio.to_thread(export_csv, local_path, local_path.with_suffix(".csv"))
            self.signals.log_message.emit(f"CSV saved: {csv_path}")
            if summary.trigger_sample is None:
                self.signals.log_message.emit(
                    "WARNING: Nano 점화 이벤트가 없는 로그입니다. CSV 시간은 취득 시작 기준입니다."
                )
            if self._retry_log_file == name:
                self._retry_log_file = None
        finally:
            partial_path.unlink(missing_ok=True)

    def export_log(self, source: Path, destination: str) -> None:
        async def export() -> str:
            path = await asyncio.to_thread(export_csv, source, destination)
            return str(path)

        self._submit(export(), self.signals.csv_exported, operation="save")

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

    def _submit(
        self, coroutine: Coroutine[Any, Any, Any], signal: Signal | None,
        *, operation: str = "command",
    ) -> None:
        if self._loop is None:
            self.signals.operation_failed.emit(operation, "Backend가 아직 준비되지 않았습니다.")
            coroutine.close()
            return
        future = asyncio.run_coroutine_threadsafe(coroutine, self._loop)

        def done(completed: Any) -> None:
            try:
                result = completed.result()
                if signal is not None:
                    signal.emit(result)
            except Exception as exc:  # noqa: BLE001 - GUI task boundary
                self.signals.operation_failed.emit(operation, str(exc))

        future.add_done_callback(done)

    def _require_backend(self) -> DashboardBackend:
        if self._backend is None:
            raise RuntimeError("Backend가 아직 준비되지 않았습니다.")
        return self._backend
