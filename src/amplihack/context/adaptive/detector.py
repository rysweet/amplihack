"""Launcher detection for adaptive context injection.

Detects which launcher (Claude Code, Copilot CLI, etc.) is being used
and provides appropriate context injection strategy.

Philosophy:
- Simple file-based detection (launcher_context.json)
- Strategy pattern for launcher-specific behavior
- Fail-safe defaults (assume Claude Code if unknown)
- No external dependencies
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

LauncherType = Literal["claude", "copilot", "unknown"]


class LauncherDetector:
    """Detect launcher and manage context injection.

    Detects launcher from launcher_context.json written by the launcher.
    Provides strategy for injecting context appropriately for each launcher.

    Example:
        >>> detector = LauncherDetector(Path("/project"))
        >>> detector.write_context("copilot", "amplihack copilot", {})
        >>> launcher = detector.detect()
        >>> print(launcher)  # "copilot"
    """

    CONTEXT_FILE = ".claude/runtime/launcher_context.json"

    # Context staleness threshold (24 hours)
    # Rationale: Balances reusing valid context vs detecting launcher changes
    # - Accommodates long dev sessions and multiple same-launcher sessions per day
    # - Cleans up stale context from crashes (detected next day)
    # - Handles developer switching between Claude Code/Copilot across days
    STALENESS_HOURS = 24

    def __init__(self, project_root: Path):
        """Initialize detector.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.context_path = project_root / self.CONTEXT_FILE

    def detect(self) -> LauncherType:
        """Detect which launcher is being used.

        Returns:
            Launcher type: "claude", "copilot", or "unknown"

        Example:
            >>> detector = LauncherDetector(Path.cwd())
            >>> launcher = detector.detect()
            >>> if launcher == "copilot":
            ...     print("Using Copilot CLI")
        """
        # If no context file, assume Claude Code (default)
        if not self.context_path.exists():
            return "claude"

        # If context is stale, assume Claude Code
        if self.is_stale():
            return "claude"

        # Read launcher type from context
        try:
            context = json.loads(self.context_path.read_text())
            launcher = context.get("launcher", "claude")

            # Validate launcher type (fail-safe to claude)
            if launcher not in ("claude", "copilot"):
                return "claude"  # Fail-safe default

            return launcher
        except (json.JSONDecodeError, KeyError):
            # Fail-safe: malformed context defaults to Claude Code
            return "claude"

    def write_context(
        self,
        launcher_type: LauncherType,
        command: str,
        environment: dict[str, str] | None = None,
    ) -> None:
        """Write launcher context for hooks to detect.

        Args:
            launcher_type: Type of launcher ("claude", "copilot")
            command: Full command that was run
            environment: Additional environment variables

        Example:
            >>> detector = LauncherDetector(Path.cwd())
            >>> detector.write_context(
            ...     launcher_type="copilot",
            ...     command="amplihack copilot --model opus",
            ...     environment={"AMPLIHACK_LAUNCHER": "copilot"}
            ... )
        """
        # Ensure runtime directory exists
        self.context_path.parent.mkdir(parents=True, exist_ok=True)

        # Build context
        context = {
            "launcher": launcher_type,
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": environment or {},
        }

        # Write context
        self.context_path.write_text(json.dumps(context, indent=2))

        # Security: Restrict file permissions (owner only)
        # Protects potentially sensitive environment variables
        try:
            self.context_path.chmod(0o600)
        except OSError:
            pass  # Best effort - Windows doesn't support POSIX permissions

    def is_stale(self, max_age_hours: int | None = None) -> bool:
        """Check if launcher context is stale.

        Args:
            max_age_hours: Maximum age in hours (default: 24)

        Returns:
            True if context is older than max_age_hours

        Example:
            >>> detector = LauncherDetector(Path.cwd())
            >>> if detector.is_stale(max_age_hours=1):
            ...     print("Context expired")
        """
        if not self.context_path.exists():
            return True

        max_age = max_age_hours or self.STALENESS_HOURS

        try:
            context = json.loads(self.context_path.read_text())
            timestamp_str = context.get("timestamp")

            if not timestamp_str:
                return True

            # Parse timestamp
            timestamp = datetime.fromisoformat(timestamp_str)

            # Make timezone-aware if needed
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            # Check age
            now = datetime.now(timezone.utc)
            age_hours = (now - timestamp).total_seconds() / 3600

            return age_hours > max_age

        except (json.JSONDecodeError, KeyError, ValueError):
            return True

    def cleanup(self) -> None:
        """Remove launcher context file.

        Called at session end to clean up temporary context.

        Example:
            >>> detector = LauncherDetector(Path.cwd())
            >>> detector.cleanup()  # Removes launcher_context.json
        """
        if self.context_path.exists():
            self.context_path.unlink()
