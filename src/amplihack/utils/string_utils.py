"""String utility functions for text processing.

This module provides utilities for converting strings to URL-safe formats.

Philosophy:
- Ruthless simplicity (stdlib only)
- Single responsibility per function
- Self-contained and regeneratable
- Zero-BS implementation (no stubs or placeholders)

Public API:
    slugify: Convert text to URL-safe slug format
    slugify_safe: Type-safe wrapper with None/type coercion handling
"""

import re
import unicodedata


def slugify(text: str) -> str:
    """Convert text to URL-safe slug format.

    Transforms any string into a URL-safe slug by:
    1. Normalizing Unicode (NFD) and converting to ASCII
    2. Converting to lowercase
    3. Replacing whitespace and special chars with hyphens
    4. Consolidating consecutive hyphens
    5. Stripping leading/trailing hyphens

    Args:
        text: Input string with any Unicode characters, special chars, or spaces.

    Returns:
        URL-safe slug with lowercase alphanumeric characters and hyphens.
        Empty string if input contains no valid characters.

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Café")
        'cafe'
        >>> slugify("Rock & Roll")
        'rock-roll'
    """
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


def slugify_safe(text: str | None | float | bool) -> str:
    """Type-safe wrapper around slugify() with None and type coercion handling.

    Converts input to string, handles None → "", then delegates to slugify().
    This is useful when dealing with user input or data that may be None or
    non-string types.

    Args:
        text: Any type that can be coerced to string, or None.
            - None returns empty string
            - Integers, floats, booleans converted via str()
            - Strings processed normally

    Returns:
        URL-safe slug. Empty string for None input.

    Examples:
        >>> slugify_safe(None)
        ''
        >>> slugify_safe(42)
        '42'
        >>> slugify_safe("Hello World")
        'hello-world'
        >>> slugify_safe(True)
        'true'
        >>> slugify_safe(12.5)
        '12-5'
    """
    if text is None:
        return ""
    return slugify(str(text))


__all__ = ["slugify", "slugify_safe"]
