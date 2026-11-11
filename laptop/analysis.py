"""Result data shared by the local and remote dashboards."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np

from common.filtering import DEFAULT_MOVING_WINDOW_SAMPLES, MovingAverage
from laptop.logs import LogError, MovingAverageLogReader, read_session_summary


@dataclass(frozen=True)
class AnalysisData:
    path: Path
    sample_indices: np.ndarray
    time_s: np.ndarray
    thrust_N: np.ndarray
    pressure_bar: np.ndarray
    time_reference: str
    window_samples: int = DEFAULT_MOVING_WINDOW_SAMPLES


def read_analysis_data(path: str | Path) -> AnalysisData:
    source = Path(path)
    try:
        if source.suffix.lower() == '.csv':
            return _read_csv(source)
        with h5py.File(source, 'r') as data:
            summary = read_session_summary(source)
            sample_rate = float(data['metadata'].attrs['sample_rate'])
            if not np.isfinite(sample_rate) or sample_rate <= 0:
                raise ValueError('invalid sample rate')
            samples = data['samples']
            count = len(samples['sample_index'])
            indices = np.empty(count, dtype=np.int64)
            thrust = np.empty(count, dtype=np.float32)
            pressure = np.empty(count, dtype=np.float32)
            reader = MovingAverageLogReader(data)
            for start in range(0, count, 100_000):
                end = min(count, start + 100_000)
                indices[start:end] = samples['sample_index'][start:end]
                thrust[start:end], pressure[start:end] = reader.read(start, end, indices[start:end])
            origin = summary.trigger_sample if summary.trigger_sample is not None else 0
            return AnalysisData(source, indices, (indices - origin) / sample_rate, thrust, pressure,
                                '점화 수신 기준' if summary.trigger_sample is not None else '수집 시작 기준')
    except (OSError, KeyError, ValueError, TypeError) as exc:
        raise LogError(f'결과 분석 파일을 읽을 수 없습니다: {source}: {exc}') from exc


def _read_csv(source: Path) -> AnalysisData:
    indices, times, thrust, pressure = [], [], [], []
    reference = '수집 시작 기준'
    with source.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        fields = set(reader.fieldnames or ())
        stored = {'thrust_N_ma', 'pressure_bar_ma', 'moving_average_window_samples'} <= fields
        for row in reader:
            indices.append(int(row['sample_index']))
            times.append(float(row['time_s']))
            if stored and int(row['moving_average_window_samples']) != DEFAULT_MOVING_WINDOW_SAMPLES:
                raise ValueError('CSV moving-average window must be 80 samples')
            thrust.append(float(row['thrust_N_ma' if stored else 'thrust_N']))
            pressure.append(float(row['pressure_bar_ma' if stored else 'pressure_bar']))
            if row.get('time_reference') == 'ignition_receipt':
                reference = '점화 수신 기준'
    indices = np.asarray(indices, dtype=np.int64)
    if stored:
        thrust, pressure = np.asarray(thrust, dtype=np.float32), np.asarray(pressure, dtype=np.float32)
    else:
        thrust, pressure = (MovingAverage().apply_indexed(np.asarray(values), indices).astype(np.float32)
                            for values in (thrust, pressure))
    return AnalysisData(source, indices, np.asarray(times), thrust, pressure, reference)
