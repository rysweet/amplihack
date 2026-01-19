"""File classification for amplihack update strategy.

This module categorizes framework files into update strategies based on their
role in the system. Each file gets one of three classifications:

- ALWAYS_UPDATE: Core framework files that should always be updated
- PRESERVE_IF_MODIFIED: Files users can customize, preserve if modified
- NEVER_UPDATE: User-generated content that should never be touched

The classification is based on file path patterns and follows the principle
that framework infrastructure should stay updated while user content is
sacred.
"""

from enum import Enum
from pathlib import Path


class FileCategory(Enum):
    """Classification for file update strategies.

    Attributes:
        ALWAYS_UPDATE: Core framework files that should always be updated
        PRESERVE_IF_MODIFIED: User-customizable files, preserve if modified
        NEVER_UPDATE: User-generated content that must never be updated
    """

    ALWAYS_UPDATE = "always"
    PRESERVE_IF_MODIFIED = "preserve"
    NEVER_UPDATE = "never"


def classify_file(file_path: str | Path) -> FileCategory:
    """Categorize a file path into its update strategy.

    Classifies files based on their role in the amplihack framework:

    ALWAYS_UPDATE:
        - agents/amplihack/*.md (framework agents)
        - tools/amplihack/*.py (framework tools, except hooks/*)
        - context/PHILOSOPHY.md, PATTERNS.md, TRUST.md
        - workflow/*.md (framework workflows)

    PRESERVE_IF_MODIFIED:
        - workflow/DEFAULT_WORKFLOW.md (user can customize)
        - context/USER_PREFERENCES.md (user settings)
        - commands/*.md (user can add custom commands)
        - tools/amplihack/hooks/*.py (user can customize)

    NEVER_UPDATE:
        - context/DISCOVERIES.md (project-specific learnings)
        - context/PROJECT.md (project description)
        - docs/* (project documentation)
        - runtime/* (logs, metrics)
        - ai_working/* (experimental tools)
        - scenarios/* (project tools)
        - skills/* (user skills)

    Args:
        file_path: Path to the file to classify (relative or absolute)

    Returns:
        FileCategory indicating the update strategy for this file

    Example:
        >>> classify_file("agents/amplihack/architect.md")
        <FileCategory.ALWAYS_UPDATE: 'always'>
        >>> classify_file("context/DISCOVERIES.md")
        <FileCategory.NEVER_UPDATE: 'never'>
        >>> classify_file("context/USER_PREFERENCES.md")
        <FileCategory.PRESERVE_IF_MODIFIED: 'preserve'>
    """
    # Normalize path to use forward slashes and remove .claude prefix if present
    path = Path(file_path)
    parts = path.parts

    # Remove leading .claude/ if present for consistent matching
    if parts and parts[0] == ".claude":
        parts = parts[1:]

    # Convert back to string path for pattern matching
    normalized = str(Path(*parts)) if parts else str(path)
    normalized = normalized.replace("\\", "/")  # Ensure forward slashes

    # NEVER_UPDATE: User-generated content
    never_update_patterns = [
        "context/DISCOVERIES.md",
        "context/PROJECT.md",
        "docs/",
        "runtime/",
        "ai_working/",
        "scenarios/",
        "skills/",
    ]

    for pattern in never_update_patterns:
        if pattern.endswith("/"):
            # Directory pattern - check if path starts with it
            if normalized.startswith(pattern) or f"/{pattern}" in f"/{normalized}":
                return FileCategory.NEVER_UPDATE
        else:
            # File pattern - exact match or ends with
            if normalized == pattern or normalized.endswith(f"/{pattern}"):
                return FileCategory.NEVER_UPDATE

    # PRESERVE_IF_MODIFIED: User-customizable framework files
    preserve_patterns = [
        "workflow/DEFAULT_WORKFLOW.md",
        "context/USER_PREFERENCES.md",
        "context/USER_REQUIREMENT_PRIORITY.md",
        "commands/",
        "tools/amplihack/hooks/",
    ]

    for pattern in preserve_patterns:
        if pattern.endswith("/"):
            # Directory pattern
            if normalized.startswith(pattern) or f"/{pattern}" in f"/{normalized}":
                return FileCategory.PRESERVE_IF_MODIFIED
        else:
            # File pattern
            if normalized == pattern or normalized.endswith(f"/{pattern}"):
                return FileCategory.PRESERVE_IF_MODIFIED

    # ALWAYS_UPDATE: Core framework infrastructure
    always_update_patterns = [
        "agents/amplihack/",
        "tools/amplihack/",  # General tools (except hooks which were already caught)
        "context/PHILOSOPHY.md",
        "context/PATTERNS.md",
        "context/TRUST.md",
        "context/AGENT_INPUT_VALIDATION.md",
        "workflow/",
    ]

    for pattern in always_update_patterns:
        if pattern.endswith("/"):
            # Directory pattern
            if normalized.startswith(pattern) or f"/{pattern}" in f"/{normalized}":
                # Special case: tools/amplihack/hooks/ was already handled above
                # This catches all other tools/amplihack/* files
                return FileCategory.ALWAYS_UPDATE
        else:
            # File pattern
            if normalized == pattern or normalized.endswith(f"/{pattern}"):
                return FileCategory.ALWAYS_UPDATE

    # Default: If we don't recognize it, preserve it to be safe
    # This ensures we don't accidentally overwrite something important
    return FileCategory.PRESERVE_IF_MODIFIED


def get_category_description(category: FileCategory) -> str:
    """Get a human-readable description of a file category.

    Args:
        category: The FileCategory to describe

    Returns:
        A descriptive string explaining the category's behavior

    Example:
        >>> desc = get_category_description(FileCategory.ALWAYS_UPDATE)
        >>> print(desc)
        Core framework file - always updated to match repository version
    """
    descriptions = {
        FileCategory.ALWAYS_UPDATE: "Core framework file - always updated to match repository version",
        FileCategory.PRESERVE_IF_MODIFIED: "User-customizable file - preserved if locally modified",
        FileCategory.NEVER_UPDATE: "User content - never touched by framework updates",
    }
    return descriptions[category]
