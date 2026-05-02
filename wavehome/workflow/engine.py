class WorkflowEngine:
    def __init__(self, rules: list[dict], action_adapter):
        self.rules = rules
        self.action_adapter = action_adapter
        self.sequence_state = {}
        self.cooldowns = {}
        self.pending_confirmation = None
        self.message = "Workflow engine ready"

    def update(self, stable_gesture: str | None, now: float, value: float | None = None) -> str | None:
        if stable_gesture is None:
            return None

        if self.pending_confirmation is not None:
            pending = self.pending_confirmation

            if now > pending["expires_at"]:
                self.pending_confirmation = None
                self.message = "Confirmation timed out"
                return "confirmation_timeout"

            if stable_gesture == pending["gesture"]:
                rule = pending["rule"]
                self.pending_confirmation = None
                result = self.action_adapter.execute(rule.get("action", {}))
                self._set_cooldown(rule, now)
                self.message = f"Confirmed: {rule.get('name', rule['id'])}"
                return result

            if stable_gesture == "THUMB_DOWN":
                self.pending_confirmation = None
                self.message = "Confirmation cancelled"
                return "confirmation_cancelled"


        for rule in self.rules:
            trigger = rule.get("trigger", {})
            kind = trigger.get("kind")

            if kind == "sequence":
                action_result = self._update_sequence_rule(rule, stable_gesture, now)
                if action_result:
                    return action_result

            if kind == "hold":
                action_result = self._update_hold_rule(rule, stable_gesture, now)
                if action_result:
                    return action_result

        return None

    def _on_cooldown(self, rule: dict, now: float) -> bool:
        until = self.cooldowns.get(rule["id"], 0.0)
        return now < until

    def _set_cooldown(self, rule: dict, now: float) -> None:
        cooldown_ms = rule.get("safety", {}).get("cooldown_ms", 0)
        if cooldown_ms > 0:
            self.cooldowns[rule["id"]] = now + cooldown_ms / 1000.0

    def _execute_rule(self, rule: dict, now: float) -> str | None:
        if self._on_cooldown(rule, now):
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

        result = self.action_adapter.execute(rule.get("action", {}))
        self._set_cooldown(rule, now)
        self.message = f"Executed: {rule.get('name', rule['id'])}"
        return result

    def _update_sequence_rule(self, rule: dict, stable_gesture: str, now: float) -> str | None:
        state = self.sequence_state.setdefault(
            rule["id"],
            {
                "index": 0,
                "started_at": None,
                "last_gesture": None,
            },
        )

        trigger = rule["trigger"]
        steps = trigger.get("steps", [])
        if not steps:
            return None

        max_total = trigger.get("max_total_ms", 15000) / 1000.0

        if state["started_at"] is not None and now - state["started_at"] > max_total:
            state["index"] = 0
            state["started_at"] = None
            state["last_gesture"] = None

        if stable_gesture == state["last_gesture"]:
            return None

        expected = steps[state["index"]]["gesture"]

        if stable_gesture != expected:
            if state["index"] > 0:
                state["index"] = 0
                state["started_at"] = None
                state["last_gesture"] = stable_gesture
                self.message = f"Sequence cancelled: {rule.get('name', rule['id'])}"
            return None

        if state["index"] == 0:
            state["started_at"] = now

        state["index"] += 1
        state["last_gesture"] = stable_gesture

        if state["index"] >= len(steps):
            state["index"] = 0
            state["started_at"] = None
            state["last_gesture"] = None
            return self._execute_rule(rule, now)

        next_gesture = steps[state["index"]]["gesture"]
        self.message = f"{rule.get('name', rule['id'])}: next {next_gesture}"
        return "sequence_step"

    def _update_hold_rule(self, rule: dict, stable_gesture: str, now: float) -> str | None:
        trigger = rule["trigger"]
        if stable_gesture != trigger.get("gesture"):
            return None
        return self._execute_rule(rule, now)
