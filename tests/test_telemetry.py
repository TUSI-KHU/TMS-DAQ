import asyncio
import threading

import h5py
import pytest

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from common.protocol import MessageType, WireMessage
from laptop.telemetry import HARDWARE_STOP_TIMEOUT_SECONDS, TelemetryClient
from pi.daq import DaqBlock, DaqError, SimulatedDaqSource
from pi.telemetry import TelemetryServer
from pi.tms_agent import AgentState, TmsAgent


def test_tcp_session_survives_dashboard_disconnect(tmp_path) -> None:
    async def scenario() -> None:
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(channel=0, scale=0.5, offset=0.0),
            pressure=ChannelConfig(channel=1, scale=0.1, offset=0.0),
            logging=LoggingConfig(
                directory=tmp_path,
                ring_buffer_sec=1.0,
                flush_interval_sec=0.01,
            ),
        )
        source = SimulatedDaqSource(config.daq, (0, 1), realtime=True)
        agent = TmsAgent(config, source)
        server = TelemetryServer(agent, config, port=0, health_interval_sec=0.02)
        await server.start()

        first_client = TelemetryClient()
        await first_client.connect(port=server.port)
        start = await first_client.start_session("TCP_TEST")
        assert start["state"] == AgentState.RECORDING.value
        block = await first_client.wait_for_block(timeout=1.0)
        assert block.sample_rate == 1000
        assert block.channel_names == ("thrust_N", "pressure_bar")
        trigger_sample = await first_client.trigger("2026-08-23T00:00:00.000+00:00")
        await first_client.disconnect()

        samples_at_disconnect = agent.samples_written
        await asyncio.sleep(0.05)
        assert agent.samples_written > samples_at_disconnect
        assert agent.state == AgentState.TRIGGERED

        second_client = TelemetryClient()
        await second_client.connect(port=server.port)
        status = await second_client.ping()
        assert status["status"]["state"] == AgentState.TRIGGERED.value
        stop = await second_client.stop_session()
        assert stop["state"] == AgentState.COMPLETE.value
        path = agent.log_path
        await second_client.disconnect()
        await server.close()

        with h5py.File(path, "r") as data:
            assert len(data["samples/sample_index"]) > 0
            assert data["events"][0]["event_type"] == b"ignition"
            assert data["events"][0]["sample_index"] == trigger_sample

    asyncio.run(scenario())


def test_stop_session_uses_hardware_stop_timeout() -> None:
    async def scenario() -> None:
        client = TelemetryClient()
        observed: dict[str, object] = {}

        async def request(
            message_type: MessageType,
            body: dict[str, object] | None = None,
            *,
            timeout: float,
        ) -> WireMessage:
            observed["message_type"] = message_type
            observed["timeout"] = timeout
            return WireMessage(MessageType.ACK, {"state": "COMPLETE"})

        client._request = request  # type: ignore[method-assign]
        assert await client.stop_session() == {"state": "COMPLETE"}
        assert observed == {
            "message_type": MessageType.STOP_SESSION,
            "timeout": HARDWARE_STOP_TIMEOUT_SECONDS,
        }

    asyncio.run(scenario())


def test_idle_calibration_capture_and_remote_ai0_persistence(tmp_path) -> None:
    async def scenario() -> None:
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(channel=0, scale=1.0, offset=0.0),
            pressure=ChannelConfig(channel=1, scale=1.0, offset=0.0),
            logging=LoggingConfig(directory=tmp_path),
        )
        source = SimulatedDaqSource(config.daq, (0, 1), realtime=True)
        agent = TmsAgent(config, source)
        persisted = []
        server = TelemetryServer(
            agent,
            config,
            port=0,
            config_update_callback=persisted.append,
        )
        await server.start()
        client = TelemetryClient()
        await client.connect(port=server.port)

        capture = await client.capture_calibration_sample(100)
        assert capture["command"] == "CALIBRATION_SAMPLE"
        assert capture["channels"]["ai0"]["sample_count"] >= 100
        assert capture["channels"]["ai1"]["sample_count"] >= 100
        assert agent.state == AgentState.READY

        saved = await client.set_thrust_calibration(
            scale_N_per_count=-0.25,
            offset_N=2500.0,
        )
        assert saved["thrust"] == {"channel": 0, "scale": -0.25, "offset": 2500.0}
        assert agent.config.thrust == ChannelConfig(0, -0.25, 2500.0)
        assert persisted == [agent.config]

        await client.disconnect()
        await server.close()

    asyncio.run(scenario())


def test_timed_out_start_is_cancelled_and_requires_daq_recovery(tmp_path) -> None:
    class DelayedDaq:
        source_kind = "usb4704"

        def __init__(self) -> None:
            self.started = threading.Event()
            self.release = threading.Event()
            self.stop_calls = 0
            self.close_calls = 0

        def probe(self) -> bool:
            return True

        def start(self) -> None:
            self.started.set()
            self.release.wait(timeout=1.0)

        def read_block(self) -> DaqBlock:
            raise AssertionError("acquisition must not start after cancellation")

        def stop(self) -> None:
            self.stop_calls += 1

        def close(self) -> None:
            self.close_calls += 1

        def recover(self) -> None:
            raise AssertionError("not used")

    async def scenario() -> None:
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(channel=0, scale=1.0, offset=0.0),
            pressure=ChannelConfig(channel=1, scale=1.0, offset=0.0),
            logging=LoggingConfig(directory=tmp_path),
        )
        source = DelayedDaq()
        agent = TmsAgent(config, source)
        server = TelemetryServer(agent, config, port=0)

        with pytest.raises(DaqError, match="did not return"):
            await server._run_bounded_hardware_command(
                "START_SESSION", agent.start_session, "LATE_START", timeout=0.02
            )
        assert await asyncio.to_thread(source.started.wait, 0.5)

        source.release.set()
        await asyncio.sleep(0.05)
        assert agent.state == AgentState.READY
        assert source.stop_calls == 1
        assert source.close_calls == 1

        with pytest.raises(DaqError, match="recovery is required"):
            await server._run_bounded_hardware_command(
                "START_SESSION", agent.start_session, "SECOND_START", timeout=0.02
            )

    asyncio.run(scenario())
