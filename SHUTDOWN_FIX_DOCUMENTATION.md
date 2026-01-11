# Power Steering Exit Hang Fix - Documentation

## Overview

The power steering system now exits cleanly within 2-3 seconds without requiring
Ctrl-C. This fix prevents asyncio event loop hangs during application shutdown
by detecting shutdown state and bypassing async operations.

## Problem Solved

**Before**: Application hung on exit when power steering sync wrapper functions
tried to create new asyncio event loops during shutdown, requiring Ctrl-C to
force quit.

**After**: Clean 2-3 second exit. All sync wrappers detect shutdown in progress
and immediately return safe defaults.

## Implementation

### Shutdown Detection Helper

```python
def is_shutting_down() -> bool:
    """Check if application shutdown is in progress.

    Returns True if AMPLIHACK_SHUTDOWN_IN_PROGRESS environment variable is set.
    This enables graceful shutdown by allowing sync wrapper functions to detect
    shutdown state and return safe defaults instead of starting new async
    operations that may hang during event loop teardown.
    """
    return os.environ.get("AMPLIHACK_SHUTDOWN_IN_PROGRESS") == "1"
```

### Modified Functions

Three sync wrapper functions now check for shutdown before starting async
operations:

#### 1. `analyze_claims_sync()`

**Shutdown behavior**: Returns `[]` (empty list - no claims detected)

```python
def analyze_claims_sync(delta_text: str, project_root: Path) -> list[str]:
    """Synchronous wrapper for analyze_claims with shutdown detection."""
    # Shutdown check: bypass async operation during teardown
    if is_shutting_down():
        return []  # Fail-open: no claims detected during shutdown

    try:
        return asyncio.run(analyze_claims(delta_text, project_root))
    except Exception:
        return []  # Fail-open on any error
```

**Why this is safe**: An empty claims list means "no completion claims
detected," which never blocks users. Power steering simply won't trigger
verification checks during shutdown.

#### 2. `analyze_if_addressed_sync()`

**Shutdown behavior**: Returns `None` (no evidence found)

```python
def analyze_if_addressed_sync(
    failure_id: str,
    failure_reason: str,
    delta_text: str,
    project_root: Path,
) -> str | None:
    """Synchronous wrapper for analyze_if_addressed with shutdown detection."""
    # Shutdown check: bypass async operation during teardown
    if is_shutting_down():
        return None  # Fail-open: no evidence found during shutdown

    try:
        return asyncio.run(
            analyze_if_addressed(failure_id, failure_reason, delta_text, project_root)
        )
    except Exception:
        return None  # Fail-open on any error
```

**Why this is safe**: Returning `None` means "no evidence found that failure was
addressed," which never blocks users. It's the same as finding no relevant
updates in the transcript.

#### 3. `analyze_consideration_sync()`

**Shutdown behavior**: Returns `(True, None)` (assume satisfied)

```python
def analyze_consideration_sync(
    conversation: list[dict], consideration: dict, project_root: Path
) -> tuple[bool, str | None]:
    """Synchronous wrapper for analyze_consideration with shutdown detection."""
    # Shutdown check: bypass async operation during teardown
    if is_shutting_down():
        return (True, None)  # Fail-open: assume satisfied during shutdown

    try:
        return asyncio.run(analyze_consideration(conversation, consideration, project_root))
    except Exception:
        return (True, None)  # Fail-open on any error
```

**Why this is safe**: Returning `(True, None)` means "consideration is
satisfied," following fail-open philosophy. During shutdown, we assume all
checks pass to never block the user from exiting.

## Fail-Open Philosophy

All shutdown returns follow the **fail-open principle**: when uncertain or
unable to check, always assume conditions are satisfied and never block the
user.

| Function                       | Shutdown Return | Meaning            | Fail-Open Behavior          |
| ------------------------------ | --------------- | ------------------ | --------------------------- |
| `analyze_claims_sync()`        | `[]`            | No claims detected | Won't trigger verification  |
| `analyze_if_addressed_sync()`  | `None`          | No evidence found  | Won't mark failure as fixed |
| `analyze_consideration_sync()` | `(True, None)`  | Satisfied          | Passes verification check   |

## Usage Examples

### Normal Operation

```python
# Power steering works normally when not shutting down
claims = analyze_claims_sync("Task complete!", project_root)
# Returns: ["...Task complete!..."] (detected claim)

evidence = analyze_if_addressed_sync("todos_complete", "3 TODOs incomplete",
                                     "Completed all TODOs", project_root)
# Returns: "Completed all TODOs" (evidence found)

satisfied, reason = analyze_consideration_sync(conversation, consideration, project_root)
# Returns: (False, "3 TODOs incomplete") or (True, None)
```

### During Shutdown

```python
# Set shutdown flag
os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

# All functions return immediately with safe defaults
claims = analyze_claims_sync("Task complete!", project_root)
# Returns: [] (no async operation started)

evidence = analyze_if_addressed_sync("todos_complete", "3 TODOs incomplete",
                                     "Completed all TODOs", project_root)
# Returns: None (no async operation started)

satisfied, reason = analyze_consideration_sync(conversation, consideration, project_root)
# Returns: (True, None) (no async operation started)
```

## Testing the Fix

### Manual Test

```bash
# Start amplihack session
amplihack

# Exit normally (type 'exit' or use Ctrl-D)
exit

# Result: Clean exit within 2-3 seconds
# Before fix: Would hang, requiring Ctrl-C
```

### Programmatic Test

```python
import os
from pathlib import Path
from claude_power_steering import (
    analyze_claims_sync,
    analyze_if_addressed_sync,
    analyze_consideration_sync
)

# Test shutdown detection
os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"

# All should return immediately with safe defaults
assert analyze_claims_sync("test", Path.cwd()) == []
assert analyze_if_addressed_sync("id", "reason", "text", Path.cwd()) is None
assert analyze_consideration_sync([], {}, Path.cwd()) == (True, None)

print("✅ Shutdown detection working correctly")
```

## Benefits

1. **Clean Exit**: 2-3 second shutdown instead of hanging
2. **No Force Quit**: Eliminates need for Ctrl-C during exit
3. **Fail-Open**: Never blocks users, maintains system philosophy
4. **Zero Impact**: Normal operation unchanged - only affects shutdown
5. **Simple Implementation**: Single environment variable check per function

## Architecture

```
Signal Handler (signal_handler in amplihack)
    ↓
Sets AMPLIHACK_SHUTDOWN_IN_PROGRESS=1
    ↓
Power Steering Sync Wrappers
    ↓
is_shutting_down() checks environment variable
    ↓
If True: Return safe defaults immediately
If False: Proceed with asyncio.run() normally
```

## Key Design Decisions

### Why Environment Variable?

- **Simple**: No complex threading or state management
- **Reliable**: Set once at signal handler, visible to all code
- **Philosophy-aligned**: Ruthlessly simple implementation
- **Zero overhead**: Single string comparison check

### Why These Default Values?

- **`[]` for claims**: Empty list = "nothing to verify" = never blocks
- **`None` for evidence**: No evidence = "failure not fixed yet" = safe
  assumption
- **`(True, None)` for consideration**: Satisfied = "let user exit" = fail-open

### Why Not Fix the Async Functions?

The async functions are fine. The problem is `asyncio.run()` creating new event
loops during shutdown. By detecting shutdown at the sync wrapper level, we
bypass the problematic operation entirely.

## Related Files

- **Signal handler**: `.claude/tools/amplihack/hooks/` (sets
  `AMPLIHACK_SHUTDOWN_IN_PROGRESS`)
- **Power steering module**:
  `.claude/tools/amplihack/hooks/claude_power_steering.py`
- **Issue tracker**: GitHub Issue #1893

## Philosophy Compliance

This fix exemplifies amplihack philosophy:

- ✅ **Ruthlessly Simple**: Single environment variable check
- ✅ **Fail-Open**: Never block users due to shutdown
- ✅ **Zero-BS**: No complex shutdown orchestration, just immediate returns
- ✅ **Modular**: Self-contained in power steering module
- ✅ **Clear Intent**: Inline comments explain shutdown check pattern

## Future Considerations

This pattern can be applied to other async wrapper functions if similar shutdown
hangs are discovered. The implementation is generic and reusable:

```python
def any_sync_wrapper(*args):
    """Template for shutdown-aware sync wrappers."""
    if is_shutting_down():
        return SAFE_DEFAULT  # Appropriate for this function

    try:
        return asyncio.run(async_function(*args))
    except Exception:
        return SAFE_DEFAULT  # Fail-open
```
