"""Date and time utilities - Batch 309"""

from datetime import datetime, timedelta
from typing import Optional

def parse_iso_timestamp(timestamp: str) -> Optional[datetime]:
    """Parse ISO format timestamp."""
    try:
        return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError:
        return None

def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def is_recent(timestamp: datetime, max_age_minutes: int = 60) -> bool:
    """Check if timestamp is within specified age."""
    age = datetime.now() - timestamp
    return age < timedelta(minutes=max_age_minutes)

def get_timestamp_str() -> str:
    """Get current timestamp as string."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')
