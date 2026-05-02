from __future__ import annotations

from copy import deepcopy
from typing import Any


RULE_PRESETS: list[dict[str, Any]] = [
    {
        "id": "preset_wake_command_mode",
        "name": "Wake command mode",
        "description": "Hold both open palms to enter command mode.",
        "rule": {
            "id": "wake_command_mode",
            "name": "Wake command mode",
            "enabled": True,
            "trigger": {
                "kind": "hold",
                "gesture": "BOTH_OPEN_PALMS",
                "hold_ms": 1000,
            },
            "action": {
                "kind": "workflow.enter_command_mode",
                "duration_ms": 10000,
            },
            "safety": {
                "cooldown_ms": 1500,
            },
        },
    },
    {
        "id": "preset_toggle_lamp_sequence",
        "name": "Toggle lamp sequence",
        "description": "Open palm, fist, open palm, fist toggles lamp.",
        "rule": {
            "id": "toggle_lamp_sequence",
            "name": "Toggle lamp",
            "enabled": True,
            "trigger": {
                "kind": "sequence",
                "steps": [
                    {"gesture": "OPEN_PALM"},
                    {"gesture": "FIST"},
                    {"gesture": "OPEN_PALM"},
                    {"gesture": "FIST"},
                ],
                "max_total_ms": 15000,
                "max_gap_ms": 4000,
            },
            "action": {
                "kind": "virtual_lamp.toggle",
            },
            "safety": {
                "cooldown_ms": 1500,
                "command_mode": {
                    "required": True,
                },
            },
        },
    },
    {
        "id": "preset_brightness_up_repeat",
        "name": "Brightness up while holding thumb up",
        "description": "Hold thumb up to repeatedly increase brightness.",
        "rule": {
            "id": "brightness_up_repeat",
            "name": "Brightness up",
            "enabled": True,
            "trigger": {
                "kind": "repeat_hold",
                "gesture": "THUMB_UP",
                "hold_ms": 900,
                "repeat_ms": 900,
            },
            "action": {
                "kind": "virtual_lamp.brightness_step",
                "direction": 1,
                "step_percent": 10,
            },
            "safety": {
                "command_mode": {
                    "required": True,
                },
            },
        },
    },
    {
        "id": "preset_brightness_down_repeat",
        "name": "Brightness down while holding thumb down",
        "description": "Hold thumb down to repeatedly decrease brightness.",
        "rule": {
            "id": "brightness_down_repeat",
            "name": "Brightness down",
            "enabled": True,
            "trigger": {
                "kind": "repeat_hold",
                "gesture": "THUMB_DOWN",
                "hold_ms": 900,
                "repeat_ms": 900,
            },
            "action": {
                "kind": "virtual_lamp.brightness_step",
                "direction": -1,
                "step_percent": 10,
            },
            "safety": {
                "command_mode": {
                    "required": True,
                },
            },
        },
    },
    {
        "id": "preset_all_off_confirmed",
        "name": "All off with confirmation",
        "description": "Hold both fists, then confirm with thumb up.",
        "rule": {
            "id": "all_off_confirmed",
            "name": "All off",
            "enabled": True,
            "trigger": {
                "kind": "hold",
                "gesture": "BOTH_FISTS",
                "hold_ms": 1000,
            },
            "action": {
                "kind": "virtual_lamp.turn_off",
            },
            "safety": {
                "cooldown_ms": 3000,
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
    },
]


def get_rule_presets() -> list[dict[str, Any]]:
    return deepcopy(RULE_PRESETS)
