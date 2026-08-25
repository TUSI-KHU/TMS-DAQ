import asyncio

import h5py

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from common.protocol import MessageType, WireMessage
from laptop.telemetry import HARDWARE_STOP_TIMEOUT_SECONDS, TelemetryClient
from pi.daq import SimulatedDaqSource
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
