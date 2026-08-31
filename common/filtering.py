"""Small deterministic filters shared by Pi logging and live telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, pi

import numpy as np
from numpy.typing import NDArray


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
