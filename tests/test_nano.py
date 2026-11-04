from dataclasses import dataclass
from threading import Event, Thread

import pytest

from common.config import NanoConfig
from laptop.nano import (
    NanoMessage,
    NanoMessageType,
    NanoProtocolError,
    NanoSerialManager,
    choose_nano_port,
    parse_nano_line,
)


@dataclass
class Port:
    device: str
    vid: int | None
    description: str | None
    manufacturer: str | None


def test_nano_protocol_parser() -> None:
    heartbeat = parse_nano_line("HB,101,50000,1")
    state = parse_nano_line("STATE,103,51000,0")
    trigger = parse_nano_line("TRIGGER,102,50731")
    armed = parse_nano_line("ARMED,session-1")

    assert heartbeat.message_type == NanoMessageType.HEARTBEAT
    assert heartbeat.sequence == 101
    assert heartbeat.gpio_state is True
    assert state.message_type == NanoMessageType.STATE
    assert state.sequence == 103
    assert state.uptime_ms == 51000
    assert state.gpio_state is False
    assert trigger.message_type == NanoMessageType.TRIGGER
    assert trigger.uptime_ms == 50731
    assert armed.session_id == "session-1"


@pytest.mark.parametrize("line", ["HB,1,500,2", "STATE,1,500,2", "STATE,1,500,", "STATE,-1,500,0"])
def test_nano_protocol_rejects_invalid_gpio(line: str) -> None:
    with pytest.raises(NanoProtocolError):
        parse_nano_line(line)


def test_auto_port_prefers_arduino() -> None:
    ports = [
        Port("COM3", 0x0403, "USB Serial", "FTDI"),
        Port("COM7", 0x2341, "Arduino Nano", "Arduino"),
    ]

    assert choose_nano_port(ports, "auto") == "COM7"
    assert choose_nano_port(ports, "COM9") == "COM9"


class FakeSerial:
    def __init__(self) -> None:
        self.is_open = True
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def close(self) -> None:
        self.is_open = False


def connected_manager() -> tuple[NanoSerialManager, FakeSerial, list[NanoMessage]]:
    received: list[NanoMessage] = []
    manager = NanoSerialManager(NanoConfig(), trigger_callback=received.append)
    port = FakeSerial()
    manager._serial = port
    return manager, port, received


def handle(manager: NanoSerialManager, line: str) -> None:
    manager._handle_message(parse_nano_line(line))


def test_arm_is_nonblocking_and_requires_matching_ack() -> None:
    manager, port, received = connected_manager()

    manager.arm_session("session-1")
    assert port.writes == []  # The GUI thread does not touch the serial port.
    assert manager.status().state == "ARMING"
    handle(manager, "ARMED,session-1")  # Cannot acknowledge an unsent request.
    handle(manager, "TRIGGER,1,100")
    assert received == []

    manager._send_pending_arm()
    assert port.writes == [b"ARM,session-1\n"]
    handle(manager, "ARMED,old-session")
    handle(manager, "TRIGGER,2,200")
    assert received == []
    handle(manager, "ARMED,session-1")
    assert manager.status().state == "ARMED"
    handle(manager, "TRIGGER,3,300")
    handle(manager, "TRIGGER,4,400")
    assert len(received) == 1
    assert received[0].session_id == "session-1"
    assert received[0].sequence == 3
    assert received[0].uptime_ms == 300
    assert manager.status().state == "TRIGGERED"


@pytest.mark.parametrize("boot_line", ["HELLO,1.0", "HB,1,500,0"])
def test_boot_message_retries_arm_lost_to_nano_reset(boot_line: str) -> None:
    manager, port, received = connected_manager()
    manager.arm_session("session-1")
    manager._send_pending_arm()

    # Opening USB serial resets a Nano: the first ARM may reach its bootloader.
    handle(manager, boot_line)
    manager._send_pending_arm()
    assert port.writes == [b"ARM,session-1\n", b"ARM,session-1\n"]
    handle(manager, "ARMED,session-1")
    handle(manager, "TRIGGER,2,700")
    assert [message.session_id for message in received] == ["session-1"]


def test_heartbeat_retries_until_arm_ack_but_not_after_ack() -> None:
    manager, port, _ = connected_manager()
    manager.arm_session("session-1")
    manager._send_pending_arm()
    handle(manager, "HELLO,1.0")
    manager._send_pending_arm()
    manager._last_arm_sent -= 1.0
    handle(manager, "HB,1,500,0")
    manager._send_pending_arm()
    assert len(port.writes) == 3

    handle(manager, "ARMED,session-1")
    manager._last_arm_sent -= 1.0
    handle(manager, "HB,2,1000,0")
    manager._send_pending_arm()
    assert len(port.writes) == 3
    assert manager.status().state == "ARMED"


def test_disarm_rejects_idle_edges_and_repeated_sessions_rearm() -> None:
    manager, port, received = connected_manager()
    handle(manager, "TRIGGER,1,100")
    handle(manager, "ARMED,session-1")
    assert received == []

    for index in (1, 2):
        session_id = f"session-{index}"
        manager.arm_session(session_id)
        manager._send_pending_arm()
        handle(manager, f"ARMED,{session_id}")
        handle(manager, f"TRIGGER,{index + 1},{index * 200}")
        manager.disarm_session()
        assert manager.status().state == "CONNECTED"
        handle(manager, f"ARMED,{session_id}")
        handle(manager, "TRIGGER,99,999")
    assert [message.session_id for message in received] == ["session-1", "session-2"]
    assert port.writes == [b"ARM,session-1\n", b"ARM,session-2\n"]


def test_reconnect_requires_new_ack_without_forgetting_accepted_trigger() -> None:
    manager, _, received = connected_manager()
    manager.arm_session("session-1")
    manager._send_pending_arm()
    handle(manager, "ARMED,session-1")
    manager._close_serial()

    port = FakeSerial()
    manager._serial = port
    handle(manager, "TRIGGER,1,100")
    assert received == []
    manager._send_pending_arm()
    handle(manager, "ARMED,session-1")
    handle(manager, "TRIGGER,2,200")
    assert len(received) == 1

    manager._close_serial()
    port = FakeSerial()
    manager._serial = port
    handle(manager, "HELLO,1.0")
    handle(manager, "HB,1,500,0")
    manager._send_pending_arm()
    handle(manager, "ARMED,session-1")
    handle(manager, "TRIGGER,2,600")
    assert port.writes == []
    assert len(received) == 1


def test_arm_can_be_queued_while_nano_is_absent() -> None:
    received: list[NanoMessage] = []
    manager = NanoSerialManager(NanoConfig(), trigger_callback=received.append)
    manager.arm_session("session-1")
    manager._send_pending_arm()
    handle(manager, "TRIGGER,1,100")
    assert received == []
    port = FakeSerial()
    manager._serial = port
    manager._send_pending_arm()
    assert port.writes == [b"ARM,session-1\n"]
    handle(manager, "ARMED,session-1")
    handle(manager, "TRIGGER,2,200")
    assert len(received) == 1


def test_session_change_during_serial_write_does_not_accept_old_ack() -> None:
    manager, _, received = connected_manager()

    class RacingSerial(FakeSerial):
        def write(self, data: bytes) -> int:
            count = super().write(data)
            if data == b"ARM,old-session\n":
                manager.arm_session("new-session")
            return count

    port = RacingSerial()
    manager._serial = port
    manager.arm_session("old-session")
    manager._send_pending_arm()
    handle(manager, "ARMED,old-session")
    handle(manager, "TRIGGER,1,100")
    assert received == []
    manager._send_pending_arm()
    handle(manager, "ARMED,new-session")
    handle(manager, "TRIGGER,2,200")
    assert port.writes == [b"ARM,old-session\n", b"ARM,new-session\n"]
    assert [message.session_id for message in received] == ["new-session"]


@pytest.mark.parametrize("boot_line", [b"HELLO,1.0\n", b"HB,1,500,0\n"])
def test_serial_worker_rearms_after_boot_and_delivers_session_trigger(boot_line: bytes) -> None:
    manager, _, received = connected_manager()

    class BootingSerial(FakeSerial):
        def __init__(self) -> None:
            super().__init__()
            self.lines = iter([boot_line, b"ARMED,session-1\n", b"TRIGGER,2,700\n"])

        def readline(self) -> bytes:
            value = next(self.lines, b"")
            if not value:
                manager._stop_event.set()
            return value

    port = BootingSerial()
    manager._serial = port
    manager.arm_session("session-1")
    manager._read_connected()
    assert port.writes == [b"ARM,session-1\n", b"ARM,session-1\n"]
    assert [message.session_id for message in received] == ["session-1"]


def test_disarm_waits_until_an_already_accepted_trigger_callback_is_queued() -> None:
    manager, _, _ = connected_manager()
    callback_started = Event()
    callback_release = Event()
    disarm_started = Event()
    disarm_done = Event()

    def callback(_message: NanoMessage) -> None:
        callback_started.set()
        callback_release.wait(1.0)

    def disarm() -> None:
        disarm_started.set()
        manager.disarm_session()
        disarm_done.set()

    manager.trigger_callback = callback
    manager.arm_session("session-1")
    manager._send_pending_arm()
    handle(manager, "ARMED,session-1")
    receiver = Thread(target=handle, args=(manager, "TRIGGER,1,100"))
    stopper = Thread(target=disarm)
    receiver.start()
    try:
        assert callback_started.wait(1.0)
        stopper.start()
        assert disarm_started.wait(1.0)
        assert not disarm_done.wait(0.02)
    finally:
        callback_release.set()
        receiver.join(1.0)
        if stopper.ident is not None:
            stopper.join(1.0)
    assert disarm_done.is_set()
    assert manager.status().state == "CONNECTED"


@pytest.mark.parametrize("session_id", ["", "x,y", "x\ny", "x\ry", "한글", "x" * 60])
def test_arm_rejects_invalid_or_firmware_oversized_session(session_id: str) -> None:
    manager, _, _ = connected_manager()
    with pytest.raises(ValueError):
        manager.arm_session(session_id)


def test_levels_record_initial_high_without_ack_or_synthetic_trigger() -> None:
    manager, _, triggers = connected_manager()
    levels: list[NanoMessage] = []
    manager.level_callback = levels.append
    handle(manager, "HB,1,500,1")
    assert levels == []  # Idle observations must not leak into a later session.
    manager.arm_session("already-high")
    handle(manager, "HB,2,1000,1")
    handle(manager, "STATE,3,1010,1")
    handle(manager, "HB,4,1500,1")
    assert triggers == []
    assert [message.gpio_state for message in levels] == [True, True, True]
    assert [message.sequence for message in levels] == [2, 3, 4]
    assert [message.uptime_ms for message in levels] == [1000, 1010, 1500]
    assert {message.session_id for message in levels} == {"already-high"}
    assert manager.status().state == "ARMING"


def test_levels_continue_for_high_low_and_repeated_edges_after_trigger() -> None:
    manager, _, triggers = connected_manager()
    levels: list[NanoMessage] = []
    manager.level_callback = levels.append
    manager.arm_session("session-1")
    manager._send_pending_arm()
    for line in (
        "ARMED,session-1", "STATE,1,100,0", "TRIGGER,2,200",
        "STATE,3,200,1", "HB,4,500,1", "STATE,5,600,0",
        "STATE,6,700,1", "HB,7,1000,1", "STATE,8,1100,0",
    ):
        handle(manager, line)
    assert len(triggers) == 1
    assert [message.gpio_state for message in levels] == [False, True, True, False, True, True, False]
    assert manager.status().state == "TRIGGERED"
    manager.disarm_session()
    handle(manager, "HB,9,1500,1")
    assert len(levels) == 7


def test_duplicate_serial_frames_do_not_duplicate_levels_or_sequence_gaps() -> None:
    manager, _, _ = connected_manager()
    levels: list[NanoMessage] = []
    manager.level_callback = levels.append
    manager.arm_session("session-1")
    for line in ("HB,1,500,0", "STATE,2,600,1", "HB,1,500,0", "STATE,2,600,1", "HB,3,1000,1"):
        handle(manager, line)
    assert [message.sequence for message in levels] == [1, 2, 3]
    assert manager.status().sequence_gaps == 0
    assert manager.status().gpio_state is True


@pytest.mark.parametrize("boundary", ["HELLO,1.1", "disconnect", "gap"])
def test_level_stream_marks_unknown_across_reset_disconnect_and_missing_frames(boundary: str) -> None:
    manager, _, triggers = connected_manager()
    levels: list[NanoMessage] = []
    manager.level_callback = levels.append
    manager.arm_session("session-1")
    handle(manager, "HB,1,500,0")
    if boundary == "disconnect":
        manager._close_serial()
        assert manager.status().gpio_state is None
        manager._serial = FakeSerial()
    elif boundary != "gap":
        handle(manager, boundary)
        assert manager.status().gpio_state is None
    handle(manager, "HB,3,1500,1" if boundary == "gap" else "HB,1,500,1")
    assert [message.gpio_state for message in levels] == [False, None, True]
    assert all(message.session_id == "session-1" for message in levels)
    assert levels[1].sequence is None
    assert triggers == []


def test_sequence_counter_wrap_keeps_continuous_level_stream() -> None:
    manager, _, _ = connected_manager()
    levels: list[NanoMessage] = []
    manager.level_callback = levels.append
    manager.arm_session("session-1")
    handle(manager, "HB,4294967295,500,0")
    handle(manager, "STATE,0,510,1")
    assert [message.gpio_state for message in levels] == [False, True]
    assert manager.status().sequence_gaps == 0


def test_disarm_waits_for_accepted_level_callback() -> None:
    manager, _, _ = connected_manager()
    started, release, stopped = Event(), Event(), Event()

    def callback(_message: NanoMessage) -> None:
        started.set()
        release.wait(1)

    def stop() -> None:
        manager.disarm_session()
        stopped.set()

    manager.level_callback = callback
    manager.arm_session("session-1")
    receiver = Thread(target=handle, args=(manager, "HB,1,500,1"))
    stopper = Thread(target=stop)
    receiver.start()
    try:
        assert started.wait(1)
        stopper.start()
        assert not stopped.wait(0.02)
    finally:
        release.set()
        receiver.join(1)
        if stopper.ident is not None:
            stopper.join(1)
    assert stopped.is_set()


def test_disconnected_polling_does_not_emit_duplicate_unknown_levels() -> None:
    manager, _, _ = connected_manager()
    levels: list[NanoMessage] = []
    manager.level_callback = levels.append
    manager.arm_session("session-1")
    manager._close_serial()
    manager._close_serial()
    manager._close_serial()
    assert len(levels) == 1
    assert levels[0].gpio_state is None


def test_startup_hello_burst_emits_one_unknown_until_fresh_sequenced_frame() -> None:
    manager, port, _ = connected_manager()
    levels: list[NanoMessage] = []
    messages: list[NanoMessage] = []
    manager.level_callback = levels.append
    manager.message_callback = messages.append
    manager.arm_session("session-1")
    manager._send_pending_arm()
    handle(manager, "HELLO,1.1")
    manager._send_pending_arm()
    handle(manager, "ARMED,session-1")
    for _ in range(5000):
        handle(manager, "HELLO,1.1")
        manager._send_pending_arm()
    assert len(levels) == 1
    assert levels[0].gpio_state is None
    assert [message.message_type for message in messages].count(NanoMessageType.HELLO) == 1
    assert port.writes == [b"ARM,session-1\n", b"ARM,session-1\n"]
    assert manager.status().state == "ARMED"

    # A real HELLO after accepted data must still break the known level.
    handle(manager, "HB,1,500,0")
    handle(manager, "HELLO,1.1")
    handle(manager, "HB,1,500,1")
    assert [message.gpio_state for message in levels] == [None, False, None, True]
    assert manager.status().state == "ARMING"


def test_reopened_serial_accepts_hello_even_if_prior_connection_only_sent_hello() -> None:
    manager, _, _ = connected_manager()
    levels: list[NanoMessage] = []
    messages: list[NanoMessage] = []
    manager.level_callback = levels.append
    manager.message_callback = messages.append
    manager.arm_session("session-1")
    handle(manager, "HELLO,1.1")
    manager._close_serial()
    manager._serial = FakeSerial()
    handle(manager, "HELLO,1.1")
    assert [message.message_type for message in messages] == [NanoMessageType.HELLO] * 2
    assert len(levels) == 3  # First boot, disconnect, second boot.
    assert all(message.gpio_state is None for message in levels)


@pytest.mark.parametrize("timeout", [1.0, 0.0])
def test_stop_does_not_close_fd_while_reader_is_using_it(timeout: float) -> None:
    reading, release, closed = Event(), Event(), Event()
    close_while_reading: list[bool] = []
    statuses = []

    class ReadingSerial(FakeSerial):
        def readline(self) -> bytes:
            reading.set()
            release.wait(1)
            reading.clear()
            return b""

        def close(self) -> None:
            close_while_reading.append(reading.is_set())
            super().close()
            closed.set()

    port = ReadingSerial()
    manager = NanoSerialManager(
        NanoConfig(port="TEST_NANO"),
        serial_factory=lambda **kwargs: port,
        status_callback=statuses.append,
    )
    stopper = Thread(target=manager.stop, kwargs={"timeout": timeout})
    manager.start()
    reader = manager._thread
    try:
        assert reading.wait(1)
        stopper.start()
        assert manager._stop_event.wait(1)
        if timeout == 0:
            stopper.join(1)
            assert manager._thread is reader
            assert reader.is_alive()
            assert not closed.is_set()
            manager.start()
            assert manager._thread is reader  # No competing second reader.
            assert statuses[-1].state == "STOPPING"
        else:
            assert not closed.wait(0.02)
    finally:
        release.set()
        if stopper.ident is not None:
            stopper.join(1)
        reader.join(1)
        manager.stop()
    assert closed.is_set()
    assert close_while_reading == [False]
    assert manager._thread is None
    assert statuses[-1].state == "DISCONNECTED"


def test_unrelated_readline_typeerror_is_not_swallowed() -> None:
    manager, _, _ = connected_manager()

    class BrokenSerial(FakeSerial):
        def readline(self) -> bytes:
            raise TypeError("unrelated serial implementation bug")

    manager._serial = BrokenSerial()
    with pytest.raises(TypeError, match="unrelated serial implementation bug"):
        manager._read_connected()
