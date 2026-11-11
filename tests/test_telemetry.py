import asyncio
import json
import threading

import h5py
import numpy as np
import pytest

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from common.protocol import MessageType, WireMessage, decode_daq_data
from laptop.telemetry import HARDWARE_STOP_TIMEOUT_SECONDS, RemoteCommandError, TelemetryClient
from pi.daq import DaqBlock, DaqError, SimulatedDaqSource
from pi.telemetry import TelemetryServer
from pi.tms_agent import AgentState, TmsAgent
from pi.recovery_probe import verify


def test_live_telemetry_uses_moving_average_values(tmp_path) -> None:
    config = TmsConfig(
        daq=DaqConfig(sample_rate=1_000, block_ms=10),
        thrust=ChannelConfig(channel=0, scale=1.0, offset=0.0),
        pressure=ChannelConfig(channel=1, scale=1.0, offset=0.0),
        logging=LoggingConfig(directory=tmp_path),
    )
    source = SimulatedDaqSource(config.daq, (0, 1), realtime=False)
    agent = TmsAgent(config, source)
    server = TelemetryServer(agent, config)
    block = DaqBlock(
        sequence=0,
        first_sample_index=0,
        sample_rate=1_000,
        channel_numbers=(0, 1),
        raw_samples=np.asarray(((0, 0), (100, 100), (100, 100)), dtype=np.uint16),
    )

    decoded = decode_daq_data(server._telemetry_message(block))
    assert decoded.values[0, 0] == 0.0
    assert decoded.values[1, 0] == 50.0
    assert decoded.values[2, 0] == pytest.approx(200 / 3)
    assert decoded.values[1, 1] == decoded.values[1, 0]


def test_repeated_sessions_do_not_replay_previous_display_blocks(tmp_path) -> None:
    async def scenario():
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(0, 1.0, 0.0), pressure=ChannelConfig(1, 1.0, 0.0),
            logging=LoggingConfig(directory=tmp_path),
        )
        agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1)))
        server = TelemetryServer(agent, config, port=0)
        await server.start()
        client = TelemetryClient()
        try:
            await client.connect(port=server.port)
            previous_id = None
            for index in range(3):
                start = await client.start_session(f"REPEAT_{index}")
                assert start["session_id"] != previous_id
                assert client.latest_health["state"] == "RECORDING"
                block = await client.wait_for_block(timeout=1)
                assert block.session_id == start["session_id"]
                assert block.first_sample_index == 0
                await asyncio.sleep(0.12)  # Leave unread old-session frames.
                await client.stop_session()
                assert client.latest_health["state"] == "COMPLETE"
                assert client._data_queue.empty()
                previous_id = start["session_id"]
            await client.disconnect()
            await client.connect(port=server.port)
            assert client._data_queue.empty()
        finally:
            if agent.state in (AgentState.RECORDING, AgentState.TRIGGERED):
                await asyncio.to_thread(agent.stop_session)
            await client.disconnect()
            await server.close()

    asyncio.run(scenario())


def test_recovery_probe_reads_twice_without_creating_session_logs(tmp_path):
    async def scenario():
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
            logging=LoggingConfig(directory=tmp_path),
        )
        agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1)))
        server = TelemetryServer(agent, config, port=0)
        await server.start()
        try:
            await verify(server.port)
            assert agent.state == AgentState.READY
            assert list(tmp_path.iterdir()) == []
        finally:
            await server.close()
    asyncio.run(scenario())


def test_stop_watchdog_preserves_log_and_blocks_reuse(tmp_path, monkeypatch) -> None:
    class DelayedClose(SimulatedDaqSource):
        def __init__(self, *args):
            super().__init__(*args)
            self.closing = threading.Event()
            self.release = threading.Event()

        def close(self):
            self.closing.set()
            self.release.wait(timeout=2)
            super().close()

    async def scenario():
        config = TmsConfig(daq=DaqConfig(sample_rate=1000, block_ms=10),
                           thrust=ChannelConfig(0, 1.0, 0.0), pressure=ChannelConfig(1, 1.0, 0.0),
                           logging=LoggingConfig(directory=tmp_path))
        source = DelayedClose(config.daq, (0, 1))
        agent = TmsAgent(config, source)
        server = TelemetryServer(agent, config, port=0)
        monkeypatch.setattr("pi.telemetry.STOP_SESSION_OPERATION_TIMEOUT_SEC", 0.05)
        await server.start()
        client = TelemetryClient()
        try:
            await client.connect(port=server.port)
            await client.start_session("STOP_TIMEOUT")
            await client.wait_for_block(timeout=1)
            with pytest.raises(RemoteCommandError, match="did not return"):
                await client.stop_session()
            assert source.closing.is_set()
            # The logger has already closed even though the USB close is stuck.
            with h5py.File(agent.log_path, "r") as data:
                assert len(data["samples/sample_index"]) > 0
            assert agent.health["logger"] == "COMPLETE"
            assert (await client.ping())["status"]["recovery_required"] == "STOP_SESSION"
            with pytest.raises(RuntimeError, match="recovery is required"):
                await client.start_session("MUST_NOT_START")
        finally:
            source.release.set()
            await asyncio.sleep(0.05)
            await client.disconnect()
            await server.close()

    asyncio.run(scenario())


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


def test_nano_trigger_validation_retry_and_session_isolation(tmp_path) -> None:
    async def scenario():
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
            logging=LoggingConfig(directory=tmp_path),
        )
        agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1)))
        server = TelemetryServer(agent, config, port=0)
        await server.start()
        client = TelemetryClient()
        try:
            await client.connect(port=server.port)
            start = await client.start_session("NANO_FIRST")
            await client.wait_for_block(timeout=1)
            event = dict(
                receive_time="2026-11-04T10:20:30.123+00:00",
                source="nano", session_id=start["session_id"],
                nano_sequence=1, nano_uptime_ms=5000,
            )
            for field, value in (
                ("session_id", "stale-id"), ("nano_sequence", -1),
                ("nano_sequence", True), ("nano_uptime_ms", "5000"),
                ("source", 42), ("receive_time", 42),
            ):
                with pytest.raises(RemoteCommandError):
                    await client.trigger(**{**event, field: value})
            with pytest.raises(RemoteCommandError, match="requires"):
                await client.trigger(source="nano")
            sample = await client.trigger(**event)
            await client.disconnect()
            await client.connect(port=server.port)
            assert await client.trigger(**event) == sample
            with pytest.raises(RemoteCommandError, match="already recorded"):
                await client.trigger(**{**event, "nano_uptime_ms": 6000})
            first_path = agent.log_path
            await client.stop_session()
            second_start = await client.start_session("NANO_SECOND")
            await client.wait_for_block(timeout=1)
            with pytest.raises(RemoteCommandError, match="does not match"):
                await client.trigger(**event)
            assert agent.trigger_sample is None
            await client.trigger(**{**event, "session_id": second_start["session_id"]})
            await client.stop_session()
            with h5py.File(first_path, "r") as data:
                assert len(data["events"]) == 1
                details = json.loads(data["events"][0]["details"])
                assert details["source"] == "nano"
                assert details["session_id"] == start["session_id"]
                assert details["nano_sequence"] == 1
        finally:
            if agent.state in (AgentState.RECORDING, AgentState.TRIGGERED):
                await asyncio.to_thread(agent.stop_session)
            await client.disconnect()
            await server.close()

    asyncio.run(scenario())


def test_ping_remains_responsive_while_trigger_waits_for_disk(tmp_path, monkeypatch):
    async def scenario():
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
            logging=LoggingConfig(directory=tmp_path),
        )
        agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1)))
        server = TelemetryServer(agent, config, port=0)
        entered = threading.Event()
        release = threading.Event()
        original = agent._logger.record_event

        def delayed_write(*args, **kwargs):
            entered.set()
            assert release.wait(timeout=2)
            original(*args, **kwargs)

        monkeypatch.setattr(agent._logger, "record_event", delayed_write)
        await server.start()
        client = TelemetryClient()
        observer = TelemetryClient()
        try:
            await client.connect(port=server.port)
            await observer.connect(port=server.port)
            await client.start_session("SLOW_TRIGGER_DISK")
            await client.wait_for_block(timeout=1)
            trigger = asyncio.create_task(client.trigger())
            assert await asyncio.to_thread(entered.wait, 1)
            assert not trigger.done()
            status = await observer.ping(timeout=0.5)
            assert status["status"]["state"] == "RECORDING"
            release.set()
            assert await trigger >= 0
            await client.stop_session()
        finally:
            release.set()
            if agent.state in (AgentState.RECORDING, AgentState.TRIGGERED):
                await asyncio.to_thread(agent.stop_session)
            await client.disconnect()
            await observer.disconnect()
            await server.close()

    asyncio.run(scenario())


def test_nano_state_round_trip_logs_levels_and_first_edge(tmp_path):
    async def scenario():
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
            logging=LoggingConfig(directory=tmp_path),
        )
        agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1)))
        server = TelemetryServer(agent, config, port=0)
        await server.start()
        client = TelemetryClient()
        try:
            await client.connect(port=server.port)
            started = await client.start_session("NANO_LEVELS")
            await client.wait_for_block(timeout=1)
            first = dict(
                session_id=started["session_id"], gpio_state=True,
                nano_sequence=1, nano_uptime_ms=500,
                receive_time="2026-11-04T10:20:30.123+00:00", event_id="first",
            )
            ack = await client.nano_state(**first)
            assert ack["sample_index"] >= 0
            assert ack["trigger_sample"] is None
            for field, value in (
                ("session_id", "old"), ("gpio_state", 1),
                ("nano_sequence", True), ("nano_uptime_ms", -1),
                ("valid_for_ms", -1), ("valid_for_ms", True), ("valid_for_ms", 2001),
                ("event_id", ""), ("receive_time", None),
            ):
                with pytest.raises(RemoteCommandError):
                    await client.nano_state(**{**first, field: value})
            await client.disconnect()
            await client.connect(port=server.port)
            assert await client.nano_state(**first) == ack
            assert (await client.nano_state(**{
                **first, "gpio_state": False, "nano_sequence": 2,
                "nano_uptime_ms": 1000, "event_id": "low",
            }))["trigger_sample"] is None
            edge = {**first, "nano_sequence": 3, "nano_uptime_ms": 1500, "event_id": "high"}
            triggered = await client.nano_state(**edge)
            assert triggered["trigger_sample"] is not None
            # The legacy explicit trigger path can ACK exactly this same
            # identified edge without writing a second ignition event.
            assert await client.trigger(
                session_id=started["session_id"], source="nano",
                receive_time=edge["receive_time"], nano_sequence=3, nano_uptime_ms=1500,
            ) == triggered["trigger_sample"]
            await client.nano_state(**{
                **first, "gpio_state": None, "nano_sequence": None,
                "nano_uptime_ms": None, "event_id": "unknown",
            })
            await client.stop_session()
            with pytest.raises(RemoteCommandError, match="cannot record Nano state"):
                await client.nano_state(**edge)
            with h5py.File(agent.log_path, "r") as data:
                rows = list(data["events"])
                assert [r["event_type"] for r in rows] == [
                    b"nano_state", b"nano_state", b"nano_state", b"ignition", b"nano_state",
                ]
                assert json.loads(rows[-1]["details"])["gpio_state"] == -1
        finally:
            if agent.state in (AgentState.RECORDING, AgentState.TRIGGERED):
                await asyncio.to_thread(agent.stop_session)
            await client.disconnect()
            await server.close()

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

        pressure_saved = await client.set_pressure_calibration(
            scale_bar_per_count=0.0025,
            offset_bar=-2.5,
        )
        assert pressure_saved["pressure"] == {
            "channel": 1,
            "scale": 0.0025,
            "offset": -2.5,
        }
        assert agent.config.pressure == ChannelConfig(1, 0.0025, -2.5)
        assert len(persisted) == 2
        assert persisted[-1] == agent.config

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


def test_calibration_profiles_survive_service_restart(tmp_path):
    from common.config import load_config, save_config

    async def scenario():
        path = tmp_path / 'config.yaml'
        config = TmsConfig(daq=DaqConfig(), thrust=ChannelConfig(0, 1., 0.),
                           pressure=ChannelConfig(1, 1., 0.), logging=LoggingConfig(directory=tmp_path))
        save_config(config, path)
        async def start(config):
            agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1)))
            server = TelemetryServer(agent, config, port=0,
                config_update_callback=lambda value: save_config(value, path))
            await server.start()
            client = TelemetryClient()
            await client.connect(port=server.port)
            return server, client
        server, client = await start(config)
        try:
            await client.set_thrust_calibration(scale_N_per_count=-.25, offset_N=2500.)
            await client.set_pressure_calibration(scale_bar_per_count=.0025, offset_bar=-2.5)
        finally:
            await client.disconnect()
            await server.close()
        server, client = await start(load_config(path))
        try:
            channels = (await client.get_config())['config']['channels']
            assert channels['thrust'] == dict(channel=0, scale=-.25, offset=2500.)
            assert channels['pressure'] == dict(channel=1, scale=.0025, offset=-2.5)
        finally:
            await client.disconnect()
            await server.close()
    asyncio.run(scenario())
