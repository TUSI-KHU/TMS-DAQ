"""Input-only integration: emulated serial -> real TCP -> HDF5 -> CSV."""

import asyncio
import csv
import queue
from dataclasses import replace

import h5py
import pytest

from common.config import ChannelConfig, DaqConfig, LoggingConfig, TmsConfig
from laptop.backend import DashboardBackend
from laptop.logs import export_csv
from laptop.nano import NanoSerialManager, parse_nano_line
from laptop.telemetry import TelemetryError
from pi.daq import SimulatedDaqSource
from pi.telemetry import TelemetryServer
from pi.tms_agent import TmsAgent


class NanoWire:
    """No OS serial device is opened and no ignition output exists."""

    def __init__(self, **kwargs):
        self.is_open = True
        self.lines = queue.Queue()
        self.writes = []
        self.lines.put(b"HELLO,1.0\n")
        self.lines.put(b"HB,1,500,0\n")

    def readline(self):
        try:
            return self.lines.get(timeout=0.02)
        except queue.Empty:
            return b""

    def write(self, payload):
        self.writes.append(payload)
        assert payload.startswith(b"ARM,")
        self.lines.put(b"ARMED," + payload.split(b",", 1)[1])
        return len(payload)

    def flush(self):
        pass

    def close(self):
        self.is_open = False


async def wait_until(predicate, timeout=3):
    async def wait():
        while not predicate():
            await asyncio.sleep(0.01)
    await asyncio.wait_for(wait(), timeout)


@pytest.mark.parametrize("delivery_fault", ["none", "lost_ack", "disconnect"])
def test_serial_nano_to_csv_repeated_sessions_and_stop_boundary(tmp_path, delivery_fault, monkeypatch):
    async def scenario():
        config = TmsConfig(
            daq=DaqConfig(sample_rate=1000, block_ms=10),
            thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
            logging=LoggingConfig(directory=tmp_path),
        )
        agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1)))
        server = TelemetryServer(agent, config, port=0)
        await server.start()
        config = replace(config, system=replace(config.system, pi_host="127.0.0.1", telemetry_port=server.port))
        nano = NanoSerialManager(
            replace(config.nano, port="VIRTUAL_NANO", heartbeat_timeout_sec=10),
            serial_factory=NanoWire,
        )
        errors, states = [], []
        backend = DashboardBackend(config, nano_manager=nano, direct_telemetry=True,
                                   error_callback=errors.append,
                                   connection_callback=lambda *state: states.append(state))
        nano.trigger_callback = backend._nano_trigger
        run = asyncio.create_task(backend.run())
        original_trigger = backend.telemetry.trigger
        ack_was_lost = False

        async def trigger(*args, **kwargs):
            nonlocal ack_was_lost
            sample = await original_trigger(*args, **kwargs)
            if delivery_fault == "lost_ack" and not ack_was_lost:
                ack_was_lost = True
                raise TelemetryError("simulated lost ACK after HDF5 flush")
            return sample

        backend.telemetry.trigger = trigger
        try:
            await wait_until(lambda: backend.telemetry.connected)
            for number in range(2):
                start = await backend.start_session(f"SIMULATED_NANO_{number}")
                await wait_until(lambda: nano.status().state == "ARMED")
                await backend.telemetry.wait_for_fresh_block(timeout=1)
                wire = nano._serial
                assert isinstance(wire, NanoWire)
                seq = 10 + number
                if number == 0:
                    if delivery_fault == "disconnect":
                        # Outage exceeds the Stop wait bound. The running
                        # session must retain the edge until TCP reconnects.
                        monkeypatch.setattr("laptop.backend.TRIGGER_DELIVERY_TIMEOUT_SEC", 0.05)
                        await backend.telemetry.disconnect()
                    # Exercise the actual serial reader thread and parser.
                    wire.lines.put(f"TRIGGER,{seq},12345\n".encode("ascii"))
                    await wait_until(lambda: backend._trigger_task is not None)
                    if delivery_fault == "disconnect":
                        await asyncio.wait_for(asyncio.shield(backend._trigger_task), 3)
                        assert backend.telemetry.connected
                else:
                    if delivery_fault == "disconnect":
                        stop = backend.telemetry.stop_session

                        async def failed_stop():
                            raise TelemetryError("simulated STOP was not sent")

                        backend.telemetry.stop_session = failed_stop
                        with pytest.raises(TelemetryError, match="STOP was not sent"):
                            await backend.stop_session()
                        backend.telemetry.stop_session = stop
                        await wait_until(lambda: nano.status().state == "ARMED")
                    # Callback is queued but has not run when Stop is pressed.
                    nano._handle_message(parse_nano_line(f"TRIGGER,{seq},12346"))
                await backend.stop_session()
                assert backend._trigger_task.done()
                with h5py.File(agent.log_path, "r") as data:
                    ignition = data["events"][:]
                    ignition = ignition[ignition["event_type"] == b"ignition"]
                    assert len(ignition) == 1
                    sample = int(ignition[0]["sample_index"])
                    assert data["metadata"].attrs["session_id"] == start["session_id"]
                output = export_csv(agent.log_path, agent.log_path.with_suffix(".csv"))
                with output.open(newline="") as source:
                    rows = list(csv.DictReader(source))
                marked = [row for row in rows if row["ignition"] == "1"]
                assert len(marked) == 1
                assert marked[0]["ignition_source"] == "nano"
                assert int(marked[0]["nano_sequence"]) == seq
                assert int(marked[0]["sample_index"]) == sample
                assert float(marked[0]["time_s"]) == 0
                assert marked[0]["ignition_receive_time_utc"]
                assert marked[0]["ignition_timing_basis"] == "pi_latest_sample_on_receipt"
            assert not errors
            assert sum(state[0] == "Trigger" and state[1].startswith("SAMPLE ") for state in states) == 2
            # Out-of-session serial noise cannot contaminate the next log.
            nano._handle_message(parse_nano_line("TRIGGER,99,99999"))
            await backend.start_session("SIMULATED_NO_IGNITION")
            await backend.telemetry.wait_for_fresh_block(timeout=1)
            await backend.stop_session()
            with h5py.File(agent.log_path, "r") as data:
                assert len(data["events"]) == 0
        finally:
            await backend.stop()
            await asyncio.wait_for(run, 2)
            await server.close()

    asyncio.run(scenario())


def test_disconnected_trigger_is_reported_not_silently_dropped(tmp_path, monkeypatch):
    async def scenario():
        config = TmsConfig(daq=DaqConfig(sample_rate=1000, block_ms=10),
                           thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
                           logging=LoggingConfig(directory=tmp_path))
        errors = []
        backend = DashboardBackend(config, error_callback=errors.append)
        backend._loop = asyncio.get_running_loop()
        backend._active_session_id = "session"
        monkeypatch.setattr("laptop.backend.TRIGGER_DELIVERY_TIMEOUT_SEC", 0.05)
        backend._nano_trigger(replace(parse_nano_line("TRIGGER,1,123"), session_id="session"))
        await asyncio.sleep(0)
        with pytest.raises(TelemetryError, match="저장 확인을 기다리는"):
            await backend._finish_trigger_delivery()
        assert not backend._trigger_task.done()  # Reconnect can still deliver it.
        await backend._finish_trigger_delivery(abort_on_timeout=True, clear_session=True)
        assert len(errors) == 1
        assert "미확인 점화 신호 전달을 중단" in errors[0]
        assert backend._active_session_id is None
    asyncio.run(scenario())


@pytest.mark.parametrize("include_edges", [False, True])
def test_continuous_level_records_initial_high_and_only_edges_trigger(tmp_path, include_edges):
    async def scenario():
        config = TmsConfig(daq=DaqConfig(sample_rate=1000, block_ms=10),
                           thrust=ChannelConfig(0, 1, 0), pressure=ChannelConfig(1, 1, 0),
                           logging=LoggingConfig(directory=tmp_path))
        agent = TmsAgent(config, SimulatedDaqSource(config.daq, (0, 1)))
        server = TelemetryServer(agent, config, port=0)
        await server.start()
        nano = NanoSerialManager(config.nano)
        states, errors = [], []
        backend = DashboardBackend(config, nano_manager=nano, error_callback=errors.append,
                                   connection_callback=lambda *state: states.append(state))
        nano.level_callback = backend._nano_level
        try:
            await backend.telemetry.connect(port=server.port)
            await backend.start_session("LEVEL_HIGH_AT_START")

            async def frame(line):
                nano._handle_message(parse_nano_line(line))
                await asyncio.sleep(0)  # Queue the serial thread callback.
                await asyncio.wait_for(backend._nano_levels.join(), 2)
                await asyncio.sleep(0.035)

            await frame("HB,1,500,1")  # No ARM ACK required to log pin state.
            await frame("HB,2,1000,1")
            await frame("HB,3,1500,1")
            assert agent.status_snapshot()["trigger_sample"] is None
            if include_edges:
                await frame("STATE,4,1510,0")
                await frame("STATE,5,1540,1")
                first_trigger = agent.status_snapshot()["trigger_sample"]
                assert first_trigger is not None
                await frame("HB,6,2000,1")
                await frame("STATE,7,2010,0")
                await frame("STATE,8,2040,1")
                assert agent.status_snapshot()["trigger_sample"] == first_trigger
            await backend.stop_session()
            assert not errors
            with h5py.File(agent.log_path, "r") as data:
                events = data["events"][:]
                assert sum(events["event_type"] == b"nano_state") == (8 if include_edges else 3)
                assert sum(events["event_type"] == b"ignition") == int(include_edges)
            exported = export_csv(agent.log_path, agent.log_path.with_suffix(".csv"), chunk_samples=7)
            with exported.open(newline="") as source:
                rows = list(csv.DictReader(source))
            assert any(row["nano_gpio"] == "1" for row in rows)
            assert sum(int(row["nano_gpio_observed"]) for row in rows) == (8 if include_edges else 3)
            assert sum(int(row["ignition"]) for row in rows) == int(include_edges)
            if include_edges:
                assert any(row["nano_gpio"] == "0" for row in rows)
                assert sum(state[0] == "Trigger" and state[1].startswith("SAMPLE ") for state in states) == 1
            else:
                assert all(row["nano_gpio"] != "0" for row in rows)
                assert all(row["ignition_recorded"] == "0" for row in rows)
        finally:
            await backend.stop()
            await server.close()
    asyncio.run(scenario())
