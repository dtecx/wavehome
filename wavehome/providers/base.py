from __future__ import annotations

from typing import Protocol


class SmartHomeCommandError(RuntimeError):
    """Raised when a provider cannot deliver a smart-home command."""


class SmartHomeProvider(Protocol):
    @property
    def available(self) -> bool:
        """Return whether the provider has enough config to send commands."""

    def set_power(self, device_id: str, on: bool) -> None:
        """Turn a smart-home device on or off."""

    def set_brightness(self, device_id: str, percent: int) -> None:
        """Set a smart-home device brightness from 0 to 100 percent."""

    def set_color(self, device_id: str, rgb: tuple[int, int, int]) -> None:
        """Set a smart-home light color."""

    def activate_scene(self, scene_id: str) -> None:
        """Activate a smart-home scene or automation."""

