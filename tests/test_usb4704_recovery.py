import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "recover-usb4704.sh"


def _tool(directory: Path, name: str, body: str) -> Path:
    path = directory / name
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_recovery_power_cycles_parent_hub_and_restarts_agent(tmp_path: Path) -> None:
    devices = tmp_path / "devices"
    hub = devices / "1-1"
    hub.mkdir(parents=True)
    (hub / "busnum").write_text("1\n", encoding="ascii")
    (hub / "devnum").write_text("2\n", encoding="ascii")
    device = devices / "1-1.1"
    device.mkdir()
    (device / "idVendor").write_text("1809\n", encoding="ascii")
    (device / "idProduct").write_text("4704\n", encoding="ascii")
    (device / "authorized").write_text("1\n", encoding="ascii")
    tools = tmp_path / "tools"
    tools.mkdir()
    calls = tmp_path / "calls"
    daq = tmp_path / "daq0"

    systemctl = _tool(
        tools,
        "systemctl",
        "printf 'systemctl %s\\n' \"$*\" >> \"$CALLS\"\n"
        'if [ "$1" = show ]; then printf "0\\n"; fi\nexit 0',
    )
    modprobe = _tool(
        tools,
        "modprobe",
        "printf 'modprobe %s\\n' \"$*\" >> \"$CALLS\"\nexit 0",
    )
    hub_power = _tool(
        tools,
        "usb-hub-power-cycle",
        "printf 'hub-power %s\\n' \"$*\" >> \"$CALLS\"\n"
        'printf "1\\n" > "$FAKE_AUTH"\ntouch "$FAKE_DAQ"\nexit 0',
    )
    udevadm = _tool(
        tools,
        "udevadm",
        "printf 'udevadm %s\\n' \"$*\" >> \"$CALLS\"\nexit 0",
    )
    startup_reset = _tool(tools, "startup-reset", "exit 0")

    result = subprocess.run(
        ["bash", str(SCRIPT), str(daq)],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "USB4704_SYSFS_ROOT": str(devices),
            "USB4704_SYSTEMCTL_BIN": str(systemctl),
            "USB4704_MODPROBE_BIN": str(modprobe),
            "USB4704_HUB_POWER_CYCLE_BIN": str(hub_power),
            "USB4704_UDEVADM_BIN": str(udevadm),
            "USB4704_STARTUP_RESET_SCRIPT": str(startup_reset),
            "USB4704_RECOVERY_REAUTHORIZE_SETTLE_SECONDS": "0",
            "USB4704_RECOVERY_SETTLE_SECONDS": "0",
            "USB4704_STOP_TIMEOUT_SECONDS": "0",
            "USB4704_POST_POWER_STOP_TIMEOUT_SECONDS": "0",
            "USB4704_RECOVERY_READY_TIMEOUT_SECONDS": "0",
            "CALLS": str(calls),
            "FAKE_DAQ": str(daq),
            "FAKE_AUTH": str(device / "authorized"),
        },
    )

    assert result.returncode == 0, result.stderr
    assert daq.exists()
    assert (device / "authorized").read_text(encoding="ascii") == "1\n"
    logged = calls.read_text(encoding="utf-8")
    assert "systemctl stop --no-block tms-agent.service" in logged
    assert "hub-power /dev/bus/usb/001/002 1 1000" in logged
    assert "modprobe biokernbase" in logged
    assert "modprobe bio4704" in logged
    assert "systemctl start --no-block tms-agent.service" in logged
    assert "systemctl is-active --quiet tms-agent.service" in logged
    assert "usbreset" not in logged.lower()
    assert "RECOVERY_RESULT=DAQ_READY" in result.stderr
