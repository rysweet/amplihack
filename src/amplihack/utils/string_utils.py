"""
String utility functions for text processing and normalization.

This module provides utilities for converting text into URL-safe slugs with
Unicode normalization, security controls, and strict validation.
"""

import re
import unicodedata

# Security constant: Absolute maximum input length to prevent DoS attacks
ABSOLUTE_MAX_INPUT_LENGTH = 10000


def slugify(text: str) -> str:
    """
    Convert text to a URL-safe slug.

    Transforms arbitrary text into a normalized, lowercase slug containing only
    alphanumeric characters (a-z, 0-9) and hyphens. Applies NFKD Unicode
    normalization for consistent handling of accented and special characters.

    Args:
        text: Input string to convert to slug. Must be non-empty and contain
              characters that can be converted to valid slug content.

    Returns:
        URL-safe slug string containing only lowercase letters, numbers, and
        hyphens. No leading or trailing hyphens, no consecutive hyphens.

    Raises:
        TypeError: If text is not a string.
        ValueError: If input is empty, exceeds 10,000 characters, or contains
                   only whitespace/special characters.

    Security:
        - Input length limited to 10,000 characters (DoS prevention)
        - Control characters removed (null bytes, etc.)
        - Unicode normalization applied (homograph prevention)
        - ASCII-only output guaranteed

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Café Naïve")
        'cafe-naive'
        >>> slugify("  Multiple   Spaces  ")
        'multiple-spaces'
        >>> slugify("Special!@#Characters")
        'special-characters'
        >>> slugify("")
        Traceback (most recent call last):
            ...
        ValueError: Input text is empty
        >>> slugify("a" * 10001)
        Traceback (most recent call last):
            ...
        ValueError: Input text exceeds maximum length of 10000 characters
    """
    # Type validation
    if not isinstance(text, str):
        raise TypeError(f"Input must be a string, got {type(text).__name__}")

    # Length and emptiness validation
    if len(text) == 0:
        raise ValueError("Input text is empty")

    if len(text) >= ABSOLUTE_MAX_INPUT_LENGTH:
        raise ValueError(
            f"Input text exceeds maximum length of {ABSOLUTE_MAX_INPUT_LENGTH} characters"
        )

    # Check for whitespace-only input
    stripped = text.strip()
    if not stripped:
        raise ValueError("Input text is empty or contains only whitespace")

    # Check for alphanumeric or high Unicode content (reject special chars only)
    if not any(c.isalnum() or ord(c) > 127 for c in stripped):
        # Allow hyphens (they're valid separators) but reject other special-char-only input
        if not all(c == "-" or c.isspace() for c in stripped):
            raise ValueError("Input text contains only special characters")

    # Remove control characters (0x00-0x08, 0x0E-0x1F except 0x20, 0x7F-0x9F)
    text = "".join(
        char
        for char in text
        if not (ord(char) < 9 or (14 <= ord(char) < 32) or (127 <= ord(char) < 160))
    )

    # Apply NFKD Unicode normalization
    text = unicodedata.normalize("NFKD", text)

    # Convert to ASCII (removes accents, non-ASCII chars)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    text = text.lower()

    # Convert whitespace to hyphens
    text = re.sub(r"\s+", "-", text)

    # Remove path separators
    text = text.replace("/", "").replace("\\", "")

    # Remove dots between digits (e.g., "2.0" → "20")
    text = re.sub(r"(\d)\.(\d)", r"\1\2", text)

    # Replace remaining special characters with hyphens
    text = re.sub(r"[^a-z0-9-]", "-", text)

    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text)

    # Remove leading/trailing hyphens
    text = text.strip("-")

    # Post-processing validation: ensure we have content after normalization
    # This prevents empty string returns for non-ASCII input without ASCII equivalents
    if not text:
        raise ValueError(
            "Input text resulted in empty slug after normalization. "
            "Ensure input contains Latin characters or ASCII-convertible Unicode."
        )

    return text
