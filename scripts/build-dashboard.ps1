$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

py -3 -m venv .venv-package
& ".venv-package\Scripts\python.exe" -m pip install --upgrade pip
& ".venv-package\Scripts\python.exe" -m pip install ".[dashboard,package]"
$env:PATH = "$env:SystemRoot\System32;$env:PATH"
& ".venv-package\Scripts\pyinstaller.exe" --clean --noconfirm "packaging\tusi-tms.spec"

Write-Host "Dashboard package created under dist\."
