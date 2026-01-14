"""Lock tool for continuous work mode.

Enables "lock mode" where the agent keeps working until explicitly unlocked.
Lock files are stored in `.amplifier/runtime/locks/` within the project.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

__amplifier_module_type__ = "tool"


@dataclass
class ToolResult:
    """Result from tool execution."""

    success: bool
    message: str
    data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result: dict[str, Any] = {
            "success": self.success,
            "message": self.message,
        }
        if self.data:
            result["data"] = self.data
        return result


def _get_project_root() -> Path:
    """Get project root from environment or fallback to cwd.

    Checks AMPLIFIER_PROJECT_DIR first (Amplifier standard),
    then CLAUDE_PROJECT_DIR for backward compatibility.
    """
    project_dir = os.environ.get("AMPLIFIER_PROJECT_DIR") or os.environ.get(
        "CLAUDE_PROJECT_DIR"
    )
    if project_dir:
        return Path(project_dir)
    return Path.cwd()


def _get_lock_paths() -> tuple[Path, Path, Path]:
    """Get lock directory and file paths.

    Returns:
        Tuple of (lock_dir, lock_file, message_file)
    """
    project_root = _get_project_root()
    lock_dir = project_root / ".amplifier" / "runtime" / "locks"
    lock_file = lock_dir / ".lock_active"
    message_file = lock_dir / ".lock_message"
    return lock_dir, lock_file, message_file


class LockTool:
    """Tool for managing continuous work mode via lock files.

    Operations:
        - lock: Enable continuous work mode (create lock file)
        - unlock: Disable continuous work mode (remove lock file)
        - check: Check if lock is currently active
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the lock tool.

        Args:
            config: Optional configuration dictionary (unused currently)
        """
        self._config = config or {}

    @property
    def name(self) -> str:
        """Tool name for registration."""
        return "lock"

    @property
    def description(self) -> str:
        """Tool description for LLM context."""
        return (
            "Manage continuous work mode. Use 'lock' to enable (agent keeps working), "
            "'unlock' to disable, 'check' to see current status."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for tool input."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["lock", "unlock", "check"],
                    "description": "Operation to perform: lock, unlock, or check",
                },
                "message": {
                    "type": "string",
                    "description": "Custom instruction when locking (optional)",
                },
            },
            "required": ["operation"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        """Execute the lock tool operation.

        Args:
            input: Dictionary with 'operation' and optional 'message'

        Returns:
            ToolResult with success status and message
        """
        operation = input.get("operation")
        message = input.get("message")

        if operation == "lock":
            return self._create_lock(message)
        elif operation == "unlock":
            return self._remove_lock()
        elif operation == "check":
            return self._check_lock()
        else:
            return ToolResult(
                success=False,
                message=f"Unknown operation: {operation}. Use 'lock', 'unlock', or 'check'.",
            )

    def _create_lock(self, message: str | None = None) -> ToolResult:
        """Create lock to enable continuous work mode."""
        lock_dir, lock_file, message_file = _get_lock_paths()

        try:
            # Create locks directory
            lock_dir.mkdir(parents=True, exist_ok=True)

            # Check if already locked
            if lock_file.exists():
                if message:
                    message_file.write_text(message)
                    return ToolResult(
                        success=True,
                        message=f"Lock was already active. Updated message: {message}",
                        data={"was_locked": True, "message_updated": True},
                    )
                return ToolResult(
                    success=True,
                    message="Lock was already active.",
                    data={"was_locked": True, "message_updated": False},
                )

            # Create lock file atomically
            fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"locked_at: {datetime.now().isoformat()}\n".encode())
            os.close(fd)

            # Save custom message if provided
            if message:
                message_file.write_text(message)

            return ToolResult(
                success=True,
                message="Lock enabled - continuous work mode active until unlocked.",
                data={
                    "locked_at": datetime.now().isoformat(),
                    "message": message,
                    "lock_file": str(lock_file),
                },
            )

        except FileExistsError:
            # Race condition - file created between check and open
            return ToolResult(
                success=True,
                message="Lock was already active (race condition).",
                data={"was_locked": True},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Failed to create lock: {e}",
            )

    def _remove_lock(self) -> ToolResult:
        """Remove lock to disable continuous work mode."""
        _lock_dir, lock_file, message_file = _get_lock_paths()

        try:
            was_locked = lock_file.exists()

            if lock_file.exists():
                lock_file.unlink()

            # Clean up message file if exists
            if message_file.exists():
                message_file.unlink()

            if was_locked:
                return ToolResult(
                    success=True,
                    message="Lock disabled - continuous work mode stopped.",
                    data={"was_locked": True},
                )
            else:
                return ToolResult(
                    success=True,
                    message="Lock was not active.",
                    data={"was_locked": False},
                )

        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Failed to remove lock: {e}",
            )

    def _check_lock(self) -> ToolResult:
        """Check if lock is active."""
        _lock_dir, lock_file, message_file = _get_lock_paths()

        try:
            if lock_file.exists():
                lock_info = lock_file.read_text().strip()
                custom_message = None

                if message_file.exists():
                    custom_message = message_file.read_text().strip()

                return ToolResult(
                    success=True,
                    message="Lock is ACTIVE - continuous work mode enabled.",
                    data={
                        "active": True,
                        "lock_info": lock_info,
                        "custom_message": custom_message,
                    },
                )
            else:
                return ToolResult(
                    success=True,
                    message="Lock is NOT active.",
                    data={"active": False},
                )

        except Exception as e:
            return ToolResult(
                success=False,
                message=f"Failed to check lock: {e}",
            )
