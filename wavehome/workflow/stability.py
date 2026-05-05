from __future__ import annotations

from wavehome.events import GestureEvent
from wavehome.gesture_catalog import gesture_kind, gesture_label


class StableGestureFilter:
    def __init__(self, hold_seconds: float, grace_seconds: float = 0.15):
        self.hold_seconds = hold_seconds
        self.grace_seconds = grace_seconds
        self.candidate = None
        self.candidate_since = 0.0
        self.last_accepted = None
        self.last_accepted_time = 0.0

    def update(self, gesture: str | None, now: float) -> str | None:
        if gesture is None:
            self.candidate = None
            self.candidate_since = 0.0
            self.last_accepted = None
            return None

        if gesture != self.candidate:
            # Grace period: if we had an accepted gesture and the new one
            # appears only briefly, keep the old one
            if (
                self.last_accepted is not None
                and now - self.last_accepted_time < self.grace_seconds
            ):
                # Ignore the blip, keep last accepted
                return self.last_accepted

            self.candidate = gesture
            self.candidate_since = now
            return None

        if now - self.candidate_since < self.hold_seconds:
            return None

        self.last_accepted = gesture
        self.last_accepted_time = now
        return gesture

    def update_event(
        self,
        gesture: str | None,
        now: float,
        value: float | None = None,
        confidence: float = 1.0,
        hand_count: int = 1,
        kind: str | None = None,
    ) -> GestureEvent | None:
        stable_gesture = self.update(gesture, now)
        if stable_gesture is None:
            return None

        candidate_since = self.candidate_since or now
        stable_ms = int(max(0.0, now - candidate_since) * 1000)

        return GestureEvent(
            key=stable_gesture,
            kind=kind or gesture_kind(stable_gesture),
            confidence=confidence,
            stable_ms=stable_ms,
            value=value,
            hand_count=hand_count,
            timestamp=now,
            label=gesture_label(stable_gesture),
        )