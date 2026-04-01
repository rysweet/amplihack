#!/usr/bin/env python3
"""Standalone lock tool for autonomous co-pilot mode.

The agent writes the goal file before calling this tool. This tool only
manages the lock state (on/off/check). Goal formulation and definition
of done are the agent's responsibility.

Usage:
    python lock_tool.py lock
    python lock_tool.py unlock
    python lock_tool.py check
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def _get_project_root() -> Path:
    """Get project root from CLAUDE_PROJECT_DIR or fallback to cwd."""
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
    return re.sub(r"[^A-Za-z0-9_\-]", "_", session_id)


def _get_session_id() -> str | None:
    """Return the active session ID when the launcher exposes one."""
    return os.environ.get("AMPLIHACK_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")


def create_lock() -> int:
    """Create lock to enable autonomous co-pilot mode."""
    try:
        LOCK_DIR.mkdir(parents=True, exist_ok=True)

        if LOCK_FILE.exists():
            print("Lock was already active")
            return 0

        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            metadata = [f"locked_at: {datetime.now().isoformat()}"]
            session_id = _sanitize_session_id(_get_session_id())
            if session_id:
                metadata.append(f"session_id: {session_id}")
            os.write(fd, ("\n".join(metadata) + "\n").encode())
        finally:
            os.close(fd)

        print("Lock enabled — autonomous co-pilot active")
        print("  Use /amplihack:unlock to disable")

        if GOAL_FILE.exists():
            goal = GOAL_FILE.read_text().strip()
            print(f"  Goal: {goal}")

        return 0

    except FileExistsError:
        print("Lock was already active")
        return 0
    except Exception as e:
        print(f"ERROR: Failed to create lock: {e}")
        return 1


def remove_lock() -> int:
    """Remove lock to disable autonomous co-pilot mode."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
            print("Lock disabled — co-pilot stopped")
        else:
            print("Lock was not enabled")

        for path in (GOAL_FILE, CONTINUATION_PROMPT_FILE, MESSAGE_FILE):
            path.unlink(missing_ok=True)

        return 0

    except Exception as e:
        print(f"ERROR: Failed to remove lock: {e}")
        return 1


def check_lock() -> int:
    """Check if lock is active."""
    try:
        if LOCK_FILE.exists():
            lock_info = LOCK_FILE.read_text().strip()
            print("Lock is ACTIVE")
            print(f"  {lock_info}")

            if GOAL_FILE.exists():
                goal = GOAL_FILE.read_text().strip()
                print(f"  Goal: {goal}")
            else:
                print("  Goal: (none — agent should write .lock_goal)")
        else:
            print("Lock is NOT active")

        return 0

    except Exception as e:
        print(f"ERROR: Failed to check lock: {e}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Lock tool for autonomous co-pilot mode")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("lock", help="Enable autonomous co-pilot mode")
    subparsers.add_parser("unlock", help="Disable autonomous co-pilot mode")
    subparsers.add_parser("check", help="Check lock status")

    args = parser.parse_args()

    if args.command == "lock":
        return create_lock()
    if args.command == "unlock":
        return remove_lock()
    if args.command == "check":
        return check_lock()
    return 1


if __name__ == "__main__":
    sys.exit(main())
