"""Date parsing and age validation for discovery entries.

This module provides utilities for extracting dates from DISCOVERIES.md headers
and determining if entries are old enough to archive.

Philosophy:
- Conservative defaults (invalid dates = KEEP content)
- Simple regex-based parsing
- No external dependencies
- Self-contained and regeneratable

Public API:
    DateParseResult: Dataclass for parse results
    parse_discovery_date: Extract date from header line
    is_old_enough: Check if entry exceeds age cutoff
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class DateParseResult:
    """Result of parsing a date from a discovery header.

    Attributes:
        valid: True if date was successfully parsed and is valid
        date: Parsed datetime object (None if invalid)
        error: Error message if parsing failed (None if successful)
    """

    valid: bool
    date: datetime | None
    error: str | None


def parse_discovery_date(header_line: str) -> DateParseResult:
    """Extract and validate date from a DISCOVERIES.md header line.

    Handles various header formats:
        - "### 2024-06-15"
        - "### 2024-06-15 10:30:00"
        - "###2024-06-15" (no space)
        - "### 2024-06-15 Some text after"

    Conservative approach: Returns valid=False for:
        - Missing dates
        - Malformed dates
        - Future dates
        - Empty/whitespace headers

    Args:
        header_line: Header line from DISCOVERIES.md (e.g., "### 2024-06-15")

    Returns:
        DateParseResult with parsing status and extracted date

    Example:
        >>> result = parse_discovery_date("### 2024-06-15")
        >>> assert result.valid is True
        >>> assert result.date.year == 2024
    """
    # Handle empty/whitespace input
    if not header_line or not header_line.strip():
        return DateParseResult(valid=False, date=None, error="Empty or whitespace-only header")

    # Extract date using regex - matches ISO 8601 date format
    # Pattern: YYYY-MM-DD optionally followed by HH:MM:SS
    date_pattern = r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}:\d{2}))?"
    match = re.search(date_pattern, header_line)

    if not match:
        return DateParseResult(
            valid=False, date=None, error="No date found in header (expected format: YYYY-MM-DD)"
        )

    # Extract date and optional time components
    date_str = match.group(1)
    time_str = match.group(2) if match.group(2) else "00:00:00"
    datetime_str = f"{date_str} {time_str}"

    # Parse the datetime
    try:
        parsed_date = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        # Add timezone awareness (UTC)
        parsed_date = parsed_date.replace(tzinfo=UTC)
    except ValueError as e:
        return DateParseResult(valid=False, date=None, error=f"Invalid date format: {e}")

    # Check if date is in the future (invalid for discoveries)
    now = datetime.now(UTC)
    if parsed_date > now:
        return DateParseResult(
            valid=False,
            date=None,
            error="Date is in the future (discoveries cannot be future-dated)",
        )

    return DateParseResult(valid=True, date=parsed_date, error=None)


def is_old_enough(entry_date: datetime, cutoff_months: int, reference_date: datetime) -> bool:
    """Check if an entry is old enough to be archived.

    Uses month-based calculation with day precision:
    - Exactly cutoff_months old = True (e.g., 6 months exactly)
    - Just under cutoff_months = False (e.g., 5.9 months)
    - Well past cutoff_months = True (e.g., 7 months)

    Args:
        entry_date: Date of the discovery entry
        cutoff_months: Age threshold in months (e.g., 6)
        reference_date: Date to compare against (typically today)

    Returns:
        True if entry_date is >= cutoff_months old, False otherwise

    Example:
        >>> ref = datetime(2024, 12, 15, tzinfo=timezone.utc)
        >>> old = datetime(2024, 6, 15, tzinfo=timezone.utc)
        >>> is_old_enough(old, cutoff_months=6, reference_date=ref)
        True
    """
    # Calculate month difference
    years_diff = reference_date.year - entry_date.year
    months_diff = reference_date.month - entry_date.month
    total_months = years_diff * 12 + months_diff

    # If we're past the cutoff in full months, check day precision
    if total_months > cutoff_months:
        return True
    if total_months == cutoff_months:
        # At exactly cutoff months - check if we've passed the same day
        return reference_date.day >= entry_date.day
    return False


__all__ = ["DateParseResult", "parse_discovery_date", "is_old_enough"]
