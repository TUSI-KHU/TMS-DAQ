from __future__ import annotations

import contextlib
import threading
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Protocol

import serial
from serial.tools import list_ports

from common.config import NanoConfig


class NanoProtocolError(ValueError):
    """Raised for malformed Arduino Nano serial messages."""


class NanoMessageType(str, Enum):
    HELLO = "HELLO"
    HEARTBEAT = "HB"
    STATE = "STATE"
    TRIGGER = "TRIGGER"
    ARMED = "ARMED"


@dataclass(frozen=True)
class NanoMessage:
    message_type: NanoMessageType
    sequence: int | None = None
    uptime_ms: int | None = None
    gpio_state: bool | None = None
    version: str | None = None
    session_id: str | None = None


@dataclass(frozen=True)
class NanoStatus:
    connected: bool
    port: str | None
    state: str
    last_heartbeat_monotonic: float | None
    gpio_state: bool | None
    sequence_gaps: int


class SerialPortInfo(Protocol):
    device: str
    vid: int | None
    description: str | None
    manufacturer: str | None


MessageCallback = Callable[[NanoMessage], None]
StatusCallback = Callable[[NanoStatus], None]
SerialFactory = Callable[..., serial.SerialBase]
PortLister = Callable[[], Sequence[SerialPortInfo]]


def parse_nano_line(line: str) -> NanoMessage:
    fields = [field.strip() for field in line.strip().split(",")]
    if fields[:1] == [NanoMessageType.HELLO.value] and len(fields) == 2:
        if not fields[1]:
            raise NanoProtocolError("HELLO version is empty")
        return NanoMessage(NanoMessageType.HELLO, version=fields[1])
    if fields[:1] in ([NanoMessageType.HEARTBEAT.value], [NanoMessageType.STATE.value]) and len(fields) == 4:
        sequence = _nonnegative_int(fields[1], "level sequence")
        uptime = _nonnegative_int(fields[2], "level uptime")
        if fields[3] not in ("0", "1"):
            raise NanoProtocolError("level GPIO state must be 0 or 1")
        return NanoMessage(
            NanoMessageType(fields[0]),
            sequence=sequence,
            uptime_ms=uptime,
            gpio_state=fields[3] == "1",
        )
    if fields[:1] == [NanoMessageType.TRIGGER.value] and len(fields) == 3:
        return NanoMessage(
            NanoMessageType.TRIGGER,
            sequence=_nonnegative_int(fields[1], "trigger sequence"),
            uptime_ms=_nonnegative_int(fields[2], "trigger uptime"),
        )
    if fields[:1] == [NanoMessageType.ARMED.value] and len(fields) == 2:
        if not fields[1]:
            raise NanoProtocolError("ARMED session ID is empty")
        return NanoMessage(NanoMessageType.ARMED, session_id=fields[1])
    raise NanoProtocolError("unknown or malformed Nano message")


def choose_nano_port(
    ports: Sequence[SerialPortInfo], configured_port: str
) -> str | None:
    if configured_port.lower() != "auto":
        return configured_port
    candidates: list[tuple[int, str]] = []
    known_vids = {0x2341, 0x2A03, 0x1A86, 0x0403}
    for port in ports:
        description = (port.description or "").lower()
        manufacturer = (port.manufacturer or "").lower()
        score = 0
        if port.vid in known_vids:
            score += 10
        if "arduino" in description or "arduino" in manufacturer:
            score += 20
        if "ch340" in description or "usb serial" in description:
            score += 5
        if score:
            candidates.append((score, port.device))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][1]


class NanoSerialManager:
    """Actual pyserial connection manager with heartbeat and reconnect handling."""

    def __init__(
        self,
        config: NanoConfig,
        *,
        message_callback: MessageCallback | None = None,
        trigger_callback: MessageCallback | None = None,
        level_callback: MessageCallback | None = None,
        status_callback: StatusCallback | None = None,
        serial_factory: SerialFactory = serial.Serial,
        port_lister: PortLister = list_ports.comports,
    ) -> None:
        self.config = config
        self.message_callback = message_callback
        self.trigger_callback = trigger_callback
        self.level_callback = level_callback
        self.status_callback = status_callback
        self._serial_factory = serial_factory
        self._port_lister = port_lister
        self._serial: serial.SerialBase | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()
        self._state_lock = threading.RLock()
        self._pending_session_id: str | None = None
        self._armed_session_id: str | None = None
        self._session_generation = 0
        self._arm_sent_generation: int | None = None
        self._arm_pending = False
        self._last_arm_sent = 0.0
        self._first_heartbeat_pending = True
        self._trigger_seen = False
        self._last_sequence: int | None = None
        # A short history catches repeated USB serial frames without confusing
        # a real second level sample (new sequence/uptime) with a duplicate.
        self._seen_frames: deque[tuple[NanoMessageType, int, int | None]] = deque(maxlen=512)
        self._seen_frame_keys: set[tuple[NanoMessageType, int, int | None]] = set()
        self._hello_waiting_for_frame = False
        self._sequence_gaps = 0
        self._last_heartbeat: float | None = None
        self._gpio_state: bool | None = None
        self._port: str | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="nano-serial", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        self.disarm_session()
        self._stop_event.set()
        reader = self._thread
        if reader is not None:
            if reader is not threading.current_thread():
                # The serial read has a 0.2 s timeout. Let its owning thread
                # leave read()/select() before closing the descriptor: pyserial
                # can otherwise race close() and pass fd=None to os.read().
                reader.join(timeout)
            if reader.is_alive():
                # Do not close a descriptor still in use or forget this worker
                # and allow start() to create a second reader. Its finally
                # block remains responsible for eventual port cleanup.
                self._emit_status("STOPPING")
                return
        self._close_serial()
        self._thread = None
        self._emit_status("DISCONNECTED")

    def arm_session(self, session_id: str) -> None:
        session_id = session_id.strip()
        if (
            not session_id
            or not session_id.isascii()
            or len(session_id) > 59  # Firmware's 64-byte command buffer, including ARM, and NUL.
            or any(value in session_id for value in ",\r\n")
        ):
            raise ValueError("session_id contains invalid serial protocol characters")
        # Serial I/O belongs to the reader thread: opening a Nano resets it,
        # and a write/flush here can both block the GUI and disappear at boot.
        with self._state_lock:
            self._session_generation += 1
            self._pending_session_id = session_id
            self._armed_session_id = None
            self._arm_sent_generation = None
            self._trigger_seen = False
            self._arm_pending = True
        self._emit_status()

    def disarm_session(self) -> None:
        """Stop both local streams; return after accepted callbacks are queued."""
        with self._state_lock:
            self._session_generation += 1
            self._pending_session_id = None
            self._armed_session_id = None
            self._arm_sent_generation = None
            self._arm_pending = False
            self._trigger_seen = False
        self._emit_status()

    def status(self, state: str | None = None) -> NanoStatus:
        with self._state_lock:
            connected = self._serial is not None and self._serial.is_open
            if not state:
                state = "CONNECTED" if connected else "DISCONNECTED"
                if connected and self._pending_session_id is not None:
                    if self._trigger_seen:
                        state = "TRIGGERED"
                    elif self._armed_session_id == self._pending_session_id:
                        state = "ARMED"
                    else:
                        state = "ARMING"
            return NanoStatus(
                connected=connected,
                port=self._port,
                state=state,
                last_heartbeat_monotonic=self._last_heartbeat,
                gpio_state=self._gpio_state,
                sequence_gaps=self._sequence_gaps,
            )

    def _run(self) -> None:
        delays = (1.0, 2.0, 5.0, 10.0)
        attempt = 0
        while not self._stop_event.is_set():
            try:
                port = choose_nano_port(self._port_lister(), self.config.port)
                if port is None:
                    self._emit_status("NOT_FOUND")
                    self._stop_event.wait(delays[min(attempt, len(delays) - 1)])
                    attempt += 1
                    continue
                self._port = port
                self._serial = self._serial_factory(
                    port=port,
                    baudrate=self.config.baudrate,
                    timeout=0.2,
                    write_timeout=0.5,
                )
                attempt = 0
                self._last_heartbeat = time.monotonic()
                self._emit_status()
                self._read_connected()
            except (OSError, serial.SerialException):
                self._emit_status("RECONNECTING")
            finally:
                self._close_serial()
                if self._stop_event.is_set():
                    self._emit_status("DISCONNECTED")

            if not self._stop_event.is_set():
                self._stop_event.wait(delays[min(attempt, len(delays) - 1)])
                attempt += 1

    def _read_connected(self) -> None:
        serial_port = self._serial
        assert serial_port is not None
        while not self._stop_event.is_set() and serial_port.is_open:
            self._send_pending_arm()
            raw = serial_port.readline()
            if raw:
                try:
                    line = raw.decode("ascii").strip()
                    message = parse_nano_line(line)
                except (UnicodeDecodeError, NanoProtocolError):
                    continue
                self._handle_message(message)
            now = time.monotonic()
            if (
                self._last_heartbeat is not None
                and now - self._last_heartbeat > self.config.heartbeat_timeout_sec
            ):
                self._emit_status("HEARTBEAT_TIMEOUT")
                return

    def _handle_message(self, message: NanoMessage) -> None:
        emit_status = False
        with self._state_lock:
            if message.sequence is not None:
                frame_key = (message.message_type, message.sequence, message.uptime_ms)
                if frame_key in self._seen_frame_keys:
                    return
                if len(self._seen_frames) == self._seen_frames.maxlen:
                    self._seen_frame_keys.discard(self._seen_frames[0])
                self._seen_frames.append(frame_key)
                self._seen_frame_keys.add(frame_key)
                self._hello_waiting_for_frame = False
                if (
                    self._last_sequence is not None
                    and message.sequence != (self._last_sequence + 1) % (2**32)
                ):
                    self._sequence_gaps += 1
                    # Missing frames can include a reset or unseen transitions.
                    # The next HIGH is a fresh observation, not a known edge.
                    self._invalidate_level()
                self._last_sequence = message.sequence
            if message.message_type == NanoMessageType.HELLO:
                # Some USB serial startup bursts repeat HELLO many times.
                # A new boot boundary is meaningful only after fresh sequenced
                # traffic, or after a physical connection has been reopened.
                if self._hello_waiting_for_frame:
                    return
                self._hello_waiting_for_frame = True
                self._seen_frames.clear()
                self._seen_frame_keys.clear()
                self._last_sequence = None
                self._invalidate_level()
                self._last_heartbeat = time.monotonic()
                self._armed_session_id = None
                self._arm_sent_generation = None
                self._first_heartbeat_pending = False
                self._arm_pending = bool(self._pending_session_id and not self._trigger_seen)
                emit_status = True
            elif message.message_type in (NanoMessageType.HEARTBEAT, NanoMessageType.STATE):
                self._last_heartbeat = time.monotonic()
                self._gpio_state = message.gpio_state
                if self._pending_session_id is not None:
                    message = replace(message, session_id=self._pending_session_id)
                    # This stream does not depend on ARM acknowledgements or
                    # the once-per-session legacy TRIGGER latch.
                    if self.level_callback is not None:
                        self.level_callback(message)
                # HELLO may be lost at serial-open. A heartbeat proves the
                # firmware is now running; retry until it acknowledges ARM.
                if (
                    self._pending_session_id is not None
                    and self._armed_session_id is None
                    and not self._trigger_seen
                    and (
                        self._first_heartbeat_pending
                        or self._last_heartbeat - self._last_arm_sent >= 0.5
                    )
                ):
                    self._arm_pending = True
                self._first_heartbeat_pending = False
                emit_status = True
            elif message.message_type == NanoMessageType.ARMED:
                if (
                    self._pending_session_id is not None
                    and message.session_id == self._pending_session_id
                    and self._arm_sent_generation == self._session_generation
                    and not self._trigger_seen
                ):
                    self._armed_session_id = message.session_id
                    self._arm_pending = False
                    emit_status = True
            elif message.message_type == NanoMessageType.TRIGGER:
                if (
                    self._pending_session_id is not None
                    and self._armed_session_id == self._pending_session_id
                    and not self._trigger_seen
                ):
                    self._trigger_seen = True
                    self._arm_pending = False
                    message = replace(message, session_id=self._pending_session_id)
                    emit_status = True
                    # The backend callback only schedules async delivery. Keep
                    # that enqueue inside the lock so disarm_session() cannot
                    # return before an already accepted edge has been queued.
                    if self.trigger_callback is not None:
                        self.trigger_callback(message)
        if emit_status:
            self._emit_status()
        if self.message_callback is not None:
            self.message_callback(message)

    def _send_pending_arm(self) -> None:
        with self._state_lock:
            if not self._arm_pending or self._pending_session_id is None or self._trigger_seen:
                return
            session_id = self._pending_session_id
            generation = self._session_generation
            self._arm_pending = False
        sent = self._write_line(f"ARM,{session_id}")
        with self._state_lock:
            if generation != self._session_generation:
                return
            if sent:
                self._arm_sent_generation = generation
                self._last_arm_sent = time.monotonic()
            else:
                self._arm_pending = True

    def _write_line(self, line: str) -> bool:
        with self._write_lock:
            serial_port = self._serial
            if serial_port is None or not serial_port.is_open:
                return False
            try:
                data = (line + "\n").encode("ascii")
                return serial_port.write(data) == len(data)
            except (OSError, serial.SerialException):
                self._close_serial()
                return False

    def _close_serial(self) -> None:
        with self._state_lock:
            serial_port = self._serial
            if serial_port is not None or self._gpio_state is not None:
                self._invalidate_level()
            self._serial = None
            self._armed_session_id = None
            self._arm_sent_generation = None
            self._last_sequence = None
            self._seen_frames.clear()
            self._seen_frame_keys.clear()
            self._hello_waiting_for_frame = False
            self._first_heartbeat_pending = True
            self._arm_pending = bool(self._pending_session_id and not self._trigger_seen)
        if serial_port is not None:
            with contextlib.suppress(OSError, serial.SerialException):
                serial_port.close()

    def _invalidate_level(self) -> None:
        """Call with _state_lock held; unknown is never equivalent to LOW."""
        self._gpio_state = None
        if self._pending_session_id is not None and self.level_callback is not None:
            self.level_callback(
                NanoMessage(NanoMessageType.STATE, session_id=self._pending_session_id)
            )

    def _emit_status(self, state: str | None = None) -> None:
        if self.status_callback is not None:
            with contextlib.suppress(Exception):
                self.status_callback(self.status(state))


def _nonnegative_int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise NanoProtocolError(f"{label} is not an integer") from exc
    if parsed < 0:
        raise NanoProtocolError(f"{label} must not be negative")
    return parsed
