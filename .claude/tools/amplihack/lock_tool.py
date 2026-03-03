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
import sys
from datetime import datetime
from pathlib import Path


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
MESSAGE_FILE = LOCK_DIR / ".lock_message"
GOAL_FILE = LOCK_DIR / ".lock_goal"


def create_lock(message: str = None, goal: str = None) -> int:
    """Create lock to enable continuous work mode.

    Args:
        message: Custom instruction for the dumb "continue" mode.
        goal: When provided, enables smart co-pilot mode using SessionCopilot
              reasoning instead of bare "continue" injection.
    """
    try:
        # Create locks directory
        LOCK_DIR.mkdir(parents=True, exist_ok=True)

        # Check if already locked
        if LOCK_FILE.exists():
            print("⚠ WARNING: Lock was already active")
            if message:
                MESSAGE_FILE.write_text(message)
                print(f"✓ Updated lock message: {message}")
            if goal:
                GOAL_FILE.write_text(goal)
                print(f"✓ Updated goal: {goal}")
            return 0

        # Create lock file atomically
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"locked_at: {datetime.now().isoformat()}\n".encode())
        os.close(fd)

        mode = "smart co-pilot" if goal else "continuous work"
        print(f"✓ Lock enabled ({mode} mode) - working until unlocked")
        print("  Use /amplihack:unlock to disable")

        # Save custom message if provided
        if message:
            MESSAGE_FILE.write_text(message)
            print(f"  Custom instruction: {message}")

        # Save goal if provided (enables smart co-pilot mode)
        if goal:
            GOAL_FILE.write_text(goal)
            print(f"  Goal: {goal}")

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

        # Clean up message and goal files
        for f in (MESSAGE_FILE, GOAL_FILE):
            if f.exists():
                f.unlink()

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

            if GOAL_FILE.exists():
                goal = GOAL_FILE.read_text().strip()
                print(f"  Mode: smart co-pilot")
                print(f"  Goal: {goal}")
            else:
                print(f"  Mode: dumb (bare continue)")

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
    lock_parser.add_argument(
        "--goal", "-g",
        help="Goal for smart co-pilot mode (uses LLM reasoning instead of bare 'continue')",
    )

    # Unlock command
    subparsers.add_parser("unlock", help="Disable continuous work mode")

    # Check command
    subparsers.add_parser("check", help="Check lock status")

    args = parser.parse_args()

    # Execute command
    if args.command == "lock":
        return create_lock(message=args.message, goal=args.goal)
    if args.command == "unlock":
        return remove_lock()
    if args.command == "check":
        return check_lock()
    return 1  # Unknown command


if __name__ == "__main__":
    sys.exit(main())
