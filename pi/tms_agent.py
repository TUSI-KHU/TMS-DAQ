from __future__ import annotations

import argparse
import json
import queue
import shutil
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias

import numpy as np

from common.config import ChannelConfig, ConfigError, TmsConfig, load_config
from common.filtering import DEFAULT_MOVING_WINDOW_SAMPLES, MovingAverage
from pi.daq import (
    DaqBlock,
    DaqError,
    DaqSource,
    DaqStopped,
    SimulatedDaqSource,
    Usb4704DaqSource,
)
from pi.logger import Hdf5SessionLogger, SessionMetadata, utc_now
from pi.ring_buffer import BlockRingBuffer


class AgentState(str, Enum):
    READY = "READY"
    RECORDING = "RECORDING"
    TRIGGERED = "TRIGGERED"
    COMPLETE = "COMPLETE"


class SessionError(RuntimeError):
    """Raised when a measurement session cannot be started or completed."""


class TriggerPendingError(SessionError):
    """The same trigger may be retried while its sample or disk receipt is pending."""


@dataclass
class EventReceipt:
    done: threading.Event = field(default_factory=threading.Event)
    error: BaseException | None = None


@dataclass(frozen=True)
class EventRequest:
    event_type: str
    sample_index: int
    receive_time: str
    details: str = ""
    receipt: EventReceipt | None = None


@dataclass
class NanoStateRequest:
    identity: tuple[object, ...]
    event: EventRequest
    received_monotonic: float
    gpio_state: bool | None
    valid_for_ms: int
    nano_uptime_ms: int | None
    ignition: EventRequest | None = None
    ignition_queued: bool = False


@dataclass(frozen=True)
class HealthRequest:
    component: str
    level: str
    message: str


class _StopLogger:
    pass


STOP_LOGGER = _StopLogger()
LogItem: TypeAlias = DaqBlock | EventRequest | HealthRequest | _StopLogger


STORAGE_WARNING_BYTES = 1024**3
STORAGE_WARNING_FRACTION = 0.10
HEALTH_REFRESH_SECONDS = 5.0
TRIGGER_WRITE_TIMEOUT_SECONDS = 2.0
NANO_STATE_RECEIPT_CACHE_SIZE = 4096


class TmsAgent:
    def __init__(
        self,
        config: TmsConfig,
        daq: DaqSource,
        *,
        output_directory: Path | None = None,
    ) -> None:
        self.config = config
        self.daq = daq
        daq_is_simulated = daq.source_kind == "simulated"
        daq_device_present = Path(config.daq.device).exists()
        if daq_is_simulated:
            initial_daq_health = "READY"
            initial_daq_description = "simulation"
            initial_daq_reason = ""
        elif daq_device_present:
            initial_daq_health = "UNKNOWN"
            initial_daq_description = ""
            initial_daq_reason = "hardware probe is deferred until acquisition starts"
        else:
            initial_daq_health = "NOT_FOUND"
            initial_daq_description = ""
            initial_daq_reason = f"{config.daq.device} is not present"
        self.state = AgentState.READY
        self.health = {
            "daq": initial_daq_health,
            "logger": "READY",
            "storage": "READY",
        }
        self.ring_buffer = BlockRingBuffer(
            config.logging.ring_buffer_sec, config.daq.block_ms
        )
        queue_blocks = max(2, self.ring_buffer.capacity_blocks)
        self._logger_queue: queue.Queue[LogItem] = queue.Queue(maxsize=queue_blocks)
        self._output_directory = Path(output_directory or config.logging.directory)
        self._logger = Hdf5SessionLogger(config, self._output_directory)
        self._stop_event = threading.Event()
        self._acquisition_thread: threading.Thread | None = None
        self._logger_thread: threading.Thread | None = None
        self._trigger_sample: int | None = None
        self._trigger_identity: tuple[object, ...] | None = None
        self._pending_trigger: EventRequest | None = None
        self._trigger_lock = threading.Lock()
        self._pending_nano_state: NanoStateRequest | None = None
        self._nano_state_receipts: OrderedDict[
            str, tuple[tuple[object, ...], dict[str, int | None]]
        ] = OrderedDict()
        self._nano_gpio_state: bool | None = None
        self._nano_state_valid_until = 0.0
        self._nano_uptime_ms: int | None = None
        self._latest_queued_sample_index: int | None = None
        self._session_id: str | None = None
        self._dropped_blocks = 0
        self._failures: list[BaseException] = []
        self._failure_lock = threading.Lock()
        self._telemetry_lock = threading.Lock()
        self._telemetry_queues: set[queue.Queue[DaqBlock]] = set()
        self._telemetry_dropped_blocks = 0
        self._moving_filters = (MovingAverage(), MovingAverage())
        self._last_block_monotonic: float | None = None
        self._last_health_refresh = 0.0
        self._storage_free_bytes: int | None = None
        self._storage_total_bytes: int | None = None
        self._daq_probe: dict[str, object] = {
            "available": daq_is_simulated,
            "description": initial_daq_description,
            "reason": initial_daq_reason,
        }
        # A USB description ioctl can wait for a driver request. Do not delay
        # service startup (and its telemetry listener) on that probe.
        self._refresh_health(force=True, probe_daq=False)

    @property
    def log_path(self) -> Path:
        return self._logger.path

    @property
    def trigger_sample(self) -> int | None:
        return self._trigger_sample

    @property
    def session_id(self) -> str | None:
        return self._session_id

    @property
    def dropped_blocks(self) -> int:
        return self._dropped_blocks

    @property
    def samples_written(self) -> int:
        return self._logger.samples_written

    @property
    def latest_sample_index(self) -> int | None:
        return self.ring_buffer.latest_sample_index()

    @property
    def telemetry_dropped_blocks(self) -> int:
        return self._telemetry_dropped_blocks

    def status_snapshot(self) -> dict[str, object]:
        # TelemetryServer calls this from its asyncio event loop for HELLO,
        # health frames, and PING replies. A USB-4704 probe includes a driver
        # ioctl which can wait for a USB request; doing it here can therefore
        # stall every TCP client even while the listening socket remains open.
        # Return the lifecycle-refreshed cache instead. start/stop/recovery and
        # service initialization still refresh this cache outside that path.
        block_age = (
            None
            if self._last_block_monotonic is None
            else max(0.0, time.monotonic() - self._last_block_monotonic)
        )
        return {
            "state": self.state.value,
            "health": dict(self.health),
            "latest_sample_index": self.latest_sample_index,
            "trigger_sample": self._trigger_sample,
            "session_id": self._session_id,
            "logger_dropped_blocks": self._dropped_blocks,
            "telemetry_dropped_blocks": self._telemetry_dropped_blocks,
            "sample_rate": self.config.daq.sample_rate,
            "display_filter": "moving_average",
            "moving_average_window_samples": DEFAULT_MOVING_WINDOW_SAMPLES,
            "low_pass": {
                "enabled": self.config.low_pass.enabled,
                "cutoff_hz": self.config.low_pass.cutoff_hz,
            },
            "daq_source": self.daq.source_kind,
            "daq_probe": dict(self._daq_probe),
            "daq_stream_age_sec": block_age,
            "storage_free_bytes": self._storage_free_bytes,
            "storage_total_bytes": self._storage_total_bytes,
            "channels": {
                "thrust": self.config.thrust.channel,
                "pressure": self.config.pressure.channel,
            },
        }

    def capture_calibration_sample(
        self,
        *,
        duration_sec: float = 1.0,
        cancel_event: threading.Event | None = None,
    ) -> dict[str, Any]:
        """Capture a short, non-recording raw AI0/AI1 reference reading.

        This deliberately opens the same buffered USB-4704 path used for a
        session, but it does not arm Nano, create an HDF5 file, or publish an
        acquisition session.  It is therefore safe to use from the dashboard
        before a test while the agent is idle.
        """

        if self.state not in (AgentState.READY, AgentState.COMPLETE):
            raise SessionError(
                "calibration sampling is only available before a measurement session"
            )
        if not 0.1 <= duration_sec <= 10.0:
            raise SessionError("calibration duration must be between 0.1 and 10 seconds")
        if cancel_event is not None and cancel_event.is_set():
            raise SessionError("calibration capture was cancelled before it started")

        original_state = self.state
        started = False
        captured: dict[int, list[np.ndarray]] = {
            self.config.thrust.channel: [],
            self.config.pressure.channel: [],
        }
        started_at = time.monotonic()
        deadline = started_at + duration_sec
        self.health["daq"] = "CALIBRATING"
        try:
            self.daq.start()
            started = True
            while time.monotonic() < deadline or not captured[self.config.thrust.channel]:
                if cancel_event is not None and cancel_event.is_set():
                    raise SessionError("calibration capture was cancelled")
                block = self.daq.read_block()
                for channel in captured:
                    captured[channel].append(
                        np.asarray(block.column_for_channel(channel), dtype=np.float64)
                    )
            if cancel_event is not None and cancel_event.is_set():
                raise SessionError("calibration capture was cancelled")
        except SessionError:
            # A timed-out remote command may still return from a blocked USB
            # ioctl later. Never publish that stale capture as a valid
            # calibration result; the dashboard must run DAQ recovery first.
            self.health["daq"] = "FAILED"
            self._daq_probe["available"] = False
            self._daq_probe["reason"] = "calibration operation was cancelled"
            raise
        except (DaqError, DaqStopped, OSError, ValueError) as exc:
            self.health["daq"] = "FAILED"
            self._daq_probe["available"] = False
            self._daq_probe["reason"] = str(exc)
            raise DaqError(f"calibration capture failed: {exc}") from exc
        finally:
            try:
                if started:
                    self.daq.stop()
                    self.daq.close()
            except (DaqError, OSError) as exc:
                self.health["daq"] = "FAILED"
                self._daq_probe["available"] = False
                self._daq_probe["reason"] = str(exc)
                raise DaqError(f"calibration cleanup failed; run DAQ 초기화: {exc}") from exc
            finally:
                self.state = original_state

        summaries: dict[str, dict[str, float | int]] = {}
        for name, channel in (
            ("ai0", self.config.thrust.channel),
            ("ai1", self.config.pressure.channel),
        ):
            values = np.concatenate(captured[channel])
            summaries[name] = {
                "sample_count": int(values.size),
                "mean": float(np.mean(values)),
                "stddev": float(np.std(values)),
                "minimum": float(np.min(values)),
                "maximum": float(np.max(values)),
            }

        self.health["daq"] = "READY"
        self._daq_probe["available"] = True
        self._daq_probe["reason"] = ""
        return {
            "duration_ms": int(round((time.monotonic() - started_at) * 1000.0)),
            "channels": summaries,
        }

    def updated_thrust_calibration(
        self, *, scale_N_per_count: float, offset_N: float
    ) -> TmsConfig:
        """Build a validation-backed config for a new fixed-AI0 calibration."""

        return replace(
            self.config,
            thrust=ChannelConfig(
                channel=self.config.thrust.channel,
                scale=scale_N_per_count,
                offset=offset_N,
            ),
        )

    def updated_pressure_calibration(
        self, *, scale_bar_per_count: float, offset_bar: float
    ) -> TmsConfig:
        """Build a validation-backed config for a new fixed-AI1 calibration."""

        return replace(
            self.config,
            pressure=ChannelConfig(
                channel=self.config.pressure.channel,
                scale=scale_bar_per_count,
                offset=offset_bar,
            ),
        )

    def apply_idle_config(self, config: TmsConfig) -> None:
        """Install a persisted calibration for the next session while idle."""

        if self.state not in (AgentState.READY, AgentState.COMPLETE):
            raise SessionError("calibration cannot change while a session is active")
        if (
            config.system != self.config.system
            or config.ssh != self.config.ssh
            or config.nano != self.config.nano
            or config.daq != self.config.daq
            or config.logging != self.config.logging
        ):
            raise SessionError("only the fixed AI0/AI1 sensor calibration may change")
        if config.thrust != self.config.thrust and config.pressure != self.config.pressure:
            raise SessionError("only one sensor calibration may change at a time")
        self.config = config
        # The logger writes the effective calibration into every subsequent
        # HDF5 session's metadata, so rebuild it before the next start.
        self._logger = Hdf5SessionLogger(config, self._output_directory)

    def add_telemetry_subscriber(
        self, *, max_blocks: int = 100
    ) -> queue.Queue[DaqBlock]:
        if max_blocks <= 0:
            raise ValueError("max_blocks must be greater than zero")
        subscriber: queue.Queue[DaqBlock] = queue.Queue(maxsize=max_blocks)
        with self._telemetry_lock:
            self._telemetry_queues.add(subscriber)
        return subscriber

    def remove_telemetry_subscriber(self, subscriber: queue.Queue[DaqBlock]) -> None:
        with self._telemetry_lock:
            self._telemetry_queues.discard(subscriber)

    def start_session(
        self, test_name: str, *, cancel_event: threading.Event | None = None
    ) -> Path:
        if self.state not in (AgentState.READY, AgentState.COMPLETE):
            raise SessionError(f"cannot start a session while state is {self.state}")
        if cancel_event is not None and cancel_event.is_set():
            raise SessionError("session start was cancelled before it started")

        self._stop_event.clear()
        for filt in self._moving_filters:
            filt.reset()
        self._failures.clear()
        self._trigger_sample = None
        self._trigger_identity = None
        self._pending_trigger = None
        self._pending_nano_state = None
        self._nano_state_receipts.clear()
        self._nano_gpio_state = None
        self._nano_state_valid_until = 0.0
        self._nano_uptime_ms = None
        self._latest_queued_sample_index = None
        self._dropped_blocks = 0
        self._telemetry_dropped_blocks = 0
        self._last_block_monotonic = None
        self.ring_buffer.clear()
        self._logger_queue = queue.Queue(
            maxsize=max(2, self.ring_buffer.capacity_blocks)
        )

        start_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        session_id = uuid.uuid4().hex[:8]
        self._session_id = session_id
        path = self._logger.open(
            SessionMetadata(
                test_name=test_name,
                session_id=session_id,
                start_time=start_time,
            )
        )

        try:
            self.daq.start()
            if cancel_event is not None and cancel_event.is_set():
                self.daq.stop()
                self.daq.close()
                self._session_id = None
                raise SessionError("session start was cancelled")
        except SessionError:
            # The command watchdog may have returned an error to the
            # dashboard while a driver ioctl was still pending. If it later
            # unblocks, close the just-opened logger instead of silently
            # beginning an unexpected measurement session.
            self.health["daq"] = "FAILED"
            self._daq_probe["available"] = False
            self._daq_probe["reason"] = "session start operation was cancelled"
            self._logger.close()
            self._session_id = None
            raise
        except BaseException as exc:
            self.health["daq"] = "FAILED"
            self._daq_probe["available"] = False
            self._daq_probe["reason"] = str(exc)
            self._logger.close()
            raise

        self.state = AgentState.RECORDING
        self.health.update(daq="RUNNING", logger="RECORDING")
        self._refresh_health(force=True)
        self._daq_probe["available"] = True
        self._daq_probe["reason"] = ""
        self._logger_thread = threading.Thread(
            target=self._logger_loop, name="tms-logger", daemon=True
        )
        self._acquisition_thread = threading.Thread(
            target=self._acquisition_loop, name="tms-acquisition", daemon=True
        )
        self._logger_thread.start()
        self._acquisition_thread.start()
        self._queue_health("daq", "OK", "acquisition started")
        self._queue_health("logger", "OK", "HDF5 recording started")
        self._queue_health("storage", self.health["storage"], "storage checked")
        return path

    def record_trigger(
        self,
        *,
        receive_time: str | None = None,
        session_id: str | None = None,
        source: str | None = None,
        nano_sequence: int | None = None,
        nano_uptime_ms: int | None = None,
    ) -> int:
        for name, value, limit in (
            ("receive_time", receive_time, 40),
            ("session_id", session_id, 64),
            ("source", source, 32),
        ):
            if value is not None and (
                not isinstance(value, str) or not value or len(value.encode("utf-8")) > limit
            ):
                raise SessionError(f"TRIGGER {name} must be a nonempty string of at most {limit} bytes")
        for name, value in (("nano_sequence", nano_sequence), ("nano_uptime_ms", nano_uptime_ms)):
            if value is not None and (type(value) is not int or not 0 <= value <= 0xFFFFFFFF):
                raise SessionError(f"TRIGGER {name} must be an unsigned 32-bit integer")
        if source == "nano" and any(
            value is None for value in (session_id, receive_time, nano_sequence, nano_uptime_ms)
        ):
            raise SessionError("Nano TRIGGER requires session_id, receive_time, nano_sequence and nano_uptime_ms")
        if source != "nano" and (nano_sequence is not None or nano_uptime_ms is not None):
            raise SessionError("Nano identity fields require source=nano")

        # A retry must identify the same edge and acquisition session; an
        # unqualified legacy trigger remains a one-shot command.
        identity = (
            (session_id, source, nano_sequence, nano_uptime_ms, receive_time)
            if source == "nano" else None
        )
        with self._trigger_lock:
            active_session_id = self._session_id
            if session_id is not None and session_id != self._session_id:
                raise SessionError("TRIGGER session_id does not match the active session")
            if self.state == AgentState.TRIGGERED:
                if identity is not None and identity == self._trigger_identity:
                    assert self._trigger_sample is not None
                    return self._trigger_sample
                raise SessionError("ignition trigger was already recorded for this session")
            if self.state != AgentState.RECORDING:
                raise SessionError(f"cannot record trigger while state is {self.state}")
            if (
                self._stop_event.is_set()
                or self.health["logger"] != "RECORDING"
                or self._logger_thread is None
                or not self._logger_thread.is_alive()
            ):
                raise SessionError("logger is not recording; trigger was not recorded")

            event = self._pending_trigger
            if self._pending_nano_state is not None:
                raise TriggerPendingError("Nano state is awaiting logger confirmation")
            if event is not None:
                if identity is None or identity != self._trigger_identity:
                    raise SessionError("a different ignition trigger is awaiting logger confirmation")
            else:
                # Reference only a sample block already handed to the writer.
                # The acquisition ring can otherwise get ahead of its queue,
                # leaving an acknowledged trigger pointing at a dropped row.
                sample_index = self._latest_queued_sample_index
                if sample_index is None:
                    raise TriggerPendingError("cannot record trigger before the first DAQ block")
                details = {
                    "source": source or "unspecified",
                    "session_id": self._session_id,
                    "timing_basis": "pi_latest_sample_on_receipt",
                }
                if source == "nano":
                    details.update(nano_sequence=nano_sequence, nano_uptime_ms=nano_uptime_ms)
                encoded_details = json.dumps(details, separators=(",", ":"))
                if len(encoded_details.encode("utf-8")) > 256:
                    raise SessionError("TRIGGER metadata exceeds the event storage capacity")
                event = EventRequest(
                    event_type="ignition",
                    sample_index=sample_index,
                    receive_time=receive_time or utc_now(),
                    details=encoded_details,
                    receipt=EventReceipt(),
                )
                try:
                    self._logger_queue.put(event, timeout=1.0)
                except queue.Full as exc:
                    raise SessionError("logger queue is full; trigger was not recorded") from exc
                self._pending_trigger = event
                self._trigger_identity = identity

            assert event.receipt is not None
            if not event.receipt.done.wait(timeout=TRIGGER_WRITE_TIMEOUT_SECONDS):
                raise TriggerPendingError("ignition trigger is awaiting logger confirmation; retry the same event")
            if event.receipt.error is not None:
                raise SessionError(f"ignition trigger was not recorded: {event.receipt.error}") from event.receipt.error
            # A disconnected client's coroutine can be cancelled while this
            # worker is still awaiting disk. Never let that late completion
            # change a stopped session or a subsequent acquisition's state.
            if (
                self._session_id != active_session_id
                or self._pending_trigger is not event
                or self.state != AgentState.RECORDING
                or self._stop_event.is_set()
            ):
                raise SessionError("session ended before ignition trigger confirmation")
            self._trigger_sample = event.sample_index
            self.state = AgentState.TRIGGERED
            return event.sample_index

    def record_nano_state(
        self,
        *,
        session_id: str,
        gpio_state: bool | None,
        nano_sequence: int | None,
        nano_uptime_ms: int | None,
        receive_time: str,
        event_id: str,
        valid_for_ms: int = 2000,
    ) -> dict[str, int | None]:
        """Persist every level, deriving ignition only from a fresh LOW→HIGH.

        An initial HIGH is a level, not evidence of when ignition began. An
        unknown state, expired heartbeat, or Nano uptime reset breaks edge
        continuity. ACKs and repeat IDs refer to flushed writer receipts.
        """
        for name, value, limit in (
            ("session_id", session_id, 64),
            ("receive_time", receive_time, 40),
            ("event_id", event_id, 64),
        ):
            if not isinstance(value, str) or not value or len(value.encode("utf-8")) > limit:
                raise SessionError(f"NANO_STATE {name} must be a nonempty string of at most {limit} bytes")
        if gpio_state is not None and type(gpio_state) is not bool:
            raise SessionError("NANO_STATE gpio_state must be a boolean or null")
        for name, value in (("nano_sequence", nano_sequence), ("nano_uptime_ms", nano_uptime_ms)):
            if value is not None and (type(value) is not int or not 0 <= value <= 0xFFFFFFFF):
                raise SessionError(f"NANO_STATE {name} must be an unsigned 32-bit integer")
        if gpio_state is not None and (nano_sequence is None or nano_uptime_ms is None):
            raise SessionError("known NANO_STATE requires nano_sequence and nano_uptime_ms")
        if type(valid_for_ms) is not int or not 0 <= valid_for_ms <= 2000:
            raise SessionError("NANO_STATE valid_for_ms must be between 0 and 2000")

        identity = (session_id, gpio_state, nano_sequence, nano_uptime_ms, receive_time, valid_for_ms)
        with self._trigger_lock:
            if session_id != self._session_id:
                raise SessionError("NANO_STATE session_id does not match the active session")
            if self.state not in (AgentState.RECORDING, AgentState.TRIGGERED):
                raise SessionError(f"cannot record Nano state while state is {self.state}")
            if (
                self._stop_event.is_set()
                or self.health["logger"] != "RECORDING"
                or self._logger_thread is None
                or not self._logger_thread.is_alive()
            ):
                raise SessionError("logger is not recording; Nano state was not recorded")
            cached = self._nano_state_receipts.get(event_id)
            if cached is not None:
                if cached[0] != identity:
                    raise SessionError("NANO_STATE event_id was reused with different contents")
                return dict(cached[1])
            pending = self._pending_nano_state
            if pending is not None:
                if pending.identity != (event_id, *identity):
                    if pending.identity[0] == event_id:
                        raise SessionError("NANO_STATE event_id was reused with different contents")
                    raise TriggerPendingError("a different Nano state is awaiting logger confirmation; retry it first")
            else:
                if self._pending_trigger is not None and self._trigger_sample is None:
                    raise TriggerPendingError("ignition trigger is awaiting logger confirmation")
                sample_index = self._latest_queued_sample_index
                if sample_index is None:
                    raise TriggerPendingError("cannot record Nano state before the first DAQ block")
                now = time.monotonic()
                details = {
                    "source": "nano",
                    "gpio_state": -1 if gpio_state is None else int(gpio_state),
                    "nano_sequence": nano_sequence,
                    "nano_uptime_ms": nano_uptime_ms,
                    "timing_basis": "pi_latest_sample_on_receipt",
                    "valid_for_ms": valid_for_ms,
                }
                # The event ID is an in-memory transport receipt key; keeping
                # it out of the fixed 256-byte field leaves room for full u32s.
                event = EventRequest(
                    "nano_state", sample_index, receive_time,
                    json.dumps(details, separators=(",", ":")), EventReceipt(),
                )
                ignition = None
                uptime_continuous = (
                    self._nano_uptime_ms is not None and nano_uptime_ms is not None
                    and (nano_uptime_ms - self._nano_uptime_ms) % (1 << 32) < (1 << 31)
                )
                if (
                    self._trigger_sample is None and self._nano_gpio_state is False
                    and gpio_state is True and now < self._nano_state_valid_until
                    and uptime_continuous and valid_for_ms > 0
                ):
                    ignition_details = {
                        "source": "nano", "session_id": session_id,
                        "nano_sequence": nano_sequence, "nano_uptime_ms": nano_uptime_ms,
                        "timing_basis": "pi_latest_sample_on_receipt",
                    }
                    ignition = EventRequest(
                        "ignition", sample_index, receive_time,
                        json.dumps(ignition_details, separators=(",", ":")), EventReceipt(),
                    )
                pending = NanoStateRequest(
                    (event_id, *identity), event, now, gpio_state, valid_for_ms,
                    nano_uptime_ms, ignition,
                )
                try:
                    self._logger_queue.put(event, timeout=1.0)
                except queue.Full as exc:
                    raise SessionError("logger queue is full; Nano state was not recorded") from exc
                self._pending_nano_state = pending

            self._wait_nano_event(pending.event)
            if (
                self._session_id != session_id or self._pending_nano_state is not pending
                or self.state not in (AgentState.RECORDING, AgentState.TRIGGERED)
                or self._stop_event.is_set()
            ):
                raise SessionError("session ended before Nano state confirmation")
            if pending.ignition is not None:
                if not pending.ignition_queued:
                    try:
                        self._logger_queue.put(pending.ignition, timeout=1.0)
                    except queue.Full as exc:
                        raise TriggerPendingError("Nano ignition is awaiting logger space; retry the same state") from exc
                    pending.ignition_queued = True
                self._wait_nano_event(pending.ignition)
            if (
                self._session_id != session_id or self._pending_nano_state is not pending
                or self.state not in (AgentState.RECORDING, AgentState.TRIGGERED)
                or self._stop_event.is_set()
            ):
                raise SessionError("session ended before Nano state confirmation")
            if pending.ignition is not None:
                self._trigger_sample = pending.ignition.sample_index
                self._trigger_identity = (session_id, "nano", nano_sequence, nano_uptime_ms, receive_time)
                self.state = AgentState.TRIGGERED
            self._nano_gpio_state = pending.gpio_state
            self._nano_uptime_ms = pending.nano_uptime_ms
            self._nano_state_valid_until = pending.received_monotonic + pending.valid_for_ms / 1000.0
            result = {"sample_index": pending.event.sample_index, "trigger_sample": self._trigger_sample}
            self._nano_state_receipts[event_id] = (identity, result)
            while len(self._nano_state_receipts) > NANO_STATE_RECEIPT_CACHE_SIZE:
                self._nano_state_receipts.popitem(last=False)
            self._pending_nano_state = None
            return dict(result)

    @staticmethod
    def _wait_nano_event(event: EventRequest) -> None:
        assert event.receipt is not None
        if not event.receipt.done.wait(timeout=TRIGGER_WRITE_TIMEOUT_SECONDS):
            raise TriggerPendingError("Nano state is awaiting logger confirmation; retry the same event")
        if event.receipt.error is not None:
            raise SessionError(f"Nano state was not recorded: {event.receipt.error}") from event.receipt.error

    def stop_session(
        self, *, timeout: float = 5.0, cancel_event: threading.Event | None = None
    ) -> Path:
        if self.state not in (AgentState.RECORDING, AgentState.TRIGGERED):
            raise SessionError(f"cannot stop a session while state is {self.state}")

        self._stop_event.set()
        self.daq.stop()
        # Never unmap a native buffer while the acquisition thread can still
        # read it. Finish the HDF5 logger before closing the USB driver: its
        # STOP ioctl may wedge, but the already acquired data must stay usable.
        self._join_thread(self._acquisition_thread, timeout, "acquisition")

        if self._logger_thread is not None and self._logger_thread.is_alive():
            try:
                if self._dropped_blocks:
                    latest_sample = self.latest_sample_index
                    self._logger_queue.put(
                        EventRequest(
                            event_type="DATA_GAP",
                            sample_index=(
                                latest_sample if latest_sample is not None else -1
                            ),
                            receive_time=utc_now(),
                            details=(
                                "application logger queue dropped "
                                f"{self._dropped_blocks} block(s)"
                            ),
                        ),
                        timeout=timeout,
                    )
                self._logger_queue.put(STOP_LOGGER, timeout=timeout)
            except queue.Full as exc:
                raise SessionError("logger did not drain its queue") from exc
        self._join_thread(self._logger_thread, timeout, "logger")
        if self.health["logger"] != "FAILED":
            self.health["logger"] = "COMPLETE"

        try:
            self.daq.close()
        except Exception as exc:
            self._record_failure(exc, "daq")
            raise DaqError(f"USB-4704 close failed; run DAQ 초기화: {exc}") from exc
        if cancel_event is not None and cancel_event.is_set():
            self.health["daq"] = "FAILED"
            raise DaqError("USB-4704 stop timed out; run DAQ 초기화")

        self.state = AgentState.COMPLETE
        if self.health["daq"] != "FAILED":
            self.health["daq"] = "READY"
        if self.health["logger"] != "FAILED":
            self.health["logger"] = "COMPLETE"
        self._refresh_health(force=True, probe_daq=False)

        failures = self._get_failures()
        if self._dropped_blocks:
            failures += (
                RuntimeError(
                    f"local logging dropped {self._dropped_blocks} DAQ block(s)"
                ),
            )
        if failures:
            messages = "; ".join(str(failure) for failure in failures)
            raise SessionError(
                f"session completed with background failures: {messages}"
            )
        return self.log_path

    def _acquisition_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                block = self.daq.read_block()
                # Compute once before the logging/transport queues split.
                # Every client, including late/reconnecting clients, receives
                # exactly the same window values that are stored in HDF5.
                indices = np.arange(block.first_sample_index, block.last_sample_index + 1)
                values = []
                for filt, channel in zip(self._moving_filters, (self.config.thrust, self.config.pressure)):
                    calibrated = block.column_for_channel(channel.channel).astype(np.float64) * channel.scale + channel.offset
                    values.append(filt.apply_indexed(calibrated, indices))
                block = replace(block, moving_average_values=np.column_stack(values).astype(np.float32))
                self._last_block_monotonic = time.monotonic()
                try:
                    self._logger_queue.put_nowait(block)
                    self._latest_queued_sample_index = block.last_sample_index
                except queue.Full:
                    self._dropped_blocks += 1
                    self.health["logger"] = "FAILED"
                self.ring_buffer.append(block)
                self._publish_telemetry(block)
            except DaqStopped:
                if not self._stop_event.is_set():
                    self._record_failure(DaqError("DAQ stopped unexpectedly"), "daq")
                return
            except DaqError as exc:
                if self._stop_event.is_set():
                    return
                if self.daq.source_kind == "usb4704" and self._recover_daq(exc):
                    continue
                if not self._stop_event.is_set():
                    self._record_failure(exc, "daq")
                    self._stop_event.set()
                return
            except Exception as exc:  # noqa: BLE001 - acquisition thread boundary
                self._record_failure(exc, "daq")
                self._stop_event.set()
                return

    def _logger_loop(self) -> None:
        try:
            while True:
                item = self._logger_queue.get()
                try:
                    if isinstance(item, _StopLogger):
                        return
                    if isinstance(item, DaqBlock):
                        self._logger.append_block(item)
                    elif isinstance(item, HealthRequest):
                        self._logger.record_health(
                            item.component, item.level, item.message
                        )
                    else:
                        self._logger.record_event(
                            item.event_type,
                            item.sample_index,
                            receive_time=item.receive_time,
                            details=item.details,
                            force_flush=item.receipt is not None,
                        )
                        if item.receipt is not None:
                            item.receipt.done.set()
                except Exception as exc:
                    if isinstance(item, EventRequest) and item.receipt is not None:
                        item.receipt.error = exc
                        item.receipt.done.set()
                    raise
                finally:
                    self._logger_queue.task_done()
        except Exception as exc:  # noqa: BLE001 - logger thread boundary
            self._record_failure(exc, "logger")
            self._stop_event.set()
        finally:
            self._logger.close()
            # Unconsumed events cannot be acknowledged after a writer error.
            while True:
                try:
                    pending = self._logger_queue.get_nowait()
                except queue.Empty:
                    break
                if isinstance(pending, EventRequest) and pending.receipt is not None:
                    pending.receipt.error = SessionError("logger stopped before writing the event")
                    pending.receipt.done.set()
                self._logger_queue.task_done()

    def _recover_daq(self, original_failure: DaqError) -> bool:
        latest_sample = self.latest_sample_index
        gap_sample = 0 if latest_sample is None else latest_sample + 1
        try:
            self._logger_queue.put(
                EventRequest(
                    event_type="DATA_GAP",
                    sample_index=gap_sample,
                    receive_time=utc_now(),
                    details=f"USB-4704 disconnected: {original_failure}",
                ),
                timeout=1.0,
            )
        except queue.Full:
            self._record_failure(
                RuntimeError("logger queue is full during DAQ recovery"), "logger"
            )
            return False

        self.health["daq"] = "RECONNECTING"
        self._queue_health("daq", "WARNING", str(original_failure))
        delays = (0.0, 1.0, 2.0, 5.0, 10.0)
        attempt = 0
        while not self._stop_event.is_set():
            delay = delays[min(attempt, len(delays) - 1)]
            if delay and self._stop_event.wait(delay):
                return False
            attempt += 1
            try:
                self.daq.recover()
            except DaqStopped:
                return False
            except DaqError as exc:
                self.health["daq"] = "RECONNECTING"
                self._daq_probe["available"] = False
                self._daq_probe["reason"] = str(exc)
                continue
            self.health["daq"] = "RUNNING"
            self._daq_probe["available"] = True
            self._daq_probe["reason"] = ""
            self._queue_health("daq", "OK", f"reconnected after {attempt} attempt(s)")
            return True
        return False

    def _queue_health(self, component: str, level: str, message: str) -> None:
        try:
            self._logger_queue.put_nowait(HealthRequest(component, level, message))
        except queue.Full:
            self._dropped_blocks += 1
            self.health["logger"] = "FAILED"

    def _refresh_health(self, *, force: bool = False, probe_daq: bool = True) -> None:
        now = time.monotonic()
        if not force and now - self._last_health_refresh < HEALTH_REFRESH_SECONDS:
            return
        self._last_health_refresh = now

        storage_path = self._output_directory
        while not storage_path.exists() and storage_path != storage_path.parent:
            storage_path = storage_path.parent
        previous_storage = self.health["storage"]
        try:
            usage = shutil.disk_usage(storage_path)
            self._storage_free_bytes = usage.free
            self._storage_total_bytes = usage.total
            warning_limit = max(
                STORAGE_WARNING_BYTES,
                int(usage.total * STORAGE_WARNING_FRACTION),
            )
            self.health["storage"] = "LOW" if usage.free < warning_limit else "OK"
        except OSError:
            self._storage_free_bytes = None
            self._storage_total_bytes = None
            self.health["storage"] = "FAILED"

        if self.health["storage"] != previous_storage and self.state in (
            AgentState.RECORDING,
            AgentState.TRIGGERED,
        ):
            self._queue_health(
                "storage",
                self.health["storage"],
                f"free_bytes={self._storage_free_bytes}",
            )

        if self.state in (AgentState.RECORDING, AgentState.TRIGGERED):
            return
        if self.daq.source_kind == "simulated":
            self.health["daq"] = "READY"
            return
        if not probe_daq:
            return
        try:
            result = self.daq.probe_result  # type: ignore[attr-defined]
            self._daq_probe = {
                "available": result.available,
                "description": result.description,
                "reason": result.reason,
            }
            self.health["daq"] = "AVAILABLE" if result.available else "NOT_FOUND"
        except (AttributeError, OSError, DaqError) as exc:
            self._daq_probe = {
                "available": False,
                "description": "",
                "reason": str(exc),
            }
            self.health["daq"] = "FAILED"

    def _record_failure(self, failure: BaseException, component: str) -> None:
        with self._failure_lock:
            self._failures.append(failure)
        self.health[component] = "FAILED"

    def _publish_telemetry(self, block: DaqBlock) -> None:
        block = replace(block, session_id=self._session_id)
        with self._telemetry_lock:
            subscribers = tuple(self._telemetry_queues)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(block)
                continue
            except queue.Full:
                self._telemetry_dropped_blocks += 1
            try:
                subscriber.get_nowait()
            except queue.Empty:
                pass
            try:
                subscriber.put_nowait(block)
            except queue.Full:
                self._telemetry_dropped_blocks += 1

    def _get_failures(self) -> tuple[BaseException, ...]:
        with self._failure_lock:
            return tuple(self._failures)

    @staticmethod
    def _join_thread(
        thread: threading.Thread | None, timeout: float, component: str
    ) -> None:
        if thread is None:
            return
        thread.join(timeout)
        if thread.is_alive():
            raise SessionError(
                f"{component} thread did not stop within {timeout} seconds"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TUSI TMS Raspberry Pi agent")
    parser.add_argument("--config", default="config.example.yaml")
    parser.add_argument("--test-name", default="SIM_TEST_001")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--trigger-after", type=float)
    parser.add_argument("--log-dir", type=Path)
    return parser


def run(args: argparse.Namespace) -> Path:
    config = load_config(args.config)
    if args.duration <= 0:
        raise SessionError("duration must be greater than zero")
    if args.trigger_after is not None and not 0 <= args.trigger_after < args.duration:
        raise SessionError("trigger-after must be within the session duration")

    if args.simulate:
        daq: DaqSource = SimulatedDaqSource(
            config.daq,
            (config.thrust.channel, config.pressure.channel),
        )
    else:
        daq = Usb4704DaqSource(
            config.daq,
            (config.thrust.channel, config.pressure.channel),
            buffer_seconds=config.logging.ring_buffer_sec,
        )

    agent = TmsAgent(config, daq, output_directory=args.log_dir)
    path = agent.start_session(args.test_name)
    started = time.monotonic()
    triggered = False
    try:
        while time.monotonic() - started < args.duration:
            elapsed = time.monotonic() - started
            if (
                args.trigger_after is not None
                and not triggered
                and elapsed >= args.trigger_after
            ):
                sample = agent.record_trigger()
                print(f"ignition trigger recorded at sample {sample}")
                triggered = True
            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        if agent.state in (AgentState.RECORDING, AgentState.TRIGGERED):
            path = agent.stop_session()

    print(f"session complete: {path}")
    print(f"samples written: {agent.samples_written}")
    return path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        run(args)
    except (ConfigError, DaqError, SessionError, OSError, ValueError) as exc:
        parser.exit(1, f"tms-agent: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
