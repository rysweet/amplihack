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


def slugify(text: str, separator: str = "-", max_length: int | None = None) -> str:
    """Convert text to URL-safe slug format.

    Transforms any string into a URL-safe slug by:
    1. Normalizing Unicode (NFD) and converting to ASCII
    2. Converting to lowercase
    3. Replacing whitespace and special chars with separator
    4. Consolidating consecutive separators
    5. Stripping leading/trailing separators
    6. Returning "untitled" for empty results
    7. Supporting custom separator and max_length

    Args:
        text: Input string with any Unicode characters, special chars, or spaces.
        separator: Character to use as word separator (default "-").
        max_length: Maximum length of the output slug.

    Returns:
        URL-safe slug with lowercase alphanumeric characters and separators.
        Returns "untitled" if input contains no valid characters.

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Café")
        'cafe'
        >>> slugify("Rock & Roll")
        'rock-roll'
        >>> slugify("")
        'untitled'
        >>> slugify("Hello World", separator="_")
        'hello_world'
        >>> slugify("Hello World", max_length=5)
        'hello'
    """
    # Type check for non-string inputs FIRST (before any string operations)
    if not isinstance(text, str):
        raise TypeError(f"slugify() expects str, got {type(text).__name__}")

    # Handle zero or negative max_length
    if max_length is not None and max_length <= 0:
        return ""

    # Normalize Unicode (NFD) and convert to ASCII, then lowercase
    # Now safe to use string methods since we've validated it's a string
    result = unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii").lower()

    # Combined regex operations for performance:
    # Step 1: Remove quotes/apostrophes (for contractions like It's -> Its)
    # Step 2: Replace all non-alphanumeric with spaces in single pass
    result = re.sub(r"['\"]", "", result)  # Remove quotes first
    result = re.sub(r"[^a-z0-9]+", " ", result).strip()  # Replace all non-alphanumeric and strip

    # If empty, return "untitled" (respecting max_length)
    if not result:
        untitled = "untitled"
        if max_length and max_length < len(untitled):
            # For very small max_length, truncate "untitled"
            # This preserves the meaning better than alternatives
            return untitled[:max_length]
        return untitled

    # Replace spaces with separator
    result = result.replace(" ", separator) if separator else result.replace(" ", "")

    # Apply max_length truncation
    if max_length and len(result) > max_length:
        truncated = result[:max_length]

        # If truncation ends exactly at a separator, keep up to that separator
        if separator and len(truncated) > 0 and truncated[-1] == separator:
            result = truncated.rstrip(separator)
        # If there's a separator right after the truncation point, keep everything before it
        elif separator and len(result) > max_length and result[max_length] == separator:
            result = truncated
        # Otherwise, try to truncate at word boundary
        elif separator and separator in truncated:
            last_sep = truncated.rfind(separator)
            if last_sep > 0:
                result = result[:last_sep]
            else:
                result = truncated
        else:
            result = truncated

    # Remove trailing separator and handle empty result
    if separator:
        result = result.rstrip(separator)

    # Return result or "untitled" if empty (respecting max_length)
    if not result:
        untitled = "untitled"
        if max_length and max_length < len(untitled):
            return untitled[:max_length]
        return untitled

    return result


__all__ = ["slugify"]
