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
