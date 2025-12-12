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


def slugify(text: str, max_length: int | None = None) -> str:
    """Convert text to URL-safe slug format.

    Transforms any string into a URL-safe slug by:
    1. Normalizing Unicode (NFD) and converting to ASCII
    2. Converting to lowercase
    3. Replacing whitespace and special chars with hyphens
    4. Consolidating consecutive hyphens
    5. Stripping leading/trailing hyphens
    6. Optionally truncating to max_length (at word boundary)

    Args:
        text: Input string with any Unicode characters, special chars, or spaces.
        max_length: Optional maximum length for the slug. If provided, truncates
            at the last hyphen before max_length to avoid cutting words.

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
        >>> slugify("This is a very long title", max_length=10)
        'this-is-a'
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
    slug = text.strip("-")

    # Truncate to max_length at word boundary if specified
    if max_length and len(slug) > max_length:
        truncated = slug[:max_length]
        # Find last hyphen to avoid cutting words
        last_hyphen = truncated.rfind("-")
        if last_hyphen > 0:
            slug = truncated[:last_hyphen]
        else:
            slug = truncated.rstrip("-")

    return slug


__all__ = ["slugify"]
