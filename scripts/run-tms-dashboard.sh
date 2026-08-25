#!/usr/bin/env bash
# Launch the operator dashboard.  The GUI opens the password SSH tunnel and
# connects to the Pi's local-only tms-agent telemetry service itself.
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
config_path=${TMS_CONFIG:-"$project_root/config.yaml"}
dashboard_bin=${TMS_DASHBOARD_BIN:-"$project_root/dist/TUSI-TMS"}

cd "$project_root"

if [[ ${TMS_SKIP_NETWORK_SETUP:-0} != 1 ]]; then
    "$project_root/scripts/provision-tms-wired-network.sh"
fi

if [[ ! -f "$config_path" ]]; then
    install -D -m 0600 "$project_root/config.example.yaml" "$config_path"
fi

if [[ ! -x "$dashboard_bin" ]]; then
    printf 'Dashboard executable not found: %s\n' "$dashboard_bin" >&2
    printf 'Build it with: ./scripts/build-dashboard.sh\n' >&2
    exit 1
fi

exec "$dashboard_bin" --config "$config_path" "$@"
