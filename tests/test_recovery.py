import threading
import time
from pathlib import Path

import h5py
import numpy as np

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from pi.daq import DaqBlock, DaqError, DaqStopped
from pi.tms_agent import TmsAgent
from pi.usb4704 import Usb4704Probe


class RecoveringDaqSource:
    source_kind = "usb4704"

    def __init__(self) -> None:
        self.sequence = 0
        self.sample_index = 0
        self.failed_once = False
        self.recover_calls = 0
        self.stop_event = threading.Event()

    @property
    def probe_result(self) -> Usb4704Probe:
        return Usb4704Probe(Path("/dev/daq0"), True, "USB-4704, BID#0")

    def probe(self) -> bool:
        return True

    def start(self) -> None:
        self.stop_event.clear()

    def read_block(self) -> DaqBlock:
        if self.stop_event.wait(0.005):
            raise DaqStopped("stopped")
        if self.sequence == 1 and not self.failed_once:
            self.failed_once = True
            raise DaqError("device disconnected")
        raw = np.full((10, 2), self.sequence, dtype=np.int16)
        block = DaqBlock(self.sequence, self.sample_index, 1000, (0, 1), raw)
        self.sequence += 1
        self.sample_index += 10
        return block

    def stop(self) -> None:
        self.stop_event.set()

    def close(self) -> None:
        return None

    def recover(self) -> None:
        self.recover_calls += 1


def test_usb_disconnect_records_gap_and_recovers(tmp_path) -> None:
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1.0, 0.0),
        pressure=ChannelConfig(1, 1.0, 0.0),
        logging=LoggingConfig(directory=tmp_path, ring_buffer_sec=1.0),
    )
    source = RecoveringDaqSource()
    agent = TmsAgent(config, source)
    path = agent.start_session("RECOVERY_TEST")
    deadline = time.monotonic() + 2.0
    while (agent.latest_sample_index or 0) < 29 and time.monotonic() < deadline:
        time.sleep(0.005)
    agent.stop_session()

    assert source.recover_calls == 1
    with h5py.File(path, "r") as data:
        event_types = [row["event_type"].rstrip(b"\0") for row in data["events"]]
        assert b"DATA_GAP" in event_types
        assert any(row["level"].rstrip(b"\0") == b"WARNING" for row in data["health"])
