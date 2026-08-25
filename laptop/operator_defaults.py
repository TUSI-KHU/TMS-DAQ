"""Fixed closed-network settings for the field Dashboard."""

from dataclasses import replace

from common.config import (
    TMS_PI_HOST,
    TMS_SSH_PASSWORD,
    TMS_SSH_PORT,
    TMS_SSH_USERNAME,
    TMS_TELEMETRY_PORT,
    SshConfig,
    SystemConfig,
    TmsConfig,
)


def apply_field_connection(config: TmsConfig) -> TmsConfig:
    """Return ``config`` with the non-configurable Pi connection applied."""

    return replace(
        config,
        system=SystemConfig(
            pi_host=TMS_PI_HOST,
            telemetry_port=TMS_TELEMETRY_PORT,
        ),
        ssh=SshConfig(
            port=TMS_SSH_PORT,
            username=TMS_SSH_USERNAME,
            password=TMS_SSH_PASSWORD,
            remember_password=True,
            connect_timeout_sec=config.ssh.connect_timeout_sec,
            keepalive_interval_sec=config.ssh.keepalive_interval_sec,
        ),
    )
