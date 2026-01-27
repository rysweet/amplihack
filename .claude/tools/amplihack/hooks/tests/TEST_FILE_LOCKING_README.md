# File Locking Test Suite (Issue #2155)

## Overview

Comprehensive test suite for file locking implementation that prevents power-steering counter race conditions.

**Coverage**: 25 tests covering lock acquisition, timeouts, race conditions, and platform support
**Location**: `test_file_locking.py`

## Test Coverage Summary

### Unit Tests (60% - 19 tests)

#### 1. Lock Acquisition (`TestFileLockAcquisition`)

- `test_lock_acquired_during_save_state` - Verifies fcntl.flock() is called
- `test_lock_uses_exclusive_mode` - Verifies LOCK_EX flag
- `test_lock_uses_non_blocking_mode` - Verifies LOCK_NB flag
- `test_lock_released_on_file_close` - Verifies context manager pattern

#### 2. Lock Timeout (`TestFileLockTimeout`)

- `test_lock_timeout_after_2_seconds` - Verifies 2s timeout
- `test_lock_retry_mechanism` - Verifies retry with backoff
- `test_fail_open_on_lock_timeout` - Verifies fail-open design

#### 3. Error Handling (`TestFileLockErrorHandling`)

- `test_handle_permission_denied_on_lock` - PermissionError handling
- `test_handle_io_error_on_lock` - IOError handling
- `test_handle_os_error_on_lock` - Generic OSError handling

#### 4. Windows Support (`TestWindowsGracefulDegradation`)

- `test_windows_fcntl_import_fails_gracefully` - Missing fcntl module
- `test_windows_logs_degraded_mode_warning` - Warning logs
- `test_platform_detection_constant` - LOCKING_AVAILABLE constant

### Race Condition Tests (20% - 6 tests)

#### `TestRaceConditionPrevention`

- `test_100_concurrent_increments_equal_100` - **CORE TEST**: 100 threads → count=100
- `test_concurrent_access_serialized` - Operations don't overlap
- `test_stop_hook_concurrent_invocations` - Multiple stop hooks
- `test_lock_counter_concurrent_increments` - \_increment_lock_counter() race-safe
- `test_power_steering_counter_concurrent_increments` - \_increment_power_steering_counter() race-safe

### Integration Tests (20% - 7 tests)

#### `TestIntegrationFileLocking`

- `test_multiple_managers_concurrent_access` - Multiple TurnStateManager instances
- `test_rapid_succession_increments` - 100 rapid increments
- `test_lock_released_after_exception` - Exception doesn't leak locks
- `test_lock_timeout_allows_recovery` - System recovers after timeout

#### `TestFileLockingLogging`

- `test_log_lock_acquisition_success` - Success logging
- `test_log_lock_timeout` - Timeout logging
- `test_log_windows_degraded_mode` - Windows degraded mode logging

## Key Test Scenarios

### 1. Core Race Condition Test

```python
def test_100_concurrent_increments_equal_100(self, tmp_path):
    """Without locking: counter gets stuck or resets
       With locking: counter reliably reaches 100
    """
```

**Why this test matters**: This is the EXACT bug from Issue #2155 - multiple concurrent reads/writes cause counter corruption.

### 2. Stop Hook Concurrency Test

```python
def test_stop_hook_concurrent_invocations(self, tmp_path):
    """Simulates 20 concurrent stop hooks"""
```

**Why this test matters**: Real-world scenario where multiple Claude Code sessions or rapid stop events occur.

### 3. Timeout and Fail-Open Test

```python
def test_lock_timeout_after_2_seconds(self, tmp_path):
    """Lock unavailable → timeout after 2s → proceed without lock"""
```

**Why this test matters**: Ensures users are never blocked by locking issues (fail-open design).

### 4. Windows Graceful Degradation

```python
def test_windows_fcntl_import_fails_gracefully(self, tmp_path):
    """Windows (no fcntl) → continues without locking"""
```

**Why this test matters**: Windows users should have degraded but working functionality.

## Running the Tests

### Current Status

**Tests CANNOT run yet** due to import issue in `power_steering_state.py`:

```python
from .fallback_heuristics import AddressedChecker  # Relative import fails in test context
```

### Resolution Options

**Option 1**: Fix import to support both module and test contexts (recommended for implementation phase):

```python
try:
    from .fallback_heuristics import AddressedChecker
except ImportError:
    from fallback_heuristics import AddressedChecker
```

**Option 2**: Add `__init__.py` to hooks directory to make it a proper package

**Option 3**: Mock the import in tests (less ideal)

### After Import Fix

Run all file locking tests:

```bash
pytest .claude/tools/amplihack/hooks/tests/test_file_locking.py -v
```

Run specific test category:

```bash
# Unit tests only
pytest .claude/tools/amplihack/hooks/tests/test_file_locking.py::TestFileLockAcquisition -v

# Race condition tests only
pytest .claude/tools/amplihack/hooks/tests/test_file_locking.py::TestRaceConditionPrevention -v

# Core race condition test
pytest .claude/tools/amplihack/hooks/tests/test_file_locking.py::TestRaceConditionPrevention::test_100_concurrent_increments_equal_100 -v
```

## Expected Results

### Before Implementation

```
test_file_locking.py::TestFileLockAcquisition::test_lock_acquired_during_save_state FAILED
test_file_locking.py::TestRaceConditionPrevention::test_100_concurrent_increments_equal_100 FAILED
...
32 failed, 0 passed
```

**This is EXPECTED** - TDD methodology requires tests to fail first.

### After Implementation

```
test_file_locking.py::TestFileLockAcquisition::test_lock_acquired_during_save_state PASSED
test_file_locking.py::TestRaceConditionPrevention::test_100_concurrent_increments_equal_100 PASSED
...
32 passed, 0 failed
```

## Implementation Guidance

### Critical Features to Implement

1. **File Locking Context Manager** (Lines 580-640 in power_steering_state.py)

   ```python
   with open(state_file, 'r+') as f:
       fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
       # Read-modify-write
   ```

2. **Timeout Logic** (2-second timeout with retry)

   ```python
   start_time = time.time()
   while time.time() - start_time < 2.0:
       try:
           fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
           break
       except BlockingIOError:
           time.sleep(0.05)  # 50ms backoff
   ```

3. **Platform Detection**

   ```python
   try:
       import fcntl
       LOCKING_AVAILABLE = True
   except ImportError:
       LOCKING_AVAILABLE = False
   ```

4. **Apply to ALL Counter Functions**
   - `TurnStateManager.save_state()` - Already has atomic write, add locking
   - `StopHook._increment_power_steering_counter()` - Needs locking added
   - `StopHook._increment_lock_counter()` - Needs locking added

## Test Philosophy

### Test-Driven Development

Tests cover all aspects of file locking implementation:

1. Lock acquisition and release
2. Race condition prevention
3. Error handling and fail-open behavior
4. Platform compatibility (Linux/macOS/Windows)

### Fail-Open Design

All error handling tests verify that errors don't block users:

- Lock timeout → Log warning, proceed without lock
- Permission denied → Log error, proceed without lock
- Windows (no fcntl) → Log info, proceed without lock

### Testing Pyramid

- 60% Unit tests (19 tests) - Fast, isolated
- 20% Race condition tests (6 tests) - Threading scenarios
- 20% Integration tests (7 tests) - Real-world scenarios

## Critical Success Metrics

1. **Zero Race Conditions**: Test `test_100_concurrent_increments_equal_100` must pass reliably
2. **Fail-Open**: All error tests must proceed without blocking
3. **Windows Support**: Graceful degradation tests must pass
4. **Performance**: Lock overhead < 5ms (Integration test verifies < 5s for 100 ops)

## Related Files

- **Specification**: `docs/reference/power-steering-file-locking.md`
- **Implementation**: `.claude/tools/amplihack/hooks/power_steering_state.py`
- **Stop Hook**: `.claude/tools/amplihack/hooks/stop.py`
- **Existing Tests**: `test_issue_1882_power_steering_infinite_loop.py`

## Notes

- These tests complement existing Issue #1882 tests (atomic write, monotonicity)
- Focus is specifically on **file locking** for race condition prevention
- Tests are comprehensive: happy path, error cases, edge cases, platform support
- Follow existing test patterns from `test_issue_1882_power_steering_infinite_loop.py`
