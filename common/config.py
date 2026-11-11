from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from math import isfinite
from pathlib import Path
from typing import Any

import yaml


# Closed, wired field network endpoint.  The dedicated DAQ cable lives on a
# private subnet so it can never compete with the operator's 192.168.0.0/24
# router Wi-Fi route.
TMS_PI_HOST = "10.47.0.2"
TMS_TELEMETRY_PORT = 29100
TMS_SSH_PORT = 22
TMS_SSH_USERNAME = "tms"
TMS_SSH_PASSWORD = "tms"

# This field installation is deliberately wired as a two-channel system.
# Keeping the mapping in one place prevents an accidental Setup edit from
# applying a load-cell calibration to a different physical AI terminal.
THRUST_AI_CHANNEL = 0
SECOND_SENSOR_AI_CHANNEL = 1


class ConfigError(ValueError):
    """Raised when a TMS configuration is incomplete or invalid."""


@dataclass(frozen=True)
class SystemConfig:
    pi_host: str = TMS_PI_HOST
    telemetry_port: int = TMS_TELEMETRY_PORT

    def __post_init__(self) -> None:
        if not self.pi_host.strip():
            raise ConfigError("system.pi_host must not be empty")
        if not 1 <= self.telemetry_port <= 65535:
            raise ConfigError("system.telemetry_port must be between 1 and 65535")


@dataclass(frozen=True)
class SshConfig:
    port: int = TMS_SSH_PORT
    username: str = TMS_SSH_USERNAME
    password: str = field(default=TMS_SSH_PASSWORD, repr=False)
    remember_password: bool = True
    connect_timeout_sec: float = 10.0
    keepalive_interval_sec: float = 5.0

    def __post_init__(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ConfigError("ssh.port must be between 1 and 65535")
        if not self.username.strip():
            raise ConfigError("ssh.username must not be empty")
        if self.connect_timeout_sec <= 0:
            raise ConfigError("ssh.connect_timeout_sec must be greater than zero")
        if self.keepalive_interval_sec <= 0:
            raise ConfigError("ssh.keepalive_interval_sec must be greater than zero")


@dataclass(frozen=True)
class NanoConfig:
    port: str = "auto"
    baudrate: int = 115200
    heartbeat_timeout_sec: float = 2.0

    def __post_init__(self) -> None:
        if self.baudrate <= 0:
            raise ConfigError("nano.baudrate must be greater than zero")
        if self.heartbeat_timeout_sec <= 0:
            raise ConfigError("nano.heartbeat_timeout_sec must be greater than zero")


@dataclass(frozen=True)
class ChannelConfig:
    channel: int
    scale: float
    offset: float

    def __post_init__(self) -> None:
        if self.channel < 0:
            raise ConfigError("channel must be zero or greater")
        if not isfinite(self.scale) or not isfinite(self.offset):
            raise ConfigError("channel scale and offset must be finite")


@dataclass(frozen=True)
class PressureInputConfig:
    """Electrical configuration for the fixed AI1 4–20 mA input.

    The field wiring uses a 100 ohm shunt.  Keeping this separate from the
    fitted bar/count calibration makes the electrical assumption explicit in
    the dashboard and in each HDF5 log without changing the fitted pressure
    coefficients.
    """

    shunt_ohms: float = 100.0
    loop_min_mA: float = 4.0
    loop_max_mA: float = 20.0

    def __post_init__(self) -> None:
        if not isfinite(self.shunt_ohms) or self.shunt_ohms <= 0.0:
            raise ConfigError("pressure_input.shunt_ohms must be greater than zero")
        if not isfinite(self.loop_min_mA) or not isfinite(self.loop_max_mA):
            raise ConfigError("pressure_input loop current limits must be finite")
        if self.loop_min_mA < 0.0 or self.loop_max_mA <= self.loop_min_mA:
            raise ConfigError("pressure_input loop current limits are invalid")

    @property
    def signal_voltage_min_v(self) -> float:
        return self.loop_min_mA / 1000.0 * self.shunt_ohms

    @property
    def signal_voltage_max_v(self) -> float:
        return self.loop_max_mA / 1000.0 * self.shunt_ohms


@dataclass(frozen=True)
class LowPassConfig:
    """Legacy LPF archive settings; the default display uses MA80."""

    enabled: bool = True
    cutoff_hz: float = 50.0

    def __post_init__(self) -> None:
        if not isfinite(self.cutoff_hz) or self.cutoff_hz <= 0.0:
            raise ConfigError("low_pass.cutoff_hz must be greater than zero")


@dataclass(frozen=True)
class DaqConfig:
    sample_rate: int = 5000
    block_ms: int = 10
    device: str = "/dev/daq0"

    def __post_init__(self) -> None:
        if self.sample_rate <= 0:
            raise ConfigError("daq.sample_rate must be greater than zero")
        if self.block_ms <= 0:
            raise ConfigError("daq.block_ms must be greater than zero")
        if self.sample_rate * self.block_ms % 1000:
            raise ConfigError(
                "daq.sample_rate * daq.block_ms must produce a whole sample count"
            )

    @property
    def samples_per_block(self) -> int:
        return self.sample_rate * self.block_ms // 1000


@dataclass(frozen=True)
class LoggingConfig:
    directory: Path = Path("logs")
    ring_buffer_sec: float = 5.0
    flush_interval_sec: float = 1.0
    pi_directory: Path = Path("/var/lib/tusi-tms/logs")

    def __post_init__(self) -> None:
        if self.ring_buffer_sec <= 0:
            raise ConfigError("logging.ring_buffer_sec must be greater than zero")
        if self.flush_interval_sec <= 0:
            raise ConfigError("logging.flush_interval_sec must be greater than zero")


@dataclass(frozen=True)
class TmsConfig:
    daq: DaqConfig
    thrust: ChannelConfig
    pressure: ChannelConfig
    logging: LoggingConfig
    system: SystemConfig = field(default_factory=SystemConfig)
    ssh: SshConfig = field(default_factory=SshConfig)
    nano: NanoConfig = field(default_factory=NanoConfig)
    pressure_input: PressureInputConfig = field(default_factory=PressureInputConfig)
    low_pass: LowPassConfig = field(default_factory=LowPassConfig)

    def __post_init__(self) -> None:
        if self.thrust.channel != THRUST_AI_CHANNEL:
            raise ConfigError(
                f"thrust/load-cell is fixed to AI{THRUST_AI_CHANNEL}"
            )
        if self.pressure.channel != SECOND_SENSOR_AI_CHANNEL:
            raise ConfigError(
                f"second sensor is fixed to AI{SECOND_SENSOR_AI_CHANNEL}"
            )
        scan_channel_count = SECOND_SENSOR_AI_CHANNEL - THRUST_AI_CHANNEL + 1
        if self.daq.sample_rate * scan_channel_count > 47_619:
            raise ConfigError(
                "DAQ sample rate multiplied by the contiguous channel scan count "
                "must not exceed 47619 samples/s"
            )
        if self.low_pass.enabled and self.low_pass.cutoff_hz >= self.daq.sample_rate / 2.0:
            raise ConfigError(
                "low_pass.cutoff_hz must be below the DAQ Nyquist frequency"
            )

    def as_dict(self, *, include_secret: bool = False) -> dict[str, Any]:
        flat = asdict(self)
        thrust = flat.pop("thrust")
        pressure = flat.pop("pressure")
        result = {
            "system": flat["system"],
            "ssh": flat["ssh"],
            "nano": flat["nano"],
            "daq": flat["daq"],
            "channels": {"thrust": thrust, "pressure": pressure},
            "pressure_input": flat["pressure_input"],
            "low_pass": flat["low_pass"],
            "logging": flat["logging"],
        }
        result["logging"]["directory"] = str(self.logging.directory)
        result["logging"]["pi_directory"] = str(self.logging.pi_directory)
        if not include_secret:
            result["ssh"]["password"] = ""
        return result


def default_config() -> TmsConfig:
    """Return a usable first-run configuration without reading a file."""

    return TmsConfig(
        system=SystemConfig(),
        ssh=SshConfig(),
        nano=NanoConfig(),
        daq=DaqConfig(),
        thrust=ChannelConfig(channel=THRUST_AI_CHANNEL, scale=0.01, offset=0.0),
        pressure=ChannelConfig(
            channel=SECOND_SENSOR_AI_CHANNEL, scale=0.001, offset=0.0
        ),
        logging=LoggingConfig(),
        pressure_input=PressureInputConfig(),
        low_pass=LowPassConfig(),
    )


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a mapping")
    return value


def load_config(path: str | Path) -> TmsConfig:
    config_path = Path(path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read configuration: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML configuration: {config_path}") from exc

    root = _mapping(raw, "configuration")
    system = _mapping(root.get("system", {}), "system")
    ssh = _mapping(root.get("ssh", {}), "ssh")
    nano = _mapping(root.get("nano", {}), "nano")
    daq = _mapping(root.get("daq", {}), "daq")
    channels = _mapping(root.get("channels", {}), "channels")
    thrust = _mapping(channels.get("thrust", {}), "channels.thrust")
    pressure = _mapping(channels.get("pressure", {}), "channels.pressure")
    logging = _mapping(root.get("logging", {}), "logging")
    pressure_input = _mapping(root.get("pressure_input", {}), "pressure_input")
    low_pass = _mapping(root.get("low_pass", {}), "low_pass")

    try:
        return TmsConfig(
            daq=DaqConfig(
                sample_rate=int(daq.get("sample_rate", 5000)),
                block_ms=int(daq.get("block_ms", 10)),
                device=str(daq.get("device", "/dev/daq0")),
            ),
            thrust=ChannelConfig(
                channel=int(thrust.get("channel", THRUST_AI_CHANNEL)),
                scale=float(thrust.get("scale", 1.0)),
                offset=float(thrust.get("offset", 0.0)),
            ),
            pressure=ChannelConfig(
                channel=int(pressure.get("channel", SECOND_SENSOR_AI_CHANNEL)),
                scale=float(pressure.get("scale", 1.0)),
                offset=float(pressure.get("offset", 0.0)),
            ),
            logging=LoggingConfig(
                directory=Path(logging.get("directory", "logs")),
                ring_buffer_sec=float(logging.get("ring_buffer_sec", 5.0)),
                flush_interval_sec=float(logging.get("flush_interval_sec", 1.0)),
                pi_directory=Path(
                    logging.get("pi_directory", "/var/lib/tusi-tms/logs")
                ),
            ),
            system=SystemConfig(
                pi_host=str(system.get("pi_host", TMS_PI_HOST)),
                telemetry_port=int(system.get("telemetry_port", TMS_TELEMETRY_PORT)),
            ),
            ssh=SshConfig(
                port=int(ssh.get("port", TMS_SSH_PORT)),
                username=str(ssh.get("username", TMS_SSH_USERNAME)),
                password=str(ssh.get("password", TMS_SSH_PASSWORD)),
                remember_password=bool(ssh.get("remember_password", True)),
                connect_timeout_sec=float(ssh.get("connect_timeout_sec", 10.0)),
                keepalive_interval_sec=float(ssh.get("keepalive_interval_sec", 5.0)),
            ),
            nano=NanoConfig(
                port=str(nano.get("port", "auto")),
                baudrate=int(nano.get("baudrate", 115200)),
                heartbeat_timeout_sec=float(nano.get("heartbeat_timeout_sec", 2.0)),
            ),
            pressure_input=PressureInputConfig(
                shunt_ohms=float(pressure_input.get("shunt_ohms", 100.0)),
                loop_min_mA=float(pressure_input.get("loop_min_mA", 4.0)),
                loop_max_mA=float(pressure_input.get("loop_max_mA", 20.0)),
            ),
            low_pass=LowPassConfig(
                enabled=bool(low_pass.get("enabled", True)),
                cutoff_hz=float(low_pass.get("cutoff_hz", 50.0)),
            ),
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, ConfigError):
            raise
        raise ConfigError(f"invalid configuration value: {exc}") from exc


def save_config(config: TmsConfig, path: str | Path) -> Path:
    """Atomically save local dashboard settings without unwanted secret leakage."""

    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = config.as_dict(include_secret=config.ssh.remember_password)
    if not config.ssh.remember_password:
        data["ssh"]["password"] = ""

    temporary = config_path.with_suffix(config_path.suffix + ".tmp")
    try:
        temporary.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        if os.name != "nt":
            temporary.chmod(0o600)
        temporary.replace(config_path)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise ConfigError(f"cannot save configuration: {config_path}") from exc
    return config_path
