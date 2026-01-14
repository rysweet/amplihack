"""
Append instruction handler for auto mode instruction injection.

Provides functionality to append new instructions to running auto mode sessions.
"""

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class AppendError(Exception):
    """Error during append operation."""


class ValidationError(Exception):
    """Validation error for instruction content."""


# Security constants
MAX_INSTRUCTION_SIZE = 100 * 1024  # 100KB
MAX_APPENDS_PER_MINUTE = 10
MAX_PENDING_INSTRUCTIONS = 100

# Suspicious patterns that might indicate prompt injection
SUSPICIOUS_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+all\s+prior",
    r"forget\s+everything",
    r"new\s+instructions:",
    r"system\s+prompt:",
    r"<\s*script",
    r"eval\s*\(",
    r"exec\s*\(",
    r"__import__",
]


@dataclass
class AppendResult:
    """Result of append_instructions operation."""

    success: bool
    filename: str
    session_id: str
    append_dir: Path
    timestamp: str
    message: str | None = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "filename": self.filename,
            "session_id": self.session_id,
            "append_dir": str(self.append_dir),
            "timestamp": self.timestamp,
            "message": self.message,
        }


def _validate_instruction(instruction: str) -> None:
    """Validate instruction content for security and size."""
    instruction_bytes = instruction.encode("utf-8")
    if len(instruction_bytes) > MAX_INSTRUCTION_SIZE:
        raise ValidationError(
            f"Instruction too large: {len(instruction_bytes)} bytes "
            f"(max {MAX_INSTRUCTION_SIZE // 1024}KB)"
        )

    instruction_lower = instruction.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, instruction_lower, re.IGNORECASE):
            raise ValidationError(
                f"Suspicious pattern detected: '{pattern}'. "
                "This might be a prompt injection attempt."
            )


def _check_rate_limit(append_dir: Path) -> None:
    """Check if rate limit has been exceeded."""
    pending_count = len(list(append_dir.glob("*.md")))
    if pending_count >= MAX_PENDING_INSTRUCTIONS:
        raise ValidationError(
            f"Too many pending instructions: {pending_count} (max {MAX_PENDING_INSTRUCTIONS})."
        )

    now = time.time()
    one_minute_ago = now - 60
    recent_appends = 0

    for md_file in append_dir.glob("*.md"):
        try:
            mtime = md_file.stat().st_mtime
            if mtime >= one_minute_ago:
                recent_appends += 1
        except (OSError, ValueError):
            pass

    if recent_appends >= MAX_APPENDS_PER_MINUTE:
        raise ValidationError(
            f"Rate limit exceeded: {recent_appends} appends in last minute "
            f"(max {MAX_APPENDS_PER_MINUTE})."
        )


def _find_workspace_root(start_dir: Path) -> Path | None:
    """Find workspace root by traversing up to find .amplifier directory."""
    current = start_dir.resolve()

    while current != current.parent:
        # Check for .amplifier or .claude directory
        for dir_name in [".amplifier", ".claude"]:
            check_dir = current / dir_name
            if check_dir.exists() and check_dir.is_dir():
                return current
        current = current.parent

    return None


def _find_active_session(
    workspace: Path,
    session_id: str | None = None,
) -> Path | None:
    """Find active auto mode session directory."""
    # Try .amplifier first, then .claude
    for config_dir in [".amplifier", ".claude"]:
        logs_dir = workspace / config_dir / "runtime" / "logs"
        if not logs_dir.exists():
            continue

        if session_id:
            session_dir = logs_dir / session_id
            if session_dir.exists() and session_dir.is_dir():
                return session_dir
            continue

        # Find most recent auto_* session
        auto_dirs = sorted(
            [d for d in logs_dir.iterdir() if d.is_dir() and d.name.startswith("auto_")],
            key=lambda d: d.name,
            reverse=True,
        )

        if auto_dirs:
            return auto_dirs[0]

    return None


def append_instructions(
    instruction: str,
    session_id: str | None = None,
    workspace_dir: Path | None = None,
) -> AppendResult:
    """Append instruction to active auto mode session.

    Args:
        instruction: Instruction text to append
        session_id: Optional session ID (auto-discovers if None)
        workspace_dir: Optional workspace directory (uses cwd if None)

    Returns:
        AppendResult with operation details

    Raises:
        ValueError: If instruction is empty
        ValidationError: If instruction fails security validation
        AppendError: If session not found or write fails
    """
    if not instruction or not instruction.strip():
        raise ValueError("Instruction cannot be empty")

    _validate_instruction(instruction)

    cwd = workspace_dir or Path.cwd()
    workspace = _find_workspace_root(cwd)

    if not workspace:
        raise AppendError(
            f"No .amplifier or .claude directory found starting from {cwd}. "
            "Start an auto mode session first."
        )

    session_dir = _find_active_session(workspace, session_id)

    if not session_dir:
        if session_id:
            raise AppendError(f"Session not found: {session_id}")
        raise AppendError(
            f"No active auto mode session found in {workspace}. Start an auto mode session first."
        )

    # Ensure append directory exists
    append_dir = session_dir / "append"
    append_dir.mkdir(parents=True, exist_ok=True)

    _check_rate_limit(append_dir)

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}.md"
    filepath = append_dir / filename

    try:
        fd = os.open(str(filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            content = "# Appended Instruction\n\n"
            content += f"**Timestamp**: {datetime.now().isoformat()}\n\n"
            content += f"{instruction}\n"
            os.write(fd, content.encode("utf-8"))
        finally:
            os.close(fd)

        return AppendResult(
            success=True,
            filename=filename,
            session_id=session_dir.name,
            append_dir=append_dir,
            timestamp=timestamp,
            message="Instruction appended successfully",
        )

    except FileExistsError as e:
        raise AppendError(f"Instruction file already exists: {filename}. Please retry.") from e
    except Exception as e:
        raise AppendError(f"Failed to write instruction: {e}") from e


def list_pending_instructions(
    session_id: str | None = None,
    workspace_dir: Path | None = None,
) -> list[dict]:
    """List pending instructions for a session.

    Args:
        session_id: Optional session ID
        workspace_dir: Optional workspace directory

    Returns:
        List of pending instruction details
    """
    cwd = workspace_dir or Path.cwd()
    workspace = _find_workspace_root(cwd)

    if not workspace:
        return []

    session_dir = _find_active_session(workspace, session_id)
    if not session_dir:
        return []

    append_dir = session_dir / "append"
    if not append_dir.exists():
        return []

    instructions = []
    for md_file in sorted(append_dir.glob("*.md")):
        try:
            stat = md_file.stat()
            instructions.append(
                {
                    "filename": md_file.name,
                    "size_bytes": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )
        except OSError:
            pass

    return instructions
