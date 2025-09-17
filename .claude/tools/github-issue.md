# GitHub Issue Creation Tool

## Purpose

Programmatic GitHub issue creation with validation and structured output.

## Module Location

`/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding/.claude/tools/github_issue.py`

## Public Interface

### Main Function

```python
from github_issue import create_issue

result = create_issue(
    title="Bug: Authentication fails",  # Required
    body="Details here",               # Optional
    labels=["bug", "auth"],           # Optional
    assignees=["username"],           # Optional
    milestone="v1.0",                 # Optional
    project="Sprint 1",               # Optional
    repo="owner/repo"                 # Optional (uses current if omitted)
)
```

### Return Structure

```python
{
    'success': bool,
    'issue_url': str,      # If successful
    'issue_number': int,   # If successful
    'error': str           # If failed
}
```

## Requirements

- GitHub CLI (`gh`) must be installed
- Must be authenticated (`gh auth login`)
- Repository must exist and user must have write access

## Error Handling

The tool handles:

- Missing GitHub CLI
- Authentication failures
- Invalid inputs
- Network timeouts (30 second limit)
- Malformed responses

## Command Line Usage

```bash
# Simple issue
python github_issue.py "Title here"

# With options
python github_issue.py "Bug report" \
    --body "Description" \
    --label bug \
    --label high-priority \
    --assignee username \
    --milestone "v2.0"
```

## Implementation Details

- Wraps `gh issue create` command
- Validates inputs before execution
- Parses output to extract issue URL and number
- Returns structured Python dict for programmatic use
- Zero dependencies beyond standard library

## Testing

Run test suite:

```bash
python test_github_issue.py
```

## Philosophy Compliance

✓ **Ruthless Simplicity**: Single-purpose wrapper around gh CLI
✓ **Zero-BS**: No stubs, every function works
✓ **Self-contained**: No external dependencies
✓ **Clear Contract**: Well-defined inputs and outputs
✓ **Regeneratable**: Can be rebuilt from this specification
