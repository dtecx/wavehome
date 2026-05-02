from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from .schema import validate_rules_config

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "default_rules.json"
USER_RULES_PATH = DEFAULT_RULES_PATH.with_name("user_rules.json")


def editable_rules_path() -> Path:
    configured_path = os.getenv("WAVEHOME_RULES_PATH")
    if configured_path:
        return Path(configured_path).expanduser()
    return USER_RULES_PATH


def ensure_editable_rules_file(path: Path | None = None) -> Path:
    rules_path = path or editable_rules_path()

    if rules_path.exists():
        return rules_path

    rules_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DEFAULT_RULES_PATH, rules_path)
    return rules_path


def load_rules(path: Path | None = None) -> dict[str, Any]:
    rules_path = path or ensure_editable_rules_file()

    with rules_path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    return validate_rules_config(config)


def save_rules(config: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    rules_path = path or ensure_editable_rules_file()
    validated = validate_rules_config(config)

    rules_path.parent.mkdir(parents=True, exist_ok=True)
    with rules_path.open("w", encoding="utf-8") as file:
        json.dump(validated, file, indent=2, ensure_ascii=False)
        file.write("\n")

    return validated


def enabled_rules(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [rule for rule in config.get("rules", []) if rule.get("enabled", True)]
