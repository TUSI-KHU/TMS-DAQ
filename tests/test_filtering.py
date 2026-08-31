import numpy as np
import pytest

from common.filtering import FirstOrderLowPass


def test_low_pass_starts_at_first_sample_and_reduces_step() -> None:
    filt = FirstOrderLowPass(sample_rate_hz=1_000.0, cutoff_hz=50.0)
    output = filt.apply(np.asarray([0.0, 100.0, 100.0]))
    assert output[0] == pytest.approx(0.0)
    assert 0.0 < output[1] < 100.0
    assert output[1] < output[2] < 100.0


def test_low_pass_resets_after_gap() -> None:
    filt = FirstOrderLowPass(sample_rate_hz=1_000.0, cutoff_hz=50.0)
    filt.apply(np.asarray([10.0, 10.0]))
    output = filt.apply(np.asarray([np.nan, 100.0]))
    assert np.isnan(output[0])
    assert output[1] == pytest.approx(100.0)

