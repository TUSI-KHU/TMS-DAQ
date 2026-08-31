import pytest

from common.pressure import raw_code_to_current_mA, raw_code_to_voltage


def test_usb4704_midscale_is_zero_volts() -> None:
    assert raw_code_to_voltage(8191.5) == pytest.approx(0.0, abs=1e-12)


def test_100_ohm_shunt_maps_4_to_20ma_to_04_to_20v() -> None:
    # The exact ADC codes corresponding to 0.4 V and 2.0 V in the +/-10 V,
    # 14-bit range are used here to check the electrical conversion path.
    code_04v = (0.4 + 10.0) / 20.0 * 16383.0
    code_20v = (2.0 + 10.0) / 20.0 * 16383.0
    assert raw_code_to_current_mA(code_04v, 100.0) == pytest.approx(4.0)
    assert raw_code_to_current_mA(code_20v, 100.0) == pytest.approx(20.0)


def test_invalid_shunt_is_rejected() -> None:
    with pytest.raises(ValueError, match="shunt"):
        raw_code_to_current_mA(9000.0, 0.0)

