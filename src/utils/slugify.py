"""Slugify utility - convert text to URL-friendly slugs.

This module provides a single function to convert arbitrary text strings
into URL-safe slug format suitable for URLs, file names, and identifiers.

Example:
    >>> from src.utils.slugify import slugify
    >>> slugify("Hello World!")
    'hello-world'
"""

import re
import unicodedata


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug format.

    Transforms input text into a lowercase, hyphen-separated string
    containing only ASCII letters, numbers, and hyphens.

    Args:
        text: Any string to convert to slug format.

    Returns:
        A lowercase string with:
        - Accented characters transliterated to ASCII
        - Spaces replaced with hyphens
        - Special characters removed
        - Multiple hyphens collapsed to single hyphen
        - No leading or trailing hyphens

    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("My Blog Post #1")
        'my-blog-post-1'
        >>> slugify("Cafe Resume")
        'cafe-resume'
        >>> slugify("  Multiple   Spaces  ")
        'multiple-spaces'
        >>> slugify("")
        ''
    """
    # Normalize Unicode - decompose accented characters (NFD)
    # This separates base characters from combining diacritical marks
    text = unicodedata.normalize("NFD", text)

    # Remove diacritical marks (combining characters)
    # Category 'Mn' = Mark, Nonspacing (accents, umlauts, etc.)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    # Convert to lowercase
    text = text.lower()

    # Replace spaces and whitespace with hyphens
    text = re.sub(r"\s+", "-", text)

    # Remove all characters except alphanumeric and hyphens
    text = re.sub(r"[^a-z0-9-]", "", text)

    # Collapse multiple consecutive hyphens into single hyphen
    text = re.sub(r"-+", "-", text)

    # Strip leading and trailing hyphens
    text = text.strip("-")

    return text


__all__ = ["slugify"]
