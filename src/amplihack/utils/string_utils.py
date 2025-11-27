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
from typing import Any


def slugify(text: Any) -> str:
    """Convert text to URL-safe slug format.

    Transforms any input into a URL-safe slug by:
    1. Converting to string (handles None, int, float, bool)
    2. Normalizing Unicode (NFD) and converting to ASCII
    3. Converting to lowercase
    4. Replacing non-alphanumeric with hyphens
    5. Consolidating consecutive hyphens
    6. Stripping leading/trailing hyphens

    Special handling:
    - None -> empty string
    - True -> "true"
    - False -> "false"
    - Negative numbers preserve the minus sign (e.g., -456 -> "-456")

    Args:
        text: Input of any type - string, None, int, float, bool, etc.

    Returns:
        URL-safe slug with lowercase alphanumeric characters and hyphens.
        Empty string if input is None or contains no valid characters.

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
        >>> slugify(-456)
        '-456'
        >>> slugify(True)
        'true'
        >>> slugify(False)
        'false'
    """
    # Convert any type to string
    if text is None:
        return ""
    if isinstance(text, bool):
        text = str(text).lower()
    else:
        text = str(text)

    # Check if this is a negative number (starts with minus and followed by digits)
    is_negative_number = False
    if text.startswith("-"):
        # Check if after the minus there's a digit
        rest = text[1:].lstrip()
        if rest and rest[0].isdigit():
            is_negative_number = True

    # Normalize Unicode and convert to ASCII
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()

    # Replace all non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text)

    # Strip edge hyphens
    slug = slug.strip("-")

    # Restore leading minus only for negative numbers
    if is_negative_number and slug and not slug.startswith("-"):
        slug = "-" + slug

    return slug


__all__ = ["slugify"]
