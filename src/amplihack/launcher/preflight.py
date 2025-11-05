"""Pre-flight safety validation for amplihack automode.

This module prevents automode from running in unsafe conditions that could lead to:
- Conflicts with active Claude Code sessions
- Loss of uncommitted changes
- Directory structure conflicts

Strategy 1 Implementation (Issue #1090 - Pre-flight Safety Validation):
- Detect if running in an active Claude Code session directory
- Check for uncommitted changes in git
- Warn user and exit before any file operations if unsafe
- Provide --force flag to override if user really wants to proceed
- Enhanced git status checking with detailed file listing
- Integration with git_state module for comprehensive validation
- Clear error messages with actionable suggestions
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple


class PreflightError(Exception):
    """Raised when pre-flight validation fails."""

    pass


def has_active_claude_session(working_dir: Path) -> bool:
    """Check if directory contains signs of active Claude Code session.

    Args:
        working_dir: Directory to check

    Returns:
        True if active session indicators found
    """
    claude_dir = working_dir / ".claude"
    if not claude_dir.exists():
        return False

    # Check for runtime directory (indicates recent/active session)
    runtime_dir = claude_dir / "runtime"
    if runtime_dir.exists():
        # Check for recent log files (within last hour)
        import time

        current_time = time.time()
        one_hour_ago = current_time - 3600

        for log_dir in runtime_dir.rglob("logs/*"):
            if log_dir.is_dir():
                # Check if directory was modified recently
                mtime = os.path.getmtime(log_dir)
                if mtime > one_hour_ago:
                    return True

    # Check for settings.json (indicates Claude project)
    settings_file = claude_dir / "settings.json"
    if settings_file.exists():
        return True

    return False


def has_uncommitted_changes(working_dir: Path) -> Tuple[bool, Optional[str]]:
    """Check if directory has uncommitted git changes using enhanced git_state module.

    Args:
        working_dir: Directory to check

    Returns:
        (has_changes, detailed_status) tuple with enhanced file listing
    """
    try:
        # Use git_state module for comprehensive status checking
        from ..utils.git_state import check_git_status, GitStateError

        try:
            status = check_git_status(working_dir)
        except GitStateError:
            # Git not available or error - fall back to no changes
            return False, None

        if not status.is_repo:
            return False, None

        if not status.has_changes:
            return False, None

        # Build detailed status output
        lines = []
        if status.staged_files:
            lines.append(f"Staged ({len(status.staged_files)}):")
            for f in status.staged_files[:10]:  # Show first 10
                lines.append(f"  M {f}")
            if len(status.staged_files) > 10:
                lines.append(f"  ... and {len(status.staged_files) - 10} more")

        if status.unstaged_files:
            lines.append(f"Modified ({len(status.unstaged_files)}):")
            for f in status.unstaged_files[:10]:  # Show first 10
                lines.append(f"  M {f}")
            if len(status.unstaged_files) > 10:
                lines.append(f"  ... and {len(status.unstaged_files) - 10} more")

        if status.untracked_files:
            lines.append(f"Untracked ({len(status.untracked_files)}):")
            for f in status.untracked_files[:10]:  # Show first 10
                lines.append(f"  ? {f}")
            if len(status.untracked_files) > 10:
                lines.append(f"  ... and {len(status.untracked_files) - 10} more")

        return True, "\n".join(lines)

    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Git not available or timed out
        return False, None


def validate_automode_safety(working_dir: Optional[Path] = None, force: bool = False) -> None:
    """Validate that it's safe to run automode in the given directory.

    Args:
        working_dir: Directory to validate (defaults to current directory)
        force: If True, skip all validation checks

    Raises:
        PreflightError: If validation fails and force is False
    """
    if force:
        return

    if working_dir is None:
        working_dir = Path.cwd()

    errors = []

    # Check 1: Active Claude Code session
    if has_active_claude_session(working_dir):
        errors.append(
            "ACTIVE CLAUDE CODE SESSION DETECTED\n"
            f"  Directory: {working_dir}\n"
            "  Risk: Automode file staging will conflict with existing .claude/ structure\n"
            "  This can cause:\n"
            "    - Directory conflict errors\n"
            "    - Lost uncommitted changes\n"
            "    - Session corruption\n"
            "\n"
            "  Recommendation: Use git worktree for isolation\n"
            "    git worktree add ./worktrees/automode-task -b automode-task\n"
            "    cd ./worktrees/automode-task\n"
            "    amplihack claude --auto -- -p 'your task'\n"
        )

    # Check 2: Uncommitted changes
    has_changes, status = has_uncommitted_changes(working_dir)
    if has_changes:
        errors.append(
            "UNCOMMITTED CHANGES DETECTED\n"
            f"  Directory: {working_dir}\n"
            "  Risk: Automode operations may conflict with or overwrite uncommitted work\n"
            f"  Uncommitted files:\n{_indent(status, '    ')}\n"
            "\n"
            "  Recommendation: Commit or stash changes first\n"
            "    git add -A && git commit -m 'WIP: before automode'\n"
            "    # or\n"
            "    git stash\n"
        )

    if errors:
        error_message = (
            "\n"
            + "=" * 80
            + "\n"
            + "PRE-FLIGHT VALIDATION FAILED\n"
            + "=" * 80
            + "\n\n"
            + "\n\n".join(errors)
            + "\n\n"
            + "=" * 80
            + "\n"
            + "SAFETY OVERRIDE\n"
            + "=" * 80
            + "\n"
            + "If you understand the risks and want to proceed anyway:\n"
            + "  amplihack claude --auto --force -- -p 'your task'\n"
            + "\n"
            + "For more information, see:\n"
            + "  docs/AUTO_MODE.md\n"
            + "  .claude/commands/amplihack/auto.md\n"
            + "=" * 80
            + "\n"
        )
        raise PreflightError(error_message)


def _indent(text: Optional[str], prefix: str) -> str:
    """Indent each line of text with the given prefix.

    Args:
        text: Text to indent
        prefix: Prefix to add to each line

    Returns:
        Indented text
    """
    if not text:
        return ""
    return "\n".join(prefix + line for line in text.splitlines())
