"""Copilot SDK adapter for recipe execution.

Agent step execution is not yet implemented for the Copilot backend.
Bash steps use direct subprocess execution.
"""

from __future__ import annotations

import subprocess


class CopilotSDKAdapter:
    """Adapter for the Copilot SDK backend.

    Agent steps raise ``NotImplementedError`` as the Copilot SDK integration
    is pending. Bash steps work via subprocess.
    """

    def __init__(self, working_dir: str = ".") -> None:
        self._working_dir = working_dir

    def execute_agent_step(
        self,
        prompt: str,
        agent_name: str | None = None,
        agent_system_prompt: str | None = None,
        mode: str | None = None,
        working_dir: str = ".",
    ) -> str:
        """Not implemented for Copilot SDK.

        Raises:
            NotImplementedError: Always. Copilot SDK agent execution is pending.
        """
        raise NotImplementedError(
            "Copilot SDK agent execution is not yet implemented. "
            "Use ClaudeSDKAdapter or CLISubprocessAdapter instead."
        )

    def execute_bash_step(
        self,
        command: str,
        working_dir: str = ".",
        timeout: int = 120,
    ) -> str:
        """Execute a bash command via subprocess."""
        result = subprocess.run(
            command,
            shell=True,
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
        """Copilot SDK is not yet available."""
        return False

    @property
    def name(self) -> str:
        return "copilot-sdk"
