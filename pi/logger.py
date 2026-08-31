from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import h5py
import numpy as np

from common.config import TmsConfig
from common.filtering import FirstOrderLowPass
from pi.daq import DaqBlock

SOFTWARE_VERSION = "0.1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def safe_test_name(test_name: str) -> str:
    cleaned = re.sub(r"[^\w-]+", "_", test_name.strip()).strip("_")
    if not cleaned:
        raise ValueError("test_name must contain at least one letter or number")
    return cleaned


@dataclass(frozen=True)
class SessionMetadata:
    test_name: str
    session_id: str
    start_time: str


class Hdf5SessionLogger:
    def __init__(self, config: TmsConfig, output_directory: Path | None = None) -> None:
        self._config = config
        self._output_directory = output_directory or config.logging.directory
        self._file: h5py.File | None = None
        self._path: Path | None = None
        self._datasets: dict[str, h5py.Dataset] = {}
        self._expected_sequence: int | None = None
        self._expected_sample_index: int | None = None
        self._samples_written = 0
        self._last_flush = 0.0
        self._thrust_filter: FirstOrderLowPass | None = None
        self._pressure_filter: FirstOrderLowPass | None = None

    @property
    def path(self) -> Path:
        if self._path is None:
            raise RuntimeError("session logger is not open")
        return self._path

    @property
    def samples_written(self) -> int:
        return self._samples_written

    def open(self, metadata: SessionMetadata) -> Path:
        if self._file is not None:
            raise RuntimeError("session logger is already open")

        self._output_directory.mkdir(parents=True, exist_ok=True)
        self._expected_sequence = None
        self._expected_sample_index = None
        self._samples_written = 0
        self._thrust_filter = FirstOrderLowPass(
            self._config.daq.sample_rate,
            self._config.low_pass.cutoff_hz,
            self._config.low_pass.enabled,
        )
        self._pressure_filter = FirstOrderLowPass(
            self._config.daq.sample_rate,
            self._config.low_pass.cutoff_hz,
            self._config.low_pass.enabled,
        )
        date = metadata.start_time[:10]
        name = safe_test_name(metadata.test_name)
        path = self._output_directory / f"{date}_{name}_{metadata.session_id}.h5"
        self._file = h5py.File(path, "x")
        self._path = path

        metadata_group = self._file.create_group("metadata")
        metadata_group.attrs["test_name"] = metadata.test_name
        metadata_group.attrs["session_id"] = metadata.session_id
        metadata_group.attrs["start_time"] = metadata.start_time
        metadata_group.attrs["sample_rate"] = self._config.daq.sample_rate
        metadata_group.attrs["software_version"] = SOFTWARE_VERSION
        config_data = self._config.as_dict()
        metadata_group.attrs["daq_configuration"] = json.dumps(
            config_data["daq"], sort_keys=True
        )
        metadata_group.attrs["sensor_calibration"] = json.dumps(
            {
                "thrust": config_data["channels"]["thrust"],
                "pressure": config_data["channels"]["pressure"],
                "pressure_input": config_data["pressure_input"],
                "low_pass": config_data["low_pass"],
            },
            sort_keys=True,
        )

        samples = self._file.create_group("samples")
        chunk_samples = max(
            self._config.daq.samples_per_block,
            min(self._config.daq.sample_rate, 8192),
        )
        self._datasets = {
            "sample_index": samples.create_dataset(
                "sample_index",
                shape=(0,),
                maxshape=(None,),
                chunks=(chunk_samples,),
                dtype="<u8",
            ),
            "raw_thrust": samples.create_dataset(
                "raw_thrust",
                shape=(0,),
                maxshape=(None,),
                chunks=(chunk_samples,),
                dtype="<i4",
            ),
            "raw_pressure": samples.create_dataset(
                "raw_pressure",
                shape=(0,),
                maxshape=(None,),
                chunks=(chunk_samples,),
                dtype="<i4",
            ),
            "thrust_N": samples.create_dataset(
                "thrust_N",
                shape=(0,),
                maxshape=(None,),
                chunks=(chunk_samples,),
                dtype="<f4",
            ),
            "pressure_bar": samples.create_dataset(
                "pressure_bar",
                shape=(0,),
                maxshape=(None,),
                chunks=(chunk_samples,),
                dtype="<f4",
            ),
            "thrust_N_lpf": samples.create_dataset(
                "thrust_N_lpf",
                shape=(0,),
                maxshape=(None,),
                chunks=(chunk_samples,),
                dtype="<f4",
            ),
            "pressure_bar_lpf": samples.create_dataset(
                "pressure_bar_lpf",
                shape=(0,),
                maxshape=(None,),
                chunks=(chunk_samples,),
                dtype="<f4",
            ),
        }

        event_dtype = np.dtype(
            [
                ("event_type", "S32"),
                ("sample_index", "<i8"),
                ("receive_time", "S40"),
                ("details", "S256"),
            ]
        )
        self._datasets["events"] = self._file.create_dataset(
            "events", shape=(0,), maxshape=(None,), chunks=(64,), dtype=event_dtype
        )

        health_dtype = np.dtype(
            [
                ("time", "S40"),
                ("component", "S32"),
                ("level", "S16"),
                ("message", "S256"),
            ]
        )
        self._datasets["health"] = self._file.create_dataset(
            "health", shape=(0,), maxshape=(None,), chunks=(64,), dtype=health_dtype
        )
        self._file.flush()
        self._last_flush = time.monotonic()
        return path

    def append_block(self, block: DaqBlock) -> None:
        self._require_open()
        if block.sample_rate != self._config.daq.sample_rate:
            raise ValueError(
                f"sample rate changed from {self._config.daq.sample_rate} "
                f"to {block.sample_rate}"
            )

        gap_details: list[str] = []
        if (
            self._expected_sequence is not None
            and block.sequence != self._expected_sequence
        ):
            gap_details.append(
                f"expected_sequence={self._expected_sequence},actual_sequence={block.sequence}"
            )
        if (
            self._expected_sample_index is not None
            and block.first_sample_index != self._expected_sample_index
        ):
            difference = block.first_sample_index - self._expected_sample_index
            gap_details.append(
                f"expected_sample={self._expected_sample_index},difference={difference}"
            )
        if gap_details:
            self.record_event(
                "DATA_GAP",
                block.first_sample_index,
                details=",".join(gap_details),
            )
            if self._thrust_filter is not None:
                self._thrust_filter.reset()
            if self._pressure_filter is not None:
                self._pressure_filter.reset()

        raw_thrust = block.column_for_channel(self._config.thrust.channel).astype(
            np.int32, copy=False
        )
        raw_pressure = block.column_for_channel(self._config.pressure.channel).astype(
            np.int32, copy=False
        )
        thrust = raw_thrust.astype(np.float64) * self._config.thrust.scale
        thrust += self._config.thrust.offset
        pressure = raw_pressure.astype(np.float64) * self._config.pressure.scale
        pressure += self._config.pressure.offset
        if self._thrust_filter is None or self._pressure_filter is None:
            raise RuntimeError("low-pass filters are not initialized")
        thrust_lpf = self._thrust_filter.apply(thrust)
        pressure_lpf = self._pressure_filter.apply(pressure)
        sample_indices = np.arange(
            block.first_sample_index,
            block.first_sample_index + block.sample_count,
            dtype=np.uint64,
        )

        start = self._samples_written
        end = start + block.sample_count
        values: dict[str, np.ndarray[Any, Any]] = {
            "sample_index": sample_indices,
            "raw_thrust": raw_thrust,
            "raw_pressure": raw_pressure,
            "thrust_N": thrust.astype(np.float32),
            "pressure_bar": pressure.astype(np.float32),
            "thrust_N_lpf": thrust_lpf.astype(np.float32),
            "pressure_bar_lpf": pressure_lpf.astype(np.float32),
        }
        for name, data in values.items():
            dataset = self._datasets[name]
            dataset.resize((end,))
            dataset[start:end] = data

        self._samples_written = end
        self._expected_sequence = block.sequence + 1
        self._expected_sample_index = block.first_sample_index + block.sample_count
        self._flush_if_due()

    def record_event(
        self,
        event_type: str,
        sample_index: int,
        *,
        receive_time: str | None = None,
        details: str = "",
    ) -> None:
        self._require_open()
        dataset = self._datasets["events"]
        index = len(dataset)
        dataset.resize((index + 1,))
        dataset[index] = (
            event_type.encode("utf-8")[:32],
            sample_index,
            (receive_time or utc_now()).encode("utf-8")[:40],
            details.encode("utf-8")[:256],
        )
        self._flush_if_due()

    def record_health(self, component: str, level: str, message: str) -> None:
        self._require_open()
        dataset = self._datasets["health"]
        index = len(dataset)
        dataset.resize((index + 1,))
        dataset[index] = (
            utc_now().encode("utf-8")[:40],
            component.encode("utf-8")[:32],
            level.encode("utf-8")[:16],
            message.encode("utf-8")[:256],
        )
        self._flush_if_due()

    def close(self) -> None:
        if self._file is None:
            return
        metadata = self._file["metadata"]
        metadata.attrs["end_time"] = utc_now()
        metadata.attrs["sample_count"] = self._samples_written
        self._file.flush()
        self._file.close()
        self._file = None
        self._datasets = {}

    def _require_open(self) -> h5py.File:
        if self._file is None:
            raise RuntimeError("session logger is not open")
        return self._file

    def _flush_if_due(self) -> None:
        now = time.monotonic()
        if now - self._last_flush >= self._config.logging.flush_interval_sec:
            self._require_open().flush()
            self._last_flush = now

    def __enter__(self) -> Hdf5SessionLogger:  # noqa: PYI034 - Python 3.10 support
        self._require_open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
