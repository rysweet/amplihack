"""String manipulation utilities.

This module provides utilities for text transformation and normalization.

Public API (the "studs"):
    slugify: Convert arbitrary text to URL-safe slug format
"""

import re
import unicodedata
from typing import Optional


def slugify(text: str, max_length: Optional[int] = None) -> str:
    """Convert text to URL-safe slug.

    Transforms arbitrary strings into URL-friendly slugs by:
    - Converting to lowercase
    - Normalizing unicode characters (NFD decomposition)
    - Removing accents and diacritics
    - Replacing spaces with hyphens
    - Removing special characters (keeping only a-z, 0-9, and hyphens)
    - Collapsing consecutive hyphens
    - Stripping leading and trailing hyphens

    Args:
        text: Text string to convert to slug
        max_length: Optional maximum length for the slug (truncates if exceeded)

    Returns:
        URL-safe slug string (lowercase, hyphens, alphanumeric only)

    Raises:
        ValueError: If text is None

    Examples:
        >>> slugify("Hello World")
        'hello-world'

        >>> slugify("Café au Lait")
        'cafe-au-lait'

        >>> slugify("foo  bar")
        'foo-bar'

        >>> slugify("---test---")
        'test'

        >>> slugify("!!!")
        ''

        >>> slugify("Hello World", max_length=8)
        'hello-wo'
    """
    if text is None:
        raise ValueError("text cannot be None")

    # 1. Normalize unicode (NFD) - separate base characters from combining marks
    # This converts é to e + combining accent
    normalized = unicodedata.normalize("NFKD", text)

    # 2. Encode to ASCII, ignoring characters that can't be represented
    # This removes the combining accents, leaving just base characters
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")

    # 3. Convert to lowercase
    lower_text = ascii_text.lower()

    # 4. Replace spaces (and multiple spaces) with single hyphen
    space_to_hyphen = re.sub(r"\s+", "-", lower_text)

    # 5. Remove all characters except a-z, 0-9, and hyphens
    cleaned = re.sub(r"[^a-z0-9-]", "", space_to_hyphen)

    # 6. Collapse consecutive hyphens to single hyphen
    collapsed = re.sub(r"-+", "-", cleaned)

    # 7. Strip leading and trailing hyphens
    slug = collapsed.strip("-")

    # 8. Apply max_length if specified
    if max_length is not None and len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")

    return slug


__all__ = ["slugify"]
