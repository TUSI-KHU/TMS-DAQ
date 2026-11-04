#!/usr/bin/env bash
set -euo pipefail
exec timeout -k 2s 30s /opt/tusi-tms/.venv/bin/python -m pi.recovery_probe
