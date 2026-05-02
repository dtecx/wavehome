from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from .base import SmartHomeCommandError


TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class GoogleHomeConfig:
    """Config for a future Google Home bridge endpoint.

    Google's current Home APIs are SDK-first on Android and iOS. This adapter
    keeps waveHome's Python command layer ready by posting normalized commands
    to a bridge service that can later own OAuth, permissions, and SDK calls.
    """

    enabled: bool = False
    bridge_url: str = ""
    access_token: str | None = None
    timeout_seconds: float = 3.0

    @classmethod
    def from_env(cls) -> "GoogleHomeConfig":
        enabled = os.getenv("WAVEHOME_GOOGLE_HOME_ENABLED", "").lower() in TRUE_VALUES
        timeout = os.getenv("WAVEHOME_GOOGLE_HOME_TIMEOUT_SECONDS", "3")
        try:
            timeout_seconds = float(timeout)
        except ValueError:
            timeout_seconds = 3.0

        return cls(
            enabled=enabled,
            bridge_url=os.getenv("WAVEHOME_GOOGLE_HOME_BRIDGE_URL", "").strip(),
            access_token=os.getenv("WAVEHOME_GOOGLE_HOME_ACCESS_TOKEN") or None,
            timeout_seconds=timeout_seconds,
        )


class GoogleHomeAdapter:
    def __init__(
        self,
        config: GoogleHomeConfig | None = None,
        session: requests.Session | None = None,
    ):
        self.config = config or GoogleHomeConfig.from_env()
        self.session = session or requests.Session()

    @classmethod
    def from_env(cls) -> "GoogleHomeAdapter":
        return cls(GoogleHomeConfig.from_env())

    @property
    def available(self) -> bool:
        return self.config.enabled and bool(self.config.bridge_url)

    def set_power(self, device_id: str, on: bool) -> None:
        self._send("set_power", {"device_id": device_id, "on": on})

    def set_brightness(self, device_id: str, percent: int) -> None:
        self._send(
            "set_brightness",
            {"device_id": device_id, "percent": max(0, min(100, int(percent)))},
        )

    def set_color(self, device_id: str, rgb: tuple[int, int, int]) -> None:
        channels = [max(0, min(255, int(channel))) for channel in rgb]
        self._send("set_color", {"device_id": device_id, "rgb": channels})

    def activate_scene(self, scene_id: str) -> None:
        self._send("activate_scene", {"scene_id": scene_id})

    def _send(self, command: str, params: dict[str, Any]) -> None:
        if not self.available:
            raise SmartHomeCommandError("Google Home bridge is not configured")

        headers = {"Content-Type": "application/json"}
        if self.config.access_token:
            headers["Authorization"] = f"Bearer {self.config.access_token}"

        url = f"{self.config.bridge_url.rstrip('/')}/commands"
        payload = {
            "provider": "google_home",
            "command": command,
            "params": params,
        }

        try:
            response = self.session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise SmartHomeCommandError(str(error)) from error

