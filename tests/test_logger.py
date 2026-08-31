from datetime import datetime, timezone

import h5py
import numpy as np
import json

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from pi.daq import DaqBlock
from pi.logger import Hdf5SessionLogger, SessionMetadata


def make_config(tmp_path) -> TmsConfig:
    return TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(channel=0, scale=0.5, offset=-1.0),
        pressure=ChannelConfig(channel=1, scale=0.1, offset=2.0),
        logging=LoggingConfig(
            directory=tmp_path, ring_buffer_sec=1.0, flush_interval_sec=0.01
        ),
    )


def make_block(sequence: int, first_sample: int) -> DaqBlock:
    raw = np.column_stack(
        (
            np.arange(10, dtype=np.uint16) + 100,
            np.arange(10, dtype=np.uint16) + 200,
        )
    )
    return DaqBlock(sequence, first_sample, 1000, (0, 1), raw)


def test_hdf5_logger_writes_samples_calibration_and_trigger(tmp_path) -> None:
    logger = Hdf5SessionLogger(make_config(tmp_path))
    start_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    path = logger.open(SessionMetadata("KNSB TEST 001", "abc12345", start_time))
    logger.append_block(make_block(0, 0))
    logger.record_event("ignition", 8, receive_time=start_time)
    logger.close()

    with h5py.File(path, "r") as data:
        assert data["metadata"].attrs["test_name"] == "KNSB TEST 001"
        assert data["metadata"].attrs["sample_count"] == 10
        sensor_calibration = json.loads(data["metadata"].attrs["sensor_calibration"])
        assert sensor_calibration["pressure_input"]["shunt_ohms"] == 100.0
        np.testing.assert_array_equal(data["samples/raw_thrust"][:3], [100, 101, 102])
        np.testing.assert_allclose(data["samples/thrust_N"][:3], [49.0, 49.5, 50.0])
        assert "thrust_N_lpf" in data["samples"]
        assert "pressure_bar_lpf" in data["samples"]
        assert data["samples/thrust_N_lpf"][1] < data["samples/thrust_N"][1]
        assert data["events"][0]["event_type"] == b"ignition"
        assert data["events"][0]["sample_index"] == 8


def test_hdf5_logger_records_data_gap(tmp_path) -> None:
    logger = Hdf5SessionLogger(make_config(tmp_path))
    start_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    path = logger.open(SessionMetadata("GAP_TEST", "def67890", start_time))
    logger.append_block(make_block(0, 0))
    logger.append_block(make_block(2, 20))
    logger.close()

    with h5py.File(path, "r") as data:
        assert data["events"][0]["event_type"] == b"DATA_GAP"
        assert data["events"][0]["sample_index"] == 20
        assert b"expected_sample=10" in data["events"][0]["details"]
