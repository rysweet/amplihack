"""Git utilities for worktree detection and shared runtime directory resolution.

Provides functions to detect git worktrees and resolve shared runtime directories
that should be used across main repo and all worktrees.

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
    """Get the shared runtime directory for power-steering state.

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

    Raises:
        RuntimeError: If git is not available and no fallback is possible.
    """
    project_path = Path(project_root).resolve()
    default_runtime = project_path / ".claude" / "runtime"

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            return str(default_runtime)

        git_common_dir = result.stdout.strip()
        if not git_common_dir:
            return str(default_runtime)

        git_common_path = Path(git_common_dir)

        if not git_common_path.is_absolute():
            git_common_path = (project_path / git_common_path).resolve()

        project_path_normalized = project_path.resolve()
        expected_main_git = project_path_normalized / ".git"

        if git_common_path.resolve() != expected_main_git.resolve():
            # We're in a worktree - find the main repo root
            if git_common_path.name == ".git":
                main_repo_root = git_common_path.parent
            else:
                main_repo_root = git_common_path

            return str(main_repo_root / ".claude" / "runtime")

        return str(default_runtime)

    except FileNotFoundError:
        # git binary not found — not a git environment, use default
        return str(default_runtime)
    except subprocess.TimeoutExpired:
        # git hung — use default
        return str(default_runtime)
