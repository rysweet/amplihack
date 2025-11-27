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
              Can be None, in which case returns empty string.

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
    """
    # Handle None input gracefully
    if text is None:
        return ""

    # First, handle special Unicode characters that need expansion
    # German ß becomes ss
    text = text.replace("ß", "ss")
    text = text.replace("ẞ", "SS")  # Capital version

    # Nordic characters that don't decompose with NFD
    text = text.replace("ø", "o")
    text = text.replace("Ø", "O")
    text = text.replace("æ", "ae")
    text = text.replace("Æ", "AE")
    text = text.replace("å", "a")
    text = text.replace("Å", "A")
    text = text.replace("þ", "th")  # Icelandic thorn
    text = text.replace("Þ", "TH")
    text = text.replace("ð", "d")  # Icelandic eth
    text = text.replace("Ð", "D")

    # Replace non-breaking spaces and other Unicode spaces with regular spaces
    # This ensures they get converted to hyphens later
    text = text.replace("\u00a0", " ")  # Non-breaking space
    text = text.replace("\u2002", " ")  # En space
    text = text.replace("\u2003", " ")  # Em space

    # Normalize Unicode and convert to ASCII
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # Lowercase conversion
    text = ascii_text.lower()

    # Remove quotes (apostrophes and double quotes)
    text = re.sub(r"[\'\"]+", "", text)

    # Replace all whitespace characters with hyphens
    # This includes spaces, tabs, newlines, and other whitespace
    text = re.sub(r"\s+", "-", text)

    # Replace common separators and special characters with hyphens
    # Include currency symbols, punctuation, brackets, etc.
    text = re.sub(r"[_/\\@!&.,;:()\[\]{}<>?#$%^*+=|`~€¥£¢]+", "-", text)

    # Remove any remaining non-alphanumeric characters (except hyphens)
    text = re.sub(r"[^a-z0-9-]", "", text)

    # Consolidate multiple consecutive hyphens into a single hyphen
    text = re.sub(r"-+", "-", text)

    # Strip leading and trailing hyphens
    return text.strip("-")


__all__ = ["slugify"]
