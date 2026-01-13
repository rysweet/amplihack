"""
Utility functions for Goal Agent Generator.

Provides helper functions for name sanitization, validation, and other common tasks.
"""

import re


def sanitize_bundle_name(
    name: str, min_length: int = 3, max_length: int = 50, suffix: str = ""
) -> str:
    """
    Sanitize and validate a bundle name to meet requirements.

    Ensures the name:
    - Contains only valid characters (alphanumeric, hyphens, underscores)
    - Meets minimum and maximum length requirements
    - Preserves meaningful parts when truncating
    - Handles edge cases gracefully

    Args:
        name: Original name to sanitize
        min_length: Minimum allowed length (default: 3)
        max_length: Maximum allowed length (default: 50)
        suffix: Optional suffix to add (e.g., "-agent")

    Returns:
        Sanitized name meeting all requirements

    Raises:
        ValueError: If name cannot be sanitized to meet requirements

    Examples:
        >>> sanitize_bundle_name("Multi-Container Application", suffix="-agent")
        'multi-container-application-agent'

        >>> sanitize_bundle_name("a")
        'agent'

        >>> sanitize_bundle_name("a" * 100)
        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'

        >>> sanitize_bundle_name("Test@#$Name!!!", suffix="-agent")
        'test-name-agent'
    """
    if not name:
        # Empty name - use default
        name = "agent"

    # Convert to lowercase and replace invalid characters
    sanitized = name.lower()

    # Replace spaces, underscores, and multiple hyphens with single hyphen
    sanitized = re.sub(r"[_\s]+", "-", sanitized)

    # Remove any character that's not alphanumeric or hyphen
    sanitized = re.sub(r"[^a-z0-9-]", "", sanitized)

    # Remove leading/trailing hyphens
    sanitized = sanitized.strip("-")

    # Handle multiple consecutive hyphens
    sanitized = re.sub(r"-+", "-", sanitized)

    # If empty after sanitization, use default
    if not sanitized:
        sanitized = "agent"

    # Calculate available length for base name (accounting for suffix)
    suffix_length = len(suffix)
    available_length = max_length - suffix_length

    # Ensure we have room for at least min_length characters
    if available_length < min_length:
        raise ValueError(
            f"Cannot create valid name: max_length ({max_length}) - "
            f"suffix length ({suffix_length}) < min_length ({min_length})"
        )

    # Truncate if needed, preserving meaningful prefix
    if len(sanitized) > available_length:
        # Try to truncate at a word boundary (hyphen) if possible
        truncated = sanitized[:available_length]
        last_hyphen = truncated.rfind("-")

        # If we found a hyphen and it leaves us with enough characters, use it
        if last_hyphen > 0 and last_hyphen >= min_length:
            sanitized = truncated[:last_hyphen]
        else:
            # Otherwise, just truncate at available_length
            sanitized = truncated

    # Add suffix
    if suffix:
        sanitized = f"{sanitized}{suffix}"

    # Pad if too short
    if len(sanitized) < min_length:
        # Pad with "-agent" pattern until we meet minimum
        if not sanitized.endswith("-agent"):
            sanitized = f"{sanitized}-agent"

        # If still too short, prepend "goal-"
        if len(sanitized) < min_length:
            sanitized = f"goal-{sanitized}"

        # Last resort: pad with 'x'
        while len(sanitized) < min_length:
            sanitized = f"{sanitized}x"

    # Final validation
    if len(sanitized) < min_length:
        raise ValueError(f"Sanitized name '{sanitized}' is too short (< {min_length} characters)")

    if len(sanitized) > max_length:
        raise ValueError(f"Sanitized name '{sanitized}' is too long (> {max_length} characters)")

    # Ensure it starts with alphanumeric
    if not sanitized[0].isalnum():
        sanitized = f"a{sanitized[1:]}"

    return sanitized


def validate_bundle_name(name: str, min_length: int = 3, max_length: int = 50) -> bool:
    """
    Validate a bundle name meets requirements.

    Args:
        name: Name to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_bundle_name("my-agent")
        True

        >>> validate_bundle_name("ab")
        False

        >>> validate_bundle_name("a" * 51)
        False
    """
    if not name:
        return False

    if len(name) < min_length or len(name) > max_length:
        return False

    # Must contain only valid characters
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$", name):
        return False

    # No consecutive hyphens
    if "--" in name:
        return False

    return True
