#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this installer with sudo." >&2
  exit 1
fi

if ! id tms >/dev/null 2>&1; then
  echo "The tms login user does not exist." >&2
  echo "Create it first with: sudo adduser tms" >&2
  exit 1
fi

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PACKAGE_SOURCE=${TMS_PACKAGE_SOURCE:-"${PROJECT_ROOT}"}
INSTALL_ROOT=/opt/tusi-tms
CONFIG_ROOT=/etc/tusi-tms
DATA_ROOT=/var/lib/tusi-tms

if [[ ! -e "${PACKAGE_SOURCE}" ]]; then
  echo "TMS package source does not exist: ${PACKAGE_SOURCE}" >&2
  exit 1
fi

install -d -m 0755 "${INSTALL_ROOT}"
# The unprivileged tms-agent atomically persists fitted AI0/AI1 calibration
# values, so it needs to create a temporary file beside config.yaml.
install -d -o tms -g tms -m 0750 "${CONFIG_ROOT}"
install -d -m 0755 "${INSTALL_ROOT}/bin"
install -d -o tms -g tms -m 0750 "${DATA_ROOT}" "${DATA_ROOT}/logs"

# Ubuntu 22.04 supplies the ARM64 scientific/runtime dependencies through apt.
# Reuse those packages in an isolated application venv so field deployment does
# not require internet access to PyPI. PACKAGE_SOURCE can be a local wheel.
python3 -m venv --system-site-packages "${INSTALL_ROOT}/.venv"
"${INSTALL_ROOT}/.venv/bin/python" -m pip install --no-deps --upgrade --force-reinstall "${PACKAGE_SOURCE}"
"${INSTALL_ROOT}/.venv/bin/python" - <<'PY'
import h5py
import numpy
import serial
import yaml
PY

if [[ ! -f "${CONFIG_ROOT}/config.yaml" ]]; then
  install -o tms -g tms -m 0600 \
    "${PROJECT_ROOT}/config.example.yaml" "${CONFIG_ROOT}/config.yaml"
fi

install -m 0644 "${PROJECT_ROOT}/packaging/tms-agent.service" \
  /etc/systemd/system/tms-agent.service
install -m 0755 "${PROJECT_ROOT}/scripts/reset-usb4704-on-start.sh" \
  "${INSTALL_ROOT}/bin/reset-usb4704-on-start.sh"
install -m 0755 "${PROJECT_ROOT}/scripts/recover-usb4704.sh" \
  "${INSTALL_ROOT}/bin/recover-usb4704.sh"
hub_power_source="${PROJECT_ROOT}/scripts/usb-hub-power-cycle.c"
hub_power_binary="${INSTALL_ROOT}/bin/usb-hub-power-cycle"
if [[ ! -f "${hub_power_source}" ]]; then
  echo "Missing USB hub recovery source: ${hub_power_source}" >&2
  exit 1
fi
if ! command -v gcc >/dev/null 2>&1; then
  echo "gcc is required to build the USB hub recovery helper." >&2
  exit 1
fi
gcc -O2 -Wall -Wextra -std=c11 "${hub_power_source}" -o "${hub_power_binary}"
chmod 0755 "${hub_power_binary}"
install -m 0755 "${PROJECT_ROOT}/scripts/tms-network-failover.sh" \
  "${INSTALL_ROOT}/bin/tms-network-failover.sh"
install -m 0644 "${PROJECT_ROOT}/packaging/tms-network-failover.service" \
  /etc/systemd/system/tms-network-failover.service
usermod -a -G plugdev tms
systemctl daemon-reload
systemctl enable --now tms-network-failover.service
systemctl enable tms-agent.service
systemctl restart tms-agent.service

echo "tms-agent installed. Check with: systemctl status tms-agent.service"
