"""Append instruction handler for auto mode instruction injection.

This module provides functionality to append new instructions to running auto mode sessions.
Instructions are written to timestamped files in the session's append/ directory.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


class AppendError(Exception):
    """Error during append operation."""

    pass


@dataclass
class AppendResult:
    """Result of append_instructions operation.

    Attributes:
        success: Whether operation succeeded
        filename: Name of created instruction file
        session_id: ID of target session
        append_dir: Path to append directory
        timestamp: Timestamp of instruction
        message: Optional message
    """

    success: bool
    filename: str
    session_id: str
    append_dir: Path
    timestamp: str
    message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all result fields
        """
        return {
            "success": self.success,
            "filename": self.filename,
            "session_id": self.session_id,
            "append_dir": str(self.append_dir),
            "timestamp": self.timestamp,
            "message": self.message,
        }


def _find_workspace_root(start_dir: Path) -> Optional[Path]:
    """Find workspace root by traversing up to find .claude directory.

    Args:
        start_dir: Directory to start search from

    Returns:
        Path to workspace root, or None if not found
    """
    current = start_dir.resolve()

    # Traverse up to find .claude directory
    while current != current.parent:
        claude_dir = current / ".claude"
        if claude_dir.exists() and claude_dir.is_dir():
            return current
        current = current.parent

    return None


def _find_active_session(workspace: Path, session_id: Optional[str] = None) -> Optional[Path]:
    """Find active auto mode session directory.

    Args:
        workspace: Workspace root directory
        session_id: Optional specific session ID to target

    Returns:
        Path to session directory, or None if not found
    """
    logs_dir = workspace / ".claude" / "runtime" / "logs"

    if not logs_dir.exists():
        return None

    if session_id:
        # Look for specific session
        session_dir = logs_dir / session_id
        if session_dir.exists() and session_dir.is_dir():
            return session_dir
        return None

    # Find most recent auto_* session
    auto_dirs = sorted(
        [d for d in logs_dir.iterdir() if d.is_dir() and d.name.startswith("auto_")],
        key=lambda d: d.name,
        reverse=True,
    )

    if auto_dirs:
        return auto_dirs[0]

    return None


def append_instructions(instruction: str, session_id: Optional[str] = None) -> AppendResult:
    """Append instruction to active auto mode session.

    Args:
        instruction: Instruction text to append
        session_id: Optional session ID (auto-discovers if None)

    Returns:
        AppendResult with operation details

    Raises:
        ValueError: If instruction is empty or whitespace
        AppendError: If session not found or write fails
    """
    # Validate instruction
    if not instruction or not instruction.strip():
        raise ValueError("Instruction cannot be empty or whitespace-only")

    # Find workspace root
    cwd = Path.cwd()
    workspace = _find_workspace_root(cwd)

    if not workspace:
        raise AppendError(
            f"No .claude directory found starting from {cwd}. "
            "Start an auto mode session first with: amplihack claude --auto -- -p \"your task\""
        )

    # Find active session
    session_dir = _find_active_session(workspace, session_id)

    if not session_dir:
        if session_id:
            raise AppendError(f"Session not found: {session_id}")
        else:
            raise AppendError(
                f"No active auto mode session found in {workspace}. "
                "Start an auto mode session first with: amplihack claude --auto -- -p \"your task\""
            )

    # Verify append directory exists
    append_dir = session_dir / "append"

    if not append_dir.exists():
        raise AppendError(f"Append directory not found in session: {session_dir}")

    # Generate timestamped filename with microsecond precision
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}.md"
    filepath = append_dir / filename

    # Write instruction atomically using temp file
    temp_filename = f".{filename}.tmp"
    temp_filepath = append_dir / temp_filename

    try:
        # Write to temp file
        with open(temp_filepath, "w", encoding="utf-8") as f:
            f.write(f"# Appended Instruction\n\n")
            f.write(f"**Timestamp**: {datetime.now().isoformat()}\n\n")
            f.write(f"{instruction}\n")

        # Atomic rename
        temp_filepath.rename(filepath)

        return AppendResult(
            success=True,
            filename=filename,
            session_id=session_dir.name,
            append_dir=append_dir,
            timestamp=timestamp,
            message="Instruction appended successfully",
        )

    except Exception as e:
        # Clean up temp file if it exists
        if temp_filepath.exists():
            try:
                temp_filepath.unlink()
            except Exception:
                pass

        raise AppendError(f"Failed to write instruction: {e}")
