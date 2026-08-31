import pytest

from laptop.calibration import (
    STANDARD_GRAVITY_MPS2,
    CalibrationError,
    CalibrationReference,
    PressureCalibrationReference,
    fit_load_cell_calibration,
    fit_pressure_calibration,
)


def point(mass_g: float, raw_mean: float) -> CalibrationReference:
    return CalibrationReference(
        mass_g=mass_g,
        raw_mean=raw_mean,
        raw_stddev=2.0,
        sample_count=5_000,
    )


def test_two_point_load_cell_calibration_preserves_measurement_direction() -> None:
    # This matches the observed chain: compression makes raw AI0 decrease.
    calibration = fit_load_cell_calibration((point(0.0, 10_239.0), point(3908.0, 10_111.0)))

    assert calibration.scale_N_per_count < 0.0
    assert calibration.force_for_raw(10_239.0) == pytest.approx(0.0)
    assert calibration.force_for_raw(10_111.0) == pytest.approx(
        3.908 * STANDARD_GRAVITY_MPS2
    )
    assert calibration.rmse_N == pytest.approx(0.0)


def test_three_point_load_cell_calibration_uses_least_squares() -> None:
    calibration = fit_load_cell_calibration(
        (
            point(0.0, 1_000.0),
            point(10.0 / STANDARD_GRAVITY_MPS2 * 1000.0, 900.0),
            point(20.0 / STANDARD_GRAVITY_MPS2 * 1000.0, 800.0),
        )
    )

    assert calibration.scale_N_per_count == pytest.approx(-0.1)
    assert calibration.offset_N == pytest.approx(100.0)
    assert calibration.r_squared == pytest.approx(1.0)


def test_calibration_rejects_identical_raw_reference_values() -> None:
    with pytest.raises(CalibrationError, match="AI0 readings"):
        fit_load_cell_calibration((point(0.0, 10_239.0), point(3908.0, 10_239.0)))


def test_pressure_calibration_fits_bar_from_two_points() -> None:
    calibration = fit_pressure_calibration(
        (
            PressureCalibrationReference(0.0, 1000.0, 1.0, 100),
            PressureCalibrationReference(10.0, 3000.0, 1.0, 100),
        )
    )
    assert calibration.scale_bar_per_count == pytest.approx(0.005)
    assert calibration.offset_bar == pytest.approx(-5.0)
    assert calibration.pressure_for_raw(2000.0) == pytest.approx(5.0)


def test_pressure_calibration_rejects_identical_references() -> None:
    with pytest.raises(CalibrationError, match="AI1 readings"):
        fit_pressure_calibration(
            (
                PressureCalibrationReference(0.0, 1000.0, 1.0, 100),
                PressureCalibrationReference(10.0, 1000.0, 1.0, 100),
            )
        )
