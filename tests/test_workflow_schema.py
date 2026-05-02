from __future__ import annotations

import pytest

from wavehome.workflow.schema import (
    RuleValidationError,
    collect_rule_diagnostics,
    validate_rules_config,
    validate_rules_with_diagnostics,
)


def test_schema_accepts_smart_home_power_action():
    config = {
        "version": 2,
        "rules": [
            {
                "id": "kitchen_on",
                "name": "Kitchen on",
                "enabled": True,
                "trigger": {
                    "kind": "hold",
                    "gesture": "OPEN_PALM",
                    "hold_ms": 500,
                },
                "action": {
                    "kind": "smart_home.set_power",
                    "device_id": "kitchen-light",
                    "on": True,
                },
                "safety": {},
            }
        ],
    }

    assert validate_rules_config(config) == config


def test_schema_rejects_invalid_smart_home_color():
    config = {
        "version": 2,
        "rules": [
            {
                "id": "bad_color",
                "name": "Bad color",
                "enabled": True,
                "trigger": {
                    "kind": "hold",
                    "gesture": "PEACE",
                    "hold_ms": 500,
                },
                "action": {
                    "kind": "smart_home.set_color",
                    "device_id": "kitchen-light",
                    "rgb": [260, 0, 0],
                },
                "safety": {},
            }
        ],
    }

    with pytest.raises(RuleValidationError):
        validate_rules_config(config)


def test_schema_rejects_unknown_gesture():
    config = {
        "version": 2,
        "rules": [
            {
                "id": "bad_gesture",
                "name": "Bad gesture",
                "enabled": True,
                "trigger": {
                    "kind": "hold",
                    "gesture": "WIGGLE",
                    "hold_ms": 500,
                },
                "action": {
                    "kind": "virtual_lamp.toggle",
                },
                "safety": {},
            }
        ],
    }

    with pytest.raises(RuleValidationError):
        validate_rules_config(config)


def test_validation_diagnostics_warn_about_unsafe_rules():
    config = {
        "version": 2,
        "rules": [
            {
                "id": "quick_all_off",
                "name": "Quick all off",
                "enabled": True,
                "trigger": {
                    "kind": "hold",
                    "gesture": "BOTH_FISTS",
                    "hold_ms": 100,
                },
                "action": {
                    "kind": "virtual_lamp.turn_off",
                },
                "safety": {},
            }
        ],
    }

    diagnostics = collect_rule_diagnostics(config)
    codes = {diagnostic["code"] for diagnostic in diagnostics}

    assert "hold_time_too_short" in codes
    assert "missing_cooldown" in codes
    assert "dangerous_without_command_mode" in codes
    assert "dangerous_without_confirmation" in codes


def test_validation_payload_includes_diagnostics():
    config = {
        "version": 2,
        "rules": [
            {
                "id": "ok",
                "name": "Ok",
                "enabled": True,
                "trigger": {
                    "kind": "hold",
                    "gesture": "OPEN_PALM",
                    "hold_ms": 800,
                },
                "action": {
                    "kind": "workflow.enter_command_mode",
                    "duration_ms": 8000,
                },
                "safety": {
                    "cooldown_ms": 1000,
                },
            }
        ],
    }

    result = validate_rules_with_diagnostics(config)

    assert result["ok"] is True
    assert result["config"] == config
    assert result["diagnostics"] == []


def test_confirmation_diagnostic_warns_about_trigger_conflict():
    config = {
        "version": 2,
        "rules": [
            {
                "id": "brightness_up",
                "name": "Brightness up",
                "enabled": True,
                "trigger": {
                    "kind": "hold",
                    "gesture": "THUMB_UP",
                    "hold_ms": 800,
                },
                "action": {
                    "kind": "virtual_lamp.brightness_step",
                    "direction": 1,
                    "step_percent": 10,
                },
                "safety": {
                    "cooldown_ms": 1000,
                },
            },
            {
                "id": "all_off",
                "name": "All off",
                "enabled": True,
                "trigger": {
                    "kind": "hold",
                    "gesture": "BOTH_FISTS",
                    "hold_ms": 1800,
                },
                "action": {
                    "kind": "virtual_lamp.turn_off",
                },
                "safety": {
                    "cooldown_ms": 5000,
                    "command_mode": {
                        "required": True,
                    },
                    "confirmation": {
                        "required": True,
                        "gesture": "THUMB_UP",
                        "timeout_ms": 4000,
                    },
                },
            },
        ],
    }

    diagnostics = collect_rule_diagnostics(config)

    assert any(
        diagnostic["code"] == "confirmation_gesture_conflict"
        and diagnostic["rule_id"] == "all_off"
        for diagnostic in diagnostics
    )
