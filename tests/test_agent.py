import json
import threading
import time
from pathlib import Path

import h5py
import pytest

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from pi.daq import SimulatedDaqSource
from pi.tms_agent import AgentState, SessionError, TmsAgent
from pi.usb4704 import Usb4704Probe


class IdleProbeDaqSource:
    """Fails if startup or a status read performs a synchronous USB probe."""

    source_kind = "usb4704"

    def __init__(self) -> None:
        self.probe_calls = 0

    @property
    def probe_result(self) -> Usb4704Probe:
        self.probe_calls += 1
        if self.probe_calls > 1:
            raise AssertionError("status snapshot must not run a USB probe")
        return Usb4704Probe(Path("/dev/daq0"), True, "USB-4704, BID#0")


def test_status_snapshot_uses_cached_usb_health(tmp_path) -> None:
    device = tmp_path / "daq0"
    device.touch()
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10, device=str(device)),
        thrust=ChannelConfig(channel=0, scale=1.0, offset=0.0),
        pressure=ChannelConfig(channel=1, scale=1.0, offset=0.0),
        logging=LoggingConfig(directory=tmp_path),
    )
    source = IdleProbeDaqSource()
    agent = TmsAgent(config, source)
    agent._last_health_refresh = 0.0

    status = agent.status_snapshot()

    assert status["health"]["daq"] == "UNKNOWN"
    assert status["daq_probe"]["reason"] == "hardware probe is deferred until acquisition starts"
    assert source.probe_calls == 0


def test_agent_records_simulated_session_and_single_trigger(tmp_path) -> None:
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(channel=0, scale=1.0, offset=0.0),
        pressure=ChannelConfig(channel=1, scale=1.0, offset=0.0),
        logging=LoggingConfig(
            directory=tmp_path, ring_buffer_sec=1.0, flush_interval_sec=0.01
        ),
    )
    source = SimulatedDaqSource(config.daq, (0, 1), realtime=True)
    agent = TmsAgent(config, source)
    path = agent.start_session("AGENT_TEST")

    deadline = time.monotonic() + 1.0
    while agent.latest_sample_index is None and time.monotonic() < deadline:
        time.sleep(0.005)
    trigger_sample = agent.record_trigger()
    with pytest.raises(SessionError, match="already recorded"):
        agent.record_trigger()
    time.sleep(0.03)
    agent.stop_session()

    assert agent.state == AgentState.COMPLETE
    assert agent.dropped_blocks == 0
    with h5py.File(path, "r") as data:
        assert len(data["samples/sample_index"]) >= 10
        assert len(data["events"]) == 1
        assert data["events"][0]["sample_index"] == trigger_sample


def _recording_agent(tmp_path):
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1.0, 0.0),
        pressure=ChannelConfig(1, 1.0, 0.0),
        logging=LoggingConfig(directory=tmp_path),
    )
    agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1)))
    agent.start_session("NANO_EVENT")
    deadline = time.monotonic() + 1.0
    while agent.latest_sample_index is None and time.monotonic() < deadline:
        time.sleep(0.005)
    assert agent.latest_sample_index is not None
    return agent


def test_nano_trigger_is_persisted_with_identity_and_retry_is_idempotent(tmp_path, monkeypatch):
    agent = _recording_agent(tmp_path)
    kwargs = dict(
        session_id=agent.session_id,
        receive_time="2026-11-04T10:20:30.123+00:00",
        source="nano",
        nano_sequence=7,
        nano_uptime_ms=123456,
    )
    original = agent._logger.record_event
    flushed = []

    def observed_write(*args, **event_kwargs):
        assert args[1] in agent._logger._datasets["sample_index"][:]
        original(*args, **event_kwargs)
        flushed.append(event_kwargs["force_flush"])

    monkeypatch.setattr(agent._logger, "record_event", observed_write)
    try:
        with pytest.raises(SessionError, match="does not match"):
            agent.record_trigger(**{**kwargs, "session_id": "old-session"})
        sample = agent.record_trigger(**kwargs)
        assert flushed == [True]  # ACK only after the write and forced flush.
        time.sleep(0.03)
        assert agent.record_trigger(**kwargs) == sample
        with pytest.raises(SessionError, match="already recorded"):
            agent.record_trigger(**{**kwargs, "nano_sequence": 8})
    finally:
        agent.stop_session()
    with h5py.File(agent.log_path, "r") as data:
        assert len(data["events"]) == 1
        event = data["events"][0]
        assert event["receive_time"].decode() == kwargs["receive_time"]
        assert json.loads(event["details"]) == {
            "source": "nano",
            "session_id": kwargs["session_id"],
            "nano_sequence": 7,
            "nano_uptime_ms": 123456,
            "timing_basis": "pi_latest_sample_on_receipt",
        }


def test_trigger_writer_failure_is_not_acknowledged(tmp_path, monkeypatch):
    agent = _recording_agent(tmp_path)

    def fail_write(*args, **kwargs):
        raise OSError("event storage failed")

    monkeypatch.setattr(agent._logger, "record_event", fail_write)
    with pytest.raises(SessionError, match="trigger was not recorded: event storage failed"):
        agent.record_trigger()
    assert agent.trigger_sample is None
    assert agent.state == AgentState.RECORDING
    with pytest.raises(SessionError, match="background failures"):
        agent.stop_session()
    with h5py.File(agent.log_path, "r") as data:
        assert len(data["events"]) == 0


def test_trigger_rejects_failed_recording(tmp_path):
    agent = _recording_agent(tmp_path)
    agent.health["logger"] = "FAILED"
    try:
        with pytest.raises(SessionError, match="logger is not recording"):
            agent.record_trigger()
        assert agent.trigger_sample is None
    finally:
        agent.stop_session()


def test_pending_nano_trigger_retry_keeps_original_sample(tmp_path, monkeypatch):
    agent = _recording_agent(tmp_path)
    kwargs = dict(
        receive_time="2026-11-04T10:20:30.123+00:00",
        session_id=agent.session_id, source="nano", nano_sequence=1, nano_uptime_ms=5000,
    )
    release = threading.Event()
    original = agent._logger.record_event

    def delayed_write(*args, **event_kwargs):
        assert release.wait(timeout=2)
        original(*args, **event_kwargs)

    monkeypatch.setattr(agent._logger, "record_event", delayed_write)
    monkeypatch.setattr("pi.tms_agent.TRIGGER_WRITE_TIMEOUT_SECONDS", 0.03)
    try:
        with pytest.raises(SessionError, match="awaiting logger confirmation"):
            agent.record_trigger(**kwargs)
        original_sample = agent._pending_trigger.sample_index
        assert agent.trigger_sample is None
        with pytest.raises(SessionError, match="different ignition trigger"):
            agent.record_trigger(**{**kwargs, "nano_sequence": 2})
        release.set()
        monkeypatch.setattr("pi.tms_agent.TRIGGER_WRITE_TIMEOUT_SECONDS", 1.0)
        assert agent.record_trigger(**kwargs) == original_sample
    finally:
        release.set()
        agent.stop_session()
    with h5py.File(agent.log_path, "r") as data:
        assert len(data["events"]) == 1
        assert data["events"][0]["sample_index"] == original_sample


def _nano_state(agent, number, level, **overrides):
    return agent.record_nano_state(**{
        "session_id": agent.session_id,
        "event_id": f"state-{number}",
        "gpio_state": level,
        "nano_sequence": number,
        "nano_uptime_ms": number * 500,
        "receive_time": "2026-11-04T10:20:30.123+00:00",
        **overrides,
    })


def test_nano_continuous_levels_persist_before_and_after_first_edge(tmp_path, monkeypatch):
    agent = _recording_agent(tmp_path)
    writes = []
    original = agent._logger.record_event

    def observed_write(*args, **kwargs):
        assert args[1] in agent._logger._datasets["sample_index"][:]
        original(*args, **kwargs)
        writes.append((args[0], kwargs["force_flush"]))

    monkeypatch.setattr(agent._logger, "record_event", observed_write)
    try:
        # Already-HIGH stays visible, but neither start nor repeated HIGH
        # masquerades as an observed rising edge.
        assert _nano_state(agent, 1, True)["trigger_sample"] is None
        assert _nano_state(agent, 2, True)["trigger_sample"] is None
        assert _nano_state(agent, 3, False)["trigger_sample"] is None
        edge = _nano_state(agent, 4, True)
        assert edge["trigger_sample"] == edge["sample_index"]
        assert agent.state == AgentState.TRIGGERED
        for number, level in ((5, True), (6, False), (7, True)):
            assert _nano_state(agent, number, level)["trigger_sample"] == edge["trigger_sample"]
        assert len(writes) == 8
        assert all(forced for _, forced in writes)
    finally:
        agent.stop_session()
    with h5py.File(agent.log_path, "r") as data:
        states = [row for row in data["events"] if row["event_type"] == b"nano_state"]
        assert [json.loads(row["details"])["gpio_state"] for row in states] == [1, 1, 0, 1, 1, 0, 1]
        assert sum(row["event_type"] == b"ignition" for row in data["events"]) == 1
        assert json.loads(states[0]["details"]) == {
            "source": "nano", "gpio_state": 1, "nano_sequence": 1,
            "nano_uptime_ms": 500, "timing_basis": "pi_latest_sample_on_receipt",
            "valid_for_ms": 2000,
        }


@pytest.mark.parametrize("continuity_break", ["unknown", "expiry", "expired_arrival", "reboot"])
def test_nano_unknown_stale_and_reboot_break_edge_continuity(tmp_path, continuity_break):
    agent = _recording_agent(tmp_path)
    try:
        _nano_state(agent, 1, False)
        overrides = {}
        if continuity_break == "unknown":
            _nano_state(agent, 2, None, nano_sequence=None, nano_uptime_ms=None)
        elif continuity_break == "expiry":
            agent._nano_state_valid_until = time.monotonic() - 1
        elif continuity_break == "expired_arrival":
            overrides["valid_for_ms"] = 0
        else:
            overrides["nano_uptime_ms"] = 10
        assert _nano_state(agent, 3, True, **overrides)["trigger_sample"] is None
        assert agent.trigger_sample is None
        _nano_state(agent, 4, False)
        assert _nano_state(agent, 5, True)["trigger_sample"] is not None
    finally:
        agent.stop_session()


def test_nano_state_deduplicates_retries_and_rejects_old_sessions(tmp_path, monkeypatch):
    agent = _recording_agent(tmp_path)
    try:
        first = _nano_state(agent, 1, True)
        assert _nano_state(agent, 1, True) == first
        with pytest.raises(SessionError, match="reused"):
            _nano_state(agent, 1, False)
        with pytest.raises(SessionError, match="does not match"):
            _nano_state(agent, 2, False, session_id="old-session")
        monkeypatch.setattr("pi.tms_agent.NANO_STATE_RECEIPT_CACHE_SIZE", 2)
        _nano_state(agent, 2, True)
        _nano_state(agent, 3, True)
        assert len(agent._nano_state_receipts) == 2
    finally:
        agent.stop_session()
    with pytest.raises(SessionError, match="cannot record Nano state"):
        _nano_state(agent, 3, True)
    with h5py.File(agent.log_path, "r") as data:
        assert len(data["events"]) == 3


def test_pending_nano_state_retry_does_not_duplicate_event_or_edge(tmp_path, monkeypatch):
    agent = _recording_agent(tmp_path)
    _nano_state(agent, 1, False)
    release = threading.Event()
    original = agent._logger.record_event

    def delayed_write(*args, **kwargs):
        assert release.wait(timeout=2)
        original(*args, **kwargs)

    monkeypatch.setattr(agent._logger, "record_event", delayed_write)
    monkeypatch.setattr("pi.tms_agent.TRIGGER_WRITE_TIMEOUT_SECONDS", 0.03)
    try:
        with pytest.raises(SessionError, match="awaiting logger confirmation"):
            _nano_state(agent, 2, True)
        sample = agent._pending_nano_state.event.sample_index
        assert agent.trigger_sample is None
        with pytest.raises(SessionError, match="different Nano state"):
            _nano_state(agent, 3, True)
        with pytest.raises(SessionError, match="reused"):
            _nano_state(agent, 2, False)
        release.set()
        monkeypatch.setattr("pi.tms_agent.TRIGGER_WRITE_TIMEOUT_SECONDS", 1.0)
        assert _nano_state(agent, 2, True) == {"sample_index": sample, "trigger_sample": sample}
        assert _nano_state(agent, 2, True) == {"sample_index": sample, "trigger_sample": sample}
    finally:
        release.set()
        agent.stop_session()
    with h5py.File(agent.log_path, "r") as data:
        assert [row["event_type"] for row in data["events"]] == [b"nano_state", b"nano_state", b"ignition"]


@pytest.mark.parametrize("fail_event_type", ["nano_state", "ignition"])
def test_nano_state_writer_failure_is_not_acknowledged(tmp_path, monkeypatch, fail_event_type):
    agent = _recording_agent(tmp_path)
    _nano_state(agent, 1, False)
    original = agent._logger.record_event

    def fail_write(*args, **kwargs):
        if args[0] == fail_event_type:
            raise OSError("Nano event storage failed")
        original(*args, **kwargs)

    monkeypatch.setattr(agent._logger, "record_event", fail_write)
    with pytest.raises(SessionError, match="Nano state was not recorded"):
        _nano_state(agent, 2, True)
    assert agent.trigger_sample is None
    with pytest.raises(SessionError, match="background failures"):
        agent.stop_session()


def test_nano_state_waits_for_first_queued_daq_block(tmp_path):
    agent = _recording_agent(tmp_path)
    agent._stop_event.set()
    agent._acquisition_thread.join(timeout=1)
    agent._stop_event.clear()
    agent._latest_queued_sample_index = None
    try:
        with pytest.raises(SessionError, match="before the first DAQ block"):
            _nano_state(agent, 1, True)
    finally:
        agent.stop_session()
