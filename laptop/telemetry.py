from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any

from common.protocol import (
    MessageType,
    TelemetryBlock,
    WireMessage,
    decode_daq_data,
    new_request_id,
    read_message,
    write_message,
)


class TelemetryError(RuntimeError):
    """Base error for the dashboard-to-agent TCP connection."""


class RemoteCommandError(TelemetryError):
    def __init__(self, error_type: str, message: str) -> None:
        self.error_type = error_type
        super().__init__(message)


HARDWARE_STOP_TIMEOUT_SECONDS = 30.0


class TelemetryClient:
    def __init__(self, *, queue_blocks: int = 200) -> None:
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._receive_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()
        self._pending: dict[str, asyncio.Future[WireMessage]] = {}
        self._data_queue: asyncio.Queue[TelemetryBlock] = asyncio.Queue(
            maxsize=queue_blocks
        )
        self._connected = False
        self._latest_health: dict[str, Any] = {}
        self._hello: dict[str, Any] = {}
        self._connection_lost = asyncio.Event()
        self._block_received = asyncio.Event()
        self._latest_block: TelemetryBlock | None = None
        self._latest_block_monotonic: float | None = None
        self.dropped_blocks = 0

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def latest_health(self) -> dict[str, Any]:
        return dict(self._latest_health)

    @property
    def hello(self) -> dict[str, Any]:
        return dict(self._hello)

    @property
    def latest_block(self) -> TelemetryBlock | None:
        return self._latest_block

    @property
    def latest_block_age_sec(self) -> float | None:
        if self._latest_block_monotonic is None:
            return None
        return max(0.0, time.monotonic() - self._latest_block_monotonic)

    async def connect(
        self, host: str = "127.0.0.1", port: int = 29100, timeout: float = 5.0
    ) -> dict[str, Any]:
        if self._connected:
            raise TelemetryError("telemetry is already connected")
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            hello = await asyncio.wait_for(read_message(self._reader), timeout=timeout)
        except (OSError, asyncio.TimeoutError, asyncio.IncompleteReadError) as exc:
            await self.disconnect()
            raise TelemetryError(
                f"cannot connect to telemetry at {host}:{port}"
            ) from exc

        if hello.message_type != MessageType.HELLO:
            await self.disconnect()
            raise TelemetryError("agent did not send a HELLO message")
        self._hello = hello.body
        self._latest_health = dict(hello.body.get("status", {}))
        self._latest_block = None
        self._latest_block_monotonic = None
        self._block_received.clear()
        self._connected = True
        self._connection_lost.clear()
        self._receive_task = asyncio.create_task(self._receive_loop())
        return self.hello

    async def disconnect(self) -> None:
        self._connected = False
        current = asyncio.current_task()
        if self._receive_task is not None and self._receive_task is not current:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task
        self._receive_task = None
        if self._writer is not None:
            self._writer.close()
            with contextlib.suppress(ConnectionError):
                await self._writer.wait_closed()
        self._reader = None
        self._writer = None
        self._connection_lost.set()
        self._fail_pending(TelemetryError("telemetry disconnected"))

    async def wait_connection_lost(self) -> None:
        await self._connection_lost.wait()

    async def wait_for_block(self, timeout: float | None = None) -> TelemetryBlock:
        if timeout is None:
            return await self._data_queue.get()
        return await asyncio.wait_for(self._data_queue.get(), timeout)

    async def wait_for_fresh_block(
        self, *, after_sequence: int | None = None, timeout: float = 5.0
    ) -> TelemetryBlock:
        async def wait() -> TelemetryBlock:
            while True:
                block = self._latest_block
                if block is not None and (
                    after_sequence is None or block.sequence != after_sequence
                ):
                    return block
                self._block_received.clear()
                await self._block_received.wait()

        return await asyncio.wait_for(wait(), timeout)

    async def ping(self, timeout: float = 5.0) -> dict[str, Any]:
        return (await self._request(MessageType.PING, timeout=timeout)).body

    async def get_config(self, timeout: float = 5.0) -> dict[str, Any]:
        return (await self._request(MessageType.CONFIG, timeout=timeout)).body

    async def start_session(
        self, test_name: str, timeout: float = 10.0
    ) -> dict[str, Any]:
        response = await self._request(
            MessageType.START_SESSION, {"test_name": test_name}, timeout=timeout
        )
        return response.body

    async def stop_session(
        self, timeout: float = HARDWARE_STOP_TIMEOUT_SECONDS
    ) -> dict[str, Any]:
        # The USB-4704 FAI_STOP control transfer can take longer than the
        # normal telemetry request timeout while the driver drains and frees
        # its DMA buffer.  Keep the dashboard waiting for the authoritative
        # COMPLETE acknowledgement rather than reporting a false stop error.
        return (await self._request(MessageType.STOP_SESSION, timeout=timeout)).body

    async def trigger(self, receive_time: str, timeout: float = 5.0) -> int:
        response = await self._request(
            MessageType.TRIGGER,
            {"receive_time": receive_time},
            timeout=timeout,
        )
        if response.message_type != MessageType.TRIGGER_ACK:
            raise TelemetryError("agent returned an invalid trigger response")
        return int(response.body["trigger_sample"])

    async def _request(
        self,
        message_type: MessageType,
        body: dict[str, Any] | None = None,
        *,
        timeout: float,
    ) -> WireMessage:
        if not self._connected or self._writer is None:
            raise TelemetryError("telemetry is not connected")
        request_id = new_request_id()
        future: asyncio.Future[WireMessage] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        try:
            async with self._send_lock:
                await write_message(
                    self._writer,
                    WireMessage(message_type, body or {}, request_id=request_id),
                )
            response = await asyncio.wait_for(future, timeout)
        except asyncio.TimeoutError as exc:
            raise TelemetryError(f"{message_type.value} response timed out") from exc
        finally:
            self._pending.pop(request_id, None)

        if response.message_type == MessageType.ERROR:
            raise RemoteCommandError(
                str(response.body.get("error_type", "RemoteError")),
                str(response.body.get("message", "unknown agent error")),
            )
        return response

    async def _receive_loop(self) -> None:
        assert self._reader is not None
        failure: BaseException = TelemetryError("telemetry connection closed")
        try:
            while True:
                message = await read_message(self._reader)
                if message.message_type == MessageType.DAQ_DATA:
                    self._queue_block(decode_daq_data(message))
                elif message.message_type == MessageType.HEALTH:
                    self._latest_health = message.body
                elif message.request_id and message.request_id in self._pending:
                    future = self._pending[message.request_id]
                    if not future.done():
                        future.set_result(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - receive-loop failure boundary
            failure = exc
        finally:
            self._connected = False
            self._connection_lost.set()
            self._fail_pending(TelemetryError(f"telemetry connection lost: {failure}"))

    def _queue_block(self, block: TelemetryBlock) -> None:
        self._latest_block = block
        self._latest_block_monotonic = time.monotonic()
        self._block_received.set()
        try:
            self._data_queue.put_nowait(block)
            return
        except asyncio.QueueFull:
            self.dropped_blocks += 1
        with contextlib.suppress(asyncio.QueueEmpty):
            self._data_queue.get_nowait()
        with contextlib.suppress(asyncio.QueueFull):
            self._data_queue.put_nowait(block)

    def _fail_pending(self, failure: BaseException) -> None:
        for future in tuple(self._pending.values()):
            if not future.done():
                future.set_exception(failure)
