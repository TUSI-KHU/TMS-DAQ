import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
NETWORK_SCRIPT = PROJECT_ROOT / "scripts" / "provision-tms-wired-network.sh"
RUN_SCRIPT = PROJECT_ROOT / "scripts" / "run-tms-dashboard.sh"


def _network_tools(tmp_path: Path) -> dict[str, str]:
    """Run provisioning against a fresh networkd Pi without touching networking."""
    tools = tmp_path / "bin"
    tools.mkdir()
    scripts = {
        "nmcli": """#!/bin/bash
if [[ "$*" == '-g NAME connection show' ]]; then
    echo TUSI-DAQ-Wired
elif [[ "$1 $2" == 'connection modify' ]]; then
    printf '%s\\n' "$*" >> "$TMS_TEST_NM_LOG"
fi
""",
        "ip": """#!/bin/bash
if [[ "$1" == route ]]; then
    echo '10.47.0.2 dev lo src 10.47.0.1'
else
    echo '2: eth0 inet 10.47.0.2/24 scope global eth0'
fi
""",
        "systemctl": """#!/bin/bash
[[ "$*" != 'is-active --quiet NetworkManager' ]]
""",
        "sudo": """#!/bin/bash
IFS= read -r password
shift 3
exec "$@"
""",
        "sshpass": """#!/bin/bash
[[ ${TMS_TEST_AUTH_FAILURE:-0} == 0 ]] || exit 5
remote_command=${!#}
exec /bin/bash -c "$remote_command"
""",
    }
    for name, contents in scripts.items():
        path = tools / name
        path.write_text(contents, encoding="utf-8")
        path.chmod(0o755)
    return {
        **os.environ,
        "PATH": f"{tools}:{os.environ['PATH']}",
        "TMS_ETH_IFACE": "lo",
        "NMCLI_BIN": str(tools / "nmcli"),
        "SSHPASS_BIN": str(tools / "sshpass"),
        "SSH_BIN": "/bin/true",
        "TMS_TEST_NM_LOG": str(tmp_path / "nmcli.log"),
    }


def test_network_bootstraps_dhcp_and_supports_networkd_pi(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(NETWORK_SCRIPT)],
        env=_network_tools(tmp_path),
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    changes = (tmp_path / "nmcli.log").read_text(encoding="utf-8")
    assert "ipv4.method shared" in changes
    assert "ipv4.shared-dhcp-range 10.47.0.2,10.47.0.2" in changes
    assert "systemd-networkd" in result.stdout
    assert "ready: 10.47.0.1 -> 10.47.0.2 via lo" in result.stderr


def test_network_reports_rejected_password_without_retrying(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(NETWORK_SCRIPT)],
        env={**_network_tools(tmp_path), "TMS_TEST_AUTH_FAILURE": "1"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "password authentication was rejected" in result.stderr


def test_network_configures_usb_ethernet_on_pc(tmp_path: Path) -> None:
    env = _network_tools(tmp_path)
    tools = tmp_path / "bin"
    ip = tools / "ip"
    ip.write_text(ip.read_text().replace("eth0", "enx00e04c3603ee"))
    (tools / "systemctl").write_text("#!/bin/bash\nexit 0\n")
    subprocess.run(
        ["bash", str(NETWORK_SCRIPT)], env=env, capture_output=True,
        text=True, timeout=10, check=True,
    )
    changes = (tmp_path / "nmcli.log").read_text()
    assert "connection.interface-name enx00e04c3603ee" in changes
    assert "connection.interface-name eth0" not in changes


def test_network_provisioner_help_is_non_mutating() -> None:
    result = subprocess.run(
        ["bash", str(NETWORK_SCRIPT), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "10.47.0.1/24" in result.stdout
    assert "10.47.0.2/24" in result.stdout


def test_dashboard_launcher_creates_fixed_operator_config(tmp_path: Path) -> None:
    config_path = tmp_path / "operator-config.yaml"
    result = subprocess.run(
        ["bash", str(RUN_SCRIPT)],
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "TMS_SKIP_NETWORK_SETUP": "1",
            "TMS_DASHBOARD_BIN": "/bin/true",
            "TMS_CONFIG": str(config_path),
        },
    )

    assert result.returncode == 0
    text = config_path.read_text(encoding="utf-8")
    assert "pi_host: 10.47.0.2" in text
    assert "username: tms" in text
    assert "password: tms" in text
    assert oct(config_path.stat().st_mode & 0o777) == "0o600"


def test_local_launcher_needs_no_network_or_ssh(tmp_path: Path) -> None:
    tools = tmp_path / "bin"
    tools.mkdir()
    systemctl = tools / "systemctl"
    systemctl.write_text("#!/bin/sh\nexit 0\n")
    systemctl.chmod(0o755)
    result = subprocess.run(
        ["/bin/bash", str(PROJECT_ROOT / "scripts/run-tms-local.sh"), "--config", "local.yaml"],
        env={**os.environ, "PATH": str(tools), "TMS_LOCAL_PYTHON": "/bin/echo"},
        capture_output=True, text=True, timeout=5, check=True,
    )
    assert result.stdout.strip() == "-m laptop.main --local-daq --config local.yaml"
