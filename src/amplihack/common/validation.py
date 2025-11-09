"""Common validation and checking utilities."""

import logging
from pathlib import Path
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


def file_exists(file_path: Path) -> bool:
    """Check if file exists.

    Args:
        file_path: Path to check

    Returns:
        True if file exists
    """
    try:
        return Path(file_path).exists() and Path(file_path).is_file()
    except Exception as e:
        logger.warning(f"Error checking if file exists: {e}")
        return False


def dir_exists(dir_path: Path) -> bool:
    """Check if directory exists.

    Args:
        dir_path: Path to check

    Returns:
        True if directory exists
    """
    try:
        return Path(dir_path).exists() and Path(dir_path).is_dir()
    except Exception as e:
        logger.warning(f"Error checking if directory exists: {e}")
        return False


def is_empty(value: Any) -> bool:
    """Check if value is empty (None, empty string, empty list, etc).

    Args:
        value: Value to check

    Returns:
        True if value is empty
    """
    if value is None:
        return True

    if isinstance(value, str):
        return len(value.strip()) == 0

    if isinstance(value, (list, dict, set)):
        return len(value) == 0

    return False


def is_not_empty(value: Any) -> bool:
    """Check if value is not empty.

    Args:
        value: Value to check

    Returns:
        True if value is not empty
    """
    return not is_empty(value)


def validate_not_empty(value: Any, field_name: str = "value") -> Any:
    """Validate that value is not empty.

    Args:
        value: Value to validate
        field_name: Name of field for error message

    Returns:
        The value if valid

    Raises:
        ValueError: If value is empty
    """
    if is_empty(value):
        raise ValueError(f"{field_name} cannot be empty")
    return value


def validate_type(value: Any, expected_type: type, field_name: str = "value") -> Any:
    """Validate value is of expected type.

    Args:
        value: Value to validate
        expected_type: Expected type
        field_name: Name of field for error message

    Returns:
        The value if valid

    Raises:
        TypeError: If type doesn't match
    """
    if not isinstance(value, expected_type):
        raise TypeError(f"{field_name} must be {expected_type.__name__}, got {type(value).__name__}")
    return value


def validate_in_range(value: float, min_val: float, max_val: float, field_name: str = "value") -> float:
    """Validate value is in range.

    Args:
        value: Value to validate
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)
        field_name: Name of field for error message

    Returns:
        The value if valid

    Raises:
        ValueError: If value is outside range
    """
    if not (min_val <= value <= max_val):
        raise ValueError(f"{field_name} must be between {min_val} and {max_val}, got {value}")
    return value


def normalize_empty_result(result: Optional[List], default: Optional[List] = None) -> List:
    """Normalize result, converting None/empty to consistent empty list.

    Args:
        result: Result to normalize
        default: Default value if result is empty (default: [])

    Returns:
        Normalized list (never None)
    """
    if is_empty(result):
        return default if default is not None else []
    return result


def safe_call(
    func: Callable,
    *args,
    default: Any = None,
    log_errors: bool = True,
    error_prefix: str = "",
    **kwargs,
) -> Any:
    """Safely call function with error handling.

    Args:
        func: Function to call
        *args: Positional arguments
        default: Default value if function raises exception
        log_errors: Whether to log errors
        error_prefix: Prefix for error messages
        **kwargs: Keyword arguments

    Returns:
        Function result or default if exception occurs
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            msg = f"{error_prefix} {func.__name__} failed: {e}" if error_prefix else f"{func.__name__} failed: {e}"
            logger.error(msg)
        return default
