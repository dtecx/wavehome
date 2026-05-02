from .config import (
    BRIGHTNESS_ARM_TIMEOUT_SECONDS,
    BRIGHTNESS_HOLD_STEP_SECONDS,
    BRIGHTNESS_MAX_PERCENT,
    BRIGHTNESS_MIN_PERCENT,
    BRIGHTNESS_STEP_PERCENT,
    COMMAND_LABELS,
    GESTURE_HOLD_SECONDS,
    LAMP_TOGGLE_SEQUENCE,
    SEQUENCE_TIMEOUT_SECONDS,
    TOGGLE_COOLDOWN_SECONDS,
)


class VirtualLampController:
    def __init__(self):
        self.lamp_on = False
        self.brightness = 60
        self.sequence = LAMP_TOGGLE_SEQUENCE
        self.step_index = 0
        self.started_at = None
        self.last_step_at = None
        self.last_toggle_accepted_key = None
        self.cooldown_until = 0.0

        self.candidate_key = None
        self.candidate_since = 0.0

        self.brightness_armed_until = 0.0
        self.brightness_hold_key = None
        self.brightness_hold_started_at = 0.0
        self.next_brightness_step_at = 0.0

        self.message = "Ready: show 5 fingers up"
        self.message_until = 0.0

    def reset_sequence(self):
        self.step_index = 0
        self.started_at = None
        self.last_step_at = None

    def active_message(self, now):
        if self.message_until and now < self.message_until:
            return self.message

        if self.brightness_hold_key is not None:
            remaining = max(0.0, self.next_brightness_step_at - now)
            return (
                f"Hold {COMMAND_LABELS[self.brightness_hold_key]}: "
                f"next brightness step in {remaining:.0f}s"
            )

        if self.brightness_armed_until > now:
            return "Brightness armed: hold thumb up/down"

        if self.step_index == 0:
            return "Ready: 5 fingers up"

        remaining = self.remaining_seconds(now)
        next_key = self.sequence[self.step_index]

        return (
            f"Step {self.step_index}/{len(self.sequence)}; "
            f"next: {COMMAND_LABELS[next_key]}; {remaining:.0f}s left"
        )

    def remaining_seconds(self, now):
        if self.started_at is None:
            return SEQUENCE_TIMEOUT_SECONDS

        return max(0.0, SEQUENCE_TIMEOUT_SECONDS - (now - self.started_at))

    def update(self, command_key, now):
        stable_key = self._stable_command_key(command_key, now)

        if stable_key is None:
            if command_key is None:
                self.last_toggle_accepted_key = None
                self.brightness_hold_key = None
            self._expire_toggle_sequence(now)
            return None

        brightness_action = self._update_brightness(stable_key, now)
        toggle_action = self._update_toggle_sequence(stable_key, now)

        return brightness_action or toggle_action

    def _stable_command_key(self, command_key, now):
        if command_key is None:
            self.candidate_key = None
            self.candidate_since = 0.0
            return None

        if command_key != self.candidate_key:
            self.candidate_key = command_key
            self.candidate_since = now
            self.brightness_hold_key = None
            return None

        if now - self.candidate_since < GESTURE_HOLD_SECONDS:
            return None

        return command_key

    def _expire_toggle_sequence(self, now):
        if (
            self.step_index > 0
            and self.started_at is not None
            and now - self.started_at > SEQUENCE_TIMEOUT_SECONDS
        ):
            self.reset_sequence()
            self.message = "Toggle sequence timed out"
            self.message_until = now + 2.0

    def _update_toggle_sequence(self, stable_key, now):
        self._expire_toggle_sequence(now)

        if stable_key == self.last_toggle_accepted_key or now < self.cooldown_until:
            return None

        if stable_key not in self.sequence:
            if self.step_index > 0:
                self.reset_sequence()
                self.message = "Toggle sequence cancelled"
                self.message_until = now + 1.5
                return "reset"
            return None

        expected_key = self.sequence[self.step_index]

        if stable_key == expected_key:
            return self._accept_toggle_step(stable_key, now)

        if self.step_index == 0:
            return None

        self.reset_sequence()
        self.last_toggle_accepted_key = stable_key

        if stable_key == self.sequence[0]:
            self.started_at = now
            self.step_index = 1
            self.last_step_at = now
            self.message = "Toggle sequence restarted"
        else:
            self.message = f"Start toggle with {COMMAND_LABELS[self.sequence[0]]}"

        self.message_until = now + 2.0
        return "reset"

    def _accept_toggle_step(self, stable_key, now):
        if self.step_index == 0:
            self.started_at = now

        self.step_index += 1
        self.last_step_at = now
        self.last_toggle_accepted_key = stable_key

        if self.step_index == len(self.sequence):
            self.lamp_on = not self.lamp_on
            self.cooldown_until = now + TOGGLE_COOLDOWN_SECONDS
            self.reset_sequence()
            self.message = f"Virtual lamp toggled {'ON' if self.lamp_on else 'OFF'}"
            self.message_until = now + 3.0
            return "toggle"

        next_key = self.sequence[self.step_index]
        self.message = f"Good; now {COMMAND_LABELS[next_key]}"
        self.message_until = now + 1.2
        return "step"

    def _update_brightness(self, stable_key, now):
        if stable_key == "FIST":
            self.brightness_armed_until = now + BRIGHTNESS_ARM_TIMEOUT_SECONDS
            self.brightness_hold_key = None
            self.message = "Brightness armed: hold thumb up/down"
            self.message_until = now + 1.0
            return "brightness_armed"

        if stable_key not in ("THUMB_UP", "THUMB_DOWN"):
            self.brightness_hold_key = None
            return None

        if self.brightness_armed_until < now and self.brightness_hold_key != stable_key:
            self.message = "Make a fist first for brightness"
            self.message_until = now + 1.5
            return None

        if self.brightness_hold_key != stable_key:
            self.brightness_hold_key = stable_key
            self.brightness_hold_started_at = now
            self.next_brightness_step_at = now + BRIGHTNESS_HOLD_STEP_SECONDS
            self.message = f"Hold {COMMAND_LABELS[stable_key]} for brightness"
            self.message_until = now + 1.2
            return "brightness_hold_started"

        if now < self.next_brightness_step_at:
            return None

        direction = 1 if stable_key == "THUMB_UP" else -1
        self.brightness = max(
            BRIGHTNESS_MIN_PERCENT,
            min(
                BRIGHTNESS_MAX_PERCENT,
                self.brightness + direction * BRIGHTNESS_STEP_PERCENT,
            ),
        )
        self.next_brightness_step_at = now + BRIGHTNESS_HOLD_STEP_SECONDS

        if stable_key == "THUMB_UP":
            self.message = f"Brightness increased to {self.brightness}%"
        else:
            self.message = f"Brightness decreased to {self.brightness}%"

        self.message_until = now + 1.5
        return "brightness_changed"
