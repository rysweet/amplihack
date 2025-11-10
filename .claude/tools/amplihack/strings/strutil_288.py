"""String manipulation utilities - Batch 288"""

import re
from typing import Optional

def snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def camel_to_snake(camel_str: str) -> str:
    """Convert camelCase to snake_case."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()

def truncate(text: str, max_length: int, suffix: str = '...') -> str:
    """Truncate text to maximum length with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def extract_between(text: str, start: str, end: str) -> Optional[str]:
    """Extract text between start and end markers."""
    pattern = re.escape(start) + r'(.*?)' + re.escape(end)
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else None
