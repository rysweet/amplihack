"""String utility functions for text processing.

This module provides utilities for converting strings to URL-safe formats.

Philosophy:
- Ruthless simplicity (stdlib only)
- Single responsibility per function
- Self-contained and regeneratable
- Zero-BS implementation (no stubs or placeholders)

Public API:
    slugify: Convert text to URL-safe slug format
"""

import re
import unicodedata


def slugify(text: str) -> str:
    """Convert text to URL-safe slug format.

    Transforms any input into a URL-safe slug by:
    1. Handling None input (returns empty string)
    2. Converting non-string types (int, float, bool) to strings
    3. Normalizing Unicode (NFD) and converting to ASCII
    4. Converting to lowercase
    5. Replacing whitespace and special chars with hyphens
    6. Consolidating consecutive hyphens
    7. Stripping leading/trailing hyphens

    Args:
        text: Input of any type - string, number, boolean, or None.
              Lists and dicts will raise TypeError.

    Returns:
        URL-safe slug with lowercase alphanumeric characters and hyphens.
        Empty string if input is None or contains no valid characters.

    Raises:
        TypeError: If input is a list, dict, or other non-convertible type.

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Café")
        'cafe'
        >>> slugify("Rock & Roll")
        'rock-roll'
        >>> slugify(None)
        ''
        >>> slugify(123)
        '123'
        >>> slugify(True)
        'true'
    """
    # Handle None input
    if text is None:
        return ""

    # Type conversion for common types
    if isinstance(text, bool):
        text = str(text).lower()  # True -> "true", False -> "false"
    elif isinstance(text, (int, float)):
        text = str(text)
    elif not isinstance(text, str):
        # Raise TypeError for unsupported types like list or dict
        raise TypeError(
            f"slugify() argument must be str or convertible type, not {type(text).__name__}"
        )

    # Normalize Unicode and convert to ASCII
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # Lowercase and remove quotes (preserve contractions)
    text = ascii_text.lower()
    text = re.sub(r"[\'\"]+", "", text)

    # Replace whitespace and separators with hyphens
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[_/\\@!&.,;:()\[\]{}<>?#$%^*+=|`~]+", "-", text)

    # Keep only alphanumeric and hyphens
    text = re.sub(r"[^a-z0-9-]", "", text)

    # Consolidate hyphens and strip edges
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


__all__ = ["slugify"]
