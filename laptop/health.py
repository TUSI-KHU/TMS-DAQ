from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum


class HealthLevel(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    GRAY = "GRAY"


@dataclass(frozen=True)
class ComponentHealth:
    component: str
    level: HealthLevel
    message: str


class HealthModel:
    def __init__(self) -> None:
        self._values: dict[str, ComponentHealth] = {}
        self._lock = threading.Lock()

    def update(self, component: str, level: HealthLevel, message: str) -> None:
        with self._lock:
            self._values[component] = ComponentHealth(component, level, message)

    def snapshot(self) -> dict[str, ComponentHealth]:
        with self._lock:
            return dict(self._values)
