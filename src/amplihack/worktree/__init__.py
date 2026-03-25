"""Worktree detection and shared runtime directory resolution.

Public API:
    get_shared_runtime_dir: Returns shared .claude/runtime directory path
"""

from .git_utils import get_shared_runtime_dir

__all__ = ["get_shared_runtime_dir"]
