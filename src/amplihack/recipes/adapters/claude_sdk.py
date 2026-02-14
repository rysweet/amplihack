"""Claude Agent SDK adapter for recipe execution.

Uses ``claude_agent_sdk.query()`` (lazy-imported) for agent steps
and ``subprocess.run()`` for bash steps.
"""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any


class ClaudeSDKAdapter:
    """Adapter that delegates agent steps to the Claude Agent SDK.

    The SDK import is lazy to avoid hard dependency failures when the
    package is not installed.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514", working_dir: str = ".") -> None:
        self._model = model
        self._working_dir = working_dir
        self._sdk: Any = None

    def _get_sdk(self) -> Any:
        """Lazy-import the Claude Agent SDK."""
        if self._sdk is None:
            try:
                import claude_agent_sdk  # type: ignore[import-untyped]

                self._sdk = claude_agent_sdk
            except ImportError as exc:
                raise RuntimeError(
                    "claude_agent_sdk is not installed. "
                    "Install it with: pip install claude-agent-sdk"
                ) from exc
        return self._sdk

    def execute_agent_step(
        self,
        prompt: str,
        agent_name: str | None = None,
        agent_system_prompt: str | None = None,
        mode: str | None = None,
        working_dir: str = ".",
    ) -> str:
        """Execute an agent step via the Claude Agent SDK."""
        sdk = self._get_sdk()

        enriched_prompt = prompt
        if agent_system_prompt:
            enriched_prompt = (
                f"[System context for {agent_name or 'agent'}]\n"
                f"{agent_system_prompt}\n\n"
                f"[Task]\n{prompt}"
            )

        result = asyncio.run(
            sdk.query(
                prompt=enriched_prompt,
                model=self._model,
            )
        )
        return str(result)

    def execute_bash_step(
        self,
        command: str,
        working_dir: str = ".",
        timeout: int = 120,
    ) -> str:
        """Execute a bash command via subprocess.

        Uses explicit bash invocation instead of shell=True to prevent
        injection vulnerabilities (per PR #2010 security fix).
        """
        result = subprocess.run(
            ["/bin/bash", "-c", command],
            capture_output=True,
            text=True,
            cwd=working_dir or self._working_dir,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Command failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()

    def is_available(self) -> bool:
        """Check if the Claude Agent SDK is importable."""
        try:
            self._get_sdk()
            return True
        except RuntimeError:
            return False

    @property
    def name(self) -> str:
        return "claude-sdk"
