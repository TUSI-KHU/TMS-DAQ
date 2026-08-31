"""Electrical conversion helpers for the fixed USB-4704 AI1 pressure input."""

from __future__ import annotations

from math import isfinite


# USB-4704 AI1 is configured by the driver for the single-ended +/-10 V range.
# The driver exposes calibrated 14-bit codes (0..0x3fff), with mid-scale at 0 V.
USB4704_AI_CODE_MIN = 0.0
USB4704_AI_CODE_MAX = 16_383.0
USB4704_AI_RANGE_MIN_V = -10.0
USB4704_AI_RANGE_MAX_V = 10.0


def raw_code_to_voltage(raw_code: float) -> float:
    """Convert a USB-4704 calibrated 14-bit AI code to volts."""

    code = float(raw_code)
    if not isfinite(code):
        raise ValueError("raw AI code must be finite")
    return USB4704_AI_RANGE_MIN_V + (
        (code - USB4704_AI_CODE_MIN)
        / (USB4704_AI_CODE_MAX - USB4704_AI_CODE_MIN)
        * (USB4704_AI_RANGE_MAX_V - USB4704_AI_RANGE_MIN_V)
    )


def raw_code_to_current_mA(raw_code: float, shunt_ohms: float = 100.0) -> float:
    """Convert a calibrated AI code across the shunt to loop current in mA."""

    resistance = float(shunt_ohms)
    if not isfinite(resistance) or resistance <= 0.0:
        raise ValueError("shunt resistance must be greater than zero")
    return raw_code_to_voltage(raw_code) / resistance * 1000.0

