import asyncio
import csv
import shutil
import threading
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from laptop.gui import runtime as runtime_module
from laptop.gui.runtime import BackendRuntime
from pi.daq import DaqBlock
from pi.logger import Hdf5SessionLogger, SessionMetadata


class Signals:
    def __init__(self):
        self.events = []
        for name in (
            "session_stopped", "remote_log_downloaded", "log_message",
            "operation_failed", "csv_exported",
        ):
            setattr(self, name, SimpleNamespace(
                emit=lambda *args, event=name: self.events.append((event, *args)),
            ))


def setup_runtime(tmp_path, *, trigger=True):
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1.0, 0.0), pressure=ChannelConfig(1, 1.0, 0.0),
        logging=LoggingConfig(directory=tmp_path / "local", pi_directory=Path("/pi/logs")),
    )
    logger = Hdf5SessionLogger(config, output_directory=tmp_path / "remote")
    path = logger.open(SessionMetadata("TEST", "session", "2026-11-04T12:00:00Z"))
    logger.append_block(DaqBlock(0, 0, 1000, (0, 1), np.ones((10, 2), dtype=np.uint16)))
    if trigger:
        logger.record_event("ignition", 5, receive_time="2026-11-04T12:00:00Z")
    logger.close()
    signals = Signals()
    requests = []

    class SSH:
        async def download_file(self, remote_path, destination):
            requests.append(remote_path)
            assert remote_path == f"/pi/logs/{path.name}"
            shutil.copyfile(path, destination)

        async def list_remote_logs(self, directory):
            raise AssertionError("Must use exact STOP/selected filename, never lexical latest")

    async def stop_session():
        return {"session_id": "session", "log_file": path.name}

    runtime = BackendRuntime(config, signals)
    runtime._backend = SimpleNamespace(ssh=SSH(), stop_session=stop_session)
    runtime._session_recording = True
    runtime._session_log_file = path.name
    return runtime, signals, requests, path


def test_stop_saves_exact_session_h5_and_csv_off_eventloop(tmp_path, monkeypatch):
    runtime, signals, requests, source = setup_runtime(tmp_path)
    original_export = runtime_module.export_csv
    loop_thread = threading.get_ident()

    def export(*args, **kwargs):
        assert threading.get_ident() != loop_thread
        assert signals.events[0][0] == "session_stopped"
        return original_export(*args, **kwargs)

    monkeypatch.setattr(runtime_module, "export_csv", export)
    asyncio.run(runtime._stop_and_save_session())
    assert requests == [f"/pi/logs/{source.name}"]
    local_h5 = runtime.config.logging.directory / source.name
    assert local_h5.read_bytes() == source.read_bytes()
    with local_h5.with_suffix(".csv").open() as data:
        rows = list(csv.DictReader(data))
    assert float(rows[5]["time_s"]) == 0.0
    assert float(rows[0]["time_s"]) < 0.0
    assert ("remote_log_downloaded", str(local_h5)) in signals.events
    assert not any(event[0] == "operation_failed" for event in signals.events)


def test_save_failure_preserves_complete_state_and_retries_exact_file(tmp_path):
    runtime, signals, requests, source = setup_runtime(tmp_path, trigger=False)
    download = runtime._backend.ssh.download_file

    async def fail(*args):
        raise OSError("SFTP unavailable")

    runtime._backend.ssh.download_file = fail
    asyncio.run(runtime._stop_and_save_session())
    assert signals.events[0][0] == "session_stopped"
    assert signals.events[1][0:2] == ("operation_failed", "save")
    assert not runtime._session_recording
    assert runtime._retry_log_file == source.name
    assert not list(runtime.config.logging.directory.iterdir())
    runtime._backend.ssh.download_file = download
    asyncio.run(runtime._fetch_remote_log("wrong_older_selection.h5"))
    assert runtime._retry_log_file is None
    assert requests == [f"/pi/logs/{source.name}"]
    assert any("Nano 점화 이벤트가 없는 로그" in str(event) for event in signals.events)


def test_existing_logs_are_not_overwritten_and_export_failure_keeps_h5(tmp_path, monkeypatch):
    runtime, signals, requests, source = setup_runtime(tmp_path)
    directory = runtime.config.logging.directory
    directory.mkdir()
    existing_h5 = directory / source.name
    existing_csv = existing_h5.with_suffix(".csv")
    existing_h5.write_bytes(b"existing HDF5 belongs to user")
    existing_csv.write_text("existing CSV belongs to user")

    def fail(*args):
        raise OSError("CSV disk write failed")

    monkeypatch.setattr(runtime_module, "export_csv", fail)
    asyncio.run(runtime._stop_and_save_session())
    assert existing_h5.read_bytes() == b"existing HDF5 belongs to user"
    assert existing_csv.read_text() == "existing CSV belongs to user"
    saved = [event[1] for event in signals.events if event[0] == "remote_log_downloaded"]
    assert len(saved) == 1 and Path(saved[0]) != existing_h5
    assert Path(saved[0]).read_bytes() == source.read_bytes()
    assert signals.events[-1][0:2] == ("operation_failed", "save")


def test_manual_fetch_uses_selected_file_and_rejects_current_open_log(tmp_path):
    runtime, signals, requests, source = setup_runtime(tmp_path)
    with pytest.raises(RuntimeError, match="측정을 종료"):
        asyncio.run(runtime._fetch_remote_log())
    runtime._session_recording = False
    runtime._session_log_file = "different_session.h5"
    asyncio.run(runtime._fetch_remote_log(source.name))
    assert requests == [f"/pi/logs/{source.name}"]
