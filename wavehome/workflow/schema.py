from __future__ import annotations

from typing import Any

from wavehome.gesture_catalog import GESTURE_CATALOG


TRIGGER_KINDS = {
    "sequence",
    "hold",
    "armed_hold",
    "repeat_hold",
    "motion",
    "value_control",
}

ACTION_KINDS = {
    "virtual_lamp.toggle",
    "virtual_lamp.turn_on",
    "virtual_lamp.turn_off",
    "virtual_lamp.toggle_party",
    "virtual_lamp.brightness_step",
    "virtual_lamp.brightness_set",
    "virtual_lamp.color_set",
    "smart_home.set_power",
    "smart_home.set_brightness",
    "smart_home.set_color",
    "smart_home.activate_scene",
    "workflow.enter_command_mode",
    "workflow.exit_command_mode",
    "workflow.cancel",
}

DANGEROUS_ACTION_KINDS = {
    "smart_home.activate_scene",
    "virtual_lamp.turn_off",
}

MIN_INTENTIONAL_HOLD_MS = 500
MIN_SEQUENCE_STEP_HOLD_MS = 250
MIN_SEQUENCE_TOTAL_MS = 1500
MIN_SEQUENCE_GAP_MS = 500


class RuleValidationError(ValueError):
    pass


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuleValidationError(f"{name} must be an object")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise RuleValidationError(f"{name} must be a list")
    return value


def _require_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleValidationError(f"{name} must be a non-empty string")
    return value


def _require_gesture(value: Any, name: str) -> str:
    gesture = _require_string(value, name)
    if gesture not in GESTURE_CATALOG:
        raise RuleValidationError(f"{name} must be a known gesture")
    return gesture


def _optional_positive_int(value: Any, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, int) or value < 0:
        raise RuleValidationError(f"{name} must be a positive integer")


def _optional_percent(value: Any, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, int) or value < 0 or value > 100:
        raise RuleValidationError(f"{name} must be an integer from 0 to 100")


def _optional_rgb(value: Any, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, list) or len(value) != 3:
        raise RuleValidationError(f"{name} must be a three-channel RGB list")
    for channel_index, channel in enumerate(value):
        if not isinstance(channel, int) or channel < 0 or channel > 255:
            raise RuleValidationError(
                f"{name}[{channel_index}] must be an integer from 0 to 255"
            )


def validate_rules_config(config: dict[str, Any]) -> dict[str, Any]:
    config = _require_dict(config, "rules config")

    version = config.get("version", 1)
    if not isinstance(version, int) or version < 1:
        raise RuleValidationError("version must be a positive integer")

    rules = _require_list(config.get("rules", []), "rules")
    seen_ids: set[str] = set()

    for index, rule in enumerate(rules):
        validate_rule(rule, index=index)

        rule_id = rule["id"]
        if rule_id in seen_ids:
            raise RuleValidationError(f"duplicate rule id: {rule_id}")
        seen_ids.add(rule_id)

    return config


def validate_rules_with_diagnostics(config: dict[str, Any]) -> dict[str, Any]:
    validated = validate_rules_config(config)
    return {
        "ok": True,
        "config": validated,
        "diagnostics": collect_rule_diagnostics(validated),
    }


def collect_rule_diagnostics(config: dict[str, Any]) -> list[dict[str, Any]]:
    config = validate_rules_config(config)
    diagnostics: list[dict[str, Any]] = []

    for rule in config.get("rules", []):
        if not rule.get("enabled", True):
            continue

        diagnostics.extend(_rule_timing_diagnostics(rule))
        diagnostics.extend(_rule_safety_diagnostics(rule))

    diagnostics.extend(_confirmation_conflict_diagnostics(config.get("rules", [])))
    return diagnostics


def validate_rule(rule: Any, index: int | None = None) -> None:
    prefix = f"rules[{index}]" if index is not None else "rule"

    rule = _require_dict(rule, prefix)
    _require_string(rule.get("id"), f"{prefix}.id")
    _require_string(rule.get("name", rule.get("id")), f"{prefix}.name")

    if not isinstance(rule.get("enabled", True), bool):
        raise RuleValidationError(f"{prefix}.enabled must be true or false")

    trigger = _require_dict(rule.get("trigger"), f"{prefix}.trigger")
    kind = _require_string(trigger.get("kind"), f"{prefix}.trigger.kind")

    if kind not in TRIGGER_KINDS:
        raise RuleValidationError(
            f"{prefix}.trigger.kind must be one of: {', '.join(sorted(TRIGGER_KINDS))}"
        )

    if kind == "sequence":
        steps = _require_list(trigger.get("steps"), f"{prefix}.trigger.steps")
        if not steps:
            raise RuleValidationError(f"{prefix}.trigger.steps cannot be empty")
        for step_index, step in enumerate(steps):
            step = _require_dict(step, f"{prefix}.trigger.steps[{step_index}]")
            _require_gesture(step.get("gesture"), f"{prefix}.trigger.steps[{step_index}].gesture")
            _optional_positive_int(step.get("hold_ms", 0), f"{prefix}.trigger.steps[{step_index}].hold_ms")
        _optional_positive_int(trigger.get("max_total_ms", 15000), f"{prefix}.trigger.max_total_ms")
        _optional_positive_int(trigger.get("max_gap_ms", 4000), f"{prefix}.trigger.max_gap_ms")

    elif kind == "hold":
        _require_gesture(trigger.get("gesture"), f"{prefix}.trigger.gesture")
        _optional_positive_int(trigger.get("hold_ms", 0), f"{prefix}.trigger.hold_ms")

    elif kind == "repeat_hold":
        _require_gesture(trigger.get("gesture"), f"{prefix}.trigger.gesture")
        _optional_positive_int(trigger.get("hold_ms", 0), f"{prefix}.trigger.hold_ms")
        _optional_positive_int(trigger.get("repeat_ms", 1000), f"{prefix}.trigger.repeat_ms")

    elif kind == "armed_hold":
        _require_gesture(trigger.get("arm_gesture"), f"{prefix}.trigger.arm_gesture")
        _require_gesture(trigger.get("gesture"), f"{prefix}.trigger.gesture")
        _optional_positive_int(trigger.get("arm_timeout_ms", 8000), f"{prefix}.trigger.arm_timeout_ms")
        _optional_positive_int(trigger.get("hold_ms", trigger.get("repeat_ms", 0)), f"{prefix}.trigger.hold_ms")
        _optional_positive_int(trigger.get("repeat_ms", 3000), f"{prefix}.trigger.repeat_ms")

    elif kind == "motion":
        _require_gesture(trigger.get("gesture"), f"{prefix}.trigger.gesture")

    elif kind == "value_control":
        _require_gesture(trigger.get("gesture"), f"{prefix}.trigger.gesture")
        _optional_positive_int(trigger.get("repeat_ms", 250), f"{prefix}.trigger.repeat_ms")

    action = _require_dict(rule.get("action", {}), f"{prefix}.action")
    action_kind = _require_string(action.get("kind"), f"{prefix}.action.kind")

    if action_kind not in ACTION_KINDS:
        raise RuleValidationError(
            f"{prefix}.action.kind must be one of: {', '.join(sorted(ACTION_KINDS))}"
        )

    if action_kind == "workflow.enter_command_mode":
        _optional_positive_int(action.get("duration_ms", 10000), f"{prefix}.action.duration_ms")

    elif action_kind == "smart_home.set_power":
        _require_string(action.get("device_id"), f"{prefix}.action.device_id")
        if not isinstance(action.get("on", True), bool):
            raise RuleValidationError(f"{prefix}.action.on must be true or false")

    elif action_kind == "smart_home.set_brightness":
        _require_string(action.get("device_id"), f"{prefix}.action.device_id")
        _optional_percent(action.get("percent"), f"{prefix}.action.percent")

    elif action_kind == "smart_home.set_color":
        _require_string(action.get("device_id"), f"{prefix}.action.device_id")
        _optional_rgb(action.get("rgb"), f"{prefix}.action.rgb")

    elif action_kind == "smart_home.activate_scene":
        _require_string(action.get("scene_id"), f"{prefix}.action.scene_id")

    safety = _require_dict(rule.get("safety", {}), f"{prefix}.safety")
    _optional_positive_int(safety.get("cooldown_ms", 0), f"{prefix}.safety.cooldown_ms")

    command_mode = safety.get("command_mode", {"required": False})
    command_mode = _require_dict(command_mode, f"{prefix}.safety.command_mode")
    if not isinstance(command_mode.get("required", False), bool):
        raise RuleValidationError(f"{prefix}.safety.command_mode.required must be true or false")

    confirmation = _require_dict(
        safety.get("confirmation", {"required": False}),
        f"{prefix}.safety.confirmation",
    )

    if not isinstance(confirmation.get("required", False), bool):
        raise RuleValidationError(f"{prefix}.safety.confirmation.required must be true or false")

    if confirmation.get("required", False):
        _require_gesture(
            confirmation.get("gesture", "THUMB_UP"),
            f"{prefix}.safety.confirmation.gesture",
        )
        _optional_positive_int(
            confirmation.get("timeout_ms", 3000),
            f"{prefix}.safety.confirmation.timeout_ms",
        )


def _diagnostic(
    rule: dict[str, Any],
    code: str,
    message: str,
    field: str,
    level: str = "warning",
) -> dict[str, Any]:
    return {
        "level": level,
        "code": code,
        "rule_id": rule.get("id"),
        "field": field,
        "message": message,
    }


def _rule_timing_diagnostics(rule: dict[str, Any]) -> list[dict[str, Any]]:
    trigger = rule.get("trigger", {})
    kind = trigger.get("kind")
    diagnostics: list[dict[str, Any]] = []

    if kind == "sequence":
        max_total_ms = trigger.get("max_total_ms", 15000)
        max_gap_ms = trigger.get("max_gap_ms", 4000)

        if max_total_ms < MIN_SEQUENCE_TOTAL_MS:
            diagnostics.append(
                _diagnostic(
                    rule,
                    "sequence_timeout_too_short",
                    "Sequence timeout is short enough that normal human gestures may miss it.",
                    "trigger.max_total_ms",
                )
            )

        if max_gap_ms < MIN_SEQUENCE_GAP_MS:
            diagnostics.append(
                _diagnostic(
                    rule,
                    "sequence_gap_too_short",
                    "Sequence gap is short enough that normal hand transitions may cancel the rule.",
                    "trigger.max_gap_ms",
                )
            )

        for index, step in enumerate(trigger.get("steps", [])):
            hold_ms = step.get("hold_ms", 0)
            if 0 < hold_ms < MIN_SEQUENCE_STEP_HOLD_MS:
                diagnostics.append(
                    _diagnostic(
                        rule,
                        "hold_time_too_short",
                        "Step hold time is below the recommended intentional gesture threshold.",
                        f"trigger.steps[{index}].hold_ms",
                    )
                )

    elif kind in {"hold", "repeat_hold"}:
        hold_ms = trigger.get("hold_ms", 0)
        if hold_ms < MIN_INTENTIONAL_HOLD_MS:
            diagnostics.append(
                _diagnostic(
                    rule,
                    "hold_time_too_short",
                    "Hold time is below the recommended intentional gesture threshold.",
                    "trigger.hold_ms",
                )
            )

    elif kind == "armed_hold":
        hold_ms = trigger.get("hold_ms", trigger.get("repeat_ms", 3000))
        if hold_ms < MIN_INTENTIONAL_HOLD_MS:
            diagnostics.append(
                _diagnostic(
                    rule,
                    "hold_time_too_short",
                    "Armed hold time is below the recommended intentional gesture threshold.",
                    "trigger.hold_ms",
                )
            )

    return diagnostics


def _rule_safety_diagnostics(rule: dict[str, Any]) -> list[dict[str, Any]]:
    trigger = rule.get("trigger", {})
    action = rule.get("action", {})
    safety = rule.get("safety", {})
    diagnostics: list[dict[str, Any]] = []

    cooldown_ms = safety.get("cooldown_ms", 0)
    if trigger.get("kind") not in {"armed_hold", "repeat_hold", "value_control"} and cooldown_ms <= 0:
        diagnostics.append(
            _diagnostic(
                rule,
                "missing_cooldown",
                "Rule has no cooldown to prevent repeated accidental triggers.",
                "safety.cooldown_ms",
            )
        )

    if _is_dangerous_action(action):
        command_mode = safety.get("command_mode", {})
        confirmation = safety.get("confirmation", {})

        if not command_mode.get("required", False):
            diagnostics.append(
                _diagnostic(
                    rule,
                    "dangerous_without_command_mode",
                    "Dangerous actions should require command mode.",
                    "safety.command_mode.required",
                )
            )

        if not confirmation.get("required", False):
            diagnostics.append(
                _diagnostic(
                    rule,
                    "dangerous_without_confirmation",
                    "Dangerous actions should require a confirmation gesture.",
                    "safety.confirmation.required",
                )
            )

    return diagnostics


def _is_dangerous_action(action: dict[str, Any]) -> bool:
    kind = action.get("kind")
    if kind in DANGEROUS_ACTION_KINDS:
        return True
    if kind == "smart_home.set_power" and action.get("on") is False:
        return True
    return False


def _trigger_gestures(rule: dict[str, Any]) -> set[str]:
    trigger = rule.get("trigger", {})
    kind = trigger.get("kind")

    if kind == "sequence":
        return {
            step["gesture"]
            for step in trigger.get("steps", [])
            if isinstance(step, dict) and step.get("gesture")
        }

    if kind == "armed_hold":
        return {
            gesture
            for gesture in (trigger.get("arm_gesture"), trigger.get("gesture"))
            if gesture
        }

    gesture = trigger.get("gesture")
    return {gesture} if gesture else set()


def _confirmation_conflict_diagnostics(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enabled_rules = [rule for rule in rules if rule.get("enabled", True)]
    trigger_uses = [
        (rule, gesture)
        for rule in enabled_rules
        for gesture in _trigger_gestures(rule)
    ]

    diagnostics: list[dict[str, Any]] = []
    for rule in enabled_rules:
        confirmation = rule.get("safety", {}).get("confirmation", {})
        if not confirmation.get("required", False):
            continue

        confirm_gesture = confirmation.get("gesture", "THUMB_UP")
        conflicts = [
            other_rule
            for other_rule, gesture in trigger_uses
            if other_rule is not rule and gesture == confirm_gesture
        ]

        if conflicts:
            conflict_names = ", ".join(
                conflict.get("name", conflict.get("id", "unnamed rule"))
                for conflict in conflicts[:3]
            )
            diagnostics.append(
                _diagnostic(
                    rule,
                    "confirmation_gesture_conflict",
                    f"Confirmation gesture is also used by: {conflict_names}.",
                    "safety.confirmation.gesture",
                )
            )

    return diagnostics
