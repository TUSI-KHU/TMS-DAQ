#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "${PROJECT_ROOT}"

python3 -m venv .venv-package
.venv-package/bin/python -m pip install --upgrade pip
.venv-package/bin/python -m pip install '.[dashboard,package]'
.venv-package/bin/pyinstaller --clean --noconfirm packaging/tusi-tms.spec

echo "Dashboard package created under dist/."
