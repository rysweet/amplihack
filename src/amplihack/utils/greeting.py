"""Greeting utility module.

Philosophy:
- Ruthless simplicity - single responsibility, minimal implementation
- Zero-BS implementation - no validation, no error handling, trust the caller
- Standard library only - no external dependencies
- Self-contained and regeneratable from specification

Public API (the "studs"):
    greet: Format a greeting message for the given name
"""


def greet(name: str) -> str:
    """Generate a greeting message for the given name.

    Args:
        name: The name to greet

    Returns:
        A greeting message in the format "Hello, {name}!"

    Example:
        >>> greet("Alice")
        'Hello, Alice!'
        >>> greet("World")
        'Hello, World!'
    """
    return f"Hello, {name}!"


__all__ = ["greet"]
