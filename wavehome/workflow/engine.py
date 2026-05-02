from __future__ import annotations

from typing import Any


class WorkflowEngine:
    def __init__(self, rules: list[dict[str, Any]], action_adapter):
        self.rules = rules
        self.action_adapter = action_adapter

        self.sequence_state: dict[str, dict[str, Any]] = {}
        self.hold_state: dict[str, dict[str, Any]] = {}
        self.armed_hold_state: dict[str, dict[str, Any]] = {}

        self.cooldowns: dict[str, float] = {}
        self.pending_confirmation: dict[str, Any] | None = None
        self.command_mode_until = 0.0
        self.message = "Workflow engine ready"

    def update(
        self,
        stable_gesture: str | None,
        now: float,
        value: float | None = None,
    ) -> str | None:
        confirmation_result = self._update_confirmation(stable_gesture, now)
        if confirmation_result is not None:
            return confirmation_result

        if stable_gesture is None:
            self._reset_hold_inputs()
            return None

        for rule in self.rules:
            if not rule.get("enabled", True):
                continue

            trigger = rule.get("trigger", {})
            kind = trigger.get("kind")

            if kind == "sequence":
                action_result = self._update_sequence_rule(rule, stable_gesture, now)
            elif kind == "hold":
                action_result = self._update_hold_rule(rule, stable_gesture, now)
            elif kind == "repeat_hold":
                action_result = self._update_repeat_hold_rule(rule, stable_gesture, now)
            elif kind == "armed_hold":
                action_result = self._update_armed_hold_rule(rule, stable_gesture, now)
            elif kind == "motion":
                action_result = self._update_motion_rule(rule, stable_gesture, now)
            elif kind == "value_control":
                action_result = self._update_value_control_rule(
                    rule,
                    stable_gesture,
                    now,
                    value,
                )
            else:
                action_result = None

            if action_result:
                return action_result

        return None

    def _update_confirmation(self, stable_gesture: str | None, now: float) -> str | None:
        if self.pending_confirmation is None:
            return None

        pending = self.pending_confirmation

        if now > pending["expires_at"]:
            self.pending_confirmation = None
            self.message = "Confirmation timed out"
            return "confirmation_timeout"

        if stable_gesture is None:
            return None

        if stable_gesture == pending["gesture"]:
            rule = pending["rule"]
            self.pending_confirmation = None

            action = rule.get("action", {})
            result = self._execute_action(action, now)
            if result is None:
                result = self.action_adapter.execute(action)

            self._set_cooldown(rule, now)
            self.message = f"Confirmed: {rule.get('name', rule['id'])}"
            return result

        if stable_gesture == "THUMB_DOWN":
            self.pending_confirmation = None
            self.message = "Confirmation cancelled"
            return "confirmation_cancelled"

        self.message = f"Waiting for confirmation: {pending['gesture']}"
        return None

    def _command_mode_active(self, now: float) -> bool:
        return now < self.command_mode_until

    def _requires_command_mode(self, rule: dict[str, Any]) -> bool:
        safety = rule.get("safety", {})
        command_mode = safety.get("command_mode", {})
        return bool(command_mode.get("required", False))

    def _execute_action(self, action: dict[str, Any], now: float) -> str | None:
        kind = action.get("kind")

        if kind == "workflow.enter_command_mode":
            duration_ms = int(action.get("duration_ms", 10000))
            self.command_mode_until = now + duration_ms / 1000.0
            return "command_mode_entered"

        if kind == "workflow.exit_command_mode":
            self.command_mode_until = 0.0
            return "command_mode_exited"

        if kind == "workflow.cancel":
            self.pending_confirmation = None
            self.sequence_state.clear()
            self.hold_state.clear()
            self.armed_hold_state.clear()
            return "workflow_cancelled"

        return None

    def _on_cooldown(self, rule: dict[str, Any], now: float) -> bool:
        until = self.cooldowns.get(rule["id"], 0.0)
        return now < until

    def _set_cooldown(self, rule: dict[str, Any], now: float) -> None:
        cooldown_ms = rule.get("safety", {}).get("cooldown_ms", 0)
        if cooldown_ms > 0:
            self.cooldowns[rule["id"]] = now + cooldown_ms / 1000.0

    def _execute_rule(
        self,
        rule: dict[str, Any],
        now: float,
        action_override: dict[str, Any] | None = None,
    ) -> str | None:
        if self._on_cooldown(rule, now):
            return None

        if self._requires_command_mode(rule) and not self._command_mode_active(now):
            self.message = "Command mode required"
            return None

        confirmation = rule.get("safety", {}).get("confirmation", {})
        if confirmation.get("required"):
            self.pending_confirmation = {
                "rule": rule,
                "gesture": confirmation.get("gesture", "THUMB_UP"),
                "expires_at": now + confirmation.get("timeout_ms", 3000) / 1000.0,
            }
            self.message = f"Confirm: {rule.get('name', rule['id'])}"
            return "pending_confirmation"

        action = action_override or rule.get("action", {})
        result = self._execute_action(action, now)
        if result is None:
            result = self.action_adapter.execute(action)

        self._set_cooldown(rule, now)

        if result == "command_mode_entered":
            duration_left = max(0.0, self.command_mode_until - now)
            self.message = f"Command mode active for {duration_left:.0f}s"
        elif result == "workflow_cancelled":
            self.message = "Workflow cancelled"
        else:
            self.message = f"Executed: {rule.get('name', rule['id'])}"

        return result

    def _update_sequence_rule(
        self,
        rule: dict[str, Any],
        stable_gesture: str,
        now: float,
    ) -> str | None:
        state = self.sequence_state.setdefault(
            rule["id"],
            {
                "index": 0,
                "started_at": None,
                "step_started_at": None,
                "last_step_at": None,
                "last_accepted_gesture": None,
            },
        )

        trigger = rule["trigger"]
        steps = trigger.get("steps", [])
        if not steps:
            return None

        max_total = trigger.get("max_total_ms", 15000) / 1000.0
        max_gap = trigger.get("max_gap_ms", 4000) / 1000.0

        if state["started_at"] is not None and now - state["started_at"] > max_total:
            self._reset_sequence_state(state)
            self.message = f"Sequence timed out: {rule.get('name', rule['id'])}"

        if (
            state["last_step_at"] is not None
            and stable_gesture != state["last_accepted_gesture"]
            and now - state["last_step_at"] > max_gap
        ):
            self._reset_sequence_state(state)
            self.message = f"Sequence gap timed out: {rule.get('name', rule['id'])}"

        if stable_gesture == state["last_accepted_gesture"]:
            return None

        expected_step = steps[state["index"]]
        expected_gesture = expected_step["gesture"]

        if stable_gesture != expected_gesture:
            if state["index"] > 0:
                self._reset_sequence_state(state)
                self.message = f"Sequence cancelled: {rule.get('name', rule['id'])}"
            return None

        if state["step_started_at"] is None:
            state["step_started_at"] = now
            if state["index"] == 0:
                state["started_at"] = now

        hold_seconds = expected_step.get("hold_ms", 0) / 1000.0
        if now - state["step_started_at"] < hold_seconds:
            remaining = hold_seconds - (now - state["step_started_at"])
            self.message = (
                f"{rule.get('name', rule['id'])}: hold {expected_gesture} "
                f"{remaining:.1f}s"
            )
            return None

        state["index"] += 1
        state["last_step_at"] = now
        state["last_accepted_gesture"] = stable_gesture
        state["step_started_at"] = None

        if state["index"] >= len(steps):
            self._reset_sequence_state(state)
            return self._execute_rule(rule, now)

        next_gesture = steps[state["index"]]["gesture"]
        self.message = f"{rule.get('name', rule['id'])}: next {next_gesture}"
        return "sequence_step"

    def _update_hold_rule(
        self,
        rule: dict[str, Any],
        stable_gesture: str,
        now: float,
    ) -> str | None:
        trigger = rule["trigger"]
        target_gesture = trigger.get("gesture")
        hold_seconds = trigger.get("hold_ms", 0) / 1000.0

        state = self.hold_state.setdefault(
            rule["id"],
            {
                "gesture": None,
                "started_at": None,
                "fired": False,
            },
        )

        if stable_gesture != target_gesture:
            state["gesture"] = None
            state["started_at"] = None
            state["fired"] = False
            return None

        if state["gesture"] != stable_gesture:
            state["gesture"] = stable_gesture
            state["started_at"] = now
            state["fired"] = False

        if state["fired"]:
            return None

        if now - state["started_at"] < hold_seconds:
            remaining = hold_seconds - (now - state["started_at"])
            self.message = (
                f"{rule.get('name', rule['id'])}: hold {target_gesture} "
                f"{remaining:.1f}s"
            )
            return None

        state["fired"] = True
        return self._execute_rule(rule, now)

    def _update_repeat_hold_rule(
        self,
        rule: dict[str, Any],
        stable_gesture: str,
        now: float,
    ) -> str | None:
        trigger = rule["trigger"]
        target_gesture = trigger.get("gesture")
        hold_seconds = trigger.get("hold_ms", 0) / 1000.0
        repeat_seconds = trigger.get("repeat_ms", 1000) / 1000.0

        state = self.hold_state.setdefault(
            f"repeat:{rule['id']}",
            {
                "gesture": None,
                "started_at": None,
                "next_action_at": None,
            },
        )

        if stable_gesture != target_gesture:
            state["gesture"] = None
            state["started_at"] = None
            state["next_action_at"] = None
            return None

        if state["gesture"] != stable_gesture:
            state["gesture"] = stable_gesture
            state["started_at"] = now
            state["next_action_at"] = now + hold_seconds
            self.message = f"{rule.get('name', rule['id'])}: hold {target_gesture}"
            return "repeat_hold_started"

        if state["next_action_at"] is None:
            state["next_action_at"] = now + hold_seconds
            return None

        if now < state["next_action_at"]:
            remaining = state["next_action_at"] - now
            self.message = f"{rule.get('name', rule['id'])}: action in {remaining:.1f}s"
            return None

        result = self._execute_rule(rule, now)
        state["next_action_at"] = now + repeat_seconds
        return result

    def _update_armed_hold_rule(
        self,
        rule: dict[str, Any],
        stable_gesture: str,
        now: float,
    ) -> str | None:
        trigger = rule["trigger"]
        arm_gesture = trigger.get("arm_gesture")
        target_gesture = trigger.get("gesture")
        arm_timeout_seconds = trigger.get("arm_timeout_ms", 8000) / 1000.0
        repeat_seconds = trigger.get("repeat_ms", 3000) / 1000.0
        first_hold_seconds = trigger.get("hold_ms", trigger.get("repeat_ms", 3000)) / 1000.0

        state = self.armed_hold_state.setdefault(
            rule["id"],
            {
                "armed_until": 0.0,
                "active_gesture": None,
                "hold_started_at": None,
                "next_action_at": None,
            },
        )

        if stable_gesture == arm_gesture:
            state["armed_until"] = now + arm_timeout_seconds
            state["active_gesture"] = None
            state["hold_started_at"] = None
            state["next_action_at"] = None
            self.message = f"{rule.get('name', rule['id'])}: armed"
            return "armed"

        if now > state["armed_until"]:
            state["active_gesture"] = None
            state["hold_started_at"] = None
            state["next_action_at"] = None
            return None

        if stable_gesture != target_gesture:
            state["active_gesture"] = None
            state["hold_started_at"] = None
            state["next_action_at"] = None
            return None

        if state["active_gesture"] != stable_gesture:
            state["active_gesture"] = stable_gesture
            state["hold_started_at"] = now
            state["next_action_at"] = now + first_hold_seconds
            self.message = f"{rule.get('name', rule['id'])}: hold {target_gesture}"
            return "armed_hold_started"

        if now < state["next_action_at"]:
            remaining = state["next_action_at"] - now
            self.message = f"{rule.get('name', rule['id'])}: action in {remaining:.1f}s"
            return None

        result = self._execute_rule(rule, now)
        state["next_action_at"] = now + repeat_seconds
        return result

    def _update_motion_rule(
        self,
        rule: dict[str, Any],
        stable_gesture: str,
        now: float,
    ) -> str | None:
        trigger = rule["trigger"]
        if stable_gesture != trigger.get("gesture"):
            return None

        return self._execute_rule(rule, now)

    def _update_value_control_rule(
        self,
        rule: dict[str, Any],
        stable_gesture: str,
        now: float,
        value: float | None,
    ) -> str | None:
        trigger = rule["trigger"]
        if stable_gesture != trigger.get("gesture"):
            return None

        if value is None:
            return None

        state = self.hold_state.setdefault(
            f"value:{rule['id']}",
            {"next_action_at": 0.0},
        )

        next_action_at = state.get("next_action_at") or 0.0
        if now < next_action_at:
            return None

        repeat_seconds = trigger.get("repeat_ms", 250) / 1000.0
        state["next_action_at"] = now + repeat_seconds

        action = dict(rule.get("action", {}))
        action["value"] = value

        return self._execute_rule(rule, now, action_override=action)

    def _reset_sequence_state(self, state: dict[str, Any]) -> None:
        state["index"] = 0
        state["started_at"] = None
        state["step_started_at"] = None
        state["last_step_at"] = None
        state["last_accepted_gesture"] = None

    def _reset_hold_inputs(self) -> None:
        for state in self.hold_state.values():
            state["gesture"] = None
            state["started_at"] = None
            state["fired"] = False
            if "next_action_at" in state:
                state["next_action_at"] = None

        for state in self.armed_hold_state.values():
            state["active_gesture"] = None
            state["hold_started_at"] = None
            state["next_action_at"] = None
