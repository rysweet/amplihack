"""Safety checker for legacy skill directory cleanup.

This module determines if a directory is safe to delete during staging cleanup.
Uses conservative safety checks to prevent data loss.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .known_skills import is_amplihack_skill

logger = logging.getLogger(__name__)

SafetyStatus = Literal["safe", "unsafe", "uncertain"]


@dataclass
class DirectorySafetyCheck:
    """Result of safety check on a directory."""

    status: SafetyStatus
    reason: str
    custom_skills: list[str] = field(default_factory=list)


def is_safe_to_delete(directory: Path) -> DirectorySafetyCheck:
    """Check if directory contains only amplihack-managed skills.

    Safety Rules (fail-safe):
    - UNSAFE if contains unknown skills (user customizations)
    - UNSAFE if directory is symlink
    - UNSAFE if directory is git repository (.git present)
    - UNSAFE if contains non-skill files in root
    - UNCERTAIN if directory doesn't exist or can't be read
    - SAFE only if all skills are in AMPLIHACK_SKILLS registry

    Args:
        directory: Path to skills directory to check

    Returns:
        DirectorySafetyCheck with status and reasoning
    """
    # Check 1: Directory must exist
    if not directory.exists():
        return DirectorySafetyCheck(
            status="uncertain",
            reason="Directory does not exist",
        )

    # Check 2: Must not be a symlink (security)
    if directory.is_symlink():
        return DirectorySafetyCheck(
            status="unsafe",
            reason="Directory is a symlink",
        )

    # Check 3: Must be readable
    try:
        list(directory.iterdir())
    except (PermissionError, OSError) as e:
        return DirectorySafetyCheck(
            status="uncertain",
            reason=f"Cannot read directory: {e}",
        )

    # Check 4: Must not be a git repository
    if (directory / ".git").exists():
        return DirectorySafetyCheck(
            status="unsafe",
            reason="Directory is a git repository",
        )

    # Check 5: All subdirectories must be amplihack skills
    custom_skills = []
    for item in directory.iterdir():
        # Skip hidden files except .git (already checked)
        if item.name.startswith("."):
            if item.name != ".gitkeep":  # .gitkeep is safe
                return DirectorySafetyCheck(
                    status="unsafe",
                    reason=f"Contains hidden file: {item.name}",
                )
            continue

        # Must be a directory (skill)
        if not item.is_dir():
            return DirectorySafetyCheck(
                status="unsafe",
                reason=f"Contains non-directory file: {item.name}",
            )

        # Check if it's an amplihack skill
        if not is_amplihack_skill(item.name):
            custom_skills.append(item.name)

    # If custom skills found, unsafe to delete
    if custom_skills:
        return DirectorySafetyCheck(
            status="unsafe",
            reason=f"Contains custom skills: {', '.join(custom_skills)}",
            custom_skills=custom_skills,
        )

    # All checks passed - safe to delete
    return DirectorySafetyCheck(
        status="safe",
        reason="Contains only amplihack-managed skills",
    )
