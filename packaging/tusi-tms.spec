import os
from pathlib import Path


project_root = Path(SPECPATH).parent
runtime_binaries = []
platform_excludes = ["serial.tools.list_ports_osx"]
if os.name == "nt":
    system_directory = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32"
    runtime_binaries = [
        (str(system_directory / name), ".")
        for name in ("msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll")
        if (system_directory / name).exists()
    ]
    platform_excludes.extend(
        ["serial.serialposix", "serial.tools.list_ports_linux"]
    )
else:
    platform_excludes.extend(
        ["serial.serialwin32", "serial.tools.list_ports_windows"]
    )

analysis = Analysis(
    [str(project_root / "laptop" / "main.py")],
    pathex=[str(project_root)],
    binaries=runtime_binaries,
    datas=[(str(project_root / "config.example.yaml"), ".")],
    hiddenimports=["asyncssh", "serial", "h5py", "pyqtgraph"],
    hookspath=[],
    runtime_hooks=[],
    excludes=platform_excludes,
    noarchive=False,
)
pyz = PYZ(analysis.pure)
executable = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="TUSI-TMS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
