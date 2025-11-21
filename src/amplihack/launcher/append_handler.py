"""Append instruction handler for auto mode instruction injection.

This module provides functionality to append new instructions to running auto mode sessions.
Instructions are written to timestamped files in the session's append/ directory.
"""

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


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


def _validate_instruction(instruction: str) -> None:
    """Validate instruction content for security and size.

    Args:
        instruction: Instruction text to validate

    Raises:
        ValidationError: If validation fails
    """
    # Check size
    instruction_bytes = instruction.encode("utf-8")
    if len(instruction_bytes) > MAX_INSTRUCTION_SIZE:
        raise ValidationError(
            f"Instruction too large: {len(instruction_bytes)} bytes "
            f"(max {MAX_INSTRUCTION_SIZE} bytes / {MAX_INSTRUCTION_SIZE // 1024}KB)"
        )

    # Check for suspicious patterns
    instruction_lower = instruction.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, instruction_lower, re.IGNORECASE):
            raise ValidationError(
                f"Suspicious pattern detected: '{pattern}'. "
                "This might be a prompt injection attempt. "
                "If this is legitimate, please rephrase your instruction."
            )


def _check_rate_limit(append_dir: Path) -> None:
    """Check if rate limit has been exceeded.

    Args:
        append_dir: Directory to check for recent appends

    Raises:
        ValidationError: If rate limit exceeded
    """
    # Check pending instructions count
    pending_count = len(list(append_dir.glob("*.md")))
    if pending_count >= MAX_PENDING_INSTRUCTIONS:
        raise ValidationError(
            f"Too many pending instructions: {pending_count} "
            f"(max {MAX_PENDING_INSTRUCTIONS}). "
            "Wait for the auto mode session to process existing instructions."
        )

    # Check appends in last minute
    now = time.time()
    one_minute_ago = now - 60

    recent_appends = 0
    for md_file in append_dir.glob("*.md"):
        try:
            # Check file modification time
            mtime = md_file.stat().st_mtime
            if mtime >= one_minute_ago:
                recent_appends += 1
        except (OSError, ValueError):
            # Ignore files we can't stat
            pass

    if recent_appends >= MAX_APPENDS_PER_MINUTE:
        raise ValidationError(
            f"Rate limit exceeded: {recent_appends} appends in last minute "
            f"(max {MAX_APPENDS_PER_MINUTE}). Please wait before appending more instructions."
        )


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
        ValidationError: If instruction fails security validation or rate limit
        AppendError: If session not found or write fails
    """
    # Validate instruction
    if not instruction or not instruction.strip():
        raise ValueError("Instruction cannot be empty or whitespace-only")

    # Security validation
    _validate_instruction(instruction)

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
        raise AppendError(
            f"No active auto mode session found in {workspace}. "
            "Start an auto mode session first with: amplihack claude --auto -- -p \"your task\""
        )

    # Verify append directory exists
    append_dir = session_dir / "append"

    if not append_dir.exists():
        raise AppendError(f"Append directory not found in session: {session_dir}")

    # Check rate limits
    _check_rate_limit(append_dir)

    # Generate timestamped filename with microsecond precision
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{timestamp}.md"
    filepath = append_dir / filename

    # Write instruction atomically using os.open() with O_CREAT|O_EXCL
    # This ensures atomic creation with proper permissions from the start
    try:
        # Open file atomically with exclusive creation flag and restrictive permissions
        # O_CREAT: Create file if it doesn't exist
        # O_EXCL: Fail if file already exists (prevents race conditions)
        # O_WRONLY: Write-only mode
        # 0o600: Owner read/write only (set atomically during creation)
        fd = os.open(
            str(filepath),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600
        )

        try:
            # Write content to file descriptor
            content = "# Appended Instruction\n\n"
            content += f"**Timestamp**: {datetime.now().isoformat()}\n\n"
            content += f"{instruction}\n"

            os.write(fd, content.encode("utf-8"))
        finally:
            # Always close file descriptor
            os.close(fd)

        return AppendResult(
            success=True,
            filename=filename,
            session_id=session_dir.name,
            append_dir=append_dir,
            timestamp=timestamp,
            message="Instruction appended successfully",
        )

    except FileExistsError:
        # File already exists (race condition or duplicate timestamp)
        # This should be extremely rare due to microsecond precision
        raise AppendError(
            f"Instruction file already exists: {filename}. "
            "Please retry - this is a rare timestamp collision."
        )
    except Exception as e:
        raise AppendError(f"Failed to write instruction: {e}")
