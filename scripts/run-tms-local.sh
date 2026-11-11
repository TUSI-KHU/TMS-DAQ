#!/usr/bin/env bash
# Standalone DAQ workstation: no Ethernet provisioning or SSH.
set -euo pipefail
runtime_python=${TMS_LOCAL_PYTHON:-/opt/tusi-tms/.venv/bin/python}
if [[ ! -x "$runtime_python" ]]; then
    echo 'Install the local dashboard with scripts/install-local-dashboard.sh first.' >&2
    exit 1
fi
if ! systemctl is-active --quiet tms-agent.service; then
    pkexec /usr/bin/systemctl start tms-agent.service
fi
exec "$runtime_python" -m laptop.main --local-daq "$@"
