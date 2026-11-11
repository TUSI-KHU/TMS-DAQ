"""Small deterministic filters shared by Pi logging and live telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, pi

import numpy as np
from numpy.typing import NDArray

DEFAULT_MOVING_WINDOW_SAMPLES = 80


class MovingAverage:
    """Trailing sample mean, retaining history across blocks without zero padding.

    A non-finite value or discontinuous sample index starts a new window.
    Startup uses the available 1..window_samples samples.
    """

    def __init__(self, window_samples: int = DEFAULT_MOVING_WINDOW_SAMPLES) -> None:
        if type(window_samples) is not int or window_samples <= 0:
            raise ValueError("window_samples must be a positive integer")
        self.window_samples = window_samples
        self.reset()

    def reset(self) -> None:
        self._history = np.empty(0, dtype=np.float64)
        self._last_index: int | None = None

    def _finite_segment(self, values: np.ndarray) -> np.ndarray:
        if not len(values):
            return values.copy()
        history_count = len(self._history)
        combined = np.concatenate((self._history, values))
        sums = np.convolve(combined, np.ones(self.window_samples), mode="full")
        counts = np.minimum(np.arange(history_count + 1, len(combined) + 1), self.window_samples)
        result = sums[history_count:len(combined)] / counts
        self._history = combined[-(self.window_samples - 1):].copy() if self.window_samples > 1 else np.empty(0)
        return result

    def apply(self, values: np.ndarray) -> np.ndarray:
        samples = np.asarray(values, dtype=np.float64)
        if samples.ndim != 1:
            raise ValueError("moving-average input must be one-dimensional")
        invalid = np.flatnonzero(~np.isfinite(samples))
        if not len(invalid):
            return self._finite_segment(samples)
        result = samples.copy()
        start = 0
        for end in invalid:
            result[start:end] = self._finite_segment(samples[start:end])
            self._history = np.empty(0, dtype=np.float64)
            start = int(end) + 1
        result[start:] = self._finite_segment(samples[start:])
        return result

    def apply_indexed(self, values: np.ndarray, indices: np.ndarray) -> np.ndarray:
        samples = np.asarray(values, dtype=np.float64)
        indices = np.asarray(indices)
        if samples.ndim != 1 or indices.ndim != 1 or len(samples) != len(indices):
            raise ValueError("values and sample indices must be matching one-dimensional arrays")
        if not len(samples):
            return samples.copy()
        if self._last_index is not None and int(indices[0]) != self._last_index + 1:
            self.reset()
        breaks = np.flatnonzero(indices[1:] != indices[:-1] + 1) + 1
        result = np.empty_like(samples)
        start = 0
        for end in breaks:
            result[start:end] = self.apply(samples[start:end])
            self.reset()
            start = int(end)
        result[start:] = self.apply(samples[start:])
        self._last_index = int(indices[-1])
        return result


@dataclass
class FirstOrderLowPass:
    """A causal one-pole low-pass filter for one calibrated channel."""

    sample_rate_hz: float
    cutoff_hz: float
    enabled: bool = True
    _state: float | None = None

    def __post_init__(self) -> None:
        if not isfinite(self.sample_rate_hz) or self.sample_rate_hz <= 0.0:
            raise ValueError("sample_rate_hz must be greater than zero")
        if not isfinite(self.cutoff_hz) or self.cutoff_hz <= 0.0:
            raise ValueError("cutoff_hz must be greater than zero")
        if self.enabled and self.cutoff_hz >= self.sample_rate_hz / 2.0:
            raise ValueError("cutoff_hz must be below the Nyquist frequency")

    @property
    def alpha(self) -> float:
        # Exact zero-order-hold coefficient; unlike cutoff/fs this remains
        # well behaved when the cutoff is changed in the Setup page.
        return 1.0 - exp(-2.0 * pi * self.cutoff_hz / self.sample_rate_hz)

    def reset(self) -> None:
        self._state = None

    def apply(self, values: NDArray[np.floating] | np.ndarray) -> NDArray[np.float64]:
        samples = np.asarray(values, dtype=np.float64)
        if samples.ndim != 1:
            raise ValueError("low-pass input must be a one-dimensional array")
        if samples.size == 0:
            return samples.copy()
        if not self.enabled:
            return samples.copy()

        filtered = np.empty_like(samples)
        state = self._state
        coefficient = self.alpha
        for index, value in enumerate(samples):
            if not isfinite(float(value)):
                # Do not let a missing sample poison every later sample. The
                # next finite sample starts a fresh state after the gap.
                filtered[index] = value
                state = None
            elif state is None:
                state = float(value)
                filtered[index] = state
            else:
                state += coefficient * (float(value) - state)
                filtered[index] = state
        self._state = state
        return filtered
