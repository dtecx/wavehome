from __future__ import annotations

from collections import deque


class MotionDetector:
    def __init__(
        self,
        window_seconds: float = 0.70,
        min_distance: float = 0.16,
        dominance_ratio: float = 1.55,
        cooldown_seconds: float = 0.80,
    ):
        self.window_seconds = window_seconds
        self.min_distance = min_distance
        self.dominance_ratio = dominance_ratio
        self.cooldown_seconds = cooldown_seconds
        self.points: deque[tuple[float, float, float]] = deque()
        self.cooldown_until = 0.0

    def update(
        self,
        center: tuple[float, float] | None,
        now: float,
    ) -> str | None:
        if center is None:
            self.points.clear()
            return None

        x, y = center
        self.points.append((now, x, y))

        while self.points and now - self.points[0][0] > self.window_seconds:
            self.points.popleft()

        if now < self.cooldown_until or len(self.points) < 3:
            return None

        start_time, start_x, start_y = self.points[0]
        end_time, end_x, end_y = self.points[-1]

        elapsed = max(0.001, end_time - start_time)
        dx = end_x - start_x
        dy = end_y - start_y

        if elapsed > self.window_seconds:
            return None

        gesture = None

        if abs(dx) >= self.min_distance and abs(dx) > abs(dy) * self.dominance_ratio:
            gesture = "SWIPE_RIGHT" if dx > 0 else "SWIPE_LEFT"

        elif abs(dy) >= self.min_distance and abs(dy) > abs(dx) * self.dominance_ratio:
            gesture = "SWIPE_DOWN" if dy > 0 else "SWIPE_UP"

        if gesture is None:
            return None

        self.cooldown_until = now + self.cooldown_seconds
        self.points.clear()
        return gesture
