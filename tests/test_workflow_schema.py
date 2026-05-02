from __future__ import annotations

import pytest

from wavehome.workflow.schema import RuleValidationError, validate_rules_config


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

