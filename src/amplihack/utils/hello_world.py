"""Simple hello world function."""

from amplihack.utils.logging_utils import log_call


@log_call
def hello_world() -> str:
    """Return hello world greeting.

    Returns:
        str: The string "hello world"
    """
    return "hello world"
