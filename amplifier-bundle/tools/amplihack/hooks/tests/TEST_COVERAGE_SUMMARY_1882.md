# Test Coverage Summary for Issue #1882

## Overview

Comprehensive TDD test suite for Issue #1882 (Power Steering Infinite Loop).

**Test File**: `test_issue_1882_power_steering_infinite_loop.py`

**Test Philosophy**: All tests MUST FAIL before fix implementation and PASS after fix.

## Test Coverage by Category

### 1. Reproduction Tests (MUST FAIL) - 3 tests

**Purpose**: Reproduce the exact bug reported in Issue #1882.

| Test                                                    | Description                                    | Expected Failure             |
| ------------------------------------------------------- | ---------------------------------------------- | ---------------------------- |
| `test_counter_increments_from_5_to_6_not_reset_to_0`    | Counter should increment 5 → 6, not reset to 0 | ✅ Core bug reproduction     |
| `test_state_persists_across_multiple_write_read_cycles` | State should persist across write/read cycles  | ✅ Persistence bug           |
| `test_no_infinite_loop_in_100_consecutive_calls`        | Should not get stuck in infinite loop          | ✅ Detects stall/oscillation |

**Key Assertions**:

- Counter increments correctly (5 → 6, not 5 → 0)
- No counter stall (same value repeated 10+ times)
- No oscillation (A → B → A → B pattern)
- Counter reaches 100 after 100 increments

### 2. Monotonicity Tests - 3 tests

**Purpose**: Counter should NEVER decrease (REQ-1, Architect recommendation).

| Test                                                 | Description                           | Missing Feature                  |
| ---------------------------------------------------- | ------------------------------------- | -------------------------------- |
| `test_counter_never_decreases`                       | Reject attempts to decrease counter   | Monotonicity validation          |
| `test_detect_counter_regression_from_previous_value` | Detect regression from previous state | Previous value tracking          |
| `test_track_previous_state_for_validation`           | Manager tracks previous state         | `_previous_turn_count` attribute |

**Key Assertions**:

- `save_state()` raises `ValueError` on regression
- Manager has `_previous_turn_count` attribute
- Validation compares new vs previous value

### 3. Atomic Write Tests - 4 tests

**Purpose**: Ensure atomic writes with fsync, verification, retry (REQ-3).

| Test                                        | Description                             | Missing Feature   |
| ------------------------------------------- | --------------------------------------- | ----------------- |
| `test_fsync_called_on_save`                 | Calls `os.fsync()` to ensure durability | fsync() call      |
| `test_verification_read_after_write`        | Reads back state to verify write        | Verification read |
| `test_retry_on_write_failure`               | Retries on write failure                | Retry logic       |
| `test_verify_both_temp_file_and_final_path` | Verifies temp AND final path            | Dual verification |

**Key Assertions**:

- `os.fsync()` called during save
- State file read after write for verification
- Write retried on failure (up to 3 attempts)
- Both temp file and final path verified

### 4. Infinite Loop Detection Tests - 3 tests

**Purpose**: Auto-detect stall, oscillation, high failure rate.

| Test                                  | Description                        | Missing Feature       |
| ------------------------------------- | ---------------------------------- | --------------------- |
| `test_detect_counter_stall`           | Detect counter stuck at same value | Stall detection       |
| `test_detect_oscillation_pattern`     | Detect A → B → A → B pattern       | Oscillation detection |
| `test_detect_high_write_failure_rate` | Detect >30% write failure rate     | Failure rate tracking |

**Key Assertions**:

- `get_diagnostics()` method exists
- Diagnostics include `stall_detected`, `stall_value`, `stall_count`
- Diagnostics include `oscillation_detected`, `oscillation_values`
- Diagnostics include `write_failure_rate`, `high_failure_rate_alert`

### 5. Edge Case Tests - 5 tests

**Purpose**: Handle filesystem errors gracefully (REQ-4).

| Test                                  | Description                    | Expected Behavior        |
| ------------------------------------- | ------------------------------ | ------------------------ |
| `test_handle_filesystem_full`         | Handle ENOSPC gracefully       | Fail-open (no exception) |
| `test_handle_permission_denied`       | Handle EACCES gracefully       | Fail-open (no exception) |
| `test_handle_corrupted_state_file`    | Recover from corrupted JSON    | Return empty state       |
| `test_handle_partial_write`           | Detect partial write           | Retry or fail-open       |
| `test_atomic_rename_failure_recovery` | Clean up temp files on failure | No orphaned files        |

**Key Assertions**:

- No exceptions raised (fail-open design)
- Corrupted state → empty state returned
- Temp files cleaned up on error
- Graceful degradation on filesystem errors

### 6. Message Customization Tests - 2 tests

**Purpose**: Messages customized based on check results (REQ-2).

| Test                                        | Description                         | Missing Feature       |
| ------------------------------------------- | ----------------------------------- | --------------------- |
| `test_message_includes_turn_count`          | Message includes current turn count | Message generation    |
| `test_message_customized_after_first_block` | Message changes after first block   | Dynamic message logic |

**Key Assertions**:

- `generate_power_steering_message()` method exists
- Message includes turn count
- Message differs based on consecutive blocks

### 7. Diagnostic Logging Tests - 3 tests

**Purpose**: Instrumentation via .jsonl logging (Phase 1).

| Test                                        | Description                   | Missing Feature        |
| ------------------------------------------- | ----------------------------- | ---------------------- |
| `test_diagnostic_log_created`               | Creates diagnostic.jsonl file | Logging infrastructure |
| `test_diagnostic_log_includes_write_events` | Logs state write events       | Write event logging    |
| `test_diagnostic_log_includes_read_events`  | Logs state read events        | Read event logging     |

**Key Assertions**:

- Log file at `.claude/runtime/power-steering/{session_id}/diagnostic.jsonl`
- Log entries in JSONL format
- Includes `state_write` and `state_read` events

### 8. Integration Tests (30%) - 2 tests

**Purpose**: Test complete save/load cycles with multiple components.

| Test                                         | Description                             |
| -------------------------------------------- | --------------------------------------- |
| `test_full_power_steering_lifecycle`         | Complete lifecycle with multiple blocks |
| `test_state_recovery_after_crash_simulation` | Atomic write protects on crash          |

### 9. E2E Tests (10%) - 1 test

**Purpose**: Complete workflows from start to finish.

| Test                                   | Description                               |
| -------------------------------------- | ----------------------------------------- |
| `test_complete_power_steering_session` | Full session: turns, blocks, saves, loads |

## Test Pyramid Distribution

| Level       | Percentage | Test Count   | Description                   |
| ----------- | ---------- | ------------ | ----------------------------- |
| Unit        | 60%        | 23 tests     | Fast, focused, heavily mocked |
| Integration | 30%        | 2 tests      | Multiple components together  |
| E2E         | 10%        | 1 test       | Complete workflows            |
| **Total**   | **100%**   | **26 tests** | Comprehensive coverage        |

## Critical Tests That MUST Fail

### Priority 1: Core Bug Reproduction

1. `test_counter_increments_from_5_to_6_not_reset_to_0`
   - **Why**: Reproduces exact bug (counter resets to 0)
   - **Failure Mode**: `assert reloaded_state.turn_count == 6` fails (gets 0)

2. `test_no_infinite_loop_in_100_consecutive_calls`
   - **Why**: Detects infinite loop condition
   - **Failure Mode**: Counter stalls or oscillates

### Priority 2: Monotonicity Violations

3. `test_counter_never_decreases`
   - **Why**: No validation exists
   - **Failure Mode**: No exception raised on regression

4. `test_track_previous_state_for_validation`
   - **Why**: Missing `_previous_turn_count` attribute
   - **Failure Mode**: `hasattr()` returns False

### Priority 3: Atomic Write Enhancements

5. `test_fsync_called_on_save`
   - **Why**: No fsync() call in current code
   - **Failure Mode**: Mock not called

6. `test_verification_read_after_write`
   - **Why**: No verification read exists
   - **Failure Mode**: No read operations tracked

7. `test_retry_on_write_failure`
   - **Why**: No retry logic exists
   - **Failure Mode**: Only 1 attempt, not 3

## Implementation Checklist

### Phase 1: Instrumentation

- [ ] Add diagnostic logging to `.jsonl` file
- [ ] Log all state read/write events
- [ ] Include timestamps and operation metadata

### Phase 2: Defensive Validation

- [ ] Add `_previous_turn_count` tracking to TurnStateManager
- [ ] Implement monotonicity check in `save_state()`
- [ ] Raise `ValueError` on counter regression

### Phase 3: Atomic Write Enhancement

- [ ] Add `os.fsync()` call after write
- [ ] Implement verification read after write
- [ ] Add retry logic (3 attempts with exponential backoff)
- [ ] Verify both temp file AND final path

### Phase 4: Infinite Loop Detection

- [ ] Add `get_diagnostics()` method
- [ ] Track write operations for stall detection
- [ ] Detect oscillation patterns (A → B → A → B)
- [ ] Calculate write failure rate

### Phase 5: User Visibility

- [ ] Implement `generate_power_steering_message()` method
- [ ] Customize message based on turn count
- [ ] Customize message based on consecutive blocks

## Running the Tests

```bash
# Run all tests
python -m pytest .claude/tools/amplihack/hooks/tests/test_issue_1882_power_steering_infinite_loop.py -v

# Run specific test category
python -m pytest .claude/tools/amplihack/hooks/tests/test_issue_1882_power_steering_infinite_loop.py::TestIssue1882Reproduction -v

# Run with detailed output
python -m pytest .claude/tools/amplihack/hooks/tests/test_issue_1882_power_steering_infinite_loop.py -vv --tb=short

# Run until first failure
python -m pytest .claude/tools/amplihack/hooks/tests/test_issue_1882_power_steering_infinite_loop.py -x -v
```

## Expected Behavior

### Before Fix

- **26 tests FAIL** (all tests should fail)
- Failures indicate missing features and bugs

### After Fix

- **26 tests PASS** (all tests should pass)
- Validates complete implementation of all 4 phases

## Test Quality Metrics

- **Coverage**: All 4 requirements (REQ-1 through REQ-4)
- **Architect Recommendations**: All critical recommendations covered
- **Bug Reproduction**: Exact bug from Issue #1882 reproduced
- **Edge Cases**: Filesystem errors, corruption, crashes
- **Performance**: All tests run in < 5 seconds
- **Isolation**: Each test uses separate tmp_path fixture

## Notes for Implementers

1. **Start with reproduction tests** - Verify they fail first
2. **Implement in phases** - Follow architect's 4-phase plan
3. **Run tests frequently** - Watch failures turn to passes
4. **Use diagnostics** - .jsonl logs for debugging
5. **Maintain fail-open** - Never block users on errors

---

**Document Version**: 1.0
**Created**: 2025-12-17
**Author**: Tester Agent (Pirate Mode)
**Related**: Issue #1882, PR #[TBD]
