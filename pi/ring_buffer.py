from __future__ import annotations

import math
import threading
from collections import deque

from pi.daq import DaqBlock


class BlockRingBuffer:
    def __init__(self, capacity_seconds: float, block_ms: int) -> None:
        self._blocks: deque[DaqBlock] = deque(
            maxlen=max(1, math.ceil(capacity_seconds * 1000.0 / block_ms))
        )
        self._lock = threading.Lock()

    @property
    def capacity_blocks(self) -> int:
        return int(self._blocks.maxlen or 0)

    def append(self, block: DaqBlock) -> None:
        with self._lock:
            self._blocks.append(block)

    def clear(self) -> None:
        with self._lock:
            self._blocks.clear()

    def snapshot(self) -> tuple[DaqBlock, ...]:
        with self._lock:
            return tuple(self._blocks)

    def latest_sample_index(self) -> int | None:
        with self._lock:
            if not self._blocks:
                return None
            return self._blocks[-1].last_sample_index
