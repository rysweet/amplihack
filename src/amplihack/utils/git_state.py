"""Git state validation utilities for automode safety.

This module provides git repository state checking to prevent data loss
when running automode with uncommitted changes.

Strategy 3 Implementation (Issue #1090):
- Check git status before automode starts
- Error if uncommitted changes exist
- Suggest commit or stash workflow
- Provide --allow-dirty override for advanced users
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class GitStatus:
    """Git repository status information."""

    is_repo: bool
    is_dirty: bool
    staged_files: List[str]
    unstaged_files: List[str]
    untracked_files: List[str]
    branch: Optional[str]

    @property
    def has_changes(self) -> bool:
        """Check if repository has any changes."""
        return bool(self.staged_files or self.unstaged_files or self.untracked_files)

    @property
    def change_summary(self) -> str:
        """Get human-readable summary of changes."""
        parts = []
        if self.staged_files:
            parts.append(f"{len(self.staged_files)} staged")
        if self.unstaged_files:
            parts.append(f"{len(self.unstaged_files)} modified")
        if self.untracked_files:
            parts.append(f"{len(self.untracked_files)} untracked")
        return ", ".join(parts) if parts else "no changes"


class GitStateError(Exception):
    """Raised when git state validation fails."""

    pass


def _run_git_command(args: List[str], cwd: Path) -> Tuple[int, str, str]:
    """Run git command and return exit code, stdout, stderr.

    Args:
        args: Git command arguments (without 'git' prefix)
        cwd: Working directory

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        raise GitStateError("Git command timed out (>10s)")
    except FileNotFoundError:
        raise GitStateError("Git command not found. Is git installed?")
    except Exception as e:
        raise GitStateError(f"Git command failed: {e}")


def check_git_status(working_dir: Optional[Path] = None) -> GitStatus:
    """Check git repository status.

    Args:
        working_dir: Directory to check (defaults to current directory)

    Returns:
        GitStatus object with repository state

    Raises:
        GitStateError: If git commands fail
    """
    if working_dir is None:
        working_dir = Path.cwd()

    working_dir = Path(working_dir).resolve()

    # Check if this is a git repository
    code, stdout, stderr = _run_git_command(["rev-parse", "--git-dir"], working_dir)
    if code != 0:
        return GitStatus(
            is_repo=False,
            is_dirty=False,
            staged_files=[],
            unstaged_files=[],
            untracked_files=[],
            branch=None,
        )

    # Get current branch
    code, stdout, stderr = _run_git_command(["branch", "--show-current"], working_dir)
    branch = stdout.strip() if code == 0 else None

    # Get detailed status with porcelain format for parsing
    code, stdout, stderr = _run_git_command(["status", "--porcelain"], working_dir)
    if code != 0:
        raise GitStateError(f"Failed to get git status: {stderr}")

    staged = []
    unstaged = []
    untracked = []

    # Parse porcelain output
    # Format: XY filename
    # X = staged status, Y = unstaged status
    # ' ' = unmodified, M = modified, A = added, D = deleted, R = renamed, C = copied
    # ? = untracked, ! = ignored
    for line in stdout.splitlines():
        if not line:
            continue

        status_code = line[:2]
        filename = line[3:]

        # Staged changes (X position)
        if status_code[0] in "MADRC":
            staged.append(filename)

        # Unstaged changes (Y position)
        if status_code[1] in "MADRC":
            unstaged.append(filename)

        # Untracked files
        if status_code == "??":
            untracked.append(filename)

    is_dirty = bool(staged or unstaged or untracked)

    return GitStatus(
        is_repo=True,
        is_dirty=is_dirty,
        staged_files=staged,
        unstaged_files=unstaged,
        untracked_files=untracked,
        branch=branch,
    )


def validate_clean_state(
    working_dir: Optional[Path] = None, allow_dirty: bool = False
) -> None:
    """Validate that git repository is in clean state for automode.

    Args:
        working_dir: Directory to check (defaults to current directory)
        allow_dirty: If True, skip validation (for advanced users)

    Raises:
        GitStateError: If repository has uncommitted changes (unless allow_dirty=True)
    """
    if allow_dirty:
        # User explicitly requested to skip validation
        return

    status = check_git_status(working_dir)

    # If not a git repo, that's fine - user might be working outside version control
    if not status.is_repo:
        return

    # If repo is clean, proceed
    if not status.is_dirty:
        return

    # Dirty repo - build helpful error message
    error_lines = [
        "Error: Cannot run automode with uncommitted changes.",
        "",
        "Git Status:",
    ]

    if status.staged_files:
        error_lines.append(f"  Staged: {len(status.staged_files)} file(s)")
        for f in status.staged_files[:5]:  # Show first 5
            error_lines.append(f"    - {f}")
        if len(status.staged_files) > 5:
            error_lines.append(f"    ... and {len(status.staged_files) - 5} more")

    if status.unstaged_files:
        error_lines.append(f"  Modified: {len(status.unstaged_files)} file(s)")
        for f in status.unstaged_files[:5]:  # Show first 5
            error_lines.append(f"    - {f}")
        if len(status.unstaged_files) > 5:
            error_lines.append(f"    ... and {len(status.unstaged_files) - 5} more")

    if status.untracked_files:
        error_lines.append(f"  Untracked: {len(status.untracked_files)} file(s)")
        for f in status.untracked_files[:5]:  # Show first 5
            error_lines.append(f"    - {f}")
        if len(status.untracked_files) > 5:
            error_lines.append(f"    ... and {len(status.untracked_files) - 5} more")

    error_lines.extend(
        [
            "",
            "Why This Matters:",
            "  Automode modifies files in .claude/ and can conflict with uncommitted work.",
            "  This check prevents data loss from file conflicts.",
            "",
            "Solutions:",
            "  1. Commit changes:     git add -A && git commit -m 'WIP: before automode'",
            "  2. Stash changes:      git stash",
            "  3. Use git worktree:   git worktree add ./worktrees/automode -b automode-task",
            "",
            "Override (Advanced):",
            "  If you know what you're doing: --allow-dirty",
            "",
        ]
    )

    raise GitStateError("\n".join(error_lines))


def format_status_summary(status: GitStatus) -> str:
    """Format git status as human-readable string.

    Args:
        status: GitStatus object

    Returns:
        Formatted status string
    """
    if not status.is_repo:
        return "Not a git repository"

    if not status.is_dirty:
        branch_info = f" (branch: {status.branch})" if status.branch else ""
        return f"Clean working directory{branch_info}"

    branch_info = f" on {status.branch}" if status.branch else ""
    return f"Uncommitted changes{branch_info}: {status.change_summary}"
