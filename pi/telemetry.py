from __future__ import annotations

import asyncio
import contextlib
import math
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from common.config import TmsConfig
from common.filtering import FirstOrderLowPass
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

ConfigUpdateCallback = Callable[[TmsConfig], None]

# The Pi still acquires and writes every 10 ms DAQ block.  Dashboard telemetry
# is intentionally batched to a human-useful 20 Hz, reducing SSH framing,
# physical-unit conversions, and GUI cross-thread events without losing a
# sample in the HDF5 acquisition log.
TELEMETRY_BATCH_INTERVAL_SEC = 0.05
IDLE_STREAM_POLL_INTERVAL_SEC = 0.01
# Driver setup normally completes in milliseconds. Keep a bounded margin so a
# stuck kernel ioctl returns a useful recovery-required error before the
# dashboard's own request timeout, instead of later starting a stale session.
START_SESSION_OPERATION_TIMEOUT_SEC = 8.0
CALIBRATION_OPERATION_GRACE_SEC = 5.0
POWER_DIAGNOSTIC_HINT = (
    "Pi undervoltage 또는 USB 전원/케이블 불안정 여부를 확인하십시오."
)


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
        config_update_callback: ConfigUpdateCallback | None = None,
    ) -> None:
        self.agent = agent
        self.config = config
        self.host = host
        self.requested_port = port if port is not None else config.system.telemetry_port
        self.health_interval_sec = health_interval_sec
        self._config_update_callback = config_update_callback
        self._server: asyncio.AbstractServer | None = None
        self._clients: set[_Client] = set()
        self._command_lock = asyncio.Lock()
        self._hardware_recovery_required: str | None = None

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
        try:
            while True:
                message = await read_message(reader)
                await self._handle_command(client, message)
        except (asyncio.IncompleteReadError, ConnectionError):
            # Dashboard/SSH tunnel teardown is a normal transport event. The
            # outer client task closes the stream; do not emit an unhandled
            # asyncio traceback that looks like an agent failure in journalctl.
            return

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
                    path = await self._run_bounded_hardware_command(
                        MessageType.START_SESSION.value,
                        self.agent.start_session,
                        test_name,
                        timeout=START_SESSION_OPERATION_TIMEOUT_SEC,
                    )
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
                elif message.message_type == MessageType.CALIBRATION_SAMPLE:
                    duration_ms = int(message.body.get("duration_ms", 1000))
                    result = await self._run_bounded_hardware_command(
                        MessageType.CALIBRATION_SAMPLE.value,
                        self.agent.capture_calibration_sample,
                        duration_sec=duration_ms / 1000.0,
                        timeout=duration_ms / 1000.0 + CALIBRATION_OPERATION_GRACE_SEC,
                    )
                    await client.send(
                        WireMessage(
                            MessageType.ACK,
                            {
                                "command": MessageType.CALIBRATION_SAMPLE.value,
                                **result,
                            },
                            request_id=request_id,
                        )
                    )
                elif message.message_type == MessageType.SET_THRUST_CALIBRATION:
                    scale = float(message.body.get("scale_N_per_count"))
                    offset = float(message.body.get("offset_N"))
                    if not math.isfinite(scale) or not math.isfinite(offset):
                        raise ProtocolError("calibration values must be finite")
                    updated_config = self.agent.updated_thrust_calibration(
                        scale_N_per_count=scale,
                        offset_N=offset,
                    )
                    # Persist first: a failed write must not leave an apparent
                    # in-memory calibration that disappears on the next reboot.
                    if self._config_update_callback is not None:
                        self._config_update_callback(updated_config)
                    self.agent.apply_idle_config(updated_config)
                    self.config = updated_config
                    await client.send(
                        WireMessage(
                            MessageType.ACK,
                            {
                                "command": MessageType.SET_THRUST_CALIBRATION.value,
                                "thrust": {
                                    "channel": updated_config.thrust.channel,
                                    "scale": updated_config.thrust.scale,
                                    "offset": updated_config.thrust.offset,
                                },
                            },
                            request_id=request_id,
                        )
                    )
                elif message.message_type == MessageType.SET_PRESSURE_CALIBRATION:
                    scale = float(message.body.get("scale_bar_per_count"))
                    offset = float(message.body.get("offset_bar"))
                    if not math.isfinite(scale) or not math.isfinite(offset):
                        raise ProtocolError("calibration values must be finite")
                    updated_config = self.agent.updated_pressure_calibration(
                        scale_bar_per_count=scale,
                        offset_bar=offset,
                    )
                    if self._config_update_callback is not None:
                        self._config_update_callback(updated_config)
                    self.agent.apply_idle_config(updated_config)
                    self.config = updated_config
                    await client.send(
                        WireMessage(
                            MessageType.ACK,
                            {
                                "command": MessageType.SET_PRESSURE_CALIBRATION.value,
                                "pressure": {
                                    "channel": updated_config.pressure.channel,
                                    "scale": updated_config.pressure.scale,
                                    "offset": updated_config.pressure.offset,
                                },
                            },
                            request_id=request_id,
                        )
                    )
                else:
                    raise ProtocolError(
                        f"unsupported command: {message.message_type.value}"
                    )
        except (
            DaqError,
            SessionError,
            ProtocolError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
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

    async def _run_bounded_hardware_command(
        self,
        command_name: str,
        operation: Callable[..., Any],
        *args: object,
        timeout: float,
        **kwargs: object,
    ) -> Any:
        """Run a USB operation without allowing a late success to surprise UI.

        Python cannot safely kill a thread stuck in a kernel USB ioctl.  The
        cancellation event tells the operation to clean itself up if that call
        eventually returns; until the external DAQ recovery restarts this
        service, later start/calibration commands are rejected deterministically.
        """

        if self._hardware_recovery_required is not None:
            raise DaqError(
                "USB-4704 recovery is required after "
                f"{self._hardware_recovery_required} timed out. "
                "Run DAQ 초기화 before starting or calibrating again. "
                + POWER_DIAGNOSTIC_HINT
            )

        cancel_event = threading.Event()
        task = asyncio.create_task(
            asyncio.to_thread(
                operation,
                *args,
                cancel_event=cancel_event,
                **kwargs,
            )
        )
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except asyncio.TimeoutError as exc:
            cancel_event.set()
            self._hardware_recovery_required = command_name
            task.add_done_callback(self._consume_timed_out_command_result)
            raise DaqError(
                f"USB-4704 {command_name} did not return within {timeout:.1f}s. "
                "Run DAQ 초기화; a delayed command will not start a session. "
                + POWER_DIAGNOSTIC_HINT
            ) from exc

    @staticmethod
    def _consume_timed_out_command_result(task: asyncio.Task[Any]) -> None:
        # A result is intentionally discarded after the caller received the
        # deterministic recovery-required error. Consume its exception so an
        # eventual driver failure does not become an unhandled asyncio task.
        with contextlib.suppress(asyncio.CancelledError, Exception):
            task.result()

    async def _stream_loop(
        self, client: _Client, subscriber: queue.Queue[DaqBlock]
    ) -> None:
        pending: list[DaqBlock] = []
        last_send = time.monotonic()
        previous_block: DaqBlock | None = None
        thrust_filter = FirstOrderLowPass(
            self.config.daq.sample_rate,
            self.config.low_pass.cutoff_hz,
            self.config.low_pass.enabled,
        )
        pressure_filter = FirstOrderLowPass(
            self.config.daq.sample_rate,
            self.config.low_pass.cutoff_hz,
            self.config.low_pass.enabled,
        )
        while True:
            try:
                block = subscriber.get_nowait()
            except queue.Empty:
                if not pending:
                    # A standard Queue has no asyncio notification. Never
                    # sleep(0) here: that would turn an idle dashboard into a
                    # busy loop after a batch is sent.
                    await asyncio.sleep(IDLE_STREAM_POLL_INTERVAL_SEC)
                    continue
                now = time.monotonic()
                if now - last_send >= TELEMETRY_BATCH_INTERVAL_SEC:
                    await client.send(
                        self._telemetry_message(
                            self._merge_blocks(pending),
                            thrust_filter=thrust_filter,
                            pressure_filter=pressure_filter,
                        )
                    )
                    pending.clear()
                    last_send = now
                    continue
                remaining = TELEMETRY_BATCH_INTERVAL_SEC - (now - last_send)
                await asyncio.sleep(min(0.005, remaining))
                continue

            # A dropped transport block must stay visible as an index gap in
            # the client. Do not concatenate it into a fabricated continuous
            # trace, and restart the causal filter after the gap/session reset.
            if previous_block is not None and not self._blocks_are_contiguous(
                previous_block, block
            ):
                if pending:
                    await client.send(
                        self._telemetry_message(
                            self._merge_blocks(pending),
                            thrust_filter=thrust_filter,
                            pressure_filter=pressure_filter,
                        )
                    )
                    pending.clear()
                thrust_filter.reset()
                pressure_filter.reset()
                last_send = time.monotonic()
            previous_block = block

            pending.append(block)
            now = time.monotonic()
            if now - last_send >= TELEMETRY_BATCH_INTERVAL_SEC:
                await client.send(
                    self._telemetry_message(
                        self._merge_blocks(pending),
                        thrust_filter=thrust_filter,
                        pressure_filter=pressure_filter,
                    )
                )
                pending.clear()
                last_send = now

    async def _health_loop(self, client: _Client) -> None:
        while True:
            await asyncio.sleep(self.health_interval_sec)
            await client.send(
                WireMessage(MessageType.HEALTH, self.agent.status_snapshot())
            )

    def _telemetry_message(
        self,
        block: DaqBlock,
        *,
        thrust_filter: FirstOrderLowPass | None = None,
        pressure_filter: FirstOrderLowPass | None = None,
    ) -> WireMessage:
        thrust = block.column_for_channel(self.config.thrust.channel).astype(np.float64)
        pressure = block.column_for_channel(self.config.pressure.channel).astype(
            np.float64
        )
        thrust = thrust * self.config.thrust.scale + self.config.thrust.offset
        pressure = pressure * self.config.pressure.scale + self.config.pressure.offset
        thrust_filter = thrust_filter or FirstOrderLowPass(
            self.config.daq.sample_rate,
            self.config.low_pass.cutoff_hz,
            self.config.low_pass.enabled,
        )
        pressure_filter = pressure_filter or FirstOrderLowPass(
            self.config.daq.sample_rate,
            self.config.low_pass.cutoff_hz,
            self.config.low_pass.enabled,
        )
        thrust = thrust_filter.apply(thrust)
        pressure = pressure_filter.apply(pressure)
        values = np.column_stack((thrust, pressure)).astype(np.float32)
        return make_daq_data_message(
            sequence=block.sequence,
            first_sample_index=block.first_sample_index,
            sample_rate=block.sample_rate,
            channel_names=("thrust_N", "pressure_bar"),
            values=values,
        )

    @staticmethod
    def _blocks_are_contiguous(previous: DaqBlock, following: DaqBlock) -> bool:
        return (
            following.sequence == previous.sequence + 1
            and following.first_sample_index == previous.last_sample_index + 1
            and following.sample_rate == previous.sample_rate
            and following.channel_numbers == previous.channel_numbers
        )

    @staticmethod
    def _merge_blocks(blocks: list[DaqBlock]) -> DaqBlock:
        if not blocks:
            raise ValueError("cannot merge an empty DAQ block list")
        if len(blocks) == 1:
            return blocks[0]
        first = blocks[0]
        last = blocks[-1]
        return DaqBlock(
            sequence=last.sequence,
            first_sample_index=first.first_sample_index,
            sample_rate=first.sample_rate,
            channel_numbers=first.channel_numbers,
            raw_samples=np.concatenate(
                [block.raw_samples for block in blocks], axis=0
            ),
        )
