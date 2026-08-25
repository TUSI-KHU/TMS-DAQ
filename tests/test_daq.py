from pathlib import Path

import numpy as np

from common.config import DaqConfig
from pi.daq import SimulatedDaqSource, Usb4704DaqSource
from pi.usb4704 import Usb4704Probe


def test_simulated_daq_produces_contiguous_blocks() -> None:
    source = SimulatedDaqSource(
        DaqConfig(sample_rate=1000, block_ms=10), (0, 1), realtime=False
    )
    source.start()
    first = source.read_block()
    second = source.read_block()
    source.stop()

    assert first.sequence == 0
    assert first.first_sample_index == 0
    assert first.raw_samples.shape == (10, 2)
    assert first.raw_samples.dtype == np.uint16
    assert second.sequence == 1
    assert second.first_sample_index == 10


def test_usb4704_source_reports_probe_result(monkeypatch) -> None:
    expected = Usb4704Probe(
        path=Path(DaqConfig().device),
        available=True,
        description="USB-4704, BID#0",
    )
    monkeypatch.setattr("pi.daq.Usb4704BufferedDevice.probe", lambda _device: expected)
    source = Usb4704DaqSource(DaqConfig(), (0, 1))

    assert source.probe()
    assert source.probe_result == expected
