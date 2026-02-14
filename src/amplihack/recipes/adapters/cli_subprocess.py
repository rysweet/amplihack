"""CLI subprocess adapter for recipe execution.

Falls back to shelling out to a CLI tool (claude, copilot, rustyclawd) for
agent steps, and uses subprocess for bash steps.
"""

from __future__ import annotations

import shutil
import subprocess


class CLISubprocessAdapter:
    """Adapter that uses CLI subprocess calls as the execution backend.

    Useful as a fallback when no SDK is available. Shells out to the
    specified CLI tool for agent steps.
    """

    def __init__(self, cli: str = "claude", working_dir: str = ".") -> None:
        self._cli = cli
        self._working_dir = working_dir

    def execute_agent_step(
        self,
        prompt: str,
        agent_name: str | None = None,
        agent_system_prompt: str | None = None,
        mode: str | None = None,
        working_dir: str = ".",
    ) -> str:
        """Execute an agent step by shelling out to the CLI tool with ``-p``."""
        cmd = [self._cli, "-p", prompt]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=working_dir or self._working_dir,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"{self._cli} failed (exit {result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()

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
        """Check if the CLI tool is on the PATH."""
        return shutil.which(self._cli) is not None

    @property
    def name(self) -> str:
        return f"cli-subprocess ({self._cli})"
