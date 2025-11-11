"""Detect configuration file conflicts during installation.

This module detects existing files that may conflict with Amplihack installation.
It follows the Brick philosophy: self-contained, single responsibility, clear contract.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class ConflictReport:
    """Report of configuration conflicts.

    Attributes:
        has_conflicts: True if any conflicts detected
        existing_claude_md: True if .claude/CLAUDE.md exists
        existing_agents: Names of custom agent files that conflict
        would_overwrite: Full paths that would be overwritten by root install
        safe_to_namespace: True if namespacing solves all conflicts
    """

    has_conflicts: bool
    existing_claude_md: bool
    existing_agents: List[str] = field(default_factory=list)
    would_overwrite: List[Path] = field(default_factory=list)
    safe_to_namespace: bool = True


def detect_conflicts(target_dir: Path, manifest: List[str]) -> ConflictReport:
    """Detect configuration conflicts in target directory.

    Args:
        target_dir: The .claude directory to check
        manifest: List of files that Amplihack wants to install (relative paths)

    Returns:
        ConflictReport with detected conflicts

    Example:
        >>> report = detect_conflicts(Path(".claude"), ["agents/architect.md"])
        >>> assert report.has_conflicts in [True, False]
    """
    # Handle missing target directory (no conflict)
    if not target_dir.exists():
        return ConflictReport(
            has_conflicts=False,
            existing_claude_md=False,
            safe_to_namespace=True,
        )

    # Handle permission errors gracefully
    try:
        # Check if we can read the directory
        list(target_dir.iterdir())
    except (PermissionError, OSError):
        # Can't read directory - assume no conflicts but warn via flag
        return ConflictReport(
            has_conflicts=True,
            existing_claude_md=False,
            safe_to_namespace=False,
        )

    # Check for CLAUDE.md at root
    claude_md = target_dir / "CLAUDE.md"
    existing_claude_md = claude_md.exists()

    # Check for amplihack namespace (upgrade scenario)
    amplihack_dir = target_dir / "amplihack"
    is_upgrade = amplihack_dir.exists() and amplihack_dir.is_dir()

    # Check for conflicting files
    would_overwrite = []
    existing_agents = []

    for rel_path in manifest:
        target_file = target_dir / rel_path

        # Skip if this is in the amplihack namespace (we expect these in upgrade)
        if "amplihack" in Path(rel_path).parts:
            continue

        # Check if file would be overwritten
        if target_file.exists():
            would_overwrite.append(target_file)

            # Track conflicting agent names
            if rel_path.startswith("agents/") and rel_path.endswith(".md"):
                agent_name = Path(rel_path).stem
                existing_agents.append(agent_name)

    # Determine conflict status
    has_conflicts = existing_claude_md or len(would_overwrite) > 0

    # Namespacing is safe if:
    # 1. It's an upgrade (amplihack dir exists), OR
    # 2. Installing to namespace wouldn't overwrite anything
    safe_to_namespace = is_upgrade or len(would_overwrite) == 0

    return ConflictReport(
        has_conflicts=has_conflicts,
        existing_claude_md=existing_claude_md,
        existing_agents=existing_agents,
        would_overwrite=would_overwrite,
        safe_to_namespace=safe_to_namespace,
    )
