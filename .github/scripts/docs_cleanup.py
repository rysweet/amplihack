#!/usr/bin/env python3
"""Weekly documentation cleanup script for PATTERNS.md and DISCOVERIES.md.

This script uses Claude to analyze and clean up the project's documentation files,
following the amplihack philosophy of ruthless simplicity.

Security notes:
- Uses environment variables for API keys (never string interpolation)
- No user input is processed (reads only from repository files)
- Output is sanitized before writing
"""

import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Error: anthropic package not installed. Run: pip install anthropic")
    sys.exit(1)


# File paths relative to repository root
PATTERNS_PATH = Path(".claude/context/PATTERNS.md")
DISCOVERIES_PATH = Path(".claude/context/DISCOVERIES.md")
ARCHIVE_PATH = Path(".claude/context/DISCOVERIES_ARCHIVE.md")
OUTPUT_PATH = Path("cleanup_changes.md")

# Claude model configuration
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 8192

# Cleanup prompt for Claude
CLEANUP_PROMPT = """You are a documentation curator for the amplihack project. Your task is to review and clean up two documentation files: PATTERNS.md and DISCOVERIES.md.

## Philosophy
Follow amplihack's ruthless simplicity philosophy:
- Remove entries that haven't been referenced in 6+ months
- Archive old DISCOVERIES entries (move to DISCOVERIES_ARCHIVE.md)
- Promote validated patterns from DISCOVERIES to PATTERNS (if used 3+ times)
- Keep only patterns that apply broadly across multiple scenarios
- Maintain clear Table of Contents in both files

## Current Date
Today is {current_date}

## PATTERNS.md Content
```markdown
{patterns_content}
```

## DISCOVERIES.md Content
```markdown
{discoveries_content}
```

## DISCOVERIES_ARCHIVE.md Content
```markdown
{archive_content}
```

## Your Task
1. **Analyze DISCOVERIES.md**:
   - Identify entries older than 6 months that should be archived
   - Identify patterns used 3+ times that should be promoted to PATTERNS.md
   - Identify entries that are now resolved/superseded

2. **Analyze PATTERNS.md**:
   - Identify patterns that haven't been referenced in 6+ months
   - Identify patterns that are too project-specific (move to DISCOVERIES or PROJECT.md)
   - Check for duplicate or overlapping patterns

3. **Output your recommendations in this exact format**:

<analysis>
[Your detailed analysis of what needs to change and why]
</analysis>

<patterns_md>
[Complete updated PATTERNS.md content if changes needed, or "NO_CHANGES" if none needed]
</patterns_md>

<discoveries_md>
[Complete updated DISCOVERIES.md content if changes needed, or "NO_CHANGES" if none needed]
</discoveries_md>

<archive_md>
[Complete updated DISCOVERIES_ARCHIVE.md content if changes needed, or "NO_CHANGES" if none needed]
</archive_md>

<summary>
## Weekly Documentation Cleanup

**Date**: {current_date}

### Changes Made
[Bulleted list of all changes made]

### Entries Archived
[List of entries moved to archive]

### Patterns Promoted
[List of patterns promoted from DISCOVERIES to PATTERNS]

### Entries Removed
[List of entries removed and why]

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
</summary>

IMPORTANT:
- Only output file content if there are actual changes to make
- Preserve all formatting, code blocks, and structure
- Update Table of Contents when adding/removing entries
- Be conservative - only remove entries that are clearly stale or resolved
"""


def read_file(path: Path) -> str:
    """Read file content, return empty string if not found."""
    if path.exists():
        return path.read_text()
    return ""


def extract_section(response: str, tag: str) -> str:
    """Extract content between XML-style tags."""
    start_tag = f"<{tag}>"
    end_tag = f"</{tag}>"
    start_idx = response.find(start_tag)
    end_idx = response.find(end_tag)

    if start_idx == -1 or end_idx == -1:
        return ""

    return response[start_idx + len(start_tag) : end_idx].strip()


def main() -> int:
    """Main entry point for documentation cleanup."""
    # Validate environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        return 1

    # Read current file contents
    patterns_content = read_file(PATTERNS_PATH)
    discoveries_content = read_file(DISCOVERIES_PATH)
    archive_content = read_file(ARCHIVE_PATH)

    if not patterns_content or not discoveries_content:
        print("Error: Could not read PATTERNS.md or DISCOVERIES.md")
        return 1

    # Format prompt with current content
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = CLEANUP_PROMPT.format(
        current_date=current_date,
        patterns_content=patterns_content,
        discoveries_content=discoveries_content,
        archive_content=archive_content or "(No archive file exists yet)",
    )

    # Call Claude API
    print("Analyzing documentation with Claude...")
    client = anthropic.Anthropic()

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.content[0].text
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        return 1

    # Extract sections from response
    patterns_new = extract_section(response_text, "patterns_md")
    discoveries_new = extract_section(response_text, "discoveries_md")
    archive_new = extract_section(response_text, "archive_md")
    summary = extract_section(response_text, "summary")
    analysis = extract_section(response_text, "analysis")

    # Check if any changes were made
    changes_made = False

    if patterns_new and patterns_new != "NO_CHANGES":
        print("Updating PATTERNS.md...")
        PATTERNS_PATH.write_text(patterns_new)
        changes_made = True

    if discoveries_new and discoveries_new != "NO_CHANGES":
        print("Updating DISCOVERIES.md...")
        DISCOVERIES_PATH.write_text(discoveries_new)
        changes_made = True

    if archive_new and archive_new != "NO_CHANGES":
        print("Updating DISCOVERIES_ARCHIVE.md...")
        ARCHIVE_PATH.write_text(archive_new)
        changes_made = True

    if changes_made:
        # Write summary for PR body
        print("Writing cleanup summary...")
        OUTPUT_PATH.write_text(summary or "Documentation cleanup completed.")
        print(f"\nCleanup complete! Summary written to {OUTPUT_PATH}")
    else:
        print("\nNo changes needed - documentation is already in good shape!")
        # Don't create output file if no changes

    # Print analysis for logs
    if analysis:
        print("\n--- Analysis ---")
        print(analysis)

    return 0


if __name__ == "__main__":
    sys.exit(main())
