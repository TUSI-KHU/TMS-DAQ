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

install -d -m 0755 "${INSTALL_ROOT}" "${CONFIG_ROOT}"
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
usermod -a -G plugdev tms
systemctl daemon-reload
systemctl enable tms-agent.service
systemctl restart tms-agent.service

echo "tms-agent installed. Check with: systemctl status tms-agent.service"
