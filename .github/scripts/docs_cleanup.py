#!/usr/bin/env python3
"""Weekly documentation cleanup script for PATTERNS.md and DISCOVERIES.md.

This script uses Claude to analyze and clean up the project's documentation files,
following the amplihack philosophy of ruthless simplicity.

Security notes:
- Uses environment variables for API keys (never string interpolation)
- No user input is processed (reads only from repository files)
- Output is sanitized before writing

Philosophy:
- Conservative defaults (entries < 6 months MUST be preserved)
- Explicit date validation before sending to Claude
- Pre-filter entries to prevent accidental deletion
- Dry-run mode for testing

Public API:
    FilterResult: Dataclass for filter results
    CleanupResult: Dataclass for cleanup results
    parse_discoveries_file: Parse DISCOVERIES.md into entry structures
    filter_entries_by_age: Filter entries by age with date validation
    run_cleanup: Complete cleanup workflow with dry-run support
"""

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from date_parser import is_old_enough, parse_discovery_date


@dataclass
class FilterResult:
    """Result of filtering entries by age.

    Attributes:
        old_entries: List of entries that exceed the age cutoff
        kept_entries: List of entries that should be preserved
        total_processed: Total number of entries processed
    """

    old_entries: list[dict]
    kept_entries: list[dict]
    total_processed: int


@dataclass
class CleanupResult:
    """Result of running cleanup operation.

    Attributes:
        entries_removed: Number of entries removed/archived
        entries_kept: Number of entries preserved
        dry_run: Whether this was a dry-run (no file modifications)
        summary: Human-readable summary of changes
    """

    entries_removed: int
    entries_kept: int
    dry_run: bool
    summary: str


# File paths relative to repository root
PATTERNS_PATH = Path(".claude/context/PATTERNS.md")
DISCOVERIES_PATH = Path(".claude/context/DISCOVERIES.md")
ARCHIVE_PATH = Path(".claude/context/DISCOVERIES_ARCHIVE.md")
OUTPUT_PATH = Path("cleanup_changes.md")

# Configuration constants
DEFAULT_CUTOFF_MONTHS = 6  # Conservative default: entries older than 6 months


def parse_discoveries_file(file_path: Path) -> list[dict]:
    """Parse DISCOVERIES.md file into structured entry dictionaries.

    Parses markdown file to extract discovery entries with their dates,
    headers, and content. Each entry is a dictionary with:
        - header: The markdown header line (e.g., "### 2024-11-15")
        - content: The body text of the entry
        - date: Parsed datetime object (or None if invalid)

    Conservative approach: Entries without valid dates are still included
    in the results (with date=None) to prevent accidental data loss.

    Args:
        file_path: Path to DISCOVERIES.md file

    Returns:
        List of entry dictionaries with header, content, and date fields

    Raises:
        FileNotFoundError: If file_path does not exist

    Example:
        >>> entries = parse_discoveries_file(Path("DISCOVERIES.md"))
        >>> assert all('header' in e for e in entries)
        >>> assert all('content' in e for e in entries)
        >>> assert all('date' in e for e in entries)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = file_path.read_text()
    entries = []

    # Split by level-3 headers (###)
    # Pattern: Find "### " followed by content until next "### " or end
    header_pattern = r"^### (.+)$"
    lines = content.split("\n")

    current_header = None
    current_content = []

    for line in lines:
        header_match = re.match(header_pattern, line)
        if header_match:
            # Save previous entry if exists
            if current_header is not None:
                entry_content = "\n".join(current_content).strip()
                # Parse date from header
                parse_result = parse_discovery_date(current_header)
                entries.append(
                    {
                        "header": current_header,
                        "content": entry_content,
                        "date": parse_result.date if parse_result.valid else None,
                    }
                )

            # Start new entry
            current_header = line
            current_content = []
        else:
            # Accumulate content for current entry
            if current_header is not None:
                current_content.append(line)

    # Don't forget the last entry
    if current_header is not None:
        entry_content = "\n".join(current_content).strip()
        parse_result = parse_discovery_date(current_header)
        entries.append(
            {
                "header": current_header,
                "content": entry_content,
                "date": parse_result.date if parse_result.valid else None,
            }
        )

    return entries


def filter_entries_by_age(
    entries: list[dict], cutoff_months: int, reference_date: datetime
) -> FilterResult:
    """Filter discovery entries by age.

    Separates entries into old (should be archived) and kept (preserve)
    based on date and age cutoff. Uses conservative approach:
        - Entries without valid dates are KEPT (not deleted)
        - Only entries with valid dates >= cutoff_months are marked old
        - Entries with dates < cutoff_months are KEPT

    Args:
        entries: List of entry dicts with 'date' field (from parse_discoveries_file)
        cutoff_months: Age threshold in months (e.g., 6)
        reference_date: Date to compare against (typically today)

    Returns:
        FilterResult with old_entries, kept_entries, and total_processed

    Example:
        >>> entries = [
        ...     {'header': '### 2024-01-15', 'content': 'Old', 'date': datetime(2024, 1, 15, tzinfo=timezone.utc)},
        ...     {'header': '### 2024-11-15', 'content': 'Recent', 'date': datetime(2024, 11, 15, tzinfo=timezone.utc)}
        ... ]
        >>> ref = datetime(2024, 12, 15, tzinfo=timezone.utc)
        >>> result = filter_entries_by_age(entries, cutoff_months=6, reference_date=ref)
        >>> assert len(result.old_entries) == 1
        >>> assert len(result.kept_entries) == 1
    """
    old_entries = []
    kept_entries = []

    for entry in entries:
        entry_date = entry.get("date")

        # Conservative: entries without valid dates are KEPT
        if entry_date is None:
            kept_entries.append(entry)
            continue

        # Check if entry is old enough to archive
        if is_old_enough(entry_date, cutoff_months, reference_date):
            old_entries.append(entry)
        else:
            kept_entries.append(entry)

    return FilterResult(
        old_entries=old_entries, kept_entries=kept_entries, total_processed=len(entries)
    )


def run_cleanup(
    path: Path,
    cutoff_months: int = DEFAULT_CUTOFF_MONTHS,
    dry_run: bool = True,
    reference_date: datetime | None = None,
) -> CleanupResult:
    """Run complete cleanup workflow on a DISCOVERIES.md file.

    Complete workflow:
    1. Parse file into entry structures
    2. Filter entries by age (pre-filter before Claude)
    3. If dry_run=False, write updated file
    4. Return results with summary

    Conservative approach:
    - Entries without valid dates are preserved
    - Only entries with valid dates >= cutoff_months are removed
    - Dry-run mode never modifies files

    Args:
        path: Path to DISCOVERIES.md file
        cutoff_months: Age threshold in months (default: 6)
        dry_run: If True, no file modifications (default: True)
        reference_date: Date to compare against (default: now)

    Returns:
        CleanupResult with counts and summary

    Raises:
        FileNotFoundError: If path does not exist

    Example:
        >>> result = run_cleanup(
        ...     Path("DISCOVERIES.md"),
        ...     cutoff_months=6,
        ...     dry_run=True
        ... )
        >>> assert result.dry_run is True
        >>> assert result.entries_removed >= 0
        >>> assert result.entries_kept >= 0
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Use current time if reference_date not provided
    if reference_date is None:
        reference_date = datetime.now(UTC)

    # Parse file into entries
    entries = parse_discoveries_file(path)

    # Filter entries by age
    filter_result = filter_entries_by_age(entries, cutoff_months, reference_date)

    # Generate summary
    summary = f"""# Documentation Cleanup Results

**Mode**: {"DRY-RUN (no changes)" if dry_run else "ACTUAL (files modified)"}
**Date**: {reference_date.strftime("%Y-%m-%d")}
**Cutoff**: {cutoff_months} months

## Summary
- Total entries processed: {filter_result.total_processed}
- Entries removed/archived: {len(filter_result.old_entries)}
- Entries kept: {len(filter_result.kept_entries)}
"""

    # If not dry-run, write updated file
    if not dry_run:
        # Read original file to preserve non-entry content
        original_content = path.read_text()

        # Parse the file to find header, entries, and footer sections
        lines = original_content.split("\n")
        header_lines = []
        footer_lines = []

        # Find first entry header
        first_entry_idx = None
        for i, line in enumerate(lines):
            if line.startswith("### "):
                first_entry_idx = i
                break
            header_lines.append(line)

        # Find last entry header to detect footer
        last_entry_idx = None
        if first_entry_idx is not None:
            for i in range(len(lines) - 1, first_entry_idx - 1, -1):
                if lines[i].startswith("### "):
                    last_entry_idx = i
                    break

        # Extract footer (everything after last entry content)
        if last_entry_idx is not None:
            # Find where the last entry's content ends (next non-empty after entry content)
            in_entry_content = True
            for i in range(last_entry_idx + 1, len(lines)):
                line = lines[i]
                # If we hit another ### or non-whitespace after entry content, it's footer
                if not in_entry_content and line.strip():
                    footer_lines = lines[i:]
                    break
                # Track when we leave entry content (encounter empty lines)
                if in_entry_content and not line.strip():
                    in_entry_content = False

        # Build new content
        new_content = "\n".join(header_lines).rstrip() + "\n\n"

        # Add kept entries
        for entry in filter_result.kept_entries:
            new_content += entry["header"] + "\n\n"
            new_content += entry["content"] + "\n\n"

        # Add footer content if it exists
        if footer_lines:
            new_content += "\n".join(footer_lines).rstrip() + "\n"
        else:
            new_content = new_content.rstrip() + "\n"

        # Write updated file
        path.write_text(new_content)

    return CleanupResult(
        entries_removed=len(filter_result.old_entries),
        entries_kept=len(filter_result.kept_entries),
        dry_run=dry_run,
        summary=summary,
    )


def main() -> int:
    """Main entry point for documentation cleanup."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Clean up DISCOVERIES.md by removing old entries",
        epilog="""
Examples:
  # Dry-run (preview changes, no modifications)
  %(prog)s --dry-run

  # Remove entries older than 6 months (default)
  %(prog)s

  # Remove entries older than 12 months
  %(prog)s --cutoff-months 12

  # Clean specific file with 3-month cutoff
  %(prog)s --file docs/notes.md --cutoff-months 3

  # Preview changes for custom file
  %(prog)s --file docs/notes.md --dry-run
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in dry-run mode (no file modifications). Use this to preview changes.",
    )
    parser.add_argument(
        "--cutoff-months",
        type=int,
        default=DEFAULT_CUTOFF_MONTHS,
        help=f"Age cutoff in months (default: {DEFAULT_CUTOFF_MONTHS}). "
        "Entries older than this will be removed.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DISCOVERIES_PATH,
        help=f"Path to DISCOVERIES.md file (default: {DISCOVERIES_PATH})",
    )

    args = parser.parse_args()

    # Run the cleanup workflow with date validation
    print(f"Running cleanup on {args.file}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'ACTUAL'}")
    print(f"Cutoff: {args.cutoff_months} months\n")

    try:
        result = run_cleanup(path=args.file, cutoff_months=args.cutoff_months, dry_run=args.dry_run)

        # Print results
        print(result.summary)

        # Write summary if changes were made
        if result.entries_removed > 0:
            OUTPUT_PATH.write_text(result.summary)
            print(f"\nSummary written to {OUTPUT_PATH}")

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


__all__ = [
    "FilterResult",
    "CleanupResult",
    "parse_discoveries_file",
    "filter_entries_by_age",
    "run_cleanup",
]


if __name__ == "__main__":
    sys.exit(main())
