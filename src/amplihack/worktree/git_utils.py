"""Git utilities for worktree detection and shared runtime directory resolution.

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

Security:
    - AMPLIHACK_RUNTIME_DIR env-var overrides the computed path. The path is
      validated to be within the user's home directory or /tmp; any path
      outside those roots raises RuntimeError to prevent path-injection attacks.
    - Runtime directories are created with chmod 0o700 (owner-only) so that
      sensitive power-steering state is not world-readable on shared systems.
"""

import logging
import os
import subprocess
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["get_shared_runtime_dir"]


def _validate_env_runtime_dir(path: Path) -> None:
    """Validate that AMPLIHACK_RUNTIME_DIR is within an allowed root.

    Allowed roots are the user's home directory and /tmp.  Path traversal
    sequences (e.g. ``../../etc``) are resolved before the check so that
    ``~/../../etc/passwd`` is correctly rejected.

    Args:
        path: The path supplied via AMPLIHACK_RUNTIME_DIR.

    Raises:
        RuntimeError: If the resolved path is outside home directory or /tmp.
    """
    resolved = path.resolve()
    home_resolved = Path.home().resolve()
    tmp_resolved = Path("/tmp").resolve()

    for allowed_root in (home_resolved, tmp_resolved):
        try:
            resolved.relative_to(allowed_root)
            return  # Within this allowed root — accept
        except ValueError:
            continue

    raise RuntimeError(
        f"AMPLIHACK_RUNTIME_DIR={str(path)!r} resolves to {str(resolved)!r}, "
        f"which is outside allowed roots ({home_resolved} or {tmp_resolved}). "
        "Set AMPLIHACK_RUNTIME_DIR to a path within your home directory or /tmp."
    )


def _create_runtime_dir_secure(path: Path) -> None:
    """Create the runtime directory with owner-only (0o700) permissions.

    Creates the directory and all missing parents.  After creation each level
    is explicitly chmod'd so the result is independent of the process umask.

    The final ``runtime`` directory receives mode 0o700.  The parent
    ``.claude`` directory has world-write (0o002) removed so it is never
    world-writable, even when the system umask is permissive.

    Args:
        path: Full path to the runtime directory (e.g. ``/project/.claude/runtime``).
    """
    path.mkdir(parents=True, exist_ok=True)

    # Harden the runtime dir itself to owner-only.
    os.chmod(path, 0o700)

    # Ensure the intermediate .claude parent is not world-writable.
    parent = path.parent
    if parent.exists():
        current_mode = os.stat(parent).st_mode & 0o777
        if current_mode & 0o002:  # world-writable bit set
            os.chmod(parent, current_mode & ~0o002)


@lru_cache(maxsize=128)
def get_shared_runtime_dir(project_root: str | Path) -> str:
    """Get the shared runtime directory for power-steering state.

    In git worktrees, power-steering state should be shared with the main repo
    to ensure consistent behavior across all worktrees. This function detects
    worktree scenarios and returns the appropriate runtime directory.

    Algorithm:
    1. If AMPLIHACK_RUNTIME_DIR env-var is set, validate and return it.
    2. Run ``git rev-parse --git-common-dir`` to detect worktree.
    3. If in worktree, resolve main repo and return main_repo/.claude/runtime.
    4. If in main repo (or git command fails), return project_root/.claude/runtime.
    5. Create the resolved directory with chmod 0o700.

    Args:
        project_root: Project root directory (as string or Path).

    Returns:
        Path to shared runtime directory (as string).  The directory is
        guaranteed to exist when this function returns (unless the
        AMPLIHACK_RUNTIME_DIR override is used, in which case the caller
        controls creation).

    Raises:
        RuntimeError: When AMPLIHACK_RUNTIME_DIR is set to a path outside
            the user's home directory or /tmp.

    Examples:
        # Main repo (non-worktree)
        >>> get_shared_runtime_dir("/home/user/project")
        '/home/user/project/.claude/runtime'

        # Worktree
        >>> get_shared_runtime_dir("/home/user/project/worktrees/feat-branch")
        '/home/user/project/.claude/runtime'  # Main repo's runtime dir

    Fail-Open Behavior:
        If git commands fail for any reason (not a git repo, git not installed,
        timeout, etc.), falls back to project_root/.claude/runtime.  This
        ensures the hook never crashes due to git issues.

    Security:
        AMPLIHACK_RUNTIME_DIR is validated before use.  Paths outside home
        or /tmp raise RuntimeError rather than silently accepting them.
        Created directories use chmod 0o700 (owner-only).
    """
    # --- P1: Environment variable override ---
    env_override = os.environ.get("AMPLIHACK_RUNTIME_DIR")
    if env_override:
        env_path = Path(env_override)
        _validate_env_runtime_dir(env_path)  # raises RuntimeError if invalid
        return str(env_path)

    project_path = Path(project_root).resolve()
    default_runtime = project_path / ".claude" / "runtime"

    try:
        # Use git rev-parse --git-common-dir to detect worktree.
        # In worktrees: returns path to main repo's .git directory.
        # In main repo: returns .git (relative) or full path to .git.
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=5,
            check=False,  # Don't raise on non-zero exit
        )

        if result.returncode != 0:
            # Not a git repo or command failed — use default.
            runtime_path = default_runtime
        else:
            git_common_dir = result.stdout.strip()
            if not git_common_dir:
                # Empty output — use default.
                runtime_path = default_runtime
            else:
                git_common_path = Path(git_common_dir)

                # Make it absolute if relative.
                if not git_common_path.is_absolute():
                    git_common_path = (project_path / git_common_path).resolve()

                # Compare against the expected .git in our project root.
                expected_main_git = project_path / ".git"

                # If git_common_dir points to a .git directory outside our
                # project_root, we're in a worktree.
                if git_common_path.resolve() != expected_main_git.resolve():
                    # We're in a worktree — find the main repo root.
                    # git_common_dir is typically main_repo/.git, so parent is main_repo.
                    if git_common_path.name == ".git":
                        main_repo_root = git_common_path.parent
                    else:
                        # Some git configurations return the bare repo path
                        # (not ending in .git); treat it directly as main_repo.
                        main_repo_root = git_common_path

                    runtime_path = main_repo_root / ".claude" / "runtime"
                else:
                    # We're in the main repo — use default.
                    runtime_path = default_runtime

    except Exception as e:
        # Fail-open: Any error (timeout, git not found, invalid path, etc.)
        # → return default. Always log so the error is never invisible.
        logger.warning("git worktree detection failed: %s", e)
        runtime_path = default_runtime

    # --- P2: Create directory with owner-only permissions ---
    _create_runtime_dir_secure(runtime_path)

    return str(runtime_path)
