import csv
import json
from datetime import datetime, timezone

import h5py
import numpy as np
import pytest

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from laptop.logs import LogError, export_csv, list_sessions, read_session_summary
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
    assert rows[5]["ignition"] == "1"
    assert sum(int(row["ignition"]) for row in rows) == 1
    assert rows[5]["ignition_source"] == "unknown"  # Legacy event, not assumed Nano.
    assert rows[5]["nano_uptime_ms"] == ""
    assert rows[0]["ignition_recorded"] == "1"
    assert rows[0]["time_reference"] == "ignition_receipt"
    assert all(row["nano_gpio"] == "" for row in rows)
    assert all(row["nano_gpio_valid"] == "0" for row in rows)
    assert all(row["nano_gpio_observed"] == "0" for row in rows)


@pytest.mark.parametrize("trigger_sample", [None, 0, 5])
def test_csv_explicit_nano_event_and_no_trigger(tmp_path, trigger_sample):
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
        logging=LoggingConfig(directory=tmp_path),
    )
    logger = Hdf5SessionLogger(config)
    received = "2026-11-04T01:02:03.456+00:00"
    path = logger.open(SessionMetadata("NANO_CSV", "12345678", received))
    logger.append_block(DaqBlock(0, 0, 1000, (0, 1), np.ones((10, 2), dtype=np.uint16)))
    if trigger_sample is not None:
        logger.record_event("ignition", trigger_sample, receive_time=received, details=json.dumps({
            "source": "nano", "session_id": "12345678", "nano_sequence": 123,
            "nano_uptime_ms": 45678, "timing_basis": "pi_latest_sample_on_receipt",
        }))
    logger.close()
    csv_path = export_csv(path, tmp_path / "export.csv", chunk_samples=2)
    with csv_path.open(newline="") as source:
        rows = list(csv.DictReader(source))
    marked = [row for row in rows if row["ignition"] == "1"]
    if trigger_sample is None:
        assert not marked
        assert all(row["ignition_recorded"] == "0" for row in rows)
        assert all(row["ignition_source"] == "" for row in rows)
        assert all(row["time_reference"] == "acquisition_start" for row in rows)
        assert rows[0]["time_s"] == "0.0"
    else:
        assert len(marked) == 1
        event = marked[0]
        assert int(event["sample_index"]) == trigger_sample
        assert float(event["time_s"]) == 0
        assert float(event["acquisition_time_s"]) == trigger_sample / 1000
        assert event["ignition_source"] == "nano"
        assert event["ignition_receive_time_utc"] == received
        assert event["nano_sequence"] == "123"
        assert event["nano_uptime_ms"] == "45678"
        assert event["ignition_timing_basis"] == "pi_latest_sample_on_receipt"
        assert float(rows[0]["time_s"]) == -trigger_sample / 1000


def test_missing_ignition_sample_does_not_replace_existing_csv(tmp_path):
    config = TmsConfig(daq=DaqConfig(sample_rate=1000, block_ms=10),
                       thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
                       logging=LoggingConfig(directory=tmp_path))
    logger = Hdf5SessionLogger(config)
    path = logger.open(SessionMetadata("MISSING", "12345678", "2026-11-04"))
    logger.record_event("ignition", 7)
    logger.close()
    destination = tmp_path / "preserve.csv"
    destination.write_text("original CSV\n")
    with pytest.raises(LogError, match="ignition sample is missing"):
        export_csv(path, destination)
    assert destination.read_text() == "original CSV\n"
    assert list(tmp_path.glob("*.tmp")) == []
    with h5py.File(path, "r") as data:
        assert len(data["events"]) == 1
    with pytest.raises(LogError, match="original HDF5"):
        export_csv(path, path)
    with h5py.File(path, "r") as data:
        assert len(data["events"]) == 1


def _state_details(state, valid_for_ms=2000, **overrides):
    return json.dumps({
        "source": "nano", "gpio_state": state, "nano_sequence": 1,
        "nano_uptime_ms": 500, "timing_basis": "pi_latest_sample_on_receipt",
        "valid_for_ms": valid_for_ms, **overrides,
    })


def _state_csv(tmp_path, states, *, count=12, chunk_samples=3, ignition=None):
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
        logging=LoggingConfig(directory=tmp_path),
    )
    logger = Hdf5SessionLogger(config)
    path = logger.open(SessionMetadata("NANO_STATE_CSV", "12345678", "2026-11-04"))
    logger.append_block(DaqBlock(0, 0, 1000, (0, 1), np.ones((count, 2), dtype=np.uint16)))
    for index, details in states:
        logger.record_event("nano_state", index, details=details)
    if ignition is not None:
        logger.record_event("ignition", ignition, details=json.dumps({"source": "nano"}))
    logger.close()
    with h5py.File(path, "r") as data:
        original_events = data["events"][:]
    output = export_csv(path, tmp_path / "export.csv", chunk_samples=chunk_samples)
    with h5py.File(path, "r") as data:
        np.testing.assert_array_equal(original_events, data["events"][:])
    with output.open(newline="") as source:
        return list(csv.DictReader(source))


@pytest.mark.parametrize("chunk_samples", [1, 3, 100])
def test_initial_high_is_continuous_state_not_ignition(tmp_path, chunk_samples):
    rows = _state_csv(tmp_path, [
        (2, _state_details(1, 5)), (6, _state_details(1, 5)),
    ], chunk_samples=chunk_samples)
    assert [row["nano_gpio"] for row in rows] == ["", ""] + ["1"] * 9 + [""]
    assert [int(row["nano_gpio_valid"]) for row in rows] == [0, 0] + [1] * 9 + [0]
    assert [i for i, row in enumerate(rows) if row["nano_gpio_observed"] == "1"] == [2, 6]
    assert all(row["ignition_recorded"] == "0" for row in rows)
    assert all(row["ignition"] == "0" for row in rows)
    assert rows[0]["time_s"] == "0.0"


def test_low_high_state_keeps_separate_recorded_ignition_origin(tmp_path):
    rows = _state_csv(tmp_path, [
        (1, _state_details(0)), (5, _state_details(1)), (9, _state_details(1)),
    ], ignition=5)
    assert [row["nano_gpio"] for row in rows] == [""] + ["0"] * 4 + ["1"] * 7
    assert [i for i, row in enumerate(rows) if row["ignition"] == "1"] == [5]
    assert rows[5]["time_s"] == "0.0"
    assert rows[0]["time_s"] == "-0.005"
    assert all(row["ignition_recorded"] == "1" for row in rows)


def test_state_expiry_and_unknown_break_do_not_become_low(tmp_path):
    rows = _state_csv(tmp_path, [
        (1, _state_details(1, 2)), (5, _state_details(0)),
        (7, _state_details(-1, 0)), (10, _state_details(1, 1)),
    ])
    assert [row["nano_gpio"] for row in rows] == ["", "1", "1", "", "", "0", "0", "", "", "", "1", ""]
    assert rows[7]["nano_gpio_valid"] == "0"
    assert rows[7]["nano_gpio_observed"] == "1"


@pytest.mark.parametrize("last_state", [0, 1, -1])
def test_last_state_at_same_sample_index_wins(tmp_path, last_state):
    rows = _state_csv(tmp_path, [
        (1, _state_details(1)), (3, _state_details(1)),
        (3, _state_details(0)), (3, _state_details(last_state)),
    ])
    assert [i for i, row in enumerate(rows) if row["nano_gpio_observed"] == "1"] == [1, 3]
    expected = "" if last_state == -1 else str(last_state)
    assert all(row["nano_gpio"] == expected for row in rows[3:])


@pytest.mark.parametrize("malformed", [
    "{bad JSON", "[]", "null", "42",
    _state_details("1"), _state_details(True), _state_details(2),
    _state_details(1, -1), _state_details(1, 2001), _state_details(1, "500"),
    _state_details(1, True), _state_details(1, float("nan")),
    _state_details(1, source="unknown"), _state_details(1, timing_basis="unknown"),
    _state_details(1, nano_sequence="broken"), _state_details(1, nano_uptime_ms=-1),
    json.dumps({"gpio_state": 1}),
])
def test_invalid_state_metadata_breaks_previous_high(tmp_path, malformed):
    rows = _state_csv(tmp_path, [(0, _state_details(1)), (4, malformed)])
    assert all(row["nano_gpio"] == "1" for row in rows[:4])
    assert all(row["nano_gpio"] == "" for row in rows[4:])
    assert all(row["nano_gpio_valid"] == "0" for row in rows[4:])
    assert rows[4]["nano_gpio_observed"] == "1"


def test_heartbeat_event_stream_crosses_hdf_read_chunks(tmp_path):
    rows = _state_csv(tmp_path, [
        (i, _state_details(i % 2, 1)) for i in range(1050)
    ], count=1052, chunk_samples=37)
    assert all(row["nano_gpio"] == str(i % 2) for i, row in enumerate(rows[:1050]))
    assert all(row["nano_gpio_observed"] == "1" for row in rows[:1050])
    assert all(row["nano_gpio"] == "" for row in rows[1050:])
