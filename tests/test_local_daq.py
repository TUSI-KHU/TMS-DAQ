import asyncio
from pathlib import Path

import pytest

from laptop.local_daq import LocalDaqAccess
from laptop.main import build_parser


def test_local_mode_is_explicit_and_remote_mode_remains_default():
    assert not build_parser().parse_args([]).local_daq
    assert build_parser().parse_args(['--local-daq']).local_daq


def test_local_log_listing_copy_and_path_validation(tmp_path):
    root = tmp_path / 'agent'
    root.mkdir()
    (root / 'sample.h5').write_bytes(b'hdf5-placeholder')
    (root / 'ignore.csv').write_text('not a source log')
    outside = tmp_path / 'outside.h5'
    outside.write_bytes(b'outside')
    (root / 'escape.h5').symlink_to(outside)
    local = LocalDaqAccess(root)
    async def scenario():
        assert await local.list_remote_logs(str(root)) == ['sample.h5']
        target = tmp_path / 'copy.h5'
        await local.download_file(str(root / 'sample.h5'), target)
        assert target.read_bytes() == b'hdf5-placeholder'
        for path in [outside, root / 'escape.h5', root / 'ignore.csv']:
            with pytest.raises(ValueError):
                await local.download_file(str(path), target)
        with pytest.raises(ValueError):
            await local.list_remote_logs(str(tmp_path))
    asyncio.run(scenario())


def test_local_recovery_uses_fixed_privileged_helper(monkeypatch):
    commands = []
    class Process:
        returncode = 0
        async def communicate(self):
            return b'BUFFERED_INPUT_VERIFIED', None
    async def spawn(*args, **kwargs):
        commands.append(args)
        return Process()
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    result = asyncio.run(LocalDaqAccess(Path('/var/lib/tusi-tms/logs')).recover_usb4704())
    assert result['daq_ready']
    assert commands == [('pkexec', '/opt/tusi-tms/bin/recover-usb4704.sh', '/dev/daq0')]


def test_local_backend_always_connects_to_loopback(tmp_path):
    from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
    from laptop.backend import DashboardBackend

    config = TmsConfig(
        daq=DaqConfig(), thrust=ChannelConfig(0, 1., 0.),
        pressure=ChannelConfig(1, 1., 0.),
        logging=LoggingConfig(directory=tmp_path),
    )
    local = DashboardBackend(config, local_daq=True)
    remote = DashboardBackend(config)
    assert local.config.system.pi_host == '127.0.0.1'
    assert local.direct_telemetry and local.ssh.is_local
    assert not remote.direct_telemetry
    assert remote.config.system.pi_host == config.system.pi_host
