from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from enum import Enum
from pathlib import Path, PurePosixPath

import asyncssh

from common.config import SshConfig, SystemConfig


class SshFailureKind(str, Enum):
    AUTHENTICATION = "AUTHENTICATION"
    TIMEOUT = "TIMEOUT"
    NETWORK = "NETWORK"
    TUNNEL = "TUNNEL"


class SshConnectionError(RuntimeError):
    def __init__(self, kind: SshFailureKind, message: str) -> None:
        self.kind = kind
        super().__init__(message)


StatusCallback = Callable[[str], None]


class SshTunnelManager:
    """Password-only SSH connection and local telemetry port forward."""

    def __init__(
        self,
        system: SystemConfig,
        ssh: SshConfig,
        *,
        status_callback: StatusCallback | None = None,
    ) -> None:
        self.system = system
        self.ssh = ssh
        self.status_callback = status_callback
        self._connection: asyncssh.SSHClientConnection | None = None
        self._listener: asyncssh.SSHListener | None = None
        self._local_port: int | None = None

    @property
    def connected(self) -> bool:
        return self._connection is not None and not self._connection.is_closed()

    @property
    def local_port(self) -> int:
        if self._local_port is None:
            raise SshConnectionError(
                SshFailureKind.TUNNEL, "SSH telemetry tunnel is not open"
            )
        return self._local_port

    async def connect(self) -> int:
        await self.disconnect()
        self._status("CONNECTING")
        try:
            self._connection = await asyncssh.connect(
                self.system.pi_host,
                port=self.ssh.port,
                username=self.ssh.username,
                password=self.ssh.password,
                client_keys=[],
                agent_path=None,
                preferred_auth=("password", "keyboard-interactive"),
                known_hosts=None,
                config=None,
                connect_timeout=self.ssh.connect_timeout_sec,
                login_timeout=self.ssh.connect_timeout_sec,
                keepalive_interval=self.ssh.keepalive_interval_sec,
                keepalive_count_max=3,
            )
        except asyncssh.PermissionDenied as exc:
            self._status("AUTHENTICATION_FAILED")
            raise SshConnectionError(
                SshFailureKind.AUTHENTICATION,
                "SSH ID 또는 Password를 확인하십시오.",
            ) from exc
        except (asyncio.TimeoutError, TimeoutError) as exc:
            self._status("TIMEOUT")
            raise SshConnectionError(
                SshFailureKind.TIMEOUT, "Raspberry Pi SSH 연결 시간이 초과되었습니다."
            ) from exc
        except (OSError, asyncssh.Error) as exc:
            self._status("DISCONNECTED")
            raise SshConnectionError(
                SshFailureKind.NETWORK,
                "Raspberry Pi에 SSH로 연결할 수 없습니다.",
            ) from exc

        try:
            self._listener = await self._connection.forward_local_port(
                "127.0.0.1",
                0,
                "127.0.0.1",
                self.system.telemetry_port,
            )
            self._local_port = self._listener.get_port()
        except (OSError, asyncssh.Error) as exc:
            await self.disconnect()
            self._status("TUNNEL_FAILED")
            raise SshConnectionError(
                SshFailureKind.TUNNEL, "SSH telemetry tunnel을 만들 수 없습니다."
            ) from exc

        self._status("CONNECTED")
        return self.local_port

    async def disconnect(self) -> None:
        if self._listener is not None:
            self._listener.close()
            await self._listener.wait_closed()
        self._listener = None
        self._local_port = None
        if self._connection is not None:
            self._connection.close()
            await self._connection.wait_closed()
        self._connection = None
        self._status("DISCONNECTED")

    async def reconnect_until(
        self,
        stop_event: asyncio.Event,
        on_connected: Callable[[int], Awaitable[None]],
    ) -> None:
        delays = (1.0, 2.0, 5.0, 10.0)
        attempt = 0
        while not stop_event.is_set():
            self._status("RECONNECTING")
            try:
                port = await self.connect()
                await on_connected(port)
                return
            except SshConnectionError as exc:
                if exc.kind == SshFailureKind.AUTHENTICATION:
                    raise
                delay = delays[min(attempt, len(delays) - 1)]
                attempt += 1
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    pass

    async def download_file(self, remote_path: str, local_path: Path) -> Path:
        if self._connection is None or self._connection.is_closed():
            raise SshConnectionError(
                SshFailureKind.NETWORK, "SSH가 연결되어 있지 않습니다."
            )
        local_path.parent.mkdir(parents=True, exist_ok=True)
        async with self._connection.start_sftp_client() as sftp:
            await sftp.get(str(PurePosixPath(remote_path)), str(local_path))
        return local_path

    async def list_remote_logs(self, remote_directory: str) -> list[str]:
        if self._connection is None or self._connection.is_closed():
            raise SshConnectionError(
                SshFailureKind.NETWORK, "SSH가 연결되어 있지 않습니다."
            )
        async with self._connection.start_sftp_client() as sftp:
            entries = await sftp.readdir(remote_directory)
        logs = []
        for entry in entries:
            filename = (
                entry.filename.decode("utf-8", errors="replace")
                if isinstance(entry.filename, bytes)
                else entry.filename
            )
            if filename.lower().endswith(".h5"):
                logs.append((entry.attrs.mtime or 0, filename))
        logs.sort()
        return [filename for _mtime, filename in logs]

    def _status(self, status: str) -> None:
        if self.status_callback is not None:
            with contextlib.suppress(Exception):
                self.status_callback(status)
