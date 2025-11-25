"""String utility functions for amplihack.

This module provides string manipulation utilities including URL slug generation.
"""

import re
import unicodedata


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Transforms arbitrary text into a clean, URL-safe slug by applying a 4-step
    algorithm:
    1. Normalize Unicode to ASCII (NFKD decomposition)
    2. Convert to lowercase and replace spaces with hyphens
    3. Remove all non-alphanumeric characters except hyphens
    4. Collapse consecutive hyphens and trim leading/trailing hyphens

    Args:
        text: The input string to convert to a slug.

    Returns:
        A URL-safe slug string. Returns empty string for invalid input
        (empty strings, only special characters, or only whitespace).

    Examples:
        Basic transformations:
        >>> slugify("Hello World")
        'hello-world'

        Unicode normalization:
        >>> slugify("Café Münchën")
        'cafe-munchen'

        Special character removal:
        >>> slugify("Hello@World! #2024")
        'helloworld-2024'

        Blog post title:
        >>> slugify("10 Tips for Better Python Code!")
        '10-tips-for-better-python-code'

        Product name with special characters:
        >>> slugify('MacBook Pro (2024) - 16" Model')
        'macbook-pro-2024-16-model'

        Empty result for invalid input:
        >>> slugify("!@#$%^&*()")
        ''

        Multiple consecutive spaces:
        >>> slugify("hello    world")
        'hello-world'
    """
    # Return empty string for empty input
    if not text:
        return ""

    # Step 1: Normalize Unicode to ASCII (NFKD decomposition)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Step 2: Convert to lowercase and replace spaces with hyphens
    text = re.sub(r"\s+", "-", text.lower())

    # Step 3: Remove all non-alphanumeric characters except hyphens
    text = re.sub(r"[^a-z0-9-]", "", text)

    # Step 4: Collapse consecutive hyphens and trim leading/trailing hyphens
    text = re.sub(r"-+", "-", text).strip("-")

    return text
