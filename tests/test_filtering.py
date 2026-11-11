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



def test_moving_average_80_exact_across_50_sample_blocks():
    from common.filtering import MovingAverage
    values = np.arange(230, dtype=float)
    expected = np.array([values[max(0, i-79):i+1].mean() for i in range(len(values))])
    filt = MovingAverage()
    actual = np.concatenate([filt.apply(values[i:i+50]) for i in range(0, len(values), 50)])
    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-12)
    assert actual[79] == 39.5
    assert actual[80] == 40.5


def test_moving_average_gap_nonfinite_and_reset():
    from common.filtering import MovingAverage
    filt = MovingAverage()
    assert filt.apply_indexed(np.array([2., 4., 100., 200.]), np.array([0, 1, 4, 5])).tolist() == [2., 3., 100., 150.]
    assert filt.apply_indexed(np.array([10.]), np.array([10])).tolist() == [10.]
    values = filt.apply(np.array([np.nan, 20., 40.]))
    assert np.isnan(values[0])
    np.testing.assert_equal(values[1:], [20., 30.])
    filt.reset()
    assert filt.apply(np.array([80.])).tolist() == [80.]


@pytest.mark.parametrize('window', [0, -1, 1.5, True])
def test_moving_average_rejects_invalid_window(window):
    from common.filtering import MovingAverage
    with pytest.raises(ValueError):
        MovingAverage(window)
