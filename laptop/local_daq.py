"""Local file/maintenance operations for the standalone DAQ workstation."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from laptop.ssh_client import SshCommandError


class LocalDaqAccess:
    is_local = True
    connected = False  # No SSH connection is needed or implied.

    def __init__(self, log_directory: Path) -> None:
        self.log_directory = Path(log_directory).resolve()

    async def disconnect(self) -> None:
        pass

    def _source(self, path: str) -> Path:
        source = Path(path).resolve()
        if source.parent != self.log_directory or source.suffix != '.h5':
            raise ValueError('DAQ 로그 디렉터리의 HDF5 파일만 읽을 수 있습니다.')
        return source

    async def download_file(self, remote_path: str, local_path: Path) -> Path:
        source = self._source(remote_path)
        await asyncio.to_thread(shutil.copyfile, source, local_path)
        return local_path

    async def list_remote_logs(self, remote_directory: str) -> list[str]:
        if Path(remote_directory).resolve() != self.log_directory:
            raise ValueError('DAQ 로그 디렉터리가 일치하지 않습니다.')
        def listing():
            return [p.name for p in sorted(self.log_directory.glob('*.h5'),
                    key=lambda p: (p.stat().st_mtime, p.name))
                    if p.is_file() and p.resolve().parent == self.log_directory]
        return await asyncio.to_thread(listing)

    async def recover_usb4704(self, *, timeout: float = 120.0) -> dict[str, object]:
        # Authenticate through the desktop's Polkit dialog, never run the GUI as root.
        process = await asyncio.create_subprocess_exec(
            'pkexec', '/opt/tusi-tms/bin/recover-usb4704.sh', '/dev/daq0',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        try:
            output, _ = await asyncio.wait_for(process.communicate(), timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                process.terminate()
            await process.wait()
            raise
        details = output.decode(errors='replace').strip()
        if process.returncode in (0, 3, 6):
            return {'daq_ready': process.returncode == 0, 'details': details}
        raise SshCommandError(f'로컬 DAQ 초기화 실패 또는 인증 취소: {details}')
