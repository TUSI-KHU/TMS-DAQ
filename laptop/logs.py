from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import repeat
from pathlib import Path
from tempfile import NamedTemporaryFile

import h5py
import numpy as np


class LogError(RuntimeError):
    """Raised when a TMS log cannot be read or exported."""


@dataclass(frozen=True)
class SessionSummary:
    path: Path
    test_name: str
    start_time: str
    sample_count: int
    trigger_sample: int | None
    trigger_source: str | None = None
    trigger_receive_time: str | None = None
    nano_sequence: int | None = None
    nano_uptime_ms: int | None = None
    trigger_timing_basis: str | None = None


def _iter_events(events: h5py.Dataset, chunk_size: int = 1024) -> Iterator[np.void]:
    # Heartbeats make the event table grow continuously. Do not load the
    # entire table just to find an ignition event or export a long session.
    for start in range(0, len(events), chunk_size):
        yield from events[start : start + chunk_size]


@dataclass(frozen=True)
class _NanoState:
    sample_index: int
    gpio: int | None
    valid_samples: float


def _nano_states(events: h5py.Dataset, sample_rate: float) -> Iterator[_NanoState]:
    previous_index: int | None = None
    for event in _iter_events(events):
        if event["event_type"].rstrip(b"\0") != b"nano_state":
            continue
        index = int(event["sample_index"])
        if previous_index is not None and index < previous_index:
            raise LogError("Nano state sample indices are not ordered")
        previous_index = index
        gpio = None
        valid_samples = 0.0
        try:
            details = json.loads(event["details"].decode("utf-8"))
            if isinstance(details, dict):
                state = details.get("gpio_state")
                valid_ms = details.get("valid_for_ms")
                valid_duration = (
                    type(valid_ms) in (int, float)
                    and math.isfinite(valid_ms)
                    and 0 <= valid_ms <= 2000
                )
                valid_counters = all(
                    details.get(name) is None
                    or (type(details[name]) is int and details[name] >= 0)
                    for name in ("nano_sequence", "nano_uptime_ms")
                )
                if (
                    index >= 0
                    and details.get("source") == "nano"
                    and details.get("timing_basis") == "pi_latest_sample_on_receipt"
                    and type(state) is int
                    and state in (0, 1)
                    and valid_duration
                    and valid_counters
                ):
                    gpio = state
                    valid_samples = valid_ms * sample_rate / 1000.0
        except (ValueError, UnicodeDecodeError, OverflowError):
            pass
        # An invalid or explicit unknown observation breaks an earlier
        # held state; it must not disappear and accidentally extend HIGH.
        yield _NanoState(index, gpio, valid_samples)


class _NanoStateCursor:
    def __init__(self, events: h5py.Dataset, sample_rate: float) -> None:
        self._states = _nano_states(events, sample_rate)
        self._pending = next(self._states, None)
        self._current: _NanoState | None = None

    def columns(self, indices: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        gpio = np.full(len(indices), "", dtype="U1")
        valid = np.zeros(len(indices), dtype=np.uint8)
        observed = np.zeros(len(indices), dtype=np.uint8)
        if not len(indices):
            return gpio, valid, observed

        def fill(start: int, end: int) -> None:
            state = self._current
            if state is None or state.gpio is None or start == end:
                return
            # Expiry is exclusive: a 500 ms observation at 1 kHz describes
            # 500 samples, not 501. Gaps are checked by index, not row count.
            expiry = state.sample_index + state.valid_samples
            valid_end = min(end, int(np.searchsorted(indices, expiry, side="left")))
            if valid_end > start:
                gpio[start:valid_end] = str(state.gpio)
                valid[start:valid_end] = 1

        start = 0
        while self._pending is not None and self._pending.sample_index <= int(indices[-1]):
            state = self._pending
            position = int(np.searchsorted(indices, state.sample_index, side="left"))
            fill(start, position)
            if position < len(indices) and int(indices[position]) == state.sample_index:
                observed[position] = 1
            self._current = state
            self._pending = next(self._states, None)
            start = position
        fill(start, len(indices))
        return gpio, valid, observed


def read_session_summary(path: str | Path) -> SessionSummary:
    log_path = Path(path)
    try:
        with h5py.File(log_path, "r") as data:
            metadata = data["metadata"].attrs
            ignition = next(
                (
                    event
                    for event in _iter_events(data["events"])
                    if event["event_type"].rstrip(b"\0") == b"ignition"
                ),
                None,
            )
            details = {}
            if ignition is not None:
                try:
                    details = json.loads(ignition["details"].decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    pass
                if not isinstance(details, dict):
                    details = {}
            return SessionSummary(
                path=log_path,
                test_name=str(metadata.get("test_name", log_path.stem)),
                start_time=str(metadata.get("start_time", "")),
                sample_count=int(
                    metadata.get("sample_count", len(data["samples/sample_index"]))
                ),
                trigger_sample=int(ignition["sample_index"]) if ignition is not None else None,
                trigger_source=str(details.get("source") or "unknown") if ignition is not None else None,
                trigger_receive_time=ignition["receive_time"].decode("utf-8") if ignition is not None else None,
                nano_sequence=details.get("nano_sequence"),
                nano_uptime_ms=details.get("nano_uptime_ms"),
                trigger_timing_basis=str(details.get("timing_basis") or "unknown") if ignition is not None else None,
            )
    except (OSError, KeyError, ValueError) as exc:
        raise LogError(f"invalid TMS log: {log_path}") from exc


def list_sessions(directory: str | Path) -> list[SessionSummary]:
    log_directory = Path(directory)
    if not log_directory.exists():
        return []
    sessions: list[SessionSummary] = []
    for path in log_directory.glob("*.h5"):
        try:
            sessions.append(read_session_summary(path))
        except LogError:
            continue
    return sorted(sessions, key=lambda session: session.start_time, reverse=True)


def export_csv(
    source: str | Path, destination: str | Path, *, chunk_samples: int = 100_000
) -> Path:
    if chunk_samples <= 0:
        raise ValueError("chunk_samples must be greater than zero")
    source_path = Path(source)
    destination_path = Path(destination)
    if source_path.resolve() == destination_path.resolve() or (
        source_path.exists() and destination_path.exists() and source_path.samefile(destination_path)
    ):
        raise LogError("CSV destination must not overwrite the original HDF5 log")
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None
    try:
        with (
            h5py.File(source_path, "r") as data,
            NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="", delete=False,
                dir=destination_path.parent, prefix=f".{destination_path.name}.", suffix=".tmp",
            ) as output,
        ):
            temporary_path = Path(output.name)
            samples = data["samples"]
            required = (
                "sample_index",
                "raw_thrust",
                "raw_pressure",
                "thrust_N",
                "pressure_bar",
            )
            for name in required:
                if name not in samples:
                    raise LogError(f"missing HDF5 dataset: /samples/{name}")
            # Logs written before LPF support remain exportable; their
            # unfiltered physical values are used as a compatibility fallback.
            thrust_lpf = samples.get("thrust_N_lpf", samples["thrust_N"])
            pressure_lpf = samples.get("pressure_bar_lpf", samples["pressure_bar"])
            sample_rate = float(data["metadata"].attrs["sample_rate"])
            if not np.isfinite(sample_rate) or sample_rate <= 0:
                raise LogError("invalid sample rate in HDF5 log")
            summary = read_session_summary(source_path)
            recorded = summary.trigger_sample is not None
            time_reference = "ignition_receipt" if recorded else "acquisition_start"
            marker_count = 0
            nano_states = _NanoStateCursor(data["events"], sample_rate)
            writer = csv.writer(output)
            writer.writerow(
                (
                    "sample_index",
                    "time_s",
                    "raw_thrust",
                    "raw_pressure",
                    "thrust_N",
                    "pressure_bar",
                    "thrust_N_lpf",
                    "pressure_bar_lpf",
                    "acquisition_time_s",
                    "ignition",
                    "ignition_recorded",
                    "time_reference",
                    "ignition_source",
                    "ignition_receive_time_utc",
                    "nano_sequence",
                    "nano_uptime_ms",
                    "ignition_timing_basis",
                    "nano_gpio",
                    "nano_gpio_valid",
                    "nano_gpio_observed",
                )
            )
            count = len(samples["sample_index"])
            for start in range(0, count, chunk_samples):
                end = min(start + chunk_samples, count)
                indices = samples["sample_index"][start:end]
                origin = (
                    summary.trigger_sample if summary.trigger_sample is not None else 0
                )
                times = (indices.astype(np.float64) - origin) / sample_rate
                markers = indices == summary.trigger_sample if recorded else np.zeros(len(indices), dtype=bool)
                marker_count += int(np.count_nonzero(markers))
                nano_gpio, nano_valid, nano_observed = nano_states.columns(indices)
                # Metadata belongs to the marked row. The repeated validity
                # and time-reference columns also make a no-trigger CSV explicit.
                event_fields = [
                    (
                        summary.trigger_source or "unknown",
                        summary.trigger_receive_time or "",
                        summary.nano_sequence if summary.nano_sequence is not None else "",
                        summary.nano_uptime_ms if summary.nano_uptime_ms is not None else "",
                        summary.trigger_timing_basis or "unknown",
                    ) if marked else ("", "", "", "", "")
                    for marked in markers
                ]
                rows = zip(
                    indices,
                    times,
                    samples["raw_thrust"][start:end],
                    samples["raw_pressure"][start:end],
                    samples["thrust_N"][start:end],
                    samples["pressure_bar"][start:end],
                    thrust_lpf[start:end],
                    pressure_lpf[start:end],
                    indices.astype(np.float64) / sample_rate,
                    markers.astype(np.uint8),
                    repeat(int(recorded)),
                    repeat(time_reference),
                    event_fields,
                    nano_gpio,
                    nano_valid,
                    nano_observed,
                )
                writer.writerows((*row[:-4], *row[-4], *row[-3:]) for row in rows)
            if recorded and marker_count != 1:
                raise LogError("ignition sample is missing or duplicated in the recorded data")
        temporary_path.replace(destination_path)
    except LogError:
        raise
    except (OSError, KeyError, ValueError) as exc:
        raise LogError(f"cannot export TMS log: {source_path}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return destination_path
