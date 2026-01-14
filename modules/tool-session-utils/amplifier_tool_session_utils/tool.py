"""
Session Utilities Tool for Amplifier.

Exposes session management operations as an Amplifier tool.
"""

import time
from pathlib import Path
from typing import Any

from .append_handler import (
    AppendError,
    ValidationError,
    append_instructions,
    list_pending_instructions,
)
from .fork_manager import ForkManager


class SessionUtilsTool:
    """Amplifier tool for session management utilities.

    Provides operations for:
    - Fork management (duration-based session forking)
    - Instruction appending (inject instructions to running sessions)
    """

    name = "session_utils"
    description = """Session management utilities for Amplifier.

Operations:
- fork_status: Get current fork manager status
- fork_reset: Reset fork manager (start new timing)
- fork_check: Check if fork is needed
- append: Append instruction to running auto mode session
- list_pending: List pending instructions for a session

Examples:
- {"operation": "fork_status"}
- {"operation": "fork_reset"}
- {"operation": "fork_check"}
- {"operation": "append", "instruction": "Focus on error handling next"}
- {"operation": "list_pending", "session_id": "auto_20250101_120000"}
"""

    def __init__(
        self,
        fork_threshold: float = 3600.0,
        workspace_dir: Path | None = None,
    ) -> None:
        """Initialize session utils tool.

        Args:
            fork_threshold: Fork threshold in seconds (default 60 min)
            workspace_dir: Optional workspace directory
        """
        self.fork_manager = ForkManager(
            start_time=time.time(),
            fork_threshold=fork_threshold,
        )
        self.workspace_dir = workspace_dir

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute a session utils operation.

        Args:
            input_data: Operation parameters

        Returns:
            Result dictionary
        """
        operation = input_data.get("operation", "").lower()

        handlers = {
            "fork_status": self._handle_fork_status,
            "fork_reset": self._handle_fork_reset,
            "fork_check": self._handle_fork_check,
            "append": self._handle_append,
            "list_pending": self._handle_list_pending,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}. Valid: {list(handlers.keys())}",
            }

        try:
            return handler(input_data)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_fork_status(self, data: dict[str, Any]) -> dict[str, Any]:
        """Get fork manager status."""
        status = self.fork_manager.get_status()
        return {"success": True, **status}

    def _handle_fork_reset(self, data: dict[str, Any]) -> dict[str, Any]:
        """Reset fork manager."""
        self.fork_manager.reset()
        return {
            "success": True,
            "message": "Fork manager reset",
            "start_time": self.fork_manager.start_time,
        }

    def _handle_fork_check(self, data: dict[str, Any]) -> dict[str, Any]:
        """Check if fork is needed."""
        should_fork = self.fork_manager.should_fork()
        status = self.fork_manager.get_status()

        result = {
            "success": True,
            "should_fork": should_fork,
            "elapsed_minutes": status["elapsed_minutes"],
            "remaining_minutes": status["remaining_minutes"],
        }

        if should_fork:
            result["recommendation"] = (
                "Session duration threshold reached. Consider forking to avoid "
                "hitting hard time limits."
            )

        return result

    def _handle_append(self, data: dict[str, Any]) -> dict[str, Any]:
        """Append instruction to running session."""
        instruction = data.get("instruction")
        if not instruction:
            return {"success": False, "error": "Missing required field: instruction"}

        session_id = data.get("session_id")

        try:
            result = append_instructions(
                instruction=instruction,
                session_id=session_id,
                workspace_dir=self.workspace_dir,
            )
            return result.to_dict()
        except ValueError as e:
            return {"success": False, "error": f"Invalid instruction: {e}"}
        except ValidationError as e:
            return {"success": False, "error": f"Validation failed: {e}"}
        except AppendError as e:
            return {"success": False, "error": str(e)}

    def _handle_list_pending(self, data: dict[str, Any]) -> dict[str, Any]:
        """List pending instructions."""
        session_id = data.get("session_id")

        instructions = list_pending_instructions(
            session_id=session_id,
            workspace_dir=self.workspace_dir,
        )

        return {
            "success": True,
            "count": len(instructions),
            "instructions": instructions,
        }


def create_tool(config: dict | None = None) -> SessionUtilsTool:
    """Factory function to create session utils tool.

    Args:
        config: Optional configuration dict

    Returns:
        Configured SessionUtilsTool instance
    """
    config = config or {}
    return SessionUtilsTool(
        fork_threshold=config.get("fork_threshold", 3600.0),
        workspace_dir=Path(config["workspace_dir"]) if config.get("workspace_dir") else None,
    )
