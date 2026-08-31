#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${PROJECT_ROOT}"

# Reuse an existing environment.  Some packaged workspaces carry the venv
# activation templates read-only; recreating the environment would fail before
# the actual dashboard build even though its Python/dependencies are usable.
if [[ ! -x .venv-package/bin/python ]]; then
    python3 -m venv .venv-package
fi
.venv-package/bin/python -m pip install --upgrade pip
.venv-package/bin/python -m pip install '.[dashboard,package]'
.venv-package/bin/pyinstaller --clean --noconfirm packaging/tusi-tms.spec

# Exercise the same frozen import path used when the calibration dialog first
# calls NumPy, so a damaged one-file archive is caught during the build.
dist/TUSI-TMS --self-test

echo "Dashboard package created under dist/."
