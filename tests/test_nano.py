from dataclasses import dataclass

import pytest

from laptop.nano import (
    NanoMessageType,
    NanoProtocolError,
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
    trigger = parse_nano_line("TRIGGER,102,50731")
    armed = parse_nano_line("ARMED,session-1")

    assert heartbeat.message_type == NanoMessageType.HEARTBEAT
    assert heartbeat.sequence == 101
    assert heartbeat.gpio_state is True
    assert trigger.message_type == NanoMessageType.TRIGGER
    assert trigger.uptime_ms == 50731
    assert armed.session_id == "session-1"


def test_nano_protocol_rejects_invalid_gpio() -> None:
    with pytest.raises(NanoProtocolError):
        parse_nano_line("HB,1,500,2")


def test_auto_port_prefers_arduino() -> None:
    ports = [
        Port("COM3", 0x0403, "USB Serial", "FTDI"),
        Port("COM7", 0x2341, "Arduino Nano", "Arduino"),
    ]

    assert choose_nano_port(ports, "auto") == "COM7"
    assert choose_nano_port(ports, "COM9") == "COM9"
