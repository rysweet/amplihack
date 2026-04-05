#!/usr/bin/env python3
"""Standalone lock tool for continuous work mode.

Usage:
    python lock_tool.py lock
    python lock_tool.py lock --message "Custom instruction"
    python lock_tool.py unlock
    python lock_tool.py check
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_\-]")


def _get_project_root() -> Path:
    """Get project root from CLAUDE_PROJECT_DIR or fallback to cwd.

    This ensures lock files are created in the correct location regardless
    of which directory the user runs the command from.
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return Path(project_dir)
    return Path.cwd()


# Lock files in runtime directory (using absolute path from project root)
_PROJECT_ROOT = _get_project_root()
LOCK_DIR = _PROJECT_ROOT / ".claude" / "runtime" / "locks"
LOCK_FILE = LOCK_DIR / ".lock_active"
GOAL_FILE = LOCK_DIR / ".lock_goal"
CONTINUATION_PROMPT_FILE = LOCK_DIR / ".continuation_prompt"
MESSAGE_FILE = LOCK_DIR / ".lock_message"


def _sanitize_session_id(session_id: str | None) -> str | None:
    """Sanitize session_id to prevent path traversal and metadata injection.

    Replaces any character that is not alphanumeric, hyphen, or underscore
    with an underscore. This neutralizes path traversal sequences (../../),
    newline injection, and other shell/filesystem metacharacters.

    Args:
        session_id: Raw session identifier from environment, or None.

    Returns:
        Sanitized string safe for use as a filesystem path component, or None
        if the input was None.
    """
    if session_id is None:
        return None
    return _SANITIZE_RE.sub("_", session_id)


def _get_session_id() -> str | None:
    """Return the active session ID when the launcher exposes one."""
    return os.environ.get("AMPLIHACK_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")


def create_lock(message: str = None) -> int:
    """Create lock to enable continuous work mode."""
    try:
        # Create locks directory
        LOCK_DIR.mkdir(parents=True, exist_ok=True)

        # Check if already locked
        if LOCK_FILE.exists():
            print("⚠ WARNING: Lock was already active")
            if message:
                MESSAGE_FILE.write_text(message)
                print(f"✓ Updated lock message: {message}")
            return 0

        # Create lock file atomically
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            metadata = [f"locked_at: {datetime.now().isoformat()}"]
            session_id = _sanitize_session_id(_get_session_id())
            if session_id:
                metadata.append(f"session_id: {session_id}")
            os.write(fd, ("\n".join(metadata) + "\n").encode())
        finally:
            os.close(fd)

        print("✓ Lock enabled - Claude will continue working until unlocked")
        print("  Use /amplihack:unlock to disable continuous work mode")

        # Save custom message if provided
        if message:
            MESSAGE_FILE.write_text(message)
            print(f"  Custom instruction: {message}")

        return 0

    except FileExistsError:
        print("⚠ WARNING: Lock was already active")
        return 0
    except Exception as e:
        print(f"✗ ERROR: Failed to create lock: {e}")
        return 1


def remove_lock() -> int:
    """Remove lock to disable continuous work mode."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
            print("✓ Lock disabled - Claude will stop normally")
        else:
            print("ℹ Lock was not enabled")

        for path in (GOAL_FILE, CONTINUATION_PROMPT_FILE, MESSAGE_FILE):
            path.unlink(missing_ok=True)

        return 0

    except Exception as e:
        print(f"✗ ERROR: Failed to remove lock: {e}")
        return 1


def check_lock() -> int:
    """Check if lock is active."""
    try:
        if LOCK_FILE.exists():
            lock_info = LOCK_FILE.read_text().strip()
            print("✓ Lock is ACTIVE")
            print(f"  {lock_info}")

            if MESSAGE_FILE.exists():
                message = MESSAGE_FILE.read_text().strip()
                print(f"  Custom instruction: {message}")
        else:
            print("ℹ Lock is NOT active")

        return 0

    except Exception as e:
        print(f"✗ ERROR: Failed to check lock: {e}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Lock tool for continuous work mode")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Lock command
    lock_parser = subparsers.add_parser("lock", help="Enable continuous work mode")
    lock_parser.add_argument("--message", "-m", help="Custom instruction for Claude")

    # Unlock command
    subparsers.add_parser("unlock", help="Disable continuous work mode")

    # Check command
    subparsers.add_parser("check", help="Check lock status")

    args = parser.parse_args()

    # Execute command
    if args.command == "lock":
        return create_lock(message=args.message)
    if args.command == "unlock":
        return remove_lock()
    if args.command == "check":
        return check_lock()
    return 1  # Unknown command


if __name__ == "__main__":
    sys.exit(main())
