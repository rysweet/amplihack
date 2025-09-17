# CI Status Tool

Check GitHub CI/CD status for branches, pull requests, and commits.

## Purpose

Provides a simple, structured way to check CI status without complex bash scripting. Returns consistent JSON output for programmatic use and human-readable summaries for display.

## Usage

### As a Python Module

```python
from ci_status import check_ci_status

# Check current branch
result = check_ci_status()

# Check specific PR
result = check_ci_status("123")  # or "#123"

# Check specific branch
result = check_ci_status("main")

# Access structured data
if result["success"]:
    print(f"Status: {result['status']}")
    print(f"Total checks: {result['summary']['total']}")
```

### As a CLI Tool

```bash
# Check current branch
python .claude/tools/ci_status.py

# Check specific PR
python .claude/tools/ci_status.py 123

# Check specific branch
python .claude/tools/ci_status.py main

# Get JSON output
python .claude/tools/ci_status.py --json

# Make executable and use directly
chmod +x .claude/tools/ci_status.py
./.claude/tools/ci_status.py
```

## Output Structure

### Successful Response

```json
{
  "success": true,
  "status": "PASSING",  // PASSING, FAILING, PENDING, RUNNING, MIXED, NO_CHECKS, NO_RUNS
  "reference_type": "pr",  // "pr" or "branch"
  "pr_number": 123,  // if checking a PR
  "branch": "feature/xyz",  // branch name
  "checks": [...],  // for PRs: list of check details
  "runs": [...],  // for branches: list of workflow runs
  "summary": {
    "total": 5,
    "passed": 5,  // for PRs
    "failed": 0,
    "pending": 0,  // for PRs
    "in_progress": 0,  // for branches
    "successful": 5,  // for branches
    "completed": 5  // for branches
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

## Status Values

- **PASSING**: All checks/runs successful
- **FAILING**: One or more checks/runs failed
- **PENDING**: Checks are queued but not started (PR only)
- **RUNNING**: Workflows are currently running
- **MIXED**: Mixed results (some passed, some other status)
- **NO_CHECKS**: No CI checks configured (PR only)
- **NO_RUNS**: No workflow runs found

## Requirements

- Python 3.6+
- GitHub CLI (`gh`) installed and authenticated
- Git repository with GitHub remote

## Examples

### Check if CI is passing before merge

```python
from ci_status import check_ci_status

result = check_ci_status()
if result["success"] and result["status"] == "PASSING":
    print("Safe to merge!")
else:
    print(f"CI status: {result['status']}")
```

### Monitor CI progress

```python
import time
from ci_status import check_ci_status

while True:
    result = check_ci_status("123")  # PR number
    print(f"Status: {result['status']}")

    if result["status"] in ["PASSING", "FAILING"]:
        break

    time.sleep(30)  # Check every 30 seconds
```

### Get failed checks details

```python
from ci_status import check_ci_status

result = check_ci_status()
if result["status"] == "FAILING" and result.get("checks"):
    failed = [c for c in result["checks"] if c["conclusion"] == "FAILURE"]
    for check in failed:
        print(f"Failed: {check['name']}")
        print(f"  URL: {check.get('detailsUrl', 'N/A')}")
```

## Error Handling

The tool handles common errors gracefully:

- Missing `gh` CLI returns clear error message
- Network timeouts (30-second default)
- Invalid PR numbers or branches
- Malformed JSON responses
- Repository without GitHub remote

## Integration with Agents

This tool can be used by agents to:

1. Wait for CI to complete before proceeding
2. Verify tests pass before creating PRs
3. Monitor deployment status
4. Generate CI status reports
5. Trigger actions based on CI results

## Performance Notes

- Commands have a 30-second timeout
- Results are not cached (always fresh)
- Minimal dependencies (Python standard library only)
- Efficient JSON parsing for large check lists
