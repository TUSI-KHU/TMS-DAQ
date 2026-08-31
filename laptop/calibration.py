"""Numerically stable linear sensor calibration helpers used by the dashboard."""

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


@dataclass(frozen=True)
class PressureCalibrationReference:
    """One stable reference pressure and the corresponding mean raw AI1 count."""

    pressure_bar: float
    raw_mean: float
    raw_stddev: float
    sample_count: int


@dataclass(frozen=True)
class PressureCalibration:
    """Affine conversion from USB-4704 raw AI1 counts to bar."""

    scale_bar_per_count: float
    offset_bar: float
    references: tuple[PressureCalibrationReference, ...]
    residuals_bar: tuple[float, ...]
    rmse_bar: float
    r_squared: float | None

    def pressure_for_raw(self, raw_count: float) -> float:
        return raw_count * self.scale_bar_per_count + self.offset_bar


def _fit_affine(
    *,
    raw: np.ndarray,
    target: np.ndarray,
    raw_label: str,
    target_label: str,
) -> tuple[float, float, tuple[float, ...], float, float | None]:
    # Do not use np.unique here.  In the one-file PyInstaller build it lazily
    # imports numpy.lib._arraysetops_impl on the first calibration, and a
    # damaged/stale archive then surfaces as ``zlib.error: incorrect header
    # check`` instead of a calibration error.  This comparison is sufficient
    # for the rank pre-check and keeps calibration independent of that module.
    raw_values = np.asarray(raw).reshape(-1)
    target_values = np.asarray(target).reshape(-1)
    if raw_values.size < 2 or not bool(np.any(raw_values[1:] != raw_values[0])):
        raise CalibrationError(f"{raw_label} readings must differ")
    if target_values.size < 2 or not bool(
        np.any(target_values[1:] != target_values[0])
    ):
        raise CalibrationError(f"{target_label} references must not all be identical")

    design = np.column_stack((raw, np.ones_like(raw)))
    coefficients, _, rank, _ = np.linalg.lstsq(design, target, rcond=None)
    if rank != 2:
        raise CalibrationError("reference readings do not define a valid line")
    scale, offset = (float(coefficients[0]), float(coefficients[1]))
    if not isfinite(scale) or not isfinite(offset) or np.isclose(scale, 0.0):
        raise CalibrationError("calibration scale is invalid")

    predicted = design @ coefficients
    residuals = target - predicted
    rmse = float(np.sqrt(np.mean(np.square(residuals))))
    target_centered = target - np.mean(target)
    total_sum_squares = float(np.sum(np.square(target_centered)))
    r_squared = (
        None
        if np.isclose(total_sum_squares, 0.0)
        else float(1.0 - np.sum(np.square(residuals)) / total_sum_squares)
    )
    return (
        scale,
        offset,
        tuple(float(value) for value in residuals),
        rmse,
        r_squared,
    )


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
    scale, offset, residuals, rmse, r_squared = _fit_affine(
        raw=raw,
        target=force,
        raw_label="AI0",
        target_label="reference mass",
    )
    return LoadCellCalibration(
        scale_N_per_count=scale,
        offset_N=offset,
        references=points,
        residuals_N=residuals,
        rmse_N=rmse,
        r_squared=r_squared,
    )


def fit_pressure_calibration(
    references: Sequence[PressureCalibrationReference],
) -> PressureCalibration:
    """Fit pressure_bar = scale * raw_AI1 + offset from two or three references."""

    points = tuple(references)
    if len(points) not in SUPPORTED_REFERENCE_POINT_COUNTS:
        counts = " or ".join(str(count) for count in SUPPORTED_REFERENCE_POINT_COUNTS)
        raise CalibrationError(f"exactly {counts} reference points are required")

    for index, point in enumerate(points, start=1):
        if not isfinite(point.pressure_bar):
            raise CalibrationError(f"reference {index} has an invalid pressure")
        if not isfinite(point.raw_mean):
            raise CalibrationError(f"reference {index} has an invalid AI1 mean")
        if not isfinite(point.raw_stddev) or point.raw_stddev < 0:
            raise CalibrationError(f"reference {index} has an invalid AI1 deviation")
        if point.sample_count <= 0:
            raise CalibrationError(f"reference {index} has no captured samples")

    raw = np.asarray([point.raw_mean for point in points], dtype=np.float64)
    pressure = np.asarray([point.pressure_bar for point in points], dtype=np.float64)
    scale, offset, residuals, rmse, r_squared = _fit_affine(
        raw=raw,
        target=pressure,
        raw_label="AI1",
        target_label="reference pressure",
    )
    return PressureCalibration(
        scale_bar_per_count=scale,
        offset_bar=offset,
        references=points,
        residuals_bar=residuals,
        rmse_bar=rmse,
        r_squared=r_squared,
    )
