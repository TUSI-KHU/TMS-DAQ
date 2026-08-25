import asyncio
from types import SimpleNamespace

import asyncssh

from common.config import SshConfig, SystemConfig
from laptop.ssh_client import SshTunnelManager


class FakeListener:
    def __init__(self) -> None:
        self.closed = False

    def get_port(self) -> int:
        return 32100

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.closed = False
        self.forward_args = None

    def is_closed(self) -> bool:
        return self.closed

    async def forward_local_port(self, *args):
        self.forward_args = args
        return FakeListener()

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        return None


def test_ssh_uses_password_only_and_local_forward(monkeypatch) -> None:
    async def scenario() -> None:
        captured = {}
        connection = FakeConnection()

        async def fake_connect(host, port, **kwargs):
            captured.update({"host": host, "port": port, **kwargs})
            return connection

        monkeypatch.setattr(asyncssh, "connect", fake_connect)
        manager = SshTunnelManager(
            SystemConfig("192.168.50.2", 29100),
            SshConfig(username="tms", password="secret"),
        )
        local_port = await manager.connect()

        assert local_port == 32100
        assert captured["username"] == "tms"
        assert captured["password"] == "secret"
        assert captured["client_keys"] == []
        assert captured["agent_path"] is None
        assert captured["preferred_auth"] == ("password", "keyboard-interactive")
        assert connection.forward_args == (
            "127.0.0.1",
            0,
            "127.0.0.1",
            29100,
        )
        await manager.disconnect()

    asyncio.run(scenario())


def test_remote_logs_are_sorted_by_modification_time() -> None:
    class FakeSftp:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def readdir(self, _directory):
            return [
                SimpleNamespace(
                    filename="2026_new.h5", attrs=SimpleNamespace(mtime=200)
                ),
                SimpleNamespace(
                    filename="ignore.txt", attrs=SimpleNamespace(mtime=300)
                ),
                SimpleNamespace(
                    filename="2026_old.h5", attrs=SimpleNamespace(mtime=100)
                ),
            ]

    class FakeSftpConnection(FakeConnection):
        def start_sftp_client(self):
            return FakeSftp()

    async def scenario() -> None:
        manager = SshTunnelManager(SystemConfig(), SshConfig())
        manager._connection = FakeSftpConnection()

        assert await manager.list_remote_logs("/logs") == [
            "2026_old.h5",
            "2026_new.h5",
        ]

    asyncio.run(scenario())
