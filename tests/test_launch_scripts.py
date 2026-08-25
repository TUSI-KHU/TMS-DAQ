import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
NETWORK_SCRIPT = PROJECT_ROOT / "scripts" / "provision-tms-wired-network.sh"
RUN_SCRIPT = PROJECT_ROOT / "scripts" / "run-tms-dashboard.sh"


def test_network_provisioner_help_is_non_mutating() -> None:
    result = subprocess.run(
        ["bash", str(NETWORK_SCRIPT), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "192.168.0.213/24" in result.stdout
    assert "192.168.0.214/24" in result.stdout


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
    assert "pi_host: 192.168.0.214" in text
    assert "username: tms" in text
    assert "password: tms" in text
    assert oct(config_path.stat().st_mode & 0o777) == "0o600"
