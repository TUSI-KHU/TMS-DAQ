from __future__ import annotations

import ctypes
import errno
import mmap
import os
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

AI_CHANNEL_COUNT = 8
AI_SET_CHSCTYPE = 0x1
AI_SET_CHGAIN = 0x2
SINGLE_ENDED = 0
GAIN_NEG10_TO_10 = 0
INTERNAL_CLOCK = 1
DAQ_ACQ_INFINITE = 2
DAQ_FN_RUNNING = 2
DAQ_IN_BUF_OVERRUN = 0x002
USB_FLAG_FAI_OVERRUN = 0x100
FAI_STOP_FREE_RES = 0x1


def linux_io(magic: str, number: int) -> int:
    """Return the Linux _IO() value used by the vendor's modern ABI."""

    if len(magic) != 1 or not 0 <= number <= 0xFF:
        raise ValueError("invalid Linux ioctl type or number")
    return ord(magic) << 8 | number


IOCTL_DEVICE_GET_DESC = linux_io("a", 1)
IOCTL_AI_SET_CHAN_CFG = linux_io("b", 1)
IOCTL_FAI_SET_PARAM = linux_io("b", 5)
IOCTL_FAI_SET_BUFFER = linux_io("b", 6)
IOCTL_FAI_START = linux_io("b", 7)
IOCTL_FAI_STOP = linux_io("b", 8)


class Usb4704NativeError(RuntimeError):
    """The native USB-4704 driver rejected or could not perform an operation."""


class Usb4704Overrun(Usb4704NativeError):
    """The kernel or device overwrote input data before it was consumed."""


class AiCalibrationInfo(ctypes.Structure):
    _fields_ = [("offset", ctypes.c_uint8), ("span", ctypes.c_uint8)]


class FaiConfig(ctypes.Structure):
    _fields_ = [
        ("xfer_mode", ctypes.c_uint32),
        ("physical_channel_start", ctypes.c_uint32),
        ("logical_channel_count", ctypes.c_uint32),
        ("clock_source", ctypes.c_uint32),
        ("sample_rate_per_channel", ctypes.c_uint32),
        ("section_size", ctypes.c_uint32),
        ("sample_count", ctypes.c_uint32),
    ]


class FaiStatus(ctypes.Structure):
    _fields_ = [
        ("acquisition_mode", ctypes.c_uint32),
        ("function_state", ctypes.c_uint32),
        ("buffer_state", ctypes.c_uint32),
        ("buffer_length", ctypes.c_uint32),
        ("write_pointer_wraps", ctypes.c_uint32),
        ("write_position", ctypes.c_uint32),
        ("read_position", ctypes.c_uint32),
        ("channel_calibration", AiCalibrationInfo * AI_CHANNEL_COUNT),
        ("current_channel", ctypes.c_uint32),
        ("hardware_flags", ctypes.c_uint32),
    ]


class DeviceSharedHead(ctypes.Structure):
    """Mapped prefix of DEVICE_SHARED; later driver-private fields are unused."""

    _fields_ = [
        ("size", ctypes.c_uint32),
        ("product_id", ctypes.c_uint32),
        ("device_number", ctypes.c_uint32),
        ("board_id", ctypes.c_uint32),
        ("init_on_load", ctypes.c_uint32),
        ("firmware_version", ctypes.c_uint32),
        ("hardware_ai_channel_type", ctypes.c_uint8),
        ("oscillator", ctypes.c_uint8),
        ("ai_channel_type", ctypes.c_uint8 * AI_CHANNEL_COUNT),
        ("ai_channel_gain", ctypes.c_uint8 * AI_CHANNEL_COUNT),
        ("ai_logical_channel_count", ctypes.c_uint32),
        ("fai_config", FaiConfig),
        ("fai_status", FaiStatus),
    ]


class AiChannelConfig(ctypes.Structure):
    _fields_ = [("scan_type", ctypes.c_uint8), ("gain", ctypes.c_uint8)]


class AiSetChannel(ctypes.Structure):
    _fields_ = [
        ("set_which", ctypes.c_uint32),
        ("physical_channel_start", ctypes.c_uint32),
        ("physical_channel_count", ctypes.c_uint32),
        ("channel_config", ctypes.POINTER(AiChannelConfig)),
    ]


@dataclass(frozen=True)
class Usb4704Probe:
    path: Path
    available: bool
    description: str = ""
    reason: str = ""


class Usb4704BufferedDevice:
    """Thin user-space binding to the ported driver's buffered-AI ABI.

    This uses the same ioctl structures and mmap status page as the vendor's
    kernel module. It intentionally does not emulate the board. Exact timing,
    channel ordering, calibration, and overrun recovery remain hardware
    acceptance items.
    """

    def __init__(
        self,
        device: Path | str,
        *,
        sample_rate: int,
        channel_numbers: tuple[int, ...],
        block_frames: int,
        buffer_seconds: float = 10.0,
    ) -> None:
        if sys.byteorder != "little":
            raise Usb4704NativeError("USB-4704 ABI requires a little-endian host")
        if sample_rate <= 0 or sample_rate > 47_619:
            raise ValueError("sample_rate must be between 1 and 47619 Hz")
        if block_frames <= 0:
            raise ValueError("block_frames must be greater than zero")
        if not channel_numbers or len(set(channel_numbers)) != len(channel_numbers):
            raise ValueError("channel_numbers must be non-empty and unique")
        if any(
            channel < 0 or channel >= AI_CHANNEL_COUNT for channel in channel_numbers
        ):
            raise ValueError("USB-4704 channel numbers must be between 0 and 7")
        if buffer_seconds <= 0:
            raise ValueError("buffer_seconds must be greater than zero")

        first = min(channel_numbers)
        last = max(channel_numbers)
        self.device = Path(device)
        self.sample_rate = sample_rate
        self.requested_channels = channel_numbers
        self.scan_channels = tuple(range(first, last + 1))
        self.block_frames = block_frames
        self.channel_count = len(self.scan_channels)
        if sample_rate * self.channel_count > 47_619:
            raise ValueError(
                "sample_rate multiplied by the contiguous scan channel count "
                "must not exceed 47619 samples/s"
            )
        capacity_frames = max(round(sample_rate * buffer_seconds), block_frames * 4)
        capacity_frames -= capacity_frames % block_frames
        self.buffer_values = capacity_frames * self.channel_count
        self.section_values = block_frames * self.channel_count

        self._libc: ctypes.CDLL | None = None
        self._fd: int | None = None
        self._status_map: mmap.mmap | None = None
        self._shared: DeviceSharedHead | None = None
        self._ring_map: mmap.mmap | None = None
        self._running = False

    @staticmethod
    def probe(device: Path | str) -> Usb4704Probe:
        path = Path(device)
        if sys.platform != "linux":
            return Usb4704Probe(path, False, reason="USB-4704 driver is Linux-only")
        try:
            fd = os.open(path, os.O_RDONLY | getattr(os, "O_CLOEXEC", 0))
        except OSError as exc:
            return Usb4704Probe(path, False, reason=_format_os_error(exc))
        try:
            description = _get_description(fd)
            if "USB-4704" not in description:
                return Usb4704Probe(
                    path,
                    False,
                    description=description,
                    reason="device node is not a USB-4704",
                )
            return Usb4704Probe(path, True, description=description)
        except OSError as exc:
            return Usb4704Probe(path, False, reason=_format_os_error(exc))
        finally:
            os.close(fd)

    def start(self) -> None:
        if self._running or self._fd is not None:
            raise Usb4704NativeError("USB-4704 buffered acquisition is already open")
        if sys.platform != "linux":
            raise Usb4704NativeError("USB-4704 acquisition requires Linux")

        try:
            self._libc = _load_libc()
            self._fd = os.open(self.device, os.O_RDWR | getattr(os, "O_CLOEXEC", 0))
            description = _get_description(self._fd, self._libc)
            if "USB-4704" not in description:
                raise Usb4704NativeError(
                    f"{self.device} reports {description!r}, not USB-4704"
                )

            page_size = mmap.PAGESIZE
            self._status_map = mmap.mmap(
                self._fd,
                page_size,
                flags=mmap.MAP_SHARED,
                prot=mmap.PROT_READ | mmap.PROT_WRITE,
                offset=0,
            )
            self._shared = DeviceSharedHead.from_buffer(self._status_map)
            if self._shared.size < ctypes.sizeof(DeviceSharedHead):
                raise Usb4704NativeError(
                    "mapped DEVICE_SHARED is smaller than the expected ABI prefix "
                    f"({self._shared.size} < {ctypes.sizeof(DeviceSharedHead)})"
                )

            self._configure_single_ended_channels()
            config = FaiConfig(
                xfer_mode=0,
                physical_channel_start=self.scan_channels[0],
                logical_channel_count=self.channel_count,
                clock_source=INTERNAL_CLOCK,
                sample_rate_per_channel=self.sample_rate,
                section_size=self.section_values,
                sample_count=self.buffer_values,
            )
            self._ioctl_pointer(IOCTL_FAI_SET_PARAM, ctypes.byref(config))

            self._ring_map = mmap.mmap(
                -1,
                self.buffer_values * ctypes.sizeof(ctypes.c_int16),
                flags=mmap.MAP_SHARED,
                prot=mmap.PROT_READ | mmap.PROT_WRITE,
            )
            ring_address = ctypes.addressof(ctypes.c_char.from_buffer(self._ring_map))
            self._ioctl_pointer(IOCTL_FAI_SET_BUFFER, ctypes.c_void_p(ring_address))
            self._ioctl_value(IOCTL_FAI_START, DAQ_ACQ_INFINITE)
            self._running = True
        except BaseException:
            self.close()
            raise

    def read_frames(
        self, stop_event: threading.Event, *, timeout: float = 1.0
    ) -> NDArray[np.int16]:
        if not self._running or self._shared is None or self._ring_map is None:
            raise Usb4704NativeError("USB-4704 buffered acquisition is not running")
        deadline = time.monotonic() + timeout
        wanted_values = self.block_frames * self.channel_count
        # The vendor ABI exposes a shared status page but no waitable file
        # descriptor. Poll at most twice per expected block instead of waking
        # Python every millisecond. At the field default (50 frames / 5 kS/s)
        # this is 5 ms: all samples remain in the driver's ring buffer while
        # substantially reducing idle CPU wakeups.
        block_period = self.block_frames / self.sample_rate
        poll_interval = min(0.010, max(0.001, block_period / 2.0))

        while not stop_event.is_set():
            status = self._shared.fai_status
            available = self._available_values(status)
            if status.hardware_flags & USB_FLAG_FAI_OVERRUN:
                raise Usb4704Overrun("USB-4704 firmware input overrun")
            if (
                status.buffer_state & DAQ_IN_BUF_OVERRUN
                or available > self.buffer_values
            ):
                raise Usb4704Overrun(
                    "USB-4704 kernel circular buffer overrun; input data was lost"
                )
            if available >= wanted_values:
                return self._consume_values(wanted_values)
            if status.function_state != DAQ_FN_RUNNING:
                raise Usb4704NativeError(
                    f"USB-4704 acquisition stopped in driver state {status.function_state}"
                )
            if time.monotonic() >= deadline:
                raise Usb4704NativeError(
                    f"USB-4704 produced no complete block for {timeout:.1f} s"
                )
            stop_event.wait(poll_interval)

        raise InterruptedError("USB-4704 read interrupted")

    def close(self) -> None:
        stop_failure: Exception | None = None
        if self._fd is not None and self._running and self._libc is not None:
            try:
                self._ioctl_value(IOCTL_FAI_STOP, FAI_STOP_FREE_RES)
            except (OSError, Usb4704NativeError) as exc:
                stop_failure = exc
        self._running = False
        self._shared = None
        if self._status_map is not None:
            self._status_map.close()
            self._status_map = None
        if self._ring_map is not None:
            self._ring_map.close()
            self._ring_map = None
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        self._libc = None
        if stop_failure is not None:
            raise Usb4704NativeError(f"USB-4704 STOP failed: {stop_failure}") from stop_failure

    def _configure_single_ended_channels(self) -> None:
        configs = (AiChannelConfig * AI_CHANNEL_COUNT)(
            *(
                AiChannelConfig(SINGLE_ENDED, GAIN_NEG10_TO_10)
                for _ in range(AI_CHANNEL_COUNT)
            )
        )
        request = AiSetChannel(
            set_which=AI_SET_CHSCTYPE | AI_SET_CHGAIN,
            physical_channel_start=0,
            physical_channel_count=AI_CHANNEL_COUNT,
            channel_config=ctypes.cast(configs, ctypes.POINTER(AiChannelConfig)),
        )
        self._ioctl_pointer(IOCTL_AI_SET_CHAN_CFG, ctypes.byref(request))

    @staticmethod
    def _available_values(status: FaiStatus) -> int:
        return (
            int(status.write_pointer_wraps) * int(status.buffer_length)
            + int(status.write_position)
            - int(status.read_position)
        )

    def _consume_values(self, count: int) -> NDArray[np.int16]:
        assert self._shared is not None
        assert self._ring_map is not None
        status = self._shared.fai_status
        start = int(status.read_position)
        tail_count = min(count, self.buffer_values - start)
        tail = np.frombuffer(
            self._ring_map, dtype="<i2", count=tail_count, offset=start * 2
        ).copy()
        if tail_count == count:
            values = tail
        else:
            head = np.frombuffer(
                self._ring_map, dtype="<i2", count=count - tail_count, offset=0
            ).copy()
            values = np.concatenate((tail, head))

        advanced = start + count
        consumed_wraps, new_position = divmod(advanced, self.buffer_values)
        if consumed_wraps:
            current_wraps = int(status.write_pointer_wraps)
            status.write_pointer_wraps = max(0, current_wraps - consumed_wraps)
        status.read_position = new_position
        return values.reshape(self.block_frames, self.channel_count)

    def _ioctl_pointer(self, request: int, argument: object) -> None:
        if self._fd is None or self._libc is None:
            raise Usb4704NativeError("USB-4704 device is not open")
        _checked_ioctl(self._libc, self._fd, request, argument)

    def _ioctl_value(self, request: int, value: int) -> None:
        if self._fd is None or self._libc is None:
            raise Usb4704NativeError("USB-4704 device is not open")
        _checked_ioctl(self._libc, self._fd, request, ctypes.c_ulong(value))

    def __enter__(self) -> Usb4704BufferedDevice:  # noqa: PYI034 - Python 3.10 support
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _load_libc() -> ctypes.CDLL:
    libc = ctypes.CDLL(None, use_errno=True)
    libc.ioctl.restype = ctypes.c_int
    return libc


def _checked_ioctl(libc: ctypes.CDLL, fd: int, request: int, argument: object) -> None:
    ctypes.set_errno(0)
    result = libc.ioctl(ctypes.c_int(fd), ctypes.c_ulong(request), argument)
    if result < 0:
        error_number = ctypes.get_errno() or errno.EIO
        raise OSError(error_number, os.strerror(error_number))


def _get_description(fd: int, libc: ctypes.CDLL | None = None) -> str:
    native = libc or _load_libc()
    buffer = ctypes.create_string_buffer(64)
    _checked_ioctl(native, fd, IOCTL_DEVICE_GET_DESC, ctypes.byref(buffer))
    return buffer.value.decode("ascii", errors="replace")


def _format_os_error(error: OSError) -> str:
    if error.filename:
        return f"{error.strerror}: {error.filename}"
    return error.strerror or str(error)
