"""Shared utilities for amplihack hook modules.

Provides common functionality used across multiple hooks to avoid duplication.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_user_preferences() -> str | None:
    """Load user preferences from standard locations.

    Searches in order:
    1. ./USER_PREFERENCES.md (project root)
    2. ./.claude/context/USER_PREFERENCES.md (Claude Code standard)
    3. ~/.claude/USER_PREFERENCES.md (global user preferences)

    Returns:
        Preferences content as string, or None if not found.
    """
    prefs_paths = [
        Path.cwd() / "USER_PREFERENCES.md",
        Path.cwd() / ".claude" / "context" / "USER_PREFERENCES.md",
        Path.home() / ".claude" / "USER_PREFERENCES.md",
    ]

    for path in prefs_paths:
        if path.exists():
            try:
                return path.read_text()
            except Exception as e:
                logger.debug(f"Failed to read preferences from {path}: {e}")
                continue
    return None


def load_project_context() -> str | None:
    """Load project-specific context files.

    Searches for philosophy, patterns, and main CLAUDE.md files.

    Returns:
        Combined context as string, or None if nothing found.
    """
    context_paths = [
        Path.cwd() / ".claude" / "context" / "PHILOSOPHY.md",
        Path.cwd() / ".claude" / "context" / "PATTERNS.md",
        Path.cwd() / "CLAUDE.md",
    ]

    context_parts = []
    for path in context_paths:
        if path.exists():
            try:
                content = path.read_text()
                context_parts.append(f"## {path.name}\n{content}")
            except Exception as e:
                logger.debug(f"Failed to read context from {path}: {e}")

    return "\n\n".join(context_parts) if context_parts else None


def get_claude_hooks_path() -> Path | None:
    """Get the path to Claude Code hooks directory.

    Walks up from current directory to find project root with .claude/tools/amplihack/hooks.

    Returns:
        Path to hooks directory, or None if not found.
    """
    current = Path.cwd()

    # Try current directory first
    hooks_path = current / ".claude" / "tools" / "amplihack" / "hooks"
    if hooks_path.exists():
        return hooks_path

    # Walk up parent directories
    for parent in current.parents:
        hooks_path = parent / ".claude" / "tools" / "amplihack" / "hooks"
        if hooks_path.exists():
            return hooks_path

    return None


__all__ = ["load_user_preferences", "load_project_context", "get_claude_hooks_path"]
