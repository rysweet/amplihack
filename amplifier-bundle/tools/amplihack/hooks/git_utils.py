#!/usr/bin/env python3
"""
Git utilities for worktree detection and shared runtime directory resolution.

Provides functions to detect git worktrees and resolve shared runtime directories
that should be used across main repo and all worktrees.

Philosophy:
- Ruthlessly Simple: Single-purpose module with clear contract
- Fail-Open: Never crash - always provide fallback path
- Zero-BS: No stubs, every function works
- Modular: Self-contained brick with standard library only

Public API (the "studs"):
    get_shared_runtime_dir(project_root: str | Path) -> str
        Returns the shared .claude/runtime directory path that should be used
        for power-steering state and semaphores. In worktrees, this returns
        the main repo's runtime directory. In main repos, returns the project's
        runtime directory.
"""

import subprocess
from functools import lru_cache
from pathlib import Path

__all__ = ["get_shared_runtime_dir"]


@lru_cache(maxsize=128)
def get_shared_runtime_dir(project_root: str | Path) -> str:
    """
    Get the shared runtime directory for power-steering state.

    In git worktrees, power-steering state should be shared with the main repo
    to ensure consistent behavior across all worktrees. This function detects
    worktree scenarios and returns the appropriate runtime directory.

    Algorithm:
    1. Run `git rev-parse --git-common-dir` to detect worktree
    2. If in worktree, resolve main repo and return main_repo/.claude/runtime
    3. If in main repo (or git command fails), return project_root/.claude/runtime

    Args:
        project_root: Project root directory (as string or Path)

    Returns:
        Path to shared runtime directory (as string)

    Examples:
        # Main repo (non-worktree)
        >>> get_shared_runtime_dir("/home/user/project")
        '/home/user/project/.claude/runtime'

        # Worktree
        >>> get_shared_runtime_dir("/home/user/project/worktrees/feat-branch")
        '/home/user/project/.claude/runtime'  # Main repo's runtime dir

    Fail-Open Behavior:
        If git commands fail for any reason (not a git repo, git not installed,
        timeout, etc.), falls back to project_root/.claude/runtime. This ensures
        the hook never crashes due to git issues.
    """
    project_path = Path(project_root).resolve()
    default_runtime = project_path / ".claude" / "runtime"

    try:
        # Use git rev-parse --git-common-dir to detect worktree
        # In worktrees: returns path to main repo's .git directory
        # In main repo: returns .git (relative) or full path to .git
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,  # Don't raise on non-zero exit
        )

        if result.returncode != 0:
            # Not a git repo or command failed - use default
            return str(default_runtime)

        git_common_dir = result.stdout.strip()
        if not git_common_dir:
            # Empty output - use default
            return str(default_runtime)

        git_common_path = Path(git_common_dir)

        # Make it absolute if relative
        if not git_common_path.is_absolute():
            git_common_path = (project_path / git_common_path).resolve()

        # Normalize both paths for comparison
        project_path_normalized = project_path.resolve()
        expected_main_git = project_path_normalized / ".git"

        # If git_common_dir points to a .git directory outside our project_root,
        # we're in a worktree
        if git_common_path.resolve() != expected_main_git.resolve():
            # We're in a worktree - find the main repo root
            # git_common_dir is typically main_repo/.git, so parent is main_repo
            if git_common_path.name == ".git":
                main_repo_root = git_common_path.parent
            else:
                # If the path doesn't end in .git, assume it's the main repo root
                # (test mocking may return this directly)
                main_repo_root = git_common_path

            return str(main_repo_root / ".claude" / "runtime")

        # We're in main repo - use default
        return str(default_runtime)

    except Exception:
        # Fail-open: Any error (timeout, git not found, invalid path, etc.) → return default
        return str(default_runtime)
