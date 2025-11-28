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

# Maximum input length to prevent resource exhaustion attacks
# 10,000 chars is chosen as a reasonable upper bound that:
# - Prevents DoS attacks from extremely long strings (megabytes/gigabytes)
# - Allows legitimate use cases (long blog posts, article titles)
# - Keeps memory usage and processing time bounded
# - Aligns with typical web framework limits (e.g., URL length limits)
MAX_INPUT_LENGTH = 10000

# Compile regex patterns at module level for performance
# These patterns are used repeatedly and compiling them once improves performance
_QUOTES_PATTERN = re.compile(r"[\'\"]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_SEPARATORS_PATTERN = re.compile(r"[_/\\@!&.,;:()\[\]{}<>?#$%^*+=|`~]+")
_NON_ALNUM_HYPHEN_PATTERN = re.compile(r"[^a-z0-9-]")
_CONSECUTIVE_HYPHENS_PATTERN = re.compile(r"-+")
# Pattern for zero-width characters (remove entirely)
_ZERO_WIDTH_PATTERN = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
# Pattern for control characters (replace with space/hyphen)
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def slugify(text: str, max_length: int | None = None) -> str:
    """Convert text to URL-safe slug format.

    Transforms any string into a URL-safe slug by:
    1. Type validation - raises TypeError for non-strings
    2. Removing zero-width and control characters
    3. Normalizing Unicode (NFD) and converting to ASCII
    4. Converting to lowercase
    5. Replacing whitespace and special chars with hyphens
    6. Consolidating consecutive hyphens
    7. Stripping leading/trailing hyphens
    8. Truncating to max_length at word boundaries when possible

    Args:
        text: Input string with any Unicode characters, special chars, or spaces.
              Raises TypeError if not a string type.
        max_length: Optional maximum length for the slug. If provided, truncates
                    intelligently at word boundaries when possible. Must be non-negative.

    Returns:
        URL-safe slug with lowercase alphanumeric characters and hyphens.
        Empty string if input contains no valid characters.

    Raises:
        TypeError: If text is not a string type.
        ValueError: If max_length is negative.

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Café")
        'cafe'
        >>> slugify("Rock & Roll")
        'rock-roll'
        >>> slugify("Very long title", max_length=10)
        'very-long'
    """
    # Type validation
    if not isinstance(text, str):
        raise TypeError(f"Expected string, got {type(text).__name__}")

    # Security check: prevent resource exhaustion
    if len(text) > MAX_INPUT_LENGTH:
        raise ValueError(f"Input text exceeds maximum length of {MAX_INPUT_LENGTH} characters")

    # Validate max_length parameter
    if max_length is not None and max_length < 0:
        raise ValueError("max_length must be non-negative")

    # Handle empty string early
    if not text:
        return ""

    # Handle max_length of 0
    if max_length == 0:
        return ""

    # Remove zero-width characters entirely
    text = _ZERO_WIDTH_PATTERN.sub("", text)
    # Replace control characters with spaces (to become hyphens later)
    text = _CONTROL_CHAR_PATTERN.sub(" ", text)

    # Normalize Unicode and convert to ASCII
    normalized = unicodedata.normalize("NFD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # If nothing left after ASCII conversion, return empty
    if not ascii_text:
        return ""

    # Lowercase and remove quotes (preserve contractions)
    text = ascii_text.lower()
    text = _QUOTES_PATTERN.sub("", text)

    # Replace whitespace and separators with hyphens
    text = _WHITESPACE_PATTERN.sub("-", text)
    text = _SEPARATORS_PATTERN.sub("-", text)

    # Keep only alphanumeric and hyphens
    text = _NON_ALNUM_HYPHEN_PATTERN.sub("", text)

    # Consolidate hyphens and strip edges
    text = _CONSECUTIVE_HYPHENS_PATTERN.sub("-", text)
    text = text.strip("-")

    # Handle max_length truncation
    if max_length is not None and len(text) > max_length:
        # If we're at a natural word boundary (next char is hyphen), keep up to max_length
        if text[max_length] == "-":
            return text[:max_length].rstrip("-")

        # Otherwise, find the last word boundary before max_length
        truncated = text[:max_length]
        last_hyphen = truncated.rfind("-")

        if last_hyphen > 0:
            # Truncate at word boundary
            return text[:last_hyphen]

        # No word boundary - hard truncate and strip any trailing hyphen
        return truncated.rstrip("-")

    return text


__all__ = ["slugify"]
