"""Validate user-selected destinations before changing the saved GUI settings."""
from pathlib import Path
from tempfile import NamedTemporaryFile


def prepare_log_directory(value: str | Path) -> Path:
    if not str(value).strip():
        raise ValueError("로그 저장 폴더를 선택하십시오.")
    directory = Path(value).expanduser().resolve()
    directory.mkdir(parents=True, exist_ok=True)
    # A real write probe also catches read-only removable/network volumes.
    with NamedTemporaryFile(dir=directory, prefix=".tms-write-check-") as probe:
        probe.write(b"ok")
        probe.flush()
    return directory
