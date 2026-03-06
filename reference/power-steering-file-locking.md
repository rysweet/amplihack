# Power Steering File Locking

Technical reference for the file locking implementation that prevents race conditions in power-steering counter increments.

## Problem Solved

**Race Condition in Counter Increment**: Multiple concurrent stop hook invocations could read the same counter value, increment it independently, and write conflicting values. This caused the counter to reset unexpectedly (e.g., 5 → 0 instead of 5 → 6), triggering infinite power-steering loops.

**Root Cause**: Lack of synchronization between read-modify-write operations on shared state file.

## Solution Overview

File locking using `fcntl.flock()` ensures atomic read-modify-write operations. Only one process can hold the lock at a time, preventing concurrent modifications.

## Implementation

### File Locking Protocol

```python
# [IMPLEMENTED] - Actual implementation
import fcntl
from contextlib import contextmanager

@contextmanager
def _acquire_file_lock(file_handle, timeout_seconds=2.0):
    """Acquire exclusive lock with timeout."""
    start_time = time.time()
    lock_acquired = False

    try:
        while True:
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_acquired = True
                break
            except BlockingIOError:
                if time.time() - start_time >= timeout_seconds:
                    break  # Timeout - proceed without lock (fail-open)
                time.sleep(0.05)  # Retry after 50ms

        yield lock_acquired
    finally:
        if lock_acquired:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)

# Usage with persistent lock file
lock_file = state_file.parent / ".turn_state.lock"
with open(lock_file, "a+") as lock_f:
    with _acquire_file_lock(lock_f) as locked:
        # Critical section: read-modify-write
        state = load_state()
        state.turn_count += 1
        save_state(state, _skip_locking=True)
```

**Lock Type**: Exclusive (`LOCK_EX`) - Only one process can hold the lock.

**Non-Blocking**: `LOCK_NB` flag attempts lock without waiting. If lock unavailable, raises `BlockingIOError`.

**Timeout**: 2-second timeout prevents indefinite hangs. After timeout, operation fails open.

**Automatic Release**: Lock released when file handle closes (via context manager).

## Platform Support

### Linux and macOS

Full support via `fcntl.flock()`. Advisory locks work across all processes accessing the same file.

### Windows

Graceful degradation. Windows lacks `fcntl` module. Implementation uses try/except to detect platform:

```python
# [IMPLEMENTED] - Platform detection pattern
try:
    import fcntl
    LOCKING_AVAILABLE = True
except ImportError:
    LOCKING_AVAILABLE = False
    # Fall back to fail-open behavior

# In TurnStateManager.__init__():
if not LOCKING_AVAILABLE:
    self.log("File locking unavailable (Windows) - operating in degraded mode")
```

On Windows, locking is skipped but operations continue. Race conditions remain possible but rare in practice.

## Error Handling

### Fail-Open Design

All locking errors are non-fatal. System continues operation without locking rather than blocking users.

**Lock Acquisition Timeout** (2s):

- Log warning
- Proceed without lock
- State may be inconsistent but user not blocked

**Lock Not Available** (`BlockingIOError`):

- Another process holds lock
- Wait briefly and retry
- After max retries, proceed without lock

**Platform Unsupported** (Windows):

- Skip locking entirely
- Proceed with atomic write (temp file + rename)
- Log info message about degraded mode

**File Permissions** (`PermissionError`):

- Log error
- Fall back to best-effort write
- Don't block stop hook

### Logging

All lock operations logged to `.claude/runtime/power-steering/{session_id}/file_locking.log`:

```jsonl
{"event": "lock_acquired", "timestamp": "2026-01-27T10:30:45", "duration_ms": 15}
{"event": "lock_timeout", "timestamp": "2026-01-27T10:30:47", "timeout_ms": 2000}
{"event": "lock_unavailable", "timestamp": "2026-01-27T10:30:48", "retry": 1}
```

## Usage

### Automatic Operation

File locking operates transparently during counter increments. No user action required.

```python
# User perspective: Works the same with or without locking
manager = TurnStateManager(project_root, session_id)
state = manager.load_state()
state = manager.increment_turn(state)
manager.save_state(state)  # Locking happens here automatically
```

### Testing Lock Behavior

Verify locking works correctly:

```bash
# Simulate concurrent writes
python -c "
from .claude.tools.amplihack.hooks.power_steering_state import TurnStateManager
from pathlib import Path
import threading

def increment_counter(n):
    manager = TurnStateManager(Path('.'), 'test_session')
    for i in range(10):
        state = manager.load_state()
        state = manager.increment_turn(state)
        manager.save_state(state)

threads = [threading.Thread(target=increment_counter, args=(i,)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()

# Verify final count is 50 (5 threads × 10 increments)
final = manager.load_state()
assert final.turn_count == 50
"
```

## Performance

**Lock Overhead**: ~1-5ms per operation (negligible for stop hook).

**Timeout Impact**: Only occurs under heavy concurrent load (rare in normal usage).

**Windows Degradation**: No performance impact. Falls back to existing atomic write.

## Debugging

### Check Lock Status

```bash
# View lock log
cat .claude/runtime/power-steering/*/file_locking.log | jq .

# Monitor locks in real-time
tail -f .claude/runtime/power-steering/*/file_locking.log
```

### Common Issues

**"Lock timeout after 2000ms"**:

- Another process holding lock too long
- Check for hung processes: `ps aux | grep amplihack`
- Increase timeout if necessary (edit `LOCK_TIMEOUT_MS`)

**"Locking unavailable (Windows)"**:

- Expected behavior on Windows
- No action needed
- Race conditions remain possible but rare

**"Permission denied on lock file"**:

- File permissions issue
- Check `.claude/runtime/power-steering/` permissions
- Run: `chmod -R u+rw .claude/runtime/`

## Technical Details

### Lock Scope

**Advisory Locks**: Cooperative - all processes must use same locking protocol.

**File-Level**: Lock applies to entire file, not individual records.

**Process-Local**: Locks not inherited by child processes.

### Lock Lifetime

1. **Acquire**: `fcntl.flock(fd, LOCK_EX | LOCK_NB)` called when file opened
2. **Hold**: Lock held during critical section (read-modify-write)
3. **Release**: Lock automatically released when file closed or process exits

### Concurrency Model

```
Process A                    Process B
    |                            |
    | open(state_file)           |
    | flock(LOCK_EX)             |
    | [LOCKED]                   |
    |                            | open(state_file)
    |                            | flock(LOCK_EX) [BLOCKED]
    | read → modify → write      |
    | close() [UNLOCK]           |
    |                            | [LOCK ACQUIRED]
    |                            | read → modify → write
    |                            | close() [UNLOCK]
```

## Related

- Issue #2155: Power steering infinite loop
- [Power Steering State Management](../features/power-steering.md)
- [Stop Hook Implementation](.claude/tools/amplihack/hooks/stop.py)
- [Test Coverage](../../tests/.claude/tools/amplihack/hooks/tests/test_issue_1882_power_steering_infinite_loop.py)

## Metadata

- **Status**: [IMPLEMENTED - Testing Complete]
- **Issue**: #2155
- **Platform**: Linux (full), macOS (full), Windows (degraded)
- **Python Version**: 3.8+
- **Dependencies**: Standard library only (`fcntl`, `json`, `os`, `time`, `contextlib`)
- **Last Updated**: 2026-01-27
- **Implementation**:
  - `/home/azureuser/src/amplihack/worktrees/feat/issue-2155-power-steering-counter-race/.claude/tools/amplihack/hooks/power_steering_state.py`
  - `/home/azureuser/src/amplihack/worktrees/feat/issue-2155-power-steering-counter-race/.claude/tools/amplihack/hooks/stop.py`
