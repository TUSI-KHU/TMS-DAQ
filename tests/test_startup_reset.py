import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "reset-usb4704-on-start.sh"


def _usb_device(root: Path, name: str, vendor: str, product: str) -> None:
    device = root / name
    device.mkdir(parents=True)
    (device / "idVendor").write_text(f"{vendor}\n", encoding="ascii")
    (device / "idProduct").write_text(f"{product}\n", encoding="ascii")


def test_startup_reset_rebinds_only_usb4704(tmp_path: Path) -> None:
    devices = tmp_path / "devices"
    driver = tmp_path / "usb-driver"
    driver.mkdir()
    (driver / "unbind").touch()
    (driver / "bind").touch()
    _usb_device(devices, "1-1.1", "1809", "4704")
    _usb_device(devices, "1-1.1:1.0", "1809", "4704")
    _usb_device(devices, "1-2", "1234", "5678")
    daq = tmp_path / "daq0"
    daq.touch()

    result = subprocess.run(
        ["bash", str(SCRIPT), str(daq)],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "USB4704_SYSFS_ROOT": str(devices),
            "USB4704_USB_DRIVER_ROOT": str(driver),
            "USB4704_RESET_SETTLE_SECONDS": "0",
            "USB4704_READY_TIMEOUT_SECONDS": "0",
        },
    )

    assert (driver / "unbind").read_text(encoding="ascii") == "1-1.1\n"
    assert (driver / "bind").read_text(encoding="ascii") == "1-1.1\n"
    assert "rebinding USB device 1-1.1" in result.stderr
    assert "1-1.1:1.0" not in result.stderr


def test_startup_reset_allows_service_to_start_without_board(tmp_path: Path) -> None:
    devices = tmp_path / "devices"
    driver = tmp_path / "usb-driver"
    devices.mkdir()
    driver.mkdir()
    (driver / "unbind").touch()
    (driver / "bind").touch()

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "USB4704_SYSFS_ROOT": str(devices),
            "USB4704_USB_DRIVER_ROOT": str(driver),
            "USB4704_RESET_SETTLE_SECONDS": "0",
            "USB4704_READY_TIMEOUT_SECONDS": "0",
        },
    )

    assert "no USB-4704" in result.stderr
