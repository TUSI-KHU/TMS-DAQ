from common.config import ChannelConfig, DaqConfig, LoggingConfig, SshConfig, SystemConfig, TmsConfig
from laptop.operator_defaults import apply_field_connection


def test_field_connection_is_fixed_for_the_closed_wired_network(tmp_path) -> None:
    source = TmsConfig(
        daq=DaqConfig(sample_rate=1000, block_ms=10),
        thrust=ChannelConfig(0, 1.0, 0.0),
        pressure=ChannelConfig(1, 1.0, 0.0),
        logging=LoggingConfig(directory=tmp_path),
        system=SystemConfig(pi_host="10.1.2.3", telemetry_port=12345),
        ssh=SshConfig(port=2200, username="other", password="other"),
    )

    config = apply_field_connection(source)

    assert config.system.pi_host == "10.47.0.2"
    assert config.system.telemetry_port == 29100
    assert config.ssh.port == 22
    assert config.ssh.username == "tms"
    assert config.ssh.password == "tms"
    assert config.ssh.remember_password is True
