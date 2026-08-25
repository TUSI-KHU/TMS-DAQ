import ctypes

import pytest

from pi.usb4704 import (
    IOCTL_AI_SET_CHAN_CFG,
    IOCTL_DEVICE_GET_DESC,
    IOCTL_FAI_SET_BUFFER,
    IOCTL_FAI_SET_PARAM,
    IOCTL_FAI_START,
    IOCTL_FAI_STOP,
    DeviceSharedHead,
    FaiConfig,
    FaiStatus,
    Usb4704BufferedDevice,
)


def test_vendor_abi_layout_and_ioctl_numbers() -> None:
    assert ctypes.sizeof(FaiConfig) == 28
    assert ctypes.sizeof(FaiStatus) == 52
    assert ctypes.sizeof(DeviceSharedHead) == 128
    assert DeviceSharedHead.fai_config.offset == 48
    assert DeviceSharedHead.fai_status.offset == 76
    assert IOCTL_DEVICE_GET_DESC == 0x6101
    assert IOCTL_AI_SET_CHAN_CFG == 0x6201
    assert IOCTL_FAI_SET_PARAM == 0x6205
    assert IOCTL_FAI_SET_BUFFER == 0x6206
    assert IOCTL_FAI_START == 0x6207
    assert IOCTL_FAI_STOP == 0x6208


def test_scan_range_and_buffer_are_block_aligned() -> None:
    device = Usb4704BufferedDevice(
        "/dev/daq0",
        sample_rate=5_000,
        channel_numbers=(1, 3),
        block_frames=50,
        buffer_seconds=5,
    )

    assert device.scan_channels == (1, 2, 3)
    assert device.section_values == 150
    assert device.buffer_values == 75_000


def test_total_scan_rate_is_bounded() -> None:
    with pytest.raises(ValueError, match="47619"):
        Usb4704BufferedDevice(
            "/dev/daq0",
            sample_rate=20_000,
            channel_numbers=(0, 1, 2),
            block_frames=200,
        )


def test_probe_of_missing_device_is_safe(tmp_path) -> None:
    result = Usb4704BufferedDevice.probe(tmp_path / "missing-daq")

    assert not result.available
    assert result.reason
