"""SDKAdapter protocol definition.

Defines the interface that all recipe execution adapters must implement.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SDKAdapter(Protocol):
    """Protocol for recipe step execution adapters.

    Adapters bridge the recipe runner to an underlying execution backend
    (Claude SDK, CLI subprocess, etc.).
    """

    def execute_agent_step(
        self,
        prompt: str,
        agent_name: str | None = None,
        agent_system_prompt: str | None = None,
        mode: str | None = None,
        working_dir: str = ".",
    ) -> str:
        """Execute an agent step and return the text output."""
        ...

    def execute_bash_step(
        self,
        command: str,
        working_dir: str = ".",
        timeout: int = 120,
    ) -> str:
        """Execute a bash command and return stdout."""
        ...

    def is_available(self) -> bool:
        """Return True if this adapter's backend is available."""
        ...

    @property
    def name(self) -> str:
        """Human-readable adapter name."""
        ...
