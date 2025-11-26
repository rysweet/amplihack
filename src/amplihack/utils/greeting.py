"""Simple greeting utility for formatted welcomes.

Philosophy:
- Single responsibility: Format greeting strings
- Pure function: No side effects
- Standard library only: No external dependencies

Public API (the "studs"):
    greet: Creates formatted greeting string

This module provides a simple, reusable greeting formatter following
the brick philosophy. It's self-contained and regeneratable from spec.
"""


def greet(name: str) -> str:
    """Generate a friendly greeting for the given name.

    Args:
        name: The name to greet (any non-empty string)

    Returns:
        Formatted greeting string in the form 'Hello, {name}!'

    Examples:
        >>> greet("Alice")
        'Hello, Alice!'

        >>> greet("World")
        'Hello, World!'

    Note:
        This is a pure function with no side effects. The same input
        always produces the same output.
    """
    return f"Hello, {name}!"


__all__ = ["greet"]
