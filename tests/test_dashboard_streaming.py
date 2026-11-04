import asyncio
from dataclasses import replace

import numpy as np

from common.protocol import TelemetryBlock
from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from laptop.backend import DashboardBackend
from pi.daq import DaqBlock, SimulatedDaqSource
from pi.telemetry import TelemetryServer
from pi.tms_agent import TmsAgent


def test_dashboard_visual_batch_preserves_contiguous_samples() -> None:
    first = TelemetryBlock(
        sequence=7,
        first_sample_index=350,
        sample_rate=5_000,
        channel_names=("thrust_N", "pressure_bar"),
        values=np.asarray(((1.0, 2.0), (3.0, 4.0)), dtype=np.float32),
    )
    second = TelemetryBlock(
        # Sequence carries the final DAQ block number of a batched telemetry
        # frame, so contiguous screen data may advance by more than one.
        sequence=12,
        first_sample_index=352,
        sample_rate=5_000,
        channel_names=("thrust_N", "pressure_bar"),
        values=np.asarray(((5.0, 6.0),), dtype=np.float32),
    )

    assert DashboardBackend._blocks_are_contiguous(first, second)
    assert not DashboardBackend._blocks_are_contiguous(
        replace(first, session_id="old"), replace(second, session_id="new")
    )
    merged = DashboardBackend._merge_blocks([first, second])

    assert merged.sequence == 12
    assert merged.first_sample_index == 350
    assert merged.sample_count == 3
    np.testing.assert_allclose(
        merged.values,
        ((1.0, 2.0), (3.0, 4.0), (5.0, 6.0)),
    )


def test_pi_telemetry_batch_preserves_raw_samples_and_detects_gap() -> None:
    first = DaqBlock(
        sequence=3,
        first_sample_index=30,
        sample_rate=1_000,
        channel_numbers=(0, 1),
        raw_samples=np.asarray(((10, 20), (11, 21)), dtype=np.uint16),
    )
    second = DaqBlock(
        sequence=4,
        first_sample_index=32,
        sample_rate=1_000,
        channel_numbers=(0, 1),
        raw_samples=np.asarray(((12, 22),), dtype=np.uint16),
    )
    gap = DaqBlock(
        sequence=6,
        first_sample_index=34,
        sample_rate=1_000,
        channel_numbers=(0, 1),
        raw_samples=np.asarray(((13, 23),), dtype=np.uint16),
    )

    assert TelemetryServer._blocks_are_contiguous(first, second)
    assert not TelemetryServer._blocks_are_contiguous(second, gap)
    merged = TelemetryServer._merge_blocks([first, second])

    assert merged.sequence == 4
    assert merged.first_sample_index == 30
    np.testing.assert_array_equal(
        merged.raw_samples,
        ((10, 20), (11, 21), (12, 22)),
    )


def test_recovery_pauses_reconnect_without_rotating_ssh(tmp_path):
    async def scenario():
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
            logging=LoggingConfig(directory=tmp_path),
        )
        server = TelemetryServer(
            TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1))), config, port=0,
        )
        await server.start()
        port = server.port
        server.requested_port = port
        errors = []
        connections = []

        class SSH:
            connected = True
            disconnects = 0

            async def connect(self):
                return port

            async def disconnect(self):
                self.disconnects += 1

            async def recover_usb4704(self):
                await server.close()
                await asyncio.sleep(0.2)
                assert not errors
                assert self.disconnects == 0
                await server.start()
                return {"daq_ready": True}

        class Nano:
            def start(self):
                pass

            def stop(self):
                pass

        ssh = SSH()
        backend = DashboardBackend(
            config, ssh_manager=ssh, nano_manager=Nano(),
            error_callback=errors.append,
            connection_callback=lambda *event: connections.append(event),
        )
        task = asyncio.create_task(backend.run())
        try:
            async def connected():
                while not backend.telemetry.connected:
                    await asyncio.sleep(0.01)
            await asyncio.wait_for(connected(), 2)
            result = await backend.reset_daq()
            assert result["daq_ready"]
            assert backend.telemetry.connected
            assert ssh.disconnects == 0
            assert errors == []
            assert ("Pi", "RECONNECTING") not in connections
        finally:
            await backend.stop()
            await asyncio.wait_for(task, 2)
            await server.close()

    asyncio.run(scenario())
