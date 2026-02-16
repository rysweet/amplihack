"""Nested session adapter for recipe execution inside Claude Code.

Enables Recipe Runner to work when already inside a Claude Code session by:
1. Unsetting CLAUDECODE environment variable
2. Using isolated temporary directories for each agent invocation
3. Cleaning up resources after execution
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class NestedSessionAdapter:
    """Adapter that allows nested Claude Code sessions.

    Solves the "cannot launch Claude Code inside Claude Code" error by:
    - Unsetting CLAUDECODE before spawning subprocess
    - Using isolated temp directories for each agent call
    - Proper cleanup of resources

    Based on the pattern from multitask skill (.claude/skills/multitask/orchestrator.py)
    """

    def __init__(
        self,
        cli: str = "claude",
        working_dir: str = ".",
        use_temp_dirs: bool = True,
    ) -> None:
        """Initialize the adapter.

        Args:
            cli: CLI command to use (claude, copilot, rustyclawd)
            working_dir: Base working directory for bash steps
            use_temp_dirs: If True, use isolated temp dirs for agent steps
        """
        self._cli = cli
        self._working_dir = working_dir
        self._use_temp_dirs = use_temp_dirs

    def execute_agent_step(
        self,
        prompt: str,
        agent_name: str | None = None,
        agent_system_prompt: str | None = None,
        mode: str | None = None,
        working_dir: str = ".",
    ) -> str:
        """Execute an agent step in a nested Claude Code session.

        Creates isolated environment with CLAUDECODE unset to allow nesting.
        Uses temporary directory if use_temp_dirs=True for full isolation.
        """
        # Prepare environment without CLAUDECODE
        env = os.environ.copy()
        if "CLAUDECODE" in env:
            del env["CLAUDECODE"]

        # Prepare working directory
        if self._use_temp_dirs:
            # Create isolated temp directory for this agent call
            temp_dir = tempfile.mkdtemp(prefix="recipe-agent-")
            actual_working_dir = temp_dir
        else:
            actual_working_dir = working_dir or self._working_dir

        try:
            # Build command
            cmd = [self._cli, "-p", prompt]

            # Execute with modified environment
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=actual_working_dir,
                env=env,  # CLAUDECODE unset here
                timeout=900,  # 15 min - agent steps need time
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"{self._cli} failed (exit {result.returncode}): {result.stderr.strip()}"
                )

            return result.stdout.strip()

        finally:
            # Cleanup temp directory if created
            if self._use_temp_dirs and Path(temp_dir).exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

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
        return f"nested-session ({self._cli})"
