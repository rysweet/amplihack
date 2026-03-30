"""Minimal hook strategy base class for compatibility tests."""

from __future__ import annotations

from abc import ABC, abstractmethod


class HookStrategy(ABC):
    @abstractmethod
    def inject_context(self, context: str) -> dict[str, object]:
        """Inject launcher-specific context."""

    @abstractmethod
    def power_steer(self, prompt: str, session_id: str | None = None) -> bool:
        """Send follow-up guidance to the launcher."""

    def get_launcher_name(self) -> str:
        name = self.__class__.__name__
        if name.endswith("Strategy"):
            name = name[: -len("Strategy")]
        return name.lower()
