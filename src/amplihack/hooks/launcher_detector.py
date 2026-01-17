"""Launcher Detection for Adaptive Hooks.

Philosophy:
- Zero-BS: No stubs, everything works
- Fail-safe defaults: Unknown launchers handled gracefully
- Fast: < 100ms overhead
- Standard library only: No external dependencies

This module detects which AI launcher invoked amplihack and writes
context information for hooks to consume.
"""

import json
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class LauncherInfo:
    """Information about the detected launcher."""

    launcher_type: str  # "claude", "copilot", "codex", "unknown"
    command: str  # Original command that launched amplihack
    detected_at: str  # ISO timestamp
    environment: Dict[str, str]  # Relevant env vars

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LauncherInfo":
        """Create from dictionary."""
        return cls(**data)


class LauncherDetector:
    """Detect and track AI launcher context."""

    CONTEXT_FILE = Path(".claude/runtime/launcher_context.json")
    STALE_THRESHOLD_SECONDS = 300  # 5 minutes

    # Environment variables that indicate launcher type
    LAUNCHER_MARKERS = {
        "claude": ["CLAUDE_CODE_SESSION", "CLAUDE_SESSION_ID", "ANTHROPIC_API_KEY"],
        "copilot": ["GITHUB_COPILOT_TOKEN", "GITHUB_TOKEN", "COPILOT_SESSION"],
        "codex": ["OPENAI_API_KEY", "CODEX_SESSION"],
    }

    @classmethod
    def detect(cls) -> LauncherInfo:
        """Detect the launcher type and gather context.

        Returns:
            LauncherInfo with detected launcher type and context

        Detection logic:
        1. Check environment variables for known markers
        2. Examine command line for launcher-specific patterns
        3. Default to "unknown" if no markers found
        """
        launcher_type = cls._detect_launcher_type()
        command = cls._get_command()
        environment = cls._gather_environment()
        detected_at = datetime.now().isoformat()

        return LauncherInfo(
            launcher_type=launcher_type,
            command=command,
            detected_at=detected_at,
            environment=environment
        )

    @classmethod
    def write_context(
        cls,
        launcher_type: str,
        command: str,
        **kwargs
    ) -> Path:
        """Write launcher context to file.

        Args:
            launcher_type: Type of launcher ("claude", "copilot", etc.)
            command: Command that launched amplihack
            **kwargs: Additional context to store

        Returns:
            Path to written context file

        Raises:
            OSError: If file write fails after retries
        """
        context = LauncherInfo(
            launcher_type=launcher_type,
            command=command,
            detected_at=datetime.now().isoformat(),
            environment=kwargs
        )

        # Ensure directory exists
        cls.CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Write with retry for cloud sync resilience
        cls._write_with_retry(cls.CONTEXT_FILE, context.to_dict())

        return cls.CONTEXT_FILE

    @classmethod
    def read_context(cls) -> Optional[LauncherInfo]:
        """Read launcher context from file.

        Returns:
            LauncherInfo if file exists and valid, None otherwise
        """
        if not cls.CONTEXT_FILE.exists():
            return None

        try:
            data = json.loads(cls.CONTEXT_FILE.read_text())
            return LauncherInfo.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            # Invalid context file - treat as missing
            return None

    @classmethod
    def is_stale(cls, context: Optional[LauncherInfo] = None) -> bool:
        """Check if launcher context is stale (> 5 minutes old).

        Args:
            context: LauncherInfo to check, or None to read from file

        Returns:
            True if context is stale or missing, False otherwise
        """
        if context is None:
            context = cls.read_context()

        if context is None:
            return True

        try:
            detected_at = datetime.fromisoformat(context.detected_at)
            age = datetime.now() - detected_at
            return age > timedelta(seconds=cls.STALE_THRESHOLD_SECONDS)
        except (ValueError, TypeError):
            # Invalid timestamp - treat as stale
            return True

    @classmethod
    def _detect_launcher_type(cls) -> str:
        """Detect launcher type from environment.

        Returns:
            Launcher type string ("claude", "copilot", "codex", "unknown")
        """
        env = os.environ

        # Check each launcher's markers
        for launcher, markers in cls.LAUNCHER_MARKERS.items():
            if any(marker in env for marker in markers):
                return launcher

        # Check parent process name (fallback heuristic)
        parent_cmd = cls._get_parent_process_name()
        if parent_cmd:
            parent_lower = parent_cmd.lower()
            if "claude" in parent_lower:
                return "claude"
            elif "copilot" in parent_lower or "github" in parent_lower:
                return "copilot"
            elif "codex" in parent_lower or "openai" in parent_lower:
                return "codex"

        return "unknown"

    @classmethod
    def _get_command(cls) -> str:
        """Get the command line that launched this process.

        Returns:
            Command string
        """
        return " ".join(sys.argv)

    @classmethod
    def _gather_environment(cls) -> Dict[str, str]:
        """Gather relevant environment variables.

        Returns:
            Dictionary of environment variables
        """
        env = {}

        # Collect all launcher markers
        all_markers = [
            marker
            for markers in cls.LAUNCHER_MARKERS.values()
            for marker in markers
        ]

        for marker in all_markers:
            value = os.environ.get(marker)
            if value:
                # Sanitize sensitive values (keep first/last 4 chars only)
                if "KEY" in marker or "TOKEN" in marker:
                    if len(value) > 8:
                        value = f"{value[:4]}...{value[-4:]}"
                env[marker] = value

        # Add useful non-sensitive vars
        for var in ["USER", "HOME", "PWD", "SHELL"]:
            if var in os.environ:
                env[var] = os.environ[var]

        return env

    @classmethod
    def _get_parent_process_name(cls) -> Optional[str]:
        """Get parent process name (best effort).

        Returns:
            Parent process name or None if unavailable
        """
        try:
            import subprocess
            result = subprocess.run(
                ["ps", "-o", "comm=", "-p", str(os.getppid())],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        return None

    @classmethod
    def _write_with_retry(
        cls,
        filepath: Path,
        data: Dict[str, Any],
        max_retries: int = 3
    ) -> None:
        """Write JSON file with retry for cloud sync resilience.

        Args:
            filepath: Path to write to
            data: Dictionary to write as JSON
            max_retries: Maximum retry attempts

        Raises:
            OSError: If all retries fail
        """
        import time

        retry_delay = 0.1
        last_error = None

        for attempt in range(max_retries):
            try:
                filepath.write_text(json.dumps(data, indent=2))
                return
            except OSError as e:
                last_error = e
                if e.errno == 5 and attempt < max_retries - 1:  # I/O error
                    if attempt == 0:
                        print(
                            f"File I/O error writing {filepath} - retrying. "
                            "May be cloud sync issue."
                        )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

        # All retries failed
        if last_error:
            raise last_error


__all__ = ["LauncherDetector", "LauncherInfo"]
