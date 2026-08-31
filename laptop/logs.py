from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

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


def read_session_summary(path: str | Path) -> SessionSummary:
    log_path = Path(path)
    try:
        with h5py.File(log_path, "r") as data:
            metadata = data["metadata"].attrs
            events = data["events"][:]
            trigger_sample = next(
                (
                    int(event["sample_index"])
                    for event in events
                    if event["event_type"].rstrip(b"\0") == b"ignition"
                ),
                None,
            )
            return SessionSummary(
                path=log_path,
                test_name=str(metadata.get("test_name", log_path.stem)),
                start_time=str(metadata.get("start_time", "")),
                sample_count=int(
                    metadata.get("sample_count", len(data["samples/sample_index"]))
                ),
                trigger_sample=trigger_sample,
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
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with (
            h5py.File(source_path, "r") as data,
            destination_path.open("w", encoding="utf-8", newline="") as output,
        ):
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
            summary = read_session_summary(source_path)
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
                rows = zip(
                    indices,
                    times,
                    samples["raw_thrust"][start:end],
                    samples["raw_pressure"][start:end],
                    samples["thrust_N"][start:end],
                    samples["pressure_bar"][start:end],
                    thrust_lpf[start:end],
                    pressure_lpf[start:end],
                )
                writer.writerows(rows)
    except LogError:
        raise
    except (OSError, KeyError, ValueError) as exc:
        raise LogError(f"cannot export TMS log: {source_path}") from exc
    return destination_path
