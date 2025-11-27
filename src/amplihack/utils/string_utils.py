"""String utility functions for text processing.

This module provides utilities for converting strings to URL-safe formats.

Philosophy:
- Ruthless simplicity (stdlib only)
- Single responsibility per function
- Self-contained and regeneratable
- Zero-BS implementation (no stubs or placeholders)

Public API:
    slugify: Convert text to URL-safe slug format
    MAX_INPUT_LENGTH: Maximum allowed input length for slugify (10,000)
"""

import re
import unicodedata

# Maximum input length to prevent memory exhaustion attacks
MAX_INPUT_LENGTH = 10000


def slugify(text: str, max_length: int = 50, separator: str = "-") -> str:
    """Convert text to URL-safe slug format.

    Transforms any string into a URL-safe slug by:
    1. Handling None by converting to string first
    2. Normalizing Unicode (NFD) and converting to ASCII
    3. Converting to lowercase
    4. Replacing spaces and underscores with separator
    5. Removing special characters (keeping only alphanumeric and separator)
    6. Collapsing multiple separators into one
    7. Stripping leading/trailing separators
    8. Truncating to max_length if needed (smart truncation at word boundaries)

    Security Note:
        The output is safe for use in URLs, filenames, and HTML contexts.
        This function prevents injection attacks by removing all special
        characters and normalizing Unicode, ensuring only alphanumeric
        characters and the separator remain in the output.

    Args:
        text: Input string with any Unicode characters, special chars, or spaces.
              Can be None (will be converted to "none").
              Input length is limited to MAX_INPUT_LENGTH (10,000) to prevent
              memory exhaustion.
        max_length: Maximum length of output (default 50).
                   Use 0 for empty string, negative for unlimited.
        separator: Separator character (default "-").

    Returns:
        URL-safe slug with lowercase alphanumeric characters and separator.
        Empty string if input contains no valid characters or max_length is 0.

    Raises:
        ValueError: If input text exceeds MAX_INPUT_LENGTH (10,000 characters).

    Examples:
        >>> slugify("Hello World")
        'hello-world'
        >>> slugify("Café")
        'cafe'
        >>> slugify("Rock & Roll")
        'rock-roll'
        >>> slugify(None)
        'none'
        >>> slugify("Hello World", separator="_")
        'hello_world'
        >>> slugify("Very long string here", max_length=10)
        'very-long'
    """
    # Handle special cases
    if text is None:
        text = "none"
    else:
        text = str(text)

    # Check input length to prevent memory exhaustion
    if len(text) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"Input text exceeds maximum allowed length of {MAX_INPUT_LENGTH} characters"
        )

    if max_length == 0:
        return ""

    # Unicode to ASCII conversion
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()

    # Remove quotes completely (not replaced with separator)
    text = re.sub(r"['\"]", "", text)

    # Replace whitespace and underscores with separator
    text = re.sub(r"[\s_]+", separator, text)

    # Remove non-alphanumeric characters (except separator)
    if separator:
        escaped_sep = re.escape(separator)
        text = re.sub(f"[^a-z0-9{escaped_sep}]+", separator, text)
        # Collapse multiple separators and strip edges
        text = re.sub(f"{escaped_sep}+", separator, text).strip(separator)
    else:
        text = re.sub(r"[^a-z0-9]+", "", text)

    # Smart truncation at word boundaries
    if 0 < max_length < len(text):
        truncated = text[:max_length]
        # Only truncate at word boundary if we cut in middle of a word
        if separator and separator in truncated:
            # Check if we cut in the middle of a word
            # (i.e., there's more text after max_length that isn't a separator)
            if len(text) > max_length and text[max_length : max_length + 1] != separator:
                last_sep = truncated.rfind(separator)
                if last_sep > 0:
                    truncated = truncated[:last_sep]
        text = truncated.rstrip(separator) if separator else truncated

    return text


__all__ = ["slugify", "MAX_INPUT_LENGTH"]
