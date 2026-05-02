from __future__ import annotations

import pytest

from wavehome.providers.base import SmartHomeCommandError
from wavehome.providers.google_home import GoogleHomeAdapter, GoogleHomeConfig


class FakeResponse:
    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self):
        self.posts = []

    def post(self, url, json, headers, timeout):
        self.posts.append(
            {
                "url": url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return FakeResponse()


def test_google_home_adapter_posts_normalized_commands():
    session = FakeSession()
    adapter = GoogleHomeAdapter(
        GoogleHomeConfig(
            enabled=True,
            bridge_url="http://bridge.local/",
            access_token="secret-token",
            timeout_seconds=4.5,
        ),
        session=session,
    )

    adapter.set_brightness("kitchen-light", 140)

    assert session.posts == [
        {
            "url": "http://bridge.local/commands",
            "json": {
                "provider": "google_home",
                "command": "set_brightness",
                "params": {
                    "device_id": "kitchen-light",
                    "percent": 100,
                },
            },
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer secret-token",
            },
            "timeout": 4.5,
        }
    ]


def test_google_home_adapter_requires_bridge_config():
    adapter = GoogleHomeAdapter(GoogleHomeConfig(enabled=False, bridge_url=""))

    with pytest.raises(SmartHomeCommandError):
        adapter.set_power("lamp", True)

