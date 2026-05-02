from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class GestureEvent:
    key: str | None
    kind: str = "static"
    confidence: float = 1.0
    stable_ms: int = 0
    value: float | None = None
    hand_count: int = 1
    timestamp: float | None = None
    label: str | None = None
    metadata: dict[str, Any] | None = None

    @property
    def gesture(self) -> str | None:
        return self.key


@dataclass(slots=True)
class StableGestureEvent:
    gesture: str
    label: str
    first_seen_at: float
    accepted_at: float
    stable_ms: int
    value: float | None = None
