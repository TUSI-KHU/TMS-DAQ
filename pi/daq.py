from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from common.config import DaqConfig
from pi.usb4704 import Usb4704BufferedDevice, Usb4704NativeError, Usb4704Probe


class DaqError(RuntimeError):
    """Base error for DAQ acquisition failures."""


class DaqStopped(DaqError):
    """Raised when a blocked read is interrupted during shutdown."""


@dataclass(frozen=True)
class DaqBlock:
    sequence: int
    first_sample_index: int
    sample_rate: int
    channel_numbers: tuple[int, ...]
    raw_samples: NDArray[np.integer]
    session_id: str | None = None
    moving_average_values: NDArray[np.float32] | None = None

    def __post_init__(self) -> None:
        if self.sequence < 0 or self.first_sample_index < 0:
            raise ValueError("sequence and first_sample_index must not be negative")
        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be greater than zero")
        if self.raw_samples.ndim != 2:
            raise ValueError("raw_samples must have shape (samples, channels)")
        if self.raw_samples.shape[0] == 0:
            raise ValueError("a DAQ block must contain at least one sample")
        if self.raw_samples.shape[1] != len(self.channel_numbers):
            raise ValueError("channel_numbers must match raw_samples columns")
        if len(set(self.channel_numbers)) != len(self.channel_numbers):
            raise ValueError("channel_numbers must be unique")
        if not np.issubdtype(self.raw_samples.dtype, np.integer):
            raise ValueError("raw_samples must use an integer dtype")
        if self.moving_average_values is not None and self.moving_average_values.shape != (self.sample_count, 2):
            raise ValueError("moving_average_values must have shape (samples, 2)")

    @property
    def sample_count(self) -> int:
        return int(self.raw_samples.shape[0])

    @property
    def channel_count(self) -> int:
        return int(self.raw_samples.shape[1])

    @property
    def last_sample_index(self) -> int:
        return self.first_sample_index + self.sample_count - 1

    def column_for_channel(self, channel: int) -> NDArray[np.integer]:
        try:
            column = self.channel_numbers.index(channel)
        except ValueError as exc:
            raise DaqError(f"DAQ block does not contain channel {channel}") from exc
        return self.raw_samples[:, column]


class DaqSource(Protocol):
    @property
    def source_kind(self) -> str: ...

    def probe(self) -> bool: ...

    def start(self) -> None: ...

    def read_block(self) -> DaqBlock: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...

    def recover(self) -> None: ...


class SimulatedDaqSource:
    """Deterministic two-channel DAQ source for development without hardware."""

    def __init__(
        self,
        config: DaqConfig,
        channel_numbers: tuple[int, int],
        *,
        realtime: bool = True,
        seed: int = 4704,
    ) -> None:
        self._config = config
        self._channel_numbers = channel_numbers
        self._realtime = realtime
        self._rng = np.random.default_rng(seed)
        self._stop_event = threading.Event()
        self._started = False
        self._sequence = 0
        self._sample_index = 0
        self._next_deadline = 0.0

    @property
    def source_kind(self) -> str:
        return "simulated"

    def probe(self) -> bool:
        return True

    def start(self) -> None:
        if self._started:
            raise DaqError("simulated DAQ is already running")
        self._stop_event.clear()
        self._started = True
        self._sequence = 0
        self._sample_index = 0
        self._next_deadline = time.monotonic()

    def read_block(self) -> DaqBlock:
        if not self._started:
            raise DaqStopped("simulated DAQ is not running")

        block_seconds = self._config.block_ms / 1000.0
        if self._realtime:
            self._next_deadline += block_seconds
            wait_seconds = max(0.0, self._next_deadline - time.monotonic())
            if self._stop_event.wait(wait_seconds):
                raise DaqStopped("simulated DAQ stopped")
        elif self._stop_event.is_set():
            raise DaqStopped("simulated DAQ stopped")

        count = self._config.samples_per_block
        indices = np.arange(
            self._sample_index, self._sample_index + count, dtype=np.float64
        )
        seconds = indices / self._config.sample_rate

        thrust = 7800.0 + 1300.0 * np.sin(2.0 * np.pi * 1.7 * seconds)
        pressure = 5200.0 + 900.0 * np.sin(2.0 * np.pi * 0.8 * seconds + np.pi / 5.0)
        thrust += self._rng.normal(0.0, 8.0, count)
        pressure += self._rng.normal(0.0, 6.0, count)
        samples = np.column_stack((thrust, pressure))
        raw = np.clip(np.rint(samples), 0, 16383).astype(np.uint16)

        block = DaqBlock(
            sequence=self._sequence,
            first_sample_index=self._sample_index,
            sample_rate=self._config.sample_rate,
            channel_numbers=self._channel_numbers,
            raw_samples=raw,
        )
        self._sequence += 1
        self._sample_index += count
        return block

    def stop(self) -> None:
        self._stop_event.set()
        self._started = False

    def close(self) -> None:
        return None

    def recover(self) -> None:
        raise DaqError("simulated DAQ does not use hardware recovery")


class Usb4704DaqSource:
    """Production DAQ source using the ported kernel driver's native ABI."""

    def __init__(
        self,
        config: DaqConfig,
        channel_numbers: tuple[int, ...],
        *,
        buffer_seconds: float = 10.0,
    ) -> None:
        self._config = config
        self._device = Path(config.device)
        self._channel_numbers = channel_numbers
        self._buffer_seconds = buffer_seconds
        self._stop_event = threading.Event()
        self._native: Usb4704BufferedDevice | None = None
        self._sequence = 0
        self._sample_index = 0

    @property
    def source_kind(self) -> str:
        return "usb4704"

    @property
    def probe_result(self) -> Usb4704Probe:
        return Usb4704BufferedDevice.probe(self._device)

    def probe(self) -> bool:
        return self.probe_result.available

    def start(self) -> None:
        if self._native is not None:
            raise DaqError("USB-4704 DAQ is already running")
        self._stop_event.clear()
        self._sequence = 0
        self._sample_index = 0
        self._open_native()

    def _open_native(self) -> None:
        native = Usb4704BufferedDevice(
            self._device,
            sample_rate=self._config.sample_rate,
            channel_numbers=self._channel_numbers,
            block_frames=self._config.samples_per_block,
            buffer_seconds=self._buffer_seconds,
        )
        try:
            native.start()
        except (OSError, Usb4704NativeError, ValueError) as exc:
            native.close()
            raise DaqError(f"cannot start USB-4704 at {self._device}: {exc}") from exc
        self._native = native

    def read_block(self) -> DaqBlock:
        native = self._native
        if native is None:
            raise DaqStopped("USB-4704 acquisition has not started")
        try:
            samples = native.read_frames(self._stop_event)
        except InterruptedError as exc:
            raise DaqStopped("USB-4704 acquisition stopped") from exc
        except (OSError, Usb4704NativeError) as exc:
            raise DaqError(str(exc)) from exc
        block = DaqBlock(
            sequence=self._sequence,
            first_sample_index=self._sample_index,
            sample_rate=self._config.sample_rate,
            channel_numbers=native.scan_channels,
            raw_samples=samples,
        )
        self._sequence += 1
        self._sample_index += block.sample_count
        return block

    def stop(self) -> None:
        self._stop_event.set()

    def close(self) -> None:
        native, self._native = self._native, None
        if native is not None:
            try:
                native.close()
            except (OSError, Usb4704NativeError) as exc:
                raise DaqError(f"USB-4704 close failed; run DAQ 초기화: {exc}") from exc

    def recover(self) -> None:
        if self._stop_event.is_set():
            raise DaqStopped("USB-4704 recovery interrupted")
        self.close()
        try:
            self._open_native()
        except DaqError:
            self.close()
            raise
