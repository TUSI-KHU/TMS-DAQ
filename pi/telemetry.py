from __future__ import annotations

import asyncio
import contextlib
import queue
from dataclasses import dataclass, field

import numpy as np

from common.config import TmsConfig
from common.protocol import (
    MessageType,
    ProtocolError,
    WireMessage,
    make_daq_data_message,
    read_message,
    write_message,
)
from pi.daq import DaqBlock, DaqError
from pi.tms_agent import SessionError, TmsAgent


@dataclass(eq=False)
class _Client:
    writer: asyncio.StreamWriter
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def send(self, message: WireMessage) -> None:
        async with self.send_lock:
            await write_message(self.writer, message)

    async def close(self) -> None:
        self.writer.close()
        with contextlib.suppress(ConnectionError):
            await self.writer.wait_closed()


class TelemetryServer:
    """Single-service TCP control and DAQ telemetry endpoint for the Pi."""

    def __init__(
        self,
        agent: TmsAgent,
        config: TmsConfig,
        *,
        host: str = "127.0.0.1",
        port: int | None = None,
        health_interval_sec: float = 0.5,
    ) -> None:
        self.agent = agent
        self.config = config
        self.host = host
        self.requested_port = port if port is not None else config.system.telemetry_port
        self.health_interval_sec = health_interval_sec
        self._server: asyncio.AbstractServer | None = None
        self._clients: set[_Client] = set()
        self._command_lock = asyncio.Lock()

    @property
    def port(self) -> int:
        if self._server is None or not self._server.sockets:
            raise RuntimeError("telemetry server is not running")
        return int(self._server.sockets[0].getsockname()[1])

    async def start(self) -> None:
        if self._server is not None:
            raise RuntimeError("telemetry server is already running")
        self._server = await asyncio.start_server(
            self._handle_client, self.host, self.requested_port
        )

    async def serve_forever(self) -> None:
        if self._server is None:
            await self.start()
        assert self._server is not None
        async with self._server:
            await self._server.serve_forever()

    async def close(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        clients = tuple(self._clients)
        self._clients.clear()
        await asyncio.gather(
            *(client.close() for client in clients), return_exceptions=True
        )

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        client = _Client(writer)
        self._clients.add(client)
        subscriber = self.agent.add_telemetry_subscriber(max_blocks=100)
        tasks: list[asyncio.Task[None]] = []
        try:
            await client.send(
                WireMessage(
                    MessageType.HELLO,
                    {
                        "service": "tms-agent",
                        "protocol_version": 1,
                        "status": self.agent.status_snapshot(),
                    },
                )
            )
            tasks = [
                asyncio.create_task(self._command_loop(client, reader)),
                asyncio.create_task(self._stream_loop(client, subscriber)),
                asyncio.create_task(self._health_loop(client)),
            ]
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            for task in done:
                with contextlib.suppress(
                    asyncio.IncompleteReadError,
                    ConnectionError,
                    ProtocolError,
                    asyncio.CancelledError,
                ):
                    task.result()
        finally:
            self.agent.remove_telemetry_subscriber(subscriber)
            self._clients.discard(client)
            await client.close()

    async def _command_loop(
        self, client: _Client, reader: asyncio.StreamReader
    ) -> None:
        while True:
            message = await read_message(reader)
            await self._handle_command(client, message)

    async def _handle_command(self, client: _Client, message: WireMessage) -> None:
        request_id = message.request_id
        try:
            if message.message_type in (MessageType.HELLO, MessageType.PING):
                await client.send(
                    WireMessage(
                        MessageType.ACK,
                        {"status": self.agent.status_snapshot()},
                        request_id=request_id,
                    )
                )
                return
            if message.message_type == MessageType.CONFIG:
                await client.send(
                    WireMessage(
                        MessageType.ACK,
                        {"config": self.config.as_dict()},
                        request_id=request_id,
                    )
                )
                return

            async with self._command_lock:
                if message.message_type == MessageType.START_SESSION:
                    test_name = str(message.body.get("test_name", "")).strip()
                    if not test_name:
                        raise SessionError("START_SESSION requires test_name")
                    path = await asyncio.to_thread(self.agent.start_session, test_name)
                    await client.send(
                        WireMessage(
                            MessageType.ACK,
                            {
                                "command": MessageType.START_SESSION.value,
                                "state": self.agent.state.value,
                                "log_file": path.name,
                                "session_id": self.agent.session_id,
                            },
                            request_id=request_id,
                        )
                    )
                elif message.message_type == MessageType.STOP_SESSION:
                    path = await asyncio.to_thread(self.agent.stop_session)
                    await client.send(
                        WireMessage(
                            MessageType.ACK,
                            {
                                "command": MessageType.STOP_SESSION.value,
                                "state": self.agent.state.value,
                                "log_file": path.name,
                            },
                            request_id=request_id,
                        )
                    )
                elif message.message_type == MessageType.TRIGGER:
                    sample = self.agent.record_trigger(
                        receive_time=str(message.body.get("receive_time") or "") or None
                    )
                    await client.send(
                        WireMessage(
                            MessageType.TRIGGER_ACK,
                            {"trigger_sample": sample},
                            request_id=request_id,
                        )
                    )
                else:
                    raise ProtocolError(
                        f"unsupported command: {message.message_type.value}"
                    )
        except (DaqError, SessionError, ProtocolError, OSError, ValueError) as exc:
            await client.send(
                WireMessage(
                    MessageType.ERROR,
                    {
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    },
                    request_id=request_id,
                )
            )

    async def _stream_loop(
        self, client: _Client, subscriber: queue.Queue[DaqBlock]
    ) -> None:
        while True:
            try:
                block = subscriber.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.005)
                continue
            await client.send(self._telemetry_message(block))

    async def _health_loop(self, client: _Client) -> None:
        while True:
            await asyncio.sleep(self.health_interval_sec)
            await client.send(
                WireMessage(MessageType.HEALTH, self.agent.status_snapshot())
            )

    def _telemetry_message(self, block: DaqBlock) -> WireMessage:
        thrust = block.column_for_channel(self.config.thrust.channel).astype(np.float64)
        pressure = block.column_for_channel(self.config.pressure.channel).astype(
            np.float64
        )
        thrust = thrust * self.config.thrust.scale + self.config.thrust.offset
        pressure = pressure * self.config.pressure.scale + self.config.pressure.offset
        values = np.column_stack((thrust, pressure)).astype(np.float32)
        return make_daq_data_message(
            sequence=block.sequence,
            first_sample_index=block.first_sample_index,
            sample_rate=block.sample_rate,
            channel_names=("thrust_N", "pressure_bar"),
            values=values,
        )
