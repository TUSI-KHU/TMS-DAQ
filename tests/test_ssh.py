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


class FakeRecoveryConnection(FakeConnection):
    def __init__(self, *, exit_status: int, stdout: str = "", stderr: str = "") -> None:
        super().__init__()
        self.exit_status = exit_status
        self.stdout = stdout
        self.stderr = stderr
        self.command = ""
        self.input = ""

    async def run(self, command, **kwargs):
        self.command = command
        self.input = kwargs.get("input", "")
        return SimpleNamespace(
            exit_status=self.exit_status,
            stdout=self.stdout,
            stderr=self.stderr,
        )


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


def test_ssh_connect_reuses_a_healthy_forward(monkeypatch) -> None:
    async def scenario() -> None:
        calls = 0
        connection = FakeConnection()

        async def fake_connect(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            return connection

        monkeypatch.setattr(asyncssh, "connect", fake_connect)
        manager = SshTunnelManager(SystemConfig(), SshConfig())
        assert await manager.connect() == 32100
        assert await manager.connect() == 32100
        assert calls == 1
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


def test_usb4704_recovery_uses_a_separate_sudo_ssh_command(monkeypatch) -> None:
    async def scenario() -> None:
        connection = FakeRecoveryConnection(
            exit_status=0, stderr="usb4704-recovery: RECOVERY_RESULT=DAQ_READY\n"
        )

        async def fake_connect(*_args, **_kwargs):
            return connection

        monkeypatch.setattr(asyncssh, "connect", fake_connect)
        manager = SshTunnelManager(
            SystemConfig("10.47.0.2", 29100),
            SshConfig(username="tms", password="secret"),
        )

        result = await manager.recover_usb4704()

        assert result["daq_ready"] is True
        assert connection.command == (
            "sudo -S -p '' /opt/tusi-tms/bin/recover-usb4704.sh /dev/daq0"
        )
        assert connection.input == "secret\n"
        assert connection.closed

    asyncio.run(scenario())


def test_usb4704_recovery_reports_when_daq_node_stays_missing(monkeypatch) -> None:
    async def scenario() -> None:
        connection = FakeRecoveryConnection(
            exit_status=3, stderr="usb4704-recovery: RECOVERY_RESULT=DAQ_MISSING\n"
        )

        async def fake_connect(*_args, **_kwargs):
            return connection

        monkeypatch.setattr(asyncssh, "connect", fake_connect)
        result = await SshTunnelManager(SystemConfig(), SshConfig()).recover_usb4704()

        assert result["daq_ready"] is False
        assert "DAQ_MISSING" in str(result["details"])

    asyncio.run(scenario())
