#!/usr/bin/env bash
# Install on an already provisioned DAQ PC. Existing agent config is preserved.
set -euo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python=/opt/tusi-tms/.venv/bin/python
[[ -x "$python" && -f /etc/tusi-tms/config.yaml ]] || {
    echo 'Install the DAQ driver and tms-agent before installing the local dashboard.' >&2
    exit 1
}
"$python" -m pip install --upgrade 'pip>=23' 'setuptools>=68' wheel
# Upgrade the NumPy/HDF5 pair together: apt's old h5py binary cannot load
# against NumPy 2 pulled in by current pyqtgraph.
"$python" -m pip install --upgrade 'numpy>=1.25' 'h5py>=3.11'
"$python" -m pip install --no-build-isolation "$project_root[dashboard]"
"$python" -c 'from PySide6.QtWidgets import QApplication; import h5py, asyncssh, pyqtgraph'
install -m 0755 "$project_root/scripts/run-tms-local.sh" /usr/local/bin/tusi-tms-local
install -m 0644 "$project_root/packaging/tusi-tms-local.desktop" /usr/share/applications/tusi-tms-local.desktop
# USB Nano access is local in standalone mode.
usermod -a -G dialout,plugdev tms
systemctl enable tms-agent.service
printf 'Installed: launch TUSI TMS (Local DAQ) from Applications or run tusi-tms-local.\n'
