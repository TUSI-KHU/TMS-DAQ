from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
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
    if fields[:1] == [NanoMessageType.HEARTBEAT.value] and len(fields) == 4:
        sequence = _nonnegative_int(fields[1], "heartbeat sequence")
        uptime = _nonnegative_int(fields[2], "heartbeat uptime")
        if fields[3] not in ("0", "1"):
            raise NanoProtocolError("heartbeat GPIO state must be 0 or 1")
        return NanoMessage(
            NanoMessageType.HEARTBEAT,
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
        status_callback: StatusCallback | None = None,
        serial_factory: SerialFactory = serial.Serial,
        port_lister: PortLister = list_ports.comports,
    ) -> None:
        self.config = config
        self.message_callback = message_callback
        self.trigger_callback = trigger_callback
        self.status_callback = status_callback
        self._serial_factory = serial_factory
        self._port_lister = port_lister
        self._serial: serial.SerialBase | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()
        self._pending_session_id: str | None = None
        self._trigger_seen = False
        self._last_sequence: int | None = None
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
        self._stop_event.set()
        self._close_serial()
        if self._thread is not None:
            self._thread.join(timeout)
        self._thread = None
        self._emit_status("DISCONNECTED")

    def arm_session(self, session_id: str) -> None:
        session_id = session_id.strip()
        if not session_id or any(value in session_id for value in ",\r\n"):
            raise ValueError("session_id contains invalid serial protocol characters")
        self._pending_session_id = session_id
        self._trigger_seen = False
        self._write_line(f"ARM,{session_id}")

    def status(self, state: str | None = None) -> NanoStatus:
        connected = self._serial is not None and self._serial.is_open
        return NanoStatus(
            connected=connected,
            port=self._port,
            state=state or ("CONNECTED" if connected else "DISCONNECTED"),
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
                self._emit_status("CONNECTED")
                if self._pending_session_id:
                    self._write_line(f"ARM,{self._pending_session_id}")
                self._read_connected()
            except (OSError, serial.SerialException):
                self._emit_status("RECONNECTING")
            finally:
                self._close_serial()

            if not self._stop_event.is_set():
                self._stop_event.wait(delays[min(attempt, len(delays) - 1)])
                attempt += 1

    def _read_connected(self) -> None:
        serial_port = self._serial
        assert serial_port is not None
        while not self._stop_event.is_set() and serial_port.is_open:
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
        if message.sequence is not None:
            if (
                self._last_sequence is not None
                and message.sequence != self._last_sequence + 1
            ):
                self._sequence_gaps += 1
            self._last_sequence = message.sequence
        if message.message_type == NanoMessageType.HEARTBEAT:
            self._last_heartbeat = time.monotonic()
            self._gpio_state = message.gpio_state
            self._emit_status("CONNECTED")
        elif message.message_type == NanoMessageType.TRIGGER:
            if not self._trigger_seen:
                self._trigger_seen = True
                if self.trigger_callback is not None:
                    self.trigger_callback(message)
        if self.message_callback is not None:
            self.message_callback(message)

    def _write_line(self, line: str) -> None:
        with self._write_lock:
            if self._serial is None or not self._serial.is_open:
                return
            try:
                self._serial.write((line + "\n").encode("ascii"))
                self._serial.flush()
            except (OSError, serial.SerialException):
                self._close_serial()

    def _close_serial(self) -> None:
        serial_port = self._serial
        self._serial = None
        if serial_port is not None:
            with contextlib.suppress(OSError, serial.SerialException):
                serial_port.close()

    def _emit_status(self, state: str) -> None:
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
