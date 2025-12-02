"""String utility functions for text processing.

This module provides utilities for converting strings to URL-safe formats.

Philosophy:
- Ruthless simplicity (stdlib only)
- Single responsibility per function
- Self-contained and regeneratable
- Zero-BS implementation (no stubs or placeholders)

Public API:
    slugify: Convert text to URL-safe slug format (handles Unicode)
    slugify_minimal: Convert text to URL-safe slug format (ASCII only, faster)
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


def slugify_minimal(text: str) -> str:
    """Convert text to URL-safe slug format (minimal variant).

    Transforms any string into a URL-safe slug by:
    1. Converting to lowercase
    2. Replacing whitespace with hyphens
    3. Removing special characters (keeping only alphanumeric + hyphens)
    4. Consolidating consecutive hyphens
    5. Stripping leading/trailing hyphens

    Uses no Unicode normalization - only handles ASCII input directly.
    For international text with diacritics, use slugify() instead.

    Args:
        text: Input string with ASCII characters, spaces, and special chars.

    Returns:
        URL-safe slug with lowercase alphanumeric characters and hyphens.
        Returns empty string if input contains no valid characters.

    Examples:
        >>> slugify_minimal("Hello World")
        'hello-world'
        >>> slugify_minimal("Multiple   Spaces")
        'multiple-spaces'
        >>> slugify_minimal("Special!@#Chars")
        'specialchars'
        >>> slugify_minimal("")
        ''
    """
    if not text:
        return ""

    # Lowercase
    slug = text.lower()

    # Replace whitespace with hyphens
    slug = re.sub(r"\s+", "-", slug)

    # Remove non-alphanumeric (except hyphens)
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Collapse multiple hyphens
    slug = re.sub(r"-+", "-", slug)

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    return slug


__all__ = ["slugify", "slugify_minimal"]
