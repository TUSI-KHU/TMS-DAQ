import numpy as np

from common.protocol import TelemetryBlock
from laptop.backend import DashboardBackend
from pi.daq import DaqBlock
from pi.telemetry import TelemetryServer


def test_dashboard_visual_batch_preserves_contiguous_samples() -> None:
    first = TelemetryBlock(
        sequence=7,
        first_sample_index=350,
        sample_rate=5_000,
        channel_names=("thrust_N", "pressure_bar"),
        values=np.asarray(((1.0, 2.0), (3.0, 4.0)), dtype=np.float32),
    )
    second = TelemetryBlock(
        # Sequence carries the final DAQ block number of a batched telemetry
        # frame, so contiguous screen data may advance by more than one.
        sequence=12,
        first_sample_index=352,
        sample_rate=5_000,
        channel_names=("thrust_N", "pressure_bar"),
        values=np.asarray(((5.0, 6.0),), dtype=np.float32),
    )

    assert DashboardBackend._blocks_are_contiguous(first, second)
    merged = DashboardBackend._merge_blocks([first, second])

    assert merged.sequence == 12
    assert merged.first_sample_index == 350
    assert merged.sample_count == 3
    np.testing.assert_allclose(
        merged.values,
        ((1.0, 2.0), (3.0, 4.0), (5.0, 6.0)),
    )


def test_pi_telemetry_batch_preserves_raw_samples_and_detects_gap() -> None:
    first = DaqBlock(
        sequence=3,
        first_sample_index=30,
        sample_rate=1_000,
        channel_numbers=(0, 1),
        raw_samples=np.asarray(((10, 20), (11, 21)), dtype=np.uint16),
    )
    second = DaqBlock(
        sequence=4,
        first_sample_index=32,
        sample_rate=1_000,
        channel_numbers=(0, 1),
        raw_samples=np.asarray(((12, 22),), dtype=np.uint16),
    )
    gap = DaqBlock(
        sequence=6,
        first_sample_index=34,
        sample_rate=1_000,
        channel_numbers=(0, 1),
        raw_samples=np.asarray(((13, 23),), dtype=np.uint16),
    )

    assert TelemetryServer._blocks_are_contiguous(first, second)
    assert not TelemetryServer._blocks_are_contiguous(second, gap)
    merged = TelemetryServer._merge_blocks([first, second])

    assert merged.sequence == 4
    assert merged.first_sample_index == 30
    np.testing.assert_array_equal(
        merged.raw_samples,
        ((10, 20), (11, 21), (12, 22)),
    )
