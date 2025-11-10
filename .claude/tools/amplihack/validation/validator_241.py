"""Input validation utilities - Batch 241"""

import re
from typing import Any, Optional

def validate_input(value: Any, validation_type: str) -> tuple[bool, Optional[str]]:
    """Validate input against specified type.

    Args:
        value: Value to validate
        validation_type: Type of validation to perform

    Returns:
        Tuple of (is_valid, error_message)
    """
    validators = {
        'email': lambda v: (bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', str(v))), "Invalid email format"),
        'url': lambda v: (bool(re.match(r'^https?://.+', str(v))), "Invalid URL format"),
        'path': lambda v: (bool(re.match(r'^[/\w\.-]+$', str(v))), "Invalid path format"),
        'alphanum': lambda v: (str(v).isalnum(), "Must be alphanumeric"),
        'positive_int': lambda v: (isinstance(v, int) and v > 0, "Must be positive integer"),
    }

    if validation_type not in validators:
        return False, f"Unknown validation type: {validation_type}"

    is_valid, error = validators[validation_type](value)
    return is_valid, None if is_valid else error
