from __future__ import annotations

import asyncio
import json
import struct
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from numpy.typing import NDArray

PROTOCOL_VERSION = 1
HEADER_SIZE = struct.Struct("!I")
MAX_HEADER_BYTES = 64 * 1024
MAX_PAYLOAD_BYTES = 32 * 1024 * 1024


class ProtocolError(ValueError):
    """Raised for malformed or unsupported TMS wire messages."""


class MessageType(str, Enum):
    HELLO = "HELLO"
    HEALTH = "HEALTH"
    START_SESSION = "START_SESSION"
    STOP_SESSION = "STOP_SESSION"
    DAQ_DATA = "DAQ_DATA"
    TRIGGER = "TRIGGER"
    TRIGGER_ACK = "TRIGGER_ACK"
    CONFIG = "CONFIG"
    PING = "PING"
    ACK = "ACK"
    ERROR = "ERROR"


@dataclass(frozen=True)
class WireMessage:
    message_type: MessageType
    body: dict[str, Any] = field(default_factory=dict)
    payload: bytes = b""
    request_id: str | None = None


@dataclass(frozen=True)
class TelemetryBlock:
    sequence: int
    first_sample_index: int
    sample_rate: int
    channel_names: tuple[str, ...]
    values: NDArray[np.float32]

    @property
    def sample_count(self) -> int:
        return int(self.values.shape[0])


def new_request_id() -> str:
    return uuid.uuid4().hex


def encode_message(message: WireMessage) -> bytes:
    if len(message.payload) > MAX_PAYLOAD_BYTES:
        raise ProtocolError("message payload is too large")

    header = {
        "protocol_version": PROTOCOL_VERSION,
        "type": message.message_type.value,
        "request_id": message.request_id,
        "body": message.body,
        "payload_length": len(message.payload),
    }
    try:
        encoded_header = json.dumps(
            header, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"message body is not JSON serializable: {exc}") from exc

    if not encoded_header or len(encoded_header) > MAX_HEADER_BYTES:
        raise ProtocolError("message header size is invalid")
    return HEADER_SIZE.pack(len(encoded_header)) + encoded_header + message.payload


def decode_message(data: bytes) -> WireMessage:
    if len(data) < HEADER_SIZE.size:
        raise ProtocolError("message is shorter than the header prefix")
    header_length = HEADER_SIZE.unpack_from(data)[0]
    if not 0 < header_length <= MAX_HEADER_BYTES:
        raise ProtocolError("message header length is invalid")
    header_end = HEADER_SIZE.size + header_length
    if len(data) < header_end:
        raise ProtocolError("message header is incomplete")
    header = _decode_header(data[HEADER_SIZE.size : header_end])
    payload_length = _payload_length(header)
    if len(data) != header_end + payload_length:
        raise ProtocolError("message payload length does not match its header")
    return _wire_message(header, data[header_end:])


async def read_message(reader: asyncio.StreamReader) -> WireMessage:
    prefix = await reader.readexactly(HEADER_SIZE.size)
    header_length = HEADER_SIZE.unpack(prefix)[0]
    if not 0 < header_length <= MAX_HEADER_BYTES:
        raise ProtocolError("message header length is invalid")
    header = _decode_header(await reader.readexactly(header_length))
    payload_length = _payload_length(header)
    payload = await reader.readexactly(payload_length) if payload_length else b""
    return _wire_message(header, payload)


async def write_message(writer: asyncio.StreamWriter, message: WireMessage) -> None:
    writer.write(encode_message(message))
    await writer.drain()


def make_daq_data_message(
    *,
    sequence: int,
    first_sample_index: int,
    sample_rate: int,
    channel_names: tuple[str, ...],
    values: NDArray[np.floating],
) -> WireMessage:
    matrix = np.asarray(values, dtype="<f4", order="C")
    if matrix.ndim != 2 or matrix.shape[1] != len(channel_names):
        raise ProtocolError("DAQ values must have shape (samples, channels)")
    return WireMessage(
        MessageType.DAQ_DATA,
        body={
            "sequence": sequence,
            "first_sample_index": first_sample_index,
            "sample_rate": sample_rate,
            "sample_count": int(matrix.shape[0]),
            "channel_names": list(channel_names),
            "dtype": "<f4",
        },
        payload=matrix.tobytes(order="C"),
    )


def decode_daq_data(message: WireMessage) -> TelemetryBlock:
    if message.message_type != MessageType.DAQ_DATA:
        raise ProtocolError("message is not DAQ_DATA")
    body = message.body
    try:
        sample_count = int(body["sample_count"])
        channel_names = tuple(str(value) for value in body["channel_names"])
        if body["dtype"] != "<f4":
            raise ProtocolError(f"unsupported DAQ dtype: {body['dtype']}")
        expected_bytes = sample_count * len(channel_names) * 4
        if expected_bytes != len(message.payload):
            raise ProtocolError("DAQ payload size does not match its dimensions")
        values = np.frombuffer(message.payload, dtype="<f4").reshape(
            sample_count, len(channel_names)
        )
        return TelemetryBlock(
            sequence=int(body["sequence"]),
            first_sample_index=int(body["first_sample_index"]),
            sample_rate=int(body["sample_rate"]),
            channel_names=channel_names,
            values=values,
        )
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, ProtocolError):
            raise
        raise ProtocolError(f"invalid DAQ_DATA metadata: {exc}") from exc


def _decode_header(data: bytes) -> dict[str, Any]:
    try:
        header = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("message header is not valid UTF-8 JSON") from exc
    if not isinstance(header, dict):
        raise ProtocolError("message header must be a JSON object")
    if header.get("protocol_version") != PROTOCOL_VERSION:
        raise ProtocolError("unsupported protocol version")
    return header


def _payload_length(header: dict[str, Any]) -> int:
    try:
        length = int(header["payload_length"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProtocolError("payload_length is missing or invalid") from exc
    if not 0 <= length <= MAX_PAYLOAD_BYTES:
        raise ProtocolError("message payload length is invalid")
    return length


def _wire_message(header: dict[str, Any], payload: bytes) -> WireMessage:
    try:
        message_type = MessageType(header["type"])
    except (KeyError, ValueError) as exc:
        raise ProtocolError("unknown message type") from exc
    body = header.get("body", {})
    if not isinstance(body, dict):
        raise ProtocolError("message body must be a JSON object")
    request_id = header.get("request_id")
    if request_id is not None and not isinstance(request_id, str):
        raise ProtocolError("request_id must be a string or null")
    return WireMessage(message_type, body, payload, request_id)
