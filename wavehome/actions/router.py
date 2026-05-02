from __future__ import annotations

from typing import Any


class CompositeActionAdapter:
    def __init__(self, adapters: list[Any]):
        self.adapters = adapters

    def execute(self, action: dict[str, Any]) -> str | None:
        for adapter in self.adapters:
            result = adapter.execute(action)
            if result is not None:
                return result
        return None

