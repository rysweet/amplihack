"""String utility functions for text processing.

This module provides utilities for converting strings to URL-safe formats.

Philosophy:
- Ruthless simplicity (stdlib only)
- Single responsibility per function
- Self-contained and regeneratable
- Zero-BS implementation (no stubs or placeholders)

Public API:
    slugify: Convert text to URL-safe slug format
    slugify_v2: Enhanced slugify with length limiting and custom separators
"""

import re
import unicodedata
from typing import Optional


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


def slugify_v2(text: str, max_length: Optional[int] = None, separator: str = "-") -> str:
    """Enhanced slug generation with length limiting and custom separators.

    An improved version of slugify that adds:
    - Maximum length with word-aware truncation
    - Custom separator support (-, _, ., empty string, multi-char)
    - Backward compatible with original slugify

    Args:
        text: Input string to convert to slug format.
        max_length: Optional maximum length. Truncates at word boundaries.
                   Must be positive if specified.
        separator: Custom separator character(s) to use instead of hyphen.
                  Common values: "-" (default), "_", ".", "" (no separator),
                  or any string like "--", "---", etc.

    Returns:
        URL-safe slug with specified constraints applied.
        Empty string if input contains no valid characters.

    Raises:
        None (handles all edge cases gracefully)

    Examples:
        Basic usage (compatible with slugify):
        >>> slugify_v2("Hello World")
        'hello-world'

        Custom separator:
        >>> slugify_v2("Hello World", separator="_")
        'hello_world'

        Length limiting (word-aware):
        >>> slugify_v2("Hello Beautiful World", max_length=11)
        'hello'  # Truncates at word boundary, not mid-word

        Combined features:
        >>> slugify_v2("Hello World Test", max_length=11, separator="_")
        'hello_world'  # Respects both constraints

    Implementation Notes:
        - Delegates to original slugify for base transformation
        - Applies custom separator via string replacement
        - Truncates at word boundaries to avoid partial words
        - Handles edge cases: empty strings, invalid lengths, special chars
    """
    # Delegate to existing slugify
    result = slugify(text)

    # Apply custom separator if different
    if separator != "-":
        result = result.replace("-", separator)

    # Apply max_length if specified
    if max_length is not None:
        if max_length <= 0:
            return ""

        if len(result) > max_length:
            # Only truncate at word boundaries if separator exists
            if separator and separator in result[:max_length]:
                # Find last complete word within max_length
                parts = result.split(separator)
                truncated = []
                current_len = 0

                for word in parts:
                    word_len = len(word) if not truncated else len(separator) + len(word)
                    if current_len + word_len <= max_length:
                        truncated.append(word)
                        current_len += word_len
                    else:
                        break

                result = separator.join(truncated)
            elif separator and separator in result:
                # Has separator but not in truncated part - truncate and strip
                result = result[:max_length].rstrip(separator)
            # else: Single word or empty separator - don't truncate

    return result


__all__ = ["slugify", "slugify_v2"]
