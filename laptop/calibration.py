"""Numerically stable load-cell calibration helpers used by the dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

import numpy as np

STANDARD_GRAVITY_MPS2 = 9.80665
SUPPORTED_REFERENCE_POINT_COUNTS = (2, 3)


class CalibrationError(ValueError):
    """Raised when a set of reference readings cannot produce a calibration."""


@dataclass(frozen=True)
class CalibrationReference:
    """One stable load and the corresponding mean raw AI0 count."""

    mass_g: float
    raw_mean: float
    raw_stddev: float
    sample_count: int

    @property
    def force_N(self) -> float:
        return self.mass_g / 1000.0 * STANDARD_GRAVITY_MPS2


@dataclass(frozen=True)
class LoadCellCalibration:
    """Affine conversion from USB-4704 raw AI0 counts to newtons."""

    scale_N_per_count: float
    offset_N: float
    references: tuple[CalibrationReference, ...]
    residuals_N: tuple[float, ...]
    rmse_N: float
    r_squared: float | None

    def force_for_raw(self, raw_count: float) -> float:
        return raw_count * self.scale_N_per_count + self.offset_N


def fit_load_cell_calibration(
    references: Sequence[CalibrationReference],
) -> LoadCellCalibration:
    """Fit force_N = scale * raw_AI0 + offset from two or three references.

    Two references produce the exact affine calibration.  With three references,
    least squares keeps all measurements and exposes the residual in the UI so
    an unstable placement or a non-linear mechanical fixture is visible.
    """

    points = tuple(references)
    if len(points) not in SUPPORTED_REFERENCE_POINT_COUNTS:
        counts = " or ".join(str(count) for count in SUPPORTED_REFERENCE_POINT_COUNTS)
        raise CalibrationError(f"exactly {counts} reference points are required")

    for index, point in enumerate(points, start=1):
        if not isfinite(point.mass_g) or point.mass_g < 0:
            raise CalibrationError(f"reference {index} has an invalid mass")
        if not isfinite(point.raw_mean):
            raise CalibrationError(f"reference {index} has an invalid AI0 mean")
        if not isfinite(point.raw_stddev) or point.raw_stddev < 0:
            raise CalibrationError(f"reference {index} has an invalid AI0 deviation")
        if point.sample_count <= 0:
            raise CalibrationError(f"reference {index} has no captured samples")

    raw = np.asarray([point.raw_mean for point in points], dtype=np.float64)
    force = np.asarray([point.force_N for point in points], dtype=np.float64)
    if np.unique(raw).size < 2:
        raise CalibrationError("AI0 readings must differ between reference loads")
    if np.unique(force).size < 2:
        raise CalibrationError("reference masses must not all be identical")

    design = np.column_stack((raw, np.ones_like(raw)))
    coefficients, _, rank, _ = np.linalg.lstsq(design, force, rcond=None)
    if rank != 2:
        raise CalibrationError("reference readings do not define a valid line")
    scale, offset = (float(coefficients[0]), float(coefficients[1]))
    if not isfinite(scale) or not isfinite(offset) or np.isclose(scale, 0.0):
        raise CalibrationError("calibration scale is invalid")

    predicted = design @ coefficients
    residuals = force - predicted
    rmse = float(np.sqrt(np.mean(np.square(residuals))))
    force_centered = force - np.mean(force)
    total_sum_squares = float(np.sum(np.square(force_centered)))
    r_squared = (
        None
        if np.isclose(total_sum_squares, 0.0)
        else float(1.0 - np.sum(np.square(residuals)) / total_sum_squares)
    )
    return LoadCellCalibration(
        scale_N_per_count=scale,
        offset_N=offset,
        references=points,
        residuals_N=tuple(float(value) for value in residuals),
        rmse_N=rmse,
        r_squared=r_squared,
    )
