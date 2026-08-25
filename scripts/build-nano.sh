#!/usr/bin/env bash
set -euo pipefail

if ! command -v arduino-cli >/dev/null 2>&1; then
  echo "arduino-cli is required. Install it and run: arduino-cli core install arduino:avr" >&2
  exit 1
fi

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
NANO_FQBN=${NANO_FQBN:-arduino:avr:nano:cpu=atmega328old}
NANO_PORT=${NANO_PORT:-}
BUILD_ROOT=$(mktemp -d /tmp/tusi-nano.XXXXXX)

cleanup() {
  case "${BUILD_ROOT}" in
    /tmp/tusi-nano.*) rm -rf -- "${BUILD_ROOT}" ;;
    *) echo "Refusing to remove unexpected build path: ${BUILD_ROOT}" >&2 ;;
  esac
}
trap cleanup EXIT

install -d "${BUILD_ROOT}/nano_trigger"
install -m 0644 "${PROJECT_ROOT}/firmware/nano/nano_trigger.ino" \
  "${BUILD_ROOT}/nano_trigger/nano_trigger.ino"

arduino-cli compile --fqbn "${NANO_FQBN}" "${BUILD_ROOT}/nano_trigger"

if [[ -n "${NANO_PORT}" ]]; then
  if [[ ! -e "${NANO_PORT}" ]]; then
    echo "Nano serial port does not exist: ${NANO_PORT}" >&2
    exit 1
  fi

  arduino-cli upload --fqbn "${NANO_FQBN}" --port "${NANO_PORT}" \
    "${BUILD_ROOT}/nano_trigger"
fi
