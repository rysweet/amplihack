#!/usr/bin/env python3
"""
Pre-commit hook: Auto-sync .github/commands/ when .claude/commands/ changes.

This ensures .github/commands/ is always up-to-date before commits,
eliminating manual sync requirements.

Philosophy:
- Single source of truth (.claude/commands/ is authoritative)
- Automated maintenance (pre-commit ensures sync)
- Zero-BS (sync happens or commit is blocked)
"""

import subprocess
import sys
from pathlib import Path


def get_changed_files() -> list[str]:
    """Get list of staged files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False
    )
    return result.stdout.strip().split("\n") if result.stdout.strip() else []


def needs_command_sync(changed_files: list[str]) -> bool:
    """Check if any .claude/commands/ files changed."""
    return any(f.startswith(".claude/commands/") for f in changed_files)


def sync_commands() -> bool:
    """Run amplihack sync-commands to regenerate .github/commands/."""
    print("📝 .claude/commands/ changed - auto-syncing to .github/commands/...")

    try:
        result = subprocess.run(
            ["amplihack", "sync-commands", "--force"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✅ Commands synced successfully")

            # Stage the newly generated files
            subprocess.run(
                ["git", "add", ".github/commands/"],
                check=False
            )
            return True
        else:
            print(f"❌ Command sync failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Command sync timed out after 30 seconds")
        return False
    except FileNotFoundError:
        print("❌ amplihack command not found")
        print("   Install amplihack or run sync manually: amplihack sync-commands")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during sync: {e}")
        return False


def main() -> int:
    """Main pre-commit hook logic."""
    changed_files = get_changed_files()

    if not changed_files:
        # No staged files, allow commit
        return 0

    if needs_command_sync(changed_files):
        if sync_commands():
            print("\n✅ Pre-commit hook: Commands auto-synced and staged")
            return 0
        else:
            print("\n❌ Pre-commit hook: Command sync failed")
            print("   Fix the error or run manually: amplihack sync-commands")
            return 1

    # No command files changed, allow commit
    return 0


if __name__ == "__main__":
    sys.exit(main())
