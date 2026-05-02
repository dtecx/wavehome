from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema import validate_rules_config


DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "default_rules.json"


def load_rules(path: Path | None = None) -> dict[str, Any]:
    rules_path = path or DEFAULT_RULES_PATH

    with rules_path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    return validate_rules_config(config)


def save_rules(config: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    rules_path = path or DEFAULT_RULES_PATH
    validated = validate_rules_config(config)

    rules_path.parent.mkdir(parents=True, exist_ok=True)

    with rules_path.open("w", encoding="utf-8") as file:
        json.dump(validated, file, indent=2, ensure_ascii=False)
        file.write("\n")

    return validated


def enabled_rules(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [rule for rule in config.get("rules", []) if rule.get("enabled", True)]
