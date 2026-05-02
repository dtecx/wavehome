from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class GestureEvent:
    gesture: str | None
    label: str
    timestamp: float
    hand_index: int | None = None
    hand_label: str | None = None
    confidence: float = 0.0
    value: float | None = None
    metadata: dict[str, Any] | None = None


@dataclass(slots=True)
class StableGestureEvent:
    gesture: str
    label: str
    first_seen_at: float
    accepted_at: float
    stable_ms: int
    value: float | None = None
