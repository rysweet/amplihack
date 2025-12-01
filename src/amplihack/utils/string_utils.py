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

    Transforms any string into a URL-safe slug by:
    1. Normalizing Unicode (NFD) and converting to ASCII
    2. Converting to lowercase
    3. Replacing whitespace and special chars with hyphens
    4. Consolidating consecutive hyphens
    5. Stripping leading/trailing hyphens

    Args:
        text: Input string with any Unicode characters, special chars, or spaces.
              Can include letters, numbers, spaces, punctuation, and symbols.

    Returns:
        URL-safe slug with lowercase alphanumeric characters and hyphens.
        Empty string if input contains no valid characters.

    Behavior Notes:
        - Preserves word boundaries with hyphens
        - Removes quotes while preserving contractions (don't → dont)
        - Normalizes Unicode to ASCII (café → cafe, naïve → naive)
        - Converts all separators (spaces, slashes, underscores) to hyphens
        - Removes special characters (&, @, !, etc.)
        - Consolidates multiple consecutive hyphens into one
        - Strips leading and trailing hyphens

    Examples:
        Basic usage:
            >>> slugify("Hello World")
            'hello-world'
            >>> slugify("The Quick Brown Fox")
            'the-quick-brown-fox'

        Unicode and accents:
            >>> slugify("Café")
            'cafe'
            >>> slugify("naïve résumé")
            'naive-resume'

        Special characters:
            >>> slugify("Rock & Roll")
            'rock-roll'
            >>> slugify("user@example.com")
            'user-example-com'

        Multiple separators:
            >>> slugify("path/to/file.txt")
            'path-to-file-txt'
            >>> slugify("one___two___three")
            'one-two-three'

        Edge cases:
            >>> slugify("don't stop")
            'dont-stop'
            >>> slugify("100% Pure!")
            '100-pure'
            >>> slugify("   spaces   ")
            'spaces'
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


__all__ = ["slugify"]
