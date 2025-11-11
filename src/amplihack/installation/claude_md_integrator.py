"""Integrate Amplihack import into user's CLAUDE.md.

This module handles adding/removing the Amplihack import statement to/from
the user's CLAUDE.md file, with backup management.
"""

import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class IntegrationResult:
    """Result of CLAUDE.md integration.

    Attributes:
        success: True if operation completed successfully
        action_taken: What action was performed (added, already_present, created_new, removed, error)
        preview: Preview of changes (what will/did change)
        backup_path: Path to backup file if created
        error: Error message if operation failed
    """

    success: bool
    action_taken: str
    preview: str = ""
    backup_path: Optional[Path] = None
    error: Optional[str] = None


# Import statement format
IMPORT_STATEMENT = "@.claude/amplihack/CLAUDE.md"


def _has_import(content: str) -> bool:
    """Check if import statement is already present.

    Args:
        content: Content of CLAUDE.md file

    Returns:
        True if import statement found (accounting for whitespace variations)
    """
    # Match import with optional whitespace
    pattern = r"^\s*@\.claude/amplihack/CLAUDE\.md\s*$"
    return bool(re.search(pattern, content, re.MULTILINE))


def _create_backup(file_path: Path) -> Optional[Path]:
    """Create timestamped backup of file.

    Args:
        file_path: File to back up

    Returns:
        Path to backup file, or None if backup failed
    """
    if not file_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.parent / f"{file_path.name}.backup.{timestamp}"

    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except (OSError, PermissionError):
        return None


def _rotate_backups(file_path: Path, keep: int = 3):
    """Keep only the most recent N backups.

    Args:
        file_path: Original file whose backups to rotate
        keep: Number of most recent backups to keep
    """
    backup_pattern = f"{file_path.name}.backup.*"
    backups = sorted(
        file_path.parent.glob(backup_pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Remove old backups beyond keep limit
    for old_backup in backups[keep:]:
        try:
            old_backup.unlink()
        except OSError:
            pass  # Ignore errors during cleanup


def integrate_import(
    claude_md_path: Path,
    namespace_path: str = ".claude/amplihack/CLAUDE.md",
    dry_run: bool = False,
) -> IntegrationResult:
    """Add Amplihack import to CLAUDE.md.

    Args:
        claude_md_path: Path to user's CLAUDE.md file
        namespace_path: Import target path (for future customization)
        dry_run: If True, preview changes without writing

    Returns:
        IntegrationResult with details of what was done

    Example:
        >>> result = integrate_import(Path(".claude/CLAUDE.md"))
        >>> assert result.success
        >>> assert result.action_taken in ["added", "already_present"]
    """
    # Check if file exists
    file_exists = claude_md_path.exists()

    if file_exists:
        try:
            content = claude_md_path.read_text(encoding="utf-8")
        except (OSError, PermissionError) as e:
            return IntegrationResult(
                success=False,
                action_taken="error",
                error=f"Cannot read file: {e}",
            )

        # Check if import already present
        if _has_import(content):
            return IntegrationResult(
                success=True,
                action_taken="already_present",
                preview="Import statement already exists in CLAUDE.md",
            )

        # Add import at the top (after any frontmatter)
        lines = content.split("\n")
        insert_index = 0

        # Skip YAML frontmatter if present
        if lines and lines[0].strip() == "---":
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    insert_index = i + 1
                    break

        # Insert import with blank line after
        lines.insert(insert_index, IMPORT_STATEMENT)
        lines.insert(insert_index + 1, "")
        new_content = "\n".join(lines)

        preview = f"Adding import at line {insert_index + 1}:\n\n{IMPORT_STATEMENT}\n"

    else:
        # Create new file with just the import
        new_content = f"# CLAUDE.md\n\n{IMPORT_STATEMENT}\n"
        preview = "Creating new CLAUDE.md with import statement"

    # Return preview in dry run mode
    if dry_run:
        return IntegrationResult(
            success=True,
            action_taken="preview",
            preview=preview,
        )

    # Create backup before modifying
    backup_path = None
    if file_exists:
        backup_path = _create_backup(claude_md_path)

    # Write updated content
    try:
        # Ensure parent directory exists
        claude_md_path.parent.mkdir(parents=True, exist_ok=True)

        claude_md_path.write_text(new_content, encoding="utf-8")

        # Rotate backups
        if file_exists:
            _rotate_backups(claude_md_path)

        action = "created_new" if not file_exists else "added"

        return IntegrationResult(
            success=True,
            action_taken=action,
            preview=preview,
            backup_path=backup_path,
        )

    except (OSError, PermissionError) as e:
        return IntegrationResult(
            success=False,
            action_taken="error",
            preview=preview,
            error=f"Failed to write file: {e}",
        )


def remove_import(
    claude_md_path: Path,
    dry_run: bool = False,
) -> IntegrationResult:
    """Remove Amplihack import from CLAUDE.md.

    Args:
        claude_md_path: Path to user's CLAUDE.md file
        dry_run: If True, preview changes without writing

    Returns:
        IntegrationResult with details of what was done

    Example:
        >>> result = remove_import(Path(".claude/CLAUDE.md"))
        >>> assert result.success
    """
    if not claude_md_path.exists():
        return IntegrationResult(
            success=True,
            action_taken="not_present",
            preview="CLAUDE.md does not exist",
        )

    try:
        content = claude_md_path.read_text(encoding="utf-8")
    except (OSError, PermissionError) as e:
        return IntegrationResult(
            success=False,
            action_taken="error",
            error=f"Cannot read file: {e}",
        )

    # Check if import is present
    if not _has_import(content):
        return IntegrationResult(
            success=True,
            action_taken="not_present",
            preview="Import statement not found in CLAUDE.md",
        )

    # Remove import line
    pattern = r"^\s*@\.claude/amplihack/CLAUDE\.md\s*$"
    new_content = re.sub(pattern, "", content, flags=re.MULTILINE)

    # Clean up any resulting double blank lines
    new_content = re.sub(r"\n\n\n+", "\n\n", new_content)

    preview = "Removing import statement:\n\n" + IMPORT_STATEMENT

    # Return preview in dry run mode
    if dry_run:
        return IntegrationResult(
            success=True,
            action_taken="preview",
            preview=preview,
        )

    # Create backup before modifying
    backup_path = _create_backup(claude_md_path)

    # Write updated content
    try:
        claude_md_path.write_text(new_content, encoding="utf-8")

        # Rotate backups
        _rotate_backups(claude_md_path)

        return IntegrationResult(
            success=True,
            action_taken="removed",
            preview=preview,
            backup_path=backup_path,
        )

    except (OSError, PermissionError) as e:
        return IntegrationResult(
            success=False,
            action_taken="error",
            preview=preview,
            error=f"Failed to write file: {e}",
        )
