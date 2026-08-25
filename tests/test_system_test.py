import asyncio

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from laptop.nano import NanoSerialManager
from laptop.system_test import SystemTestRunner
from laptop.system_test import TestStatus as SystemTestStatus
from laptop.telemetry import TelemetryClient
from pi.daq import SimulatedDaqSource
from pi.telemetry import TelemetryServer
from pi.tms_agent import AgentState, TmsAgent


class ConnectedSsh:
    connected = True


def test_system_check_exercises_real_stream_path(tmp_path) -> None:
    async def scenario() -> None:
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(0, 1.0, 0.0),
            pressure=ChannelConfig(1, 1.0, 0.0),
            logging=LoggingConfig(directory=tmp_path, ring_buffer_sec=1.0),
        )
        agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1), realtime=True))
        server = TelemetryServer(agent, config, port=0, health_interval_sec=0.02)
        await server.start()
        client = TelemetryClient()
        await client.connect(port=server.port)
        nano = NanoSerialManager(config.nano, port_lister=list)
        runner = SystemTestRunner(nano, ConnectedSsh(), client, tmp_path)

        results = {result.name: result for result in await runner.run()}

        assert results["Pi Agent"].status == SystemTestStatus.PASS
        assert results["USB4704"].status == SystemTestStatus.SKIP
        assert results["DAQ Stream"].status == SystemTestStatus.PASS
        assert results["Thrust Channel"].status == SystemTestStatus.PASS
        assert results["Pressure Channel"].status == SystemTestStatus.PASS
        assert agent.state == AgentState.COMPLETE
        await client.disconnect()
        await server.close()

    asyncio.run(scenario())
