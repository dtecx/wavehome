class StableGestureFilter:
    def __init__(self, hold_seconds: float):
        self.hold_seconds = hold_seconds
        self.candidate = None
        self.candidate_since = 0.0
        self.last_accepted = None

    def update(self, gesture: str | None, now: float) -> str | None:
        if gesture is None:
            self.candidate = None
            self.candidate_since = 0.0
            self.last_accepted = None
            return None

        if gesture != self.candidate:
            self.candidate = gesture
            self.candidate_since = now
            return None

        if now - self.candidate_since < self.hold_seconds:
            return None

        return gesture
