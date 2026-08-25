import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "reset-usb4704-on-start.sh"


def _usb_device(root: Path, name: str, vendor: str, product: str) -> Path:
    device = root / name
    device.mkdir(parents=True)
    (device / "idVendor").write_text(f"{vendor}\n", encoding="ascii")
    (device / "idProduct").write_text(f"{product}\n", encoding="ascii")
    return device


def _tool(directory: Path, name: str, body: str = "exit 0") -> Path:
    path = directory / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _environment(
    *, devices: Path, driver: Path, tools: Path, **extra: str
) -> dict[str, str]:
    modprobe = tools / "modprobe"
    udevadm = tools / "udevadm"
    if not modprobe.exists():
        _tool(tools, "modprobe")
    if not udevadm.exists():
        _tool(tools, "udevadm")
    return {
        **os.environ,
        "USB4704_SYSFS_ROOT": str(devices),
        "USB4704_USB_DRIVER_ROOT": str(driver),
        "USB4704_MODPROBE_BIN": str(modprobe),
        "USB4704_UDEVADM_BIN": str(udevadm),
        "USB4704_REAUTHORIZE_SETTLE_SECONDS": "0",
        "USB4704_REBIND_SETTLE_SECONDS": "0",
        "USB4704_READY_TIMEOUT_SECONDS": "0",
        "USB4704_FALLBACK_READY_TIMEOUT_SECONDS": "0",
        **extra,
    }


def test_startup_reset_leaves_healthy_usb4704_untouched(tmp_path: Path) -> None:
    devices = tmp_path / "devices"
    driver = tmp_path / "usb-driver"
    tools = tmp_path / "tools"
    driver.mkdir()
    tools.mkdir()
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
        env=_environment(devices=devices, driver=driver, tools=tools),
    )

    assert (driver / "unbind").read_text(encoding="ascii") == ""
    assert (driver / "bind").read_text(encoding="ascii") == ""
    assert "leaving USB topology untouched" in result.stderr
    assert "1-1.1:1.0" not in result.stderr


def test_startup_reset_allows_service_to_start_without_board(tmp_path: Path) -> None:
    devices = tmp_path / "devices"
    driver = tmp_path / "usb-driver"
    tools = tmp_path / "tools"
    devices.mkdir()
    driver.mkdir()
    tools.mkdir()
    (driver / "unbind").touch()
    (driver / "bind").touch()

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=True,
        capture_output=True,
        text=True,
        env=_environment(devices=devices, driver=driver, tools=tools),
    )

    assert "no USB-4704" in result.stderr


def test_startup_reset_reauthorizes_before_core_rebind(tmp_path: Path) -> None:
    devices = tmp_path / "devices"
    driver = tmp_path / "usb-driver"
    tools = tmp_path / "tools"
    driver.mkdir()
    tools.mkdir()
    (driver / "unbind").touch()
    (driver / "bind").touch()
    device = _usb_device(devices, "1-1.1", "1809", "4704")
    (device / "authorized").write_text("1\n", encoding="ascii")
    daq = tmp_path / "daq0"
    udevadm = _tool(
        tools,
        "udevadm",
        'if [ "$1" = trigger ]; then touch "$FAKE_DAQ"; fi\nexit 0',
    )

    result = subprocess.run(
        ["bash", str(SCRIPT), str(daq)],
        check=True,
        capture_output=True,
        text=True,
        env=_environment(
            devices=devices,
            driver=driver,
            tools=tools,
            USB4704_UDEVADM_BIN=str(udevadm),
            FAKE_DAQ=str(daq),
        ),
    )

    assert daq.exists()
    assert (device / "authorized").read_text(encoding="ascii") == "1\n"
    assert (driver / "unbind").read_text(encoding="ascii") == ""
    assert "attempting non-destructive USB reauthorization" in result.stderr
    assert "last-resort USB core rebind" not in result.stderr


def test_startup_reset_uses_core_rebind_only_as_last_resort(tmp_path: Path) -> None:
    devices = tmp_path / "devices"
    driver = tmp_path / "usb-driver"
    tools = tmp_path / "tools"
    driver.mkdir()
    tools.mkdir()
    (driver / "unbind").touch()
    (driver / "bind").touch()
    device = _usb_device(devices, "1-1.1", "1809", "4704")
    (device / "authorized").write_text("1\n", encoding="ascii")
    daq = tmp_path / "daq0"

    result = subprocess.run(
        ["bash", str(SCRIPT), str(daq)],
        check=True,
        capture_output=True,
        text=True,
        env=_environment(devices=devices, driver=driver, tools=tools),
    )

    assert not daq.exists()
    assert (driver / "unbind").read_text(encoding="ascii") == "1-1.1\n"
    assert (driver / "bind").read_text(encoding="ascii") == "1-1.1\n"
    assert "last-resort USB core rebind" in result.stderr
    assert "usbreset" not in result.stderr.lower()
