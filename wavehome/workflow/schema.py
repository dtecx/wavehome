from __future__ import annotations

from typing import Any


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
    "workflow.enter_command_mode",
    "workflow.exit_command_mode",
    "workflow.cancel",
}


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


def _optional_positive_int(value: Any, name: str) -> None:
    if value is None:
        return
    if not isinstance(value, int) or value < 0:
        raise RuleValidationError(f"{name} must be a positive integer")


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
            _require_string(step.get("gesture"), f"{prefix}.trigger.steps[{step_index}].gesture")
            _optional_positive_int(step.get("hold_ms", 0), f"{prefix}.trigger.steps[{step_index}].hold_ms")
        _optional_positive_int(trigger.get("max_total_ms", 15000), f"{prefix}.trigger.max_total_ms")
        _optional_positive_int(trigger.get("max_gap_ms", 4000), f"{prefix}.trigger.max_gap_ms")

    elif kind == "hold":
        _require_string(trigger.get("gesture"), f"{prefix}.trigger.gesture")
        _optional_positive_int(trigger.get("hold_ms", 0), f"{prefix}.trigger.hold_ms")

    elif kind == "repeat_hold":
        _require_string(trigger.get("gesture"), f"{prefix}.trigger.gesture")
        _optional_positive_int(trigger.get("hold_ms", 0), f"{prefix}.trigger.hold_ms")
        _optional_positive_int(trigger.get("repeat_ms", 1000), f"{prefix}.trigger.repeat_ms")

    elif kind == "armed_hold":
        _require_string(trigger.get("arm_gesture"), f"{prefix}.trigger.arm_gesture")
        _require_string(trigger.get("gesture"), f"{prefix}.trigger.gesture")
        _optional_positive_int(trigger.get("arm_timeout_ms", 8000), f"{prefix}.trigger.arm_timeout_ms")
        _optional_positive_int(trigger.get("hold_ms", trigger.get("repeat_ms", 0)), f"{prefix}.trigger.hold_ms")
        _optional_positive_int(trigger.get("repeat_ms", 3000), f"{prefix}.trigger.repeat_ms")

    elif kind == "motion":
        _require_string(trigger.get("gesture"), f"{prefix}.trigger.gesture")

    elif kind == "value_control":
        _require_string(trigger.get("gesture"), f"{prefix}.trigger.gesture")
        _optional_positive_int(trigger.get("repeat_ms", 250), f"{prefix}.trigger.repeat_ms")

    action = _require_dict(rule.get("action", {}), f"{prefix}.action")
    action_kind = _require_string(action.get("kind"), f"{prefix}.action.kind")

    if action_kind not in ACTION_KINDS:
        raise RuleValidationError(
            f"{prefix}.action.kind must be one of: {', '.join(sorted(ACTION_KINDS))}"
        )

    if action_kind == "workflow.enter_command_mode":
        _optional_positive_int(action.get("duration_ms", 10000), f"{prefix}.action.duration_ms")

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
        _require_string(
            confirmation.get("gesture", "THUMB_UP"),
            f"{prefix}.safety.confirmation.gesture",
        )
        _optional_positive_int(
            confirmation.get("timeout_ms", 3000),
            f"{prefix}.safety.confirmation.timeout_ms",
        )
