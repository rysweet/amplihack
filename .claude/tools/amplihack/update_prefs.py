"""
Update preference management for amplihack.

Handles storage and retrieval of user preferences for automatic updates.
Preferences are stored in .claude/.update_preference as JSON.

Storage Format:
{
    "auto_update": "always" | "never" | null,
    "last_prompted": "2025-11-16T10:30:00Z"
}
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _get_preference_file_path() -> Path:
    """Get the path to the update preference file.

    Returns:
        Path object pointing to .claude/.update_preference

    Raises:
        RuntimeError: If .claude directory cannot be located
    """
    # Start from current file and traverse up to find .claude directory
    current = Path(__file__).resolve()

    # We're in .claude/tools/amplihack/, so go up 3 levels to get to .claude
    # __file__ -> amplihack/ -> tools/ -> .claude/
    claude_dir = current.parent.parent.parent

    if not claude_dir.name == ".claude":
        raise RuntimeError(f"Expected .claude directory, found {claude_dir}")

    return claude_dir / ".update_preference"


def load_update_preference() -> str | None:
    """Load user's auto-update preference from storage.

    Priority:
    1. USER_PREFERENCES.md (if set via /amplihack:customize)
    2. .claude/.update_preference (if set via session_start prompt)

    Returns:
        'always': Automatically update without prompting
        'never': Never update automatically
        None: Ask user each time (default if not set or file doesn't exist)

    Example:
        >>> pref = load_update_preference()
        >>> if pref == 'always':
        ...     perform_update()
        >>> elif pref == 'never':
        ...     skip_update()
        >>> else:
        ...     ask_user()
    """
    # Priority 1: Check USER_PREFERENCES.md
    try:
        # Navigate from .claude/tools/amplihack to .claude/context
        claude_dir = Path(__file__).resolve().parent.parent.parent
        user_prefs_file = claude_dir / "context" / "USER_PREFERENCES.md"

        if user_prefs_file.exists():
            content = user_prefs_file.read_text()
            # Look for "### Auto Update" section
            if "### Auto Update" in content:
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    # Use exact match to distinguish "### Auto Update" from
                    # "### .claude Directory Auto-Update" and other similar sections
                    if line.strip() == "### Auto Update" and i + 2 < len(lines):
                        value = lines[i + 2].strip().lower()
                        if value in ["always", "never"]:
                            return value
                        # If "ask" or empty, fall through to check .update_preference
    except Exception:
        pass  # Fall through to .update_preference file

    # Priority 2: Check .claude/.update_preference
    try:
        pref_file = _get_preference_file_path()

        if not pref_file.exists():
            return None

        with open(pref_file, encoding="utf-8") as f:
            data = json.load(f)

        auto_update = data.get("auto_update")

        # Validate the value
        if auto_update not in ("always", "never", None):
            return None

        return auto_update

    except (json.JSONDecodeError, OSError, RuntimeError):
        # On any error, return None (ask each time) as safe default
        return None


def save_update_preference(value: str) -> None:
    """Save user's auto-update preference to storage.

    Args:
        value: Must be 'always', 'never', or 'ask' (treated as None)

    Raises:
        ValueError: If value is not 'always', 'never', or 'ask'
        OSError: If file cannot be written
        RuntimeError: If .claude directory cannot be located

    Example:
        >>> save_update_preference('always')  # Enable auto-update
        >>> save_update_preference('never')   # Disable auto-update
        >>> save_update_preference('ask')     # Prompt each time
    """
    # Validate input
    if value not in ("always", "never", "ask"):
        raise ValueError(f"Invalid preference value: {value}. Must be 'always', 'never', or 'ask'")

    # Convert 'ask' to None for storage
    auto_update_value = None if value == "ask" else value

    pref_file = _get_preference_file_path()

    # Create data structure
    data: dict[str, Any] = {
        "auto_update": auto_update_value,
        "last_prompted": datetime.utcnow().isoformat() + "Z",
    }

    # Ensure parent directory exists
    pref_file.parent.mkdir(parents=True, exist_ok=True)

    # Write atomically using temp file and rename
    temp_file = pref_file.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")  # Add trailing newline

        # Atomic rename
        temp_file.replace(pref_file)

    except Exception:
        # Clean up temp file on error
        if temp_file.exists():
            temp_file.unlink()
        raise


def get_last_prompted() -> datetime | None:
    """Get the timestamp of when user was last prompted about updates.

    Returns:
        datetime object if timestamp exists, None otherwise

    Example:
        >>> last = get_last_prompted()
        >>> if last and (datetime.utcnow() - last).days < 7:
        ...     print("Don't prompt again yet")
    """
    try:
        pref_file = _get_preference_file_path()

        if not pref_file.exists():
            return None

        with open(pref_file, encoding="utf-8") as f:
            data = json.load(f)

        last_prompted = data.get("last_prompted")
        if not last_prompted:
            return None

        # Parse ISO format timestamp
        # Remove 'Z' suffix and parse
        timestamp_str = last_prompted.rstrip("Z")
        return datetime.fromisoformat(timestamp_str)

    except (json.JSONDecodeError, OSError, RuntimeError, ValueError):
        return None


def reset_preference() -> None:
    """Reset preference to default (ask each time).

    Removes the preference file entirely, returning to default behavior.

    Example:
        >>> reset_preference()
        >>> assert load_update_preference() is None
    """
    try:
        pref_file = _get_preference_file_path()
        if pref_file.exists():
            pref_file.unlink()
    except (OSError, RuntimeError):
        # If we can't delete, that's okay - preference will remain
        pass
