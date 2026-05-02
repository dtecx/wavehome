from __future__ import annotations

from typing import Any

from .schema import ACTION_KINDS, TRIGGER_KINDS


TRIGGER_BLOCKS: dict[str, dict[str, Any]] = {
    "sequence": {
        "label": "Gesture sequence",
        "description": "Run an action after gestures are shown in order.",
        "fields": ["steps", "max_total_ms", "max_gap_ms"],
    },
    "hold": {
        "label": "Hold gesture",
        "description": "Run an action after one gesture is held long enough.",
        "fields": ["gesture", "hold_ms"],
    },
    "repeat_hold": {
        "label": "Repeat while holding",
        "description": "Run an action after first hold, then repeat while still held.",
        "fields": ["gesture", "hold_ms", "repeat_ms"],
    },
    "armed_hold": {
        "label": "Arm then hold",
        "description": "First gesture arms control, second gesture repeats action.",
        "fields": ["arm_gesture", "gesture", "arm_timeout_ms", "hold_ms", "repeat_ms"],
    },
    "motion": {
        "label": "Motion gesture",
        "description": "Run an action from movement like swipe up/down/left/right.",
        "fields": ["gesture"],
    },
    "value_control": {
        "label": "Continuous value control",
        "description": "Send a numeric value from a gesture, for example peace rotation.",
        "fields": ["gesture", "repeat_ms"],
    },
}


ACTION_BLOCKS: dict[str, dict[str, Any]] = {
    "workflow.enter_command_mode": {
        "label": "Enter command mode",
        "description": "Allow protected rules for a limited time.",
        "fields": ["duration_ms"],
    },
    "workflow.exit_command_mode": {
        "label": "Exit command mode",
        "description": "Immediately leave command mode.",
        "fields": [],
    },
    "workflow.cancel": {
        "label": "Cancel workflow",
        "description": "Clear pending confirmations and active sequence state.",
        "fields": [],
    },
    "virtual_lamp.toggle": {
        "label": "Toggle lamp",
        "description": "Turn lamp on if off, or off if on.",
        "fields": [],
    },
    "virtual_lamp.turn_on": {
        "label": "Turn lamp on",
        "description": "Force lamp on.",
        "fields": [],
    },
    "virtual_lamp.turn_off": {
        "label": "Turn lamp off",
        "description": "Force lamp off and disable party mode.",
        "fields": [],
    },
    "virtual_lamp.toggle_party": {
        "label": "Toggle party mode",
        "description": "Enable or disable color cycling/blinking.",
        "fields": [],
    },
    "virtual_lamp.brightness_step": {
        "label": "Brightness step",
        "description": "Increase or decrease brightness by a fixed amount.",
        "fields": ["direction", "step_percent"],
    },
    "virtual_lamp.brightness_set": {
        "label": "Set brightness",
        "description": "Set brightness from a fixed percent or continuous value.",
        "fields": ["percent", "value"],
    },
    "virtual_lamp.color_set": {
        "label": "Set color",
        "description": "Set RGB color or derive greyscale from continuous value.",
        "fields": ["rgb", "value"],
    },
}


SAFETY_BLOCKS: dict[str, dict[str, Any]] = {
    "cooldown": {
        "label": "Cooldown",
        "description": "Prevent repeated accidental triggers.",
        "fields": ["cooldown_ms"],
    },
    "command_mode": {
        "label": "Require command mode",
        "description": "Rule only works after wake gesture.",
        "fields": ["required"],
    },
    "confirmation": {
        "label": "Confirmation",
        "description": "Require a second gesture before executing.",
        "fields": ["required", "gesture", "timeout_ms"],
    },
}


def workflow_catalog() -> dict[str, Any]:
    return {
        "trigger_kinds": sorted(TRIGGER_KINDS),
        "action_kinds": sorted(ACTION_KINDS),
        "trigger_blocks": TRIGGER_BLOCKS,
        "action_blocks": ACTION_BLOCKS,
        "safety_blocks": SAFETY_BLOCKS,
    }
