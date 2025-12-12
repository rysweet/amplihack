"""CLAUDE.md preservation module for amplihack installations.

Philosophy:
- Ruthless simplicity: Clear state detection and backup logic
- Zero-BS implementation: Every function works or doesn't exist
- Brick design: Self-contained module with clear public API
- Standard library only: No internal amplihack dependencies

Public API (the "studs"):
    ClaudeState: Enum for CLAUDE.md states
    HandleMode: Enum for handling modes
    ActionTaken: Enum for actions taken
    ClaudeHandlerResult: Result dataclass
    detect_claude_state: Detect current CLAUDE.md state
    handle_claude_md: Main handler for CLAUDE.md preservation
    compute_content_hash: Compute SHA-256 hash of content
    backup_to_project_md: Backup to PROJECT.md with section markers
    backup_to_preserved: Backup to CLAUDE.md.preserved

This module mirrors the pattern from project_initializer.py
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Version marker to identify amplihack's CLAUDE.md
CLAUDE_VERSION_MARKER = "<!-- amplihack-version:"
CURRENT_VERSION = "0.9.0"

# Section markers for PROJECT.md preservation
BEGIN_MARKER = "<!-- BEGIN AMPLIHACK-PRESERVED-CONTENT"
END_MARKER = "<!-- END AMPLIHACK-PRESERVED-CONTENT -->"

__all__ = [
    "ClaudeState",
    "HandleMode",
    "ActionTaken",
    "ClaudeHandlerResult",
    "detect_claude_state",
    "handle_claude_md",
    "compute_content_hash",
    "backup_to_project_md",
    "backup_to_preserved",
]


class ClaudeState(Enum):
    """State of CLAUDE.md file."""

    MISSING = "missing"  # No CLAUDE.md exists
    VALID = "valid"  # Current amplihack version
    OUTDATED = "outdated"  # Older amplihack version
    CUSTOM_CONTENT = "custom"  # User's custom CLAUDE.md


class HandleMode(Enum):
    """Handling mode for CLAUDE.md preservation."""

    AUTO = "auto"  # Normal installation behavior
    FORCE = "force"  # Override even custom content
    CHECK = "check"  # Only check state, don't modify


class ActionTaken(Enum):
    """Actions taken during CLAUDE.md handling."""

    DEPLOYED = "deployed"  # Deployed amplihack's CLAUDE.md
    BACKED_UP_AND_REPLACED = "backed_up_and_replaced"  # Backed up and replaced
    SKIPPED = "skipped"  # Skipped (already preserved)
    CHECK_ONLY = "check_only"  # Only checked state


@dataclass
class ClaudeHandlerResult:
    """Result of CLAUDE.md handling operation."""

    action_taken: ActionTaken
    state: ClaudeState
    backup_path: Path | None
    message: str
    success: bool = True


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content, ignoring whitespace-only changes.

    Args:
        content: Content to hash

    Returns:
        SHA-256 hash as hex string
    """
    # Normalize whitespace: strip trailing spaces, normalize line endings
    lines = content.split("\n")
    normalized_lines = [line.rstrip() for line in lines]
    # Remove empty lines at start and end
    while normalized_lines and not normalized_lines[0]:
        normalized_lines.pop(0)
    while normalized_lines and not normalized_lines[-1]:
        normalized_lines.pop()
    normalized = "\n".join(normalized_lines)

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def detect_claude_state(target_dir: Path) -> tuple[ClaudeState, str]:
    """Detect current state of CLAUDE.md in target directory.

    Args:
        target_dir: Directory where CLAUDE.md should exist (project root)

    Returns:
        Tuple of (state, reason)
    """
    # Resolve path to prevent directory traversal attacks
    target_dir = target_dir.resolve()
    claude_md = target_dir / "CLAUDE.md"

    # Check if file exists
    if not claude_md.exists():
        return ClaudeState.MISSING, "CLAUDE.md not found"

    # Check for symlink attack - treat symlinks as custom content to preserve
    if claude_md.is_symlink():
        logger.warning("CLAUDE.md is a symlink - treating as custom")
        return ClaudeState.CUSTOM_CONTENT, "Symlink detected (security)"

    try:
        content = claude_md.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to read CLAUDE.md: {e}")
        # Treat unreadable as custom to preserve it
        return ClaudeState.CUSTOM_CONTENT, f"Unreadable file (will preserve): {e}"

    # Check for version marker
    if CLAUDE_VERSION_MARKER not in content:
        return ClaudeState.CUSTOM_CONTENT, "No version marker (user modified)"

    # Extract version from marker
    # Expected format: <!-- amplihack-version: 0.9.0 -->
    # This parsing logic extracts the version string between the marker and the closing comment
    try:
        # Find the line containing the version marker
        marker_line = [line for line in content.split("\n") if CLAUDE_VERSION_MARKER in line][0]

        # Split on the marker to get the part after "<!-- amplihack-version:"
        # Then split on "-->" to get just the version string
        # Finally strip whitespace to get clean version
        version_str = marker_line.split(CLAUDE_VERSION_MARKER)[1].split("-->")[0].strip()

        # Compare extracted version with current version
        if version_str == CURRENT_VERSION:
            return ClaudeState.VALID, f"Version {version_str} matches current"
        return ClaudeState.OUTDATED, f"Version {version_str} < {CURRENT_VERSION}"
    except (IndexError, ValueError) as e:
        # If parsing fails (malformed marker), treat as custom content to preserve
        logger.warning(f"Failed to parse version marker: {e}")
        return ClaudeState.CUSTOM_CONTENT, "Invalid version marker (user modified)"


def backup_to_project_md(target_dir: Path, content: str) -> Path:
    """Backup CLAUDE.md content to PROJECT.md with section markers.

    Args:
        target_dir: Target directory (project root)
        content: Content to backup

    Returns:
        Path to PROJECT.md
    """
    # Resolve path to prevent directory traversal attacks
    target_dir = target_dir.resolve()
    project_md = target_dir / ".claude" / "context" / "PROJECT.md"
    project_md.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()

    # Check if PROJECT.md exists
    if project_md.exists():
        existing_content = project_md.read_text(encoding="utf-8")

        # Check if already preserved (idempotent)
        if BEGIN_MARKER in existing_content:
            logger.info("CLAUDE.md content already preserved in PROJECT.md")
            return project_md

        # Append to existing content
        section = f"\n\n---\n{BEGIN_MARKER} {timestamp} -->\nPreserved from original CLAUDE.md\n\n{content}\n{END_MARKER}\n---\n"
        new_content = existing_content + section
    else:
        # Create new PROJECT.md with preserved content
        section = f"{BEGIN_MARKER} {timestamp} -->\nPreserved from original CLAUDE.md\n\n{content}\n{END_MARKER}\n"
        new_content = f"""# Project Context

**This file provides project-specific context to Claude Code agents.**

---

{section}"""

    project_md.write_text(new_content, encoding="utf-8")
    logger.info(f"Backed up CLAUDE.md to PROJECT.md at {timestamp}")

    return project_md


def backup_to_preserved(target_dir: Path, content: str) -> Path:
    """Create backup copy of CLAUDE.md as CLAUDE.md.preserved.

    Args:
        target_dir: Target directory (project root)
        content: Content to backup

    Returns:
        Path to preserved backup
    """
    # Resolve path to prevent directory traversal attacks
    target_dir = target_dir.resolve()
    preserved_path = target_dir / ".claude" / "context" / "CLAUDE.md.preserved"
    preserved_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()

    # Add timestamp header
    preserved_content = f"""# Preserved CLAUDE.md Content
# Original file preserved on: {timestamp}
# This file contains your original CLAUDE.md before amplihack installation

{content}"""

    preserved_path.write_text(preserved_content, encoding="utf-8")
    logger.info(f"Created preserved backup at {preserved_path}")

    return preserved_path


def handle_claude_md(
    source_claude: Path, target_dir: Path, mode: HandleMode = HandleMode.AUTO
) -> ClaudeHandlerResult:
    """Handle CLAUDE.md deployment with preservation logic.

    Args:
        source_claude: Path to amplihack's CLAUDE.md
        target_dir: Target directory (project root, not .claude/)
        mode: Handling mode (AUTO, FORCE, CHECK)

    Returns:
        ClaudeHandlerResult with action taken and details
    """
    # Detect current state
    state, reason = detect_claude_state(target_dir)

    logger.debug(f"Detected CLAUDE.md state: {state.value} - {reason}")

    # CHECK mode: just report state
    if mode == HandleMode.CHECK:
        return ClaudeHandlerResult(
            action_taken=ActionTaken.CHECK_ONLY,
            state=state,
            backup_path=None,
            message=f"State: {state.value} - {reason}",
            success=True,
        )

    target_claude = target_dir / "CLAUDE.md"

    # State: MISSING - just deploy
    if state == ClaudeState.MISSING:
        try:
            source_content = source_claude.read_text(encoding="utf-8")
            target_claude.write_text(source_content, encoding="utf-8")
            logger.info("Deployed amplihack's CLAUDE.md (no existing file)")
            return ClaudeHandlerResult(
                action_taken=ActionTaken.DEPLOYED,
                state=state,
                backup_path=None,
                message="Installed amplihack CLAUDE.md",
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to deploy CLAUDE.md: {e}")
            return ClaudeHandlerResult(
                action_taken=ActionTaken.SKIPPED,
                state=state,
                backup_path=None,
                message=f"Failed to deploy: {e}",
                success=False,
            )

    # State: VALID - check if already preserved (idempotent)
    if state == ClaudeState.VALID:
        preserved_file = target_dir / ".claude" / "context" / "CLAUDE.md.preserved"
        if preserved_file.exists():
            return ClaudeHandlerResult(
                action_taken=ActionTaken.SKIPPED,
                state=state,
                backup_path=preserved_file,
                message="Custom CLAUDE.md already preserved (idempotent)",
                success=True,
            )

        # Valid version, no backup needed
        return ClaudeHandlerResult(
            action_taken=ActionTaken.SKIPPED,
            state=state,
            backup_path=None,
            message="CLAUDE.md is current version",
            success=True,
        )

    # State: OUTDATED - update without backup (unless FORCE mode)
    if state == ClaudeState.OUTDATED and mode != HandleMode.FORCE:
        try:
            source_content = source_claude.read_text(encoding="utf-8")
            target_claude.write_text(source_content, encoding="utf-8")
            logger.info("Updated outdated amplihack CLAUDE.md")
            return ClaudeHandlerResult(
                action_taken=ActionTaken.DEPLOYED,
                state=state,
                backup_path=None,
                message="Updated outdated amplihack CLAUDE.md",
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to update CLAUDE.md: {e}")
            return ClaudeHandlerResult(
                action_taken=ActionTaken.SKIPPED,
                state=state,
                backup_path=None,
                message=f"Failed to update: {e}",
                success=False,
            )

    # State: CUSTOM_CONTENT - preserve before replacing
    if state == ClaudeState.CUSTOM_CONTENT or mode == HandleMode.FORCE:
        try:
            # Check if already preserved (idempotent)
            preserved_file = target_dir / ".claude" / "context" / "CLAUDE.md.preserved"
            if preserved_file.exists():
                logger.info("Custom CLAUDE.md already preserved")
                return ClaudeHandlerResult(
                    action_taken=ActionTaken.SKIPPED,
                    state=state,
                    backup_path=preserved_file,
                    message="Custom CLAUDE.md already preserved (idempotent)",
                    success=True,
                )

            # Read current content
            current_content = target_claude.read_text(encoding="utf-8")

            # Create both backups
            backup_to_project_md(target_dir, current_content)
            preserved_path = backup_to_preserved(target_dir, current_content)

            # Deploy amplihack's CLAUDE.md
            source_content = source_claude.read_text(encoding="utf-8")
            target_claude.write_text(source_content, encoding="utf-8")

            logger.info("Preserved custom CLAUDE.md and deployed amplihack version")
            return ClaudeHandlerResult(
                action_taken=ActionTaken.BACKED_UP_AND_REPLACED,
                state=state,
                backup_path=preserved_path,
                message="Preserved custom CLAUDE.md content",
                success=True,
            )
        except Exception as e:
            logger.error(f"Failed to preserve and deploy CLAUDE.md: {e}")
            return ClaudeHandlerResult(
                action_taken=ActionTaken.SKIPPED,
                state=state,
                backup_path=None,
                message=f"Failed to preserve: {e}",
                success=False,
            )

    # Should not reach here
    return ClaudeHandlerResult(
        action_taken=ActionTaken.SKIPPED,
        state=state,
        backup_path=None,
        message=f"Unexpected state: {state.value}",
        success=False,
    )
