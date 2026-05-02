from __future__ import annotations

from typing import Any

from wavehome.providers.base import SmartHomeCommandError, SmartHomeProvider


class SmartHomeActions:
    def __init__(self, provider: SmartHomeProvider):
        self.provider = provider

    def execute(self, action: dict[str, Any]) -> str | None:
        kind = action.get("kind")

        if not str(kind).startswith("smart_home."):
            return None

        if not self.provider.available:
            return "smart_home.unavailable"

        try:
            if kind == "smart_home.set_power":
                self.provider.set_power(
                    self._require_id(action, "device_id"),
                    self._bool_value(action.get("on", True)),
                )
                return kind

            if kind == "smart_home.set_brightness":
                self.provider.set_brightness(
                    self._require_id(action, "device_id"),
                    self._percent(action.get("percent", action.get("value", 100))),
                )
                return kind

            if kind == "smart_home.set_color":
                self.provider.set_color(
                    self._require_id(action, "device_id"),
                    self._rgb(action.get("rgb", [255, 255, 255])),
                )
                return kind

            if kind == "smart_home.activate_scene":
                self.provider.activate_scene(self._require_id(action, "scene_id"))
                return kind
        except (SmartHomeCommandError, ValueError):
            return "smart_home.error"

        return None

    def _require_id(self, action: dict[str, Any], field: str) -> str:
        value = action.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required")
        return value.strip()

    def _bool_value(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).lower() in {"1", "true", "yes", "on"}

    def _percent(self, value: Any) -> int:
        return max(0, min(100, int(float(value))))

    def _rgb(self, value: Any) -> tuple[int, int, int]:
        if not isinstance(value, (list, tuple)) or len(value) != 3:
            raise ValueError("rgb must have three channels")
        return tuple(max(0, min(255, int(channel))) for channel in value)

