from __future__ import annotations

import json

from wavehome.workflow.loader import load_rules, save_rules


def test_load_rules_creates_editable_copy(tmp_path, monkeypatch):
    rules_path = tmp_path / "user_rules.json"
    monkeypatch.setenv("WAVEHOME_RULES_PATH", str(rules_path))

    config = load_rules()

    assert rules_path.exists()
    assert config["version"] >= 1
    assert isinstance(config["rules"], list)


def test_save_rules_writes_validated_config(tmp_path):
    rules_path = tmp_path / "rules.json"
    config = {
        "version": 2,
        "rules": [
            {
                "id": "test_toggle",
                "name": "Test toggle",
                "enabled": True,
                "trigger": {
                    "kind": "hold",
                    "gesture": "OPEN_PALM",
                    "hold_ms": 500,
                },
                "action": {
                    "kind": "virtual_lamp.toggle",
                },
            }
        ],
    }

    saved = save_rules(config, path=rules_path)

    assert saved == config
    assert json.loads(rules_path.read_text(encoding="utf-8")) == config
