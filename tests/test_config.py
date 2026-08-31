from dataclasses import replace
from pathlib import Path

import pytest

from common.config import (
    ChannelConfig,
    ConfigError,
    SshConfig,
    default_config,
    load_config,
    save_config,
)


def test_example_configuration_loads() -> None:
    config = load_config(Path(__file__).parents[1] / "config.example.yaml")

    assert config.daq.sample_rate == 5000
    assert config.daq.samples_per_block == 50
    assert config.thrust.channel == 0
    assert config.pressure.channel == 1
    assert config.pressure_input.shunt_ohms == 100.0
    assert config.pressure_input.signal_voltage_min_v == pytest.approx(0.4)
    assert config.pressure_input.signal_voltage_max_v == pytest.approx(2.0)
    assert config.low_pass.enabled is True
    assert config.low_pass.cutoff_hz == 50.0
    assert config.system.telemetry_port == 29100


def test_default_configuration_matches_first_run_channels() -> None:
    config = default_config()

    assert config.thrust.channel == 0
    assert config.pressure.channel == 1
    assert config.pressure_input.shunt_ohms == 100.0
    assert config.low_pass.cutoff_hz == 50.0
    assert config.daq.sample_rate == 5000


def test_saved_configuration_omits_unremembered_password(tmp_path) -> None:
    source = Path(__file__).parents[1] / "config.example.yaml"
    config = load_config(source)
    config = replace(
        config,
        ssh=SshConfig(
            username="tms",
            password="do-not-save-this",
            remember_password=False,
        ),
    )
    saved = save_config(config, tmp_path / "config.yaml")

    text = saved.read_text(encoding="utf-8")
    assert "pi_host: 10.47.0.2" in text
    assert "password: ''" in text or 'password: ""' in text
    assert "do-not-save-this" not in text
    assert "do-not-save-this" not in repr(config)
    reloaded = load_config(saved)
    assert reloaded.thrust == config.thrust
    assert reloaded.pressure == config.pressure
    assert reloaded.ssh.password == ""


def test_field_channel_mapping_is_fixed_to_ai0_and_ai1() -> None:
    config = default_config()
    with pytest.raises(ConfigError, match="thrust/load-cell is fixed to AI0"):
        replace(config, thrust=ChannelConfig(channel=2, scale=1.0, offset=0.0))
    with pytest.raises(ConfigError, match="second sensor is fixed to AI1"):
        replace(config, pressure=ChannelConfig(channel=2, scale=1.0, offset=0.0))
