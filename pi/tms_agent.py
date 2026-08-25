from __future__ import annotations

import argparse
import queue
import shutil
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TypeAlias

from common.config import ConfigError, TmsConfig, load_config
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


@dataclass(frozen=True)
class EventRequest:
    event_type: str
    sample_index: int
    receive_time: str
    details: str = ""


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
        self._session_id: str | None = None
        self._dropped_blocks = 0
        self._failures: list[BaseException] = []
        self._failure_lock = threading.Lock()
        self._telemetry_lock = threading.Lock()
        self._telemetry_queues: set[queue.Queue[DaqBlock]] = set()
        self._telemetry_dropped_blocks = 0
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

    def start_session(self, test_name: str) -> Path:
        if self.state not in (AgentState.READY, AgentState.COMPLETE):
            raise SessionError(f"cannot start a session while state is {self.state}")

        self._stop_event.clear()
        self._failures.clear()
        self._trigger_sample = None
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

    def record_trigger(self, *, receive_time: str | None = None) -> int:
        if self.state == AgentState.TRIGGERED:
            raise SessionError("ignition trigger was already recorded for this session")
        if self.state != AgentState.RECORDING:
            raise SessionError(f"cannot record trigger while state is {self.state}")

        sample_index = self.latest_sample_index
        if sample_index is None:
            raise SessionError("cannot record trigger before the first DAQ block")

        event = EventRequest(
            event_type="ignition",
            sample_index=sample_index,
            receive_time=receive_time or utc_now(),
        )
        try:
            self._logger_queue.put(event, timeout=1.0)
        except queue.Full as exc:
            self.health["logger"] = "FAILED"
            raise SessionError(
                "logger queue is full; trigger was not recorded"
            ) from exc

        self._trigger_sample = sample_index
        self.state = AgentState.TRIGGERED
        return sample_index

    def stop_session(self, *, timeout: float = 5.0) -> Path:
        if self.state not in (AgentState.RECORDING, AgentState.TRIGGERED):
            raise SessionError(f"cannot stop a session while state is {self.state}")

        self._stop_event.set()
        self.daq.stop()
        try:
            self._join_thread(self._acquisition_thread, timeout, "acquisition")
        finally:
            self.daq.close()

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
                self._last_block_monotonic = time.monotonic()
                self.ring_buffer.append(block)
                self._publish_telemetry(block)
                try:
                    self._logger_queue.put_nowait(block)
                except queue.Full:
                    self._dropped_blocks += 1
                    self.health["logger"] = "FAILED"
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
                        )
                finally:
                    self._logger_queue.task_done()
        except Exception as exc:  # noqa: BLE001 - logger thread boundary
            self._record_failure(exc, "logger")
            self._stop_event.set()
        finally:
            self._logger.close()

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
