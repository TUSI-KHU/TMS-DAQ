import csv
from datetime import datetime, timezone

import numpy as np

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from laptop.logs import export_csv, list_sessions, read_session_summary
from pi.daq import DaqBlock
from pi.logger import Hdf5SessionLogger, SessionMetadata


def test_log_listing_and_csv_export(tmp_path) -> None:
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 0.5, 0.0),
        pressure=ChannelConfig(1, 0.1, 0.0),
        logging=LoggingConfig(directory=tmp_path),
    )
    start = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    logger = Hdf5SessionLogger(config)
    path = logger.open(SessionMetadata("CSV_TEST", "12345678", start))
    raw = np.column_stack(
        (np.arange(10, dtype=np.uint16), np.arange(10, dtype=np.uint16) + 10)
    )
    logger.append_block(DaqBlock(0, 0, 1000, (0, 1), raw))
    logger.record_event("ignition", 5, receive_time=start)
    logger.close()

    summary = read_session_summary(path)
    assert summary.trigger_sample == 5
    assert list_sessions(tmp_path)[0].test_name == "CSV_TEST"

    csv_path = export_csv(path, tmp_path / "export.csv", chunk_samples=3)
    with csv_path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 10
    assert float(rows[5]["time_s"]) == 0.0
    assert float(rows[2]["thrust_N"]) == 1.0
    assert "thrust_N_lpf" in rows[0]
    assert "pressure_bar_lpf" in rows[0]
