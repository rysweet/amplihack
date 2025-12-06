"""Text slugification utilities for URL-safe string conversion.

This module provides utilities for converting arbitrary text into URL-safe
slug format, suitable for URLs, file names, and identifiers.

Philosophy:
- Ruthless simplicity (stdlib only)
- Single responsibility per function
- Self-contained and regeneratable
- Zero-BS implementation (no stubs or placeholders)

Public API:
    slugify: Convert text to URL-safe slug format

Example:
    >>> from amplihack.utils.string_utils import slugify
    >>> slugify("Hello World!")
    'hello-world'
    >>> slugify("My Article Title", max_length=10)
    'my'
    >>> slugify("one two three", separator="_")
    'one_two_three'
"""

import re
import unicodedata


def slugify(
    text: str,
    *,
    max_length: int | None = None,
    separator: str = "-",
) -> str:
    """Convert text to URL-safe slug format.

    Transforms arbitrary text into a lowercase, URL-safe string by:
    1. Converting to lowercase
    2. Replacing spaces and non-alphanumeric characters with the separator
    3. Collapsing consecutive separators
    4. Stripping leading/trailing separators
    5. Optionally truncating at word boundaries

    Args:
        text: The input text to convert. Can contain any Unicode characters.
        max_length: Maximum length of the output slug. When specified,
            truncates at the nearest word boundary that fits within the
            limit. If None, no length limit is applied.
        separator: Character(s) used to separate words. Defaults to hyphen.
            Common alternatives: underscore ("_"), dot ("."), empty string ("").

    Returns:
        A URL-safe slug string. Returns empty string if input contains
        no alphanumeric characters.

    Raises:
        ValueError: If max_length is negative.

    Examples:
        Basic usage:

        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("  Multiple   Spaces  ")
        'multiple-spaces'

        With max_length (truncates at word boundary):

        >>> slugify("The Quick Brown Fox", max_length=15)
        'the-quick-brown'
        >>> slugify("Supercalifragilistic", max_length=5)
        'super'

        With custom separator:

        >>> slugify("hello world", separator="_")
        'hello_world'
        >>> slugify("hello world", separator="")
        'helloworld'
    """
    # Validate parameters
    if max_length is not None and max_length < 0:
        raise ValueError("max_length must be non-negative")

    # Handle max_length=0 early
    if max_length == 0:
        return ""

    # Escape separator for regex use
    sep_escaped = re.escape(separator) if separator else ""

    # Normalize Unicode and convert to ASCII
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # Lowercase and remove quotes
    result = ascii_text.lower()
    result = re.sub(r"[\'\"]+", "", result)

    # Replace whitespace with separator
    result = re.sub(r"\s+", separator, result)

    # Replace special characters (including hyphens) with separator
    result = re.sub(r"[-_/\\@!&.,;:()\[\]{}<>?#$%^*+=|`~]+", separator, result)

    # Keep only alphanumeric and separator characters
    if separator:
        allowed_pattern = f"[^a-z0-9{sep_escaped}]"
    else:
        allowed_pattern = r"[^a-z0-9]"
    result = re.sub(allowed_pattern, "", result)

    # Consolidate multiple separators
    if separator:
        result = re.sub(f"{sep_escaped}+", separator, result)

    # Strip separator from edges
    result = result.strip(separator) if separator else result

    # Apply max_length truncation at word boundaries
    if max_length is not None and len(result) > max_length:
        if separator:
            # Find last separator within limit
            truncate_at = result.rfind(separator, 0, max_length + 1)
            if truncate_at > 0:
                result = result[:truncate_at]
            else:
                # No separator found - hard truncate
                result = result[:max_length]
        else:
            # No separator - hard truncate
            result = result[:max_length]

    return result


__all__ = ["slugify"]
