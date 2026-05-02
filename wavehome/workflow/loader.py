import json
from pathlib import Path
from typing import Any


DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "default_rules.json"


def load_rules(path: Path | None = None) -> dict[str, Any]:
    rules_path = path or DEFAULT_RULES_PATH
    with rules_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def enabled_rules(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [rule for rule in config.get("rules", []) if rule.get("enabled", True)]
