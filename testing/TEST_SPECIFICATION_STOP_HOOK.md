# Comprehensive Test Suite Specification: Stop Hook Fix (Issue #962)

## Executive Summary

This document provides a comprehensive test plan for validating the stop hook
API compliance fix. The test suite follows the testing pyramid principle (60%
unit, 30% integration, 10% E2E) and ensures all requirements from Issue #962 are
met.

## Test Coverage Analysis

### Current State

**Fixed Implementation Location**:
`../worktree-issue-962/.claude/tools/amplihack/hooks/stop.py`

**API Specification Compliance**:

- Input: JSON with session_id, hook_event_name, etc.
- Output when allowing stop: `{}` (empty dict)
- Output when blocking stop: `{"decision": "block", "reason": "..."}`
- Exit code: 0 for all successful operations

**Critical Components**:

1. `StopHook.process()` - Main processing logic
2. `StopHook.read_continuation_prompt()` - Prompt file reading
3. `HookProcessor.run()` - Hook lifecycle management
4. Lock file detection and handling
5. JSON input/output processing

## Test Pyramid Structure

### Level 1: Unit Tests (60% - ~36 tests)

**Purpose**: Test individual functions and methods in isolation

#### 1.1 StopHook.process() Method Tests (12 tests)

**Test ID**: UNIT-PROCESS-001 **Test**: No lock file exists **Input**:
`{"session_id": "test_123", "hook_event_name": "stop"}` **Expected Output**:
`{}` **Expected Behavior**: Returns empty dict, logs "No lock active - allowing
stop"

**Test ID**: UNIT-PROCESS-002 **Test**: Lock file exists with default prompt
**Input**: `{"session_id": "test_123", "hook_event_name": "stop"}`
**Precondition**: Lock file `~/.amplihack/.claude/tools/amplihack/.lock_active` exists
**Expected Output**:

```json
{
  "decision": "block",
  "reason": "we must keep pursuing the user's objective and must not stop the turn - look for any additional TODOs, next steps, or unfinished work and pursue it diligently in as many parallel tasks as you can"
}
```

**Test ID**: UNIT-PROCESS-003 **Test**: Lock file exists with custom prompt
**Input**: `{"session_id": "test_123", "hook_event_name": "stop"}`
**Precondition**:

- Lock file exists
- Custom prompt file exists with content "Custom continuation message"
  **Expected Output**:

```json
{
  "decision": "block",
  "reason": "Custom continuation message"
}
```

**Test ID**: UNIT-PROCESS-004 **Test**: Permission error accessing lock file
**Input**: `{"session_id": "test_123", "hook_event_name": "stop"}` **Mock**:
`lock_flag.exists()` raises `PermissionError` **Expected Output**: `{}`
**Expected Behavior**: Fail-safe behavior, logs warning

**Test ID**: UNIT-PROCESS-005 **Test**: OSError accessing lock file **Input**:
`{"session_id": "test_123", "hook_event_name": "stop"}` **Mock**:
`lock_flag.exists()` raises `OSError` **Expected Output**: `{}` **Expected
Behavior**: Fail-safe behavior, logs warning

**Test ID**: UNIT-PROCESS-006 **Test**: Empty input data **Input**: `{}`
**Expected Output**: `{}` **Expected Behavior**: Handles gracefully without
errors

**Test ID**: UNIT-PROCESS-007 **Test**: Input with extra fields **Input**:
`{"session_id": "test_123", "hook_event_name": "stop", "extra": "field"}`
**Expected Output**: `{}` or block decision based on lock **Expected Behavior**:
Ignores extra fields

**Test ID**: UNIT-PROCESS-008 **Test**: Lock file created during execution
**Input**: `{"session_id": "test_123", "hook_event_name": "stop"}` **Test
Logic**: Check lock state atomically **Expected Output**: Consistent with lock
state at check time

**Test ID**: UNIT-PROCESS-009 **Test**: Lock file deleted during execution
**Input**: `{"session_id": "test_123", "hook_event_name": "stop"}` **Test
Logic**: Handle race condition gracefully **Expected Behavior**: No crash,
returns safe default

**Test ID**: UNIT-PROCESS-010 **Test**: Output structure validation - no extra
fields **Input**: `{"session_id": "test_123", "hook_event_name": "stop"}`
**Expected**: Output only contains "decision" and "reason" OR is empty
**Expected Behavior**: No "continue" field or other non-API fields

**Test ID**: UNIT-PROCESS-011 **Test**: Output structure validation - field
types **Input**: Lock active scenario **Expected**: "decision" is string,
"reason" is string **Expected Behavior**: Type validation passes

**Test ID**: UNIT-PROCESS-012 **Test**: Metrics saved on lock block **Input**:
Lock active scenario **Expected Behavior**: `save_metric("lock_blocks", 1)`
called

#### 1.2 StopHook.read_continuation_prompt() Tests (9 tests)

**Test ID**: UNIT-PROMPT-001 **Test**: No custom prompt file exists **Expected
Return**: `DEFAULT_CONTINUATION_PROMPT` constant **Expected Behavior**: Logs "No
custom continuation prompt file - using default"

**Test ID**: UNIT-PROMPT-002 **Test**: Custom prompt file exists with valid
content **Precondition**: File contains "Continue working on tasks" **Expected
Return**: "Continue working on tasks" **Expected Behavior**: Logs character
count

**Test ID**: UNIT-PROMPT-003 **Test**: Custom prompt file is empty
**Precondition**: File exists but contains only whitespace **Expected Return**:
`DEFAULT_CONTINUATION_PROMPT` **Expected Behavior**: Logs "Custom continuation
prompt file is empty"

**Test ID**: UNIT-PROMPT-004 **Test**: Custom prompt exceeds 1000 characters
**Precondition**: File contains 1001 character string **Expected Return**:
`DEFAULT_CONTINUATION_PROMPT` **Expected Behavior**: Logs "Custom prompt too
long" WARNING

**Test ID**: UNIT-PROMPT-005 **Test**: Custom prompt between 500-1000 characters
**Precondition**: File contains 750 character string **Expected Return**: The
750 character string **Expected Behavior**: Logs "Custom prompt is long" WARNING
but uses it

**Test ID**: UNIT-PROMPT-006 **Test**: Permission error reading custom prompt
**Mock**: `read_text()` raises `PermissionError` **Expected Return**:
`DEFAULT_CONTINUATION_PROMPT` **Expected Behavior**: Logs error and falls back

**Test ID**: UNIT-PROMPT-007 **Test**: OSError reading custom prompt **Mock**:
`read_text()` raises `OSError` **Expected Return**:
`DEFAULT_CONTINUATION_PROMPT` **Expected Behavior**: Logs error and falls back

**Test ID**: UNIT-PROMPT-008 **Test**: Unicode decode error reading custom
prompt **Mock**: `read_text()` raises `UnicodeDecodeError` **Expected Return**:
`DEFAULT_CONTINUATION_PROMPT` **Expected Behavior**: Logs error and falls back

**Test ID**: UNIT-PROMPT-009 **Test**: Custom prompt with special characters
**Precondition**: File contains Unicode, newlines, quotes **Expected Return**:
The exact content (stripped) **Expected Behavior**: Handles special characters
correctly

#### 1.3 HookProcessor.run() Tests (8 tests)

**Test ID**: UNIT-RUN-001 **Test**: Valid JSON input to stdout output **Input**:
`{"session_id": "test"}` **Expected**: Valid JSON written to stdout **Expected
Behavior**: Exit code 0

**Test ID**: UNIT-RUN-002 **Test**: Empty JSON input **Input**: `{}`
**Expected**: Valid JSON output **Expected Behavior**: Exit code 0

**Test ID**: UNIT-RUN-003 **Test**: Invalid JSON input **Input**:
`{invalid json}` **Expected Output**: `{"error": "Invalid JSON input"}`
**Expected Behavior**: Exit code 0 (fail-safe)

**Test ID**: UNIT-RUN-004 **Test**: Empty stdin input **Input**: Empty string
**Expected Output**: `{}` **Expected Behavior**: Exit code 0

**Test ID**: UNIT-RUN-005 **Test**: Process method returns None **Mock**:
`process()` returns `None` **Expected Output**: `{}` **Expected Behavior**:
Converts None to empty dict

**Test ID**: UNIT-RUN-006 **Test**: Process method returns non-dict **Mock**:
`process()` returns `"string"` **Expected Output**: `{"result": "string"}`
**Expected Behavior**: Wraps non-dict in dict

**Test ID**: UNIT-RUN-007 **Test**: Process method raises exception **Mock**:
`process()` raises `RuntimeError("Test error")` **Expected Output**: `{}`
**Expected Behavior**: Logs error, writes empty dict, exit code 0

**Test ID**: UNIT-RUN-008 **Test**: Logging functionality **Test**: Verify log
messages written to log file **Expected**: Log file contains timestamped entries

#### 1.4 JSON Serialization Tests (4 tests)

**Test ID**: UNIT-JSON-001 **Test**: Output dict is JSON serializable - allow
case **Output**: `{}` **Expected**: `json.dumps({})` succeeds

**Test ID**: UNIT-JSON-002 **Test**: Output dict is JSON serializable - block
case **Output**: `{"decision": "block", "reason": "Continue working"}`
**Expected**: `json.dumps()` produces valid JSON

**Test ID**: UNIT-JSON-003 **Test**: Output parseable by Claude Code **Test**:
Verify output matches expected schema **Expected**: Schema validation passes

**Test ID**: UNIT-JSON-004 **Test**: Unicode in reason field **Output**:
`{"decision": "block", "reason": "Continue with 日本語"}` **Expected**: Properly
serialized with UTF-8

#### 1.5 Path and File System Tests (3 tests)

**Test ID**: UNIT-PATH-001 **Test**: Lock file path resolution **Expected**:
Path is `~/.amplihack/.claude/tools/amplihack/.lock_active`

**Test ID**: UNIT-PATH-002 **Test**: Continuation prompt file path resolution
**Expected**: Path is `~/.amplihack/.claude/tools/amplihack/.continuation_prompt`

**Test ID**: UNIT-PATH-003 **Test**: Log file path resolution **Expected**: Path
is `~/.amplihack/.claude/runtime/logs/stop.log`

### Level 2: Integration Tests (30% - ~18 tests)

**Purpose**: Test component interactions and subprocess execution

#### 2.1 Subprocess Execution Tests (6 tests)

**Test ID**: INTEG-SUBPROCESS-001 **Test**: Hook executed as subprocess with no
lock **Execution**: `python stop.py < input.json` **Input**:
`{"session_id": "test_123"}` **Expected**:

- stdout contains `{}`
- stderr is empty
- exit code is 0

**Test ID**: INTEG-SUBPROCESS-002 **Test**: Hook executed as subprocess with
active lock **Precondition**: Lock file exists **Execution**:
`python stop.py < input.json` **Input**: `{"session_id": "test_123"}`
**Expected**:

- stdout contains block decision JSON
- stderr is empty (no diagnostic output during normal operation)
- exit code is 0

**Test ID**: INTEG-SUBPROCESS-003 **Test**: Hook executed with corrupted JSON
input **Execution**: `echo '{bad json}' | python stop.py` **Expected**:

- stdout contains `{"error": "Invalid JSON input"}`
- stderr may contain error details
- exit code is 0 (fail-safe)

**Test ID**: INTEG-SUBPROCESS-004 **Test**: Hook executed with no stdin
**Execution**: `python stop.py < /dev/null` **Expected**:

- stdout contains `{}`
- exit code is 0

**Test ID**: INTEG-SUBPROCESS-005 **Test**: Hook execution performance
**Execution**: Time the subprocess execution **Expected**: Completes in < 200ms
**Performance Requirement**: Hook must be fast to avoid blocking UI

**Test ID**: INTEG-SUBPROCESS-006 **Test**: Multiple concurrent hook executions
**Execution**: Run 5 instances simultaneously **Expected**: All succeed, no race
conditions, consistent results

#### 2.2 Lock File Integration Tests (4 tests)

**Test ID**: INTEG-LOCK-001 **Test**: Lock file created and hook responds
immediately **Steps**:

1. Execute hook (no lock) - verify allows
2. Create lock file
3. Execute hook - verify blocks **Expected**: Second execution blocks

**Test ID**: INTEG-LOCK-002 **Test**: Lock file deleted and hook responds
immediately **Steps**:

1. Create lock file
2. Execute hook - verify blocks
3. Delete lock file
4. Execute hook - verify allows **Expected**: Fourth execution allows

**Test ID**: INTEG-LOCK-003 **Test**: Continuous work mode scenario **Steps**:

1. Create lock file with custom prompt
2. Execute hook multiple times
3. Verify each execution blocks with same prompt **Expected**: Consistent
   blocking behavior

**Test ID**: INTEG-LOCK-004 **Test**: Lock file permission changes **Steps**:

1. Create lock file with restricted permissions
2. Execute hook **Expected**: Handles permission error gracefully

#### 2.3 Custom Prompt Integration Tests (4 tests)

**Test ID**: INTEG-PROMPT-001 **Test**: Default prompt to custom prompt
transition **Steps**:

1. Execute with no custom prompt file
2. Create custom prompt file
3. Execute again **Expected**: Second execution uses custom prompt

**Test ID**: INTEG-PROMPT-002 **Test**: Custom prompt file updated during
execution **Steps**:

1. Create custom prompt "Version 1"
2. Execute hook - verify uses "Version 1"
3. Update prompt to "Version 2"
4. Execute hook - verify uses "Version 2" **Expected**: Reads fresh content each
   time

**Test ID**: INTEG-PROMPT-003 **Test**: Custom prompt file deleted during lock
active **Steps**:

1. Create lock and custom prompt
2. Execute hook - verify uses custom
3. Delete custom prompt
4. Execute hook - verify falls back to default **Expected**: Graceful fallback
   behavior

**Test ID**: INTEG-PROMPT-004 **Test**: Custom prompt with edge case content
**Content**: Very long line, special Unicode, control characters **Expected**:
Handles robustly or falls back

#### 2.4 Logging and Metrics Integration (4 tests)

**Test ID**: INTEG-LOG-001 **Test**: Log file created and populated
**Execution**: Run hook multiple times **Expected**: Log file contains entries
for each execution

**Test ID**: INTEG-LOG-002 **Test**: Metrics file created and populated
**Execution**: Run hook with lock active **Expected**: Metrics file contains
"lock_blocks" entry

**Test ID**: INTEG-LOG-003 **Test**: Log rotation when file exceeds 10MB
**Precondition**: Create large log file **Expected**: Log file rotated with
timestamp backup

**Test ID**: INTEG-LOG-004 **Test**: Concurrent logging from multiple hook
executions **Execution**: Run 10 hooks simultaneously **Expected**: All log
entries present, no corruption

### Level 3: End-to-End Tests (10% - ~6 tests)

**Purpose**: Test complete workflows and real-world scenarios

#### 3.1 Complete Workflow Tests (3 tests)

**Test ID**: E2E-WORKFLOW-001 **Test**: Standard stop without lock (user stops
session) **Scenario**: User completes task and stops **Steps**:

1. No lock file exists
2. Claude Code calls stop hook
3. Hook returns `{}`
4. Claude Code stops normally **Expected**: Clean stop, no messages to user

**Test ID**: E2E-WORKFLOW-002 **Test**: Continuous work mode active (hook blocks
stop) **Scenario**: User enables continuous work, tries to stop **Steps**:

1. Lock file created (continuous work enabled)
2. Custom prompt set to "Complete all TODOs"
3. Claude Code calls stop hook
4. Hook returns block decision with custom prompt
5. Claude Code continues with prompt **Expected**: Claude continues working,
   user sees prompt

**Test ID**: E2E-WORKFLOW-003 **Test**: Continuous work mode disabled (user
regains control) **Scenario**: User disables continuous work after enabling
**Steps**:

1. Lock file exists
2. Hook blocks stop (continuous work happening)
3. User disables mode (deletes lock file)
4. Claude Code calls stop hook
5. Hook returns `{}`
6. Claude Code stops **Expected**: Clean stop after mode disabled

#### 3.2 Error Recovery Tests (2 tests)

**Test ID**: E2E-ERROR-001 **Test**: Recovery from corrupted lock file
**Scenario**: Lock file exists but is corrupted/inaccessible **Steps**:

1. Create lock file with invalid permissions
2. Claude Code calls stop hook
3. Hook catches permission error
4. Hook returns `{}` (fail-safe) **Expected**: Claude Code stops normally, error
   logged

**Test ID**: E2E-ERROR-002 **Test**: Recovery from missing directories
**Scenario**: Runtime directories don't exist **Steps**:

1. Delete `~/.amplihack/.claude/runtime/logs`
2. Execute hook **Expected**: Hook creates directories, executes normally

#### 3.3 Performance and Reliability Test (1 test)

**Test ID**: E2E-PERF-001 **Test**: Hook performance under load **Scenario**:
Rapid repeated stop calls **Steps**:

1. Execute hook 100 times in quick succession
2. Mix lock active/inactive states
3. Measure execution times **Expected**:

- All executions < 200ms
- No failures
- Consistent results
- No memory leaks

## Mock and Fixture Requirements

### Fixtures

#### 1. `temp_project_root` (pytest fixture)

```python
@pytest.fixture
def temp_project_root(tmp_path):
    """Create temporary project structure."""
    project = tmp_path / "project"
    project.mkdir()

    # Create directory structure
    (project / ".claude/tools/amplihack/hooks").mkdir(parents=True)
    (project / ".claude/runtime/logs").mkdir(parents=True)
    (project / ".claude/runtime/metrics").mkdir(parents=True)

    return project
```

#### 2. `stop_hook` (pytest fixture)

```python
@pytest.fixture
def stop_hook(temp_project_root):
    """Create StopHook instance with test paths."""
    hook = StopHook()
    hook.project_root = temp_project_root
    hook.lock_flag = temp_project_root / ".claude/tools/amplihack/.lock_active"
    hook.continuation_prompt_file = temp_project_root / ".claude/tools/amplihack/.continuation_prompt"
    hook.log_dir = temp_project_root / ".claude/runtime/logs"
    hook.metrics_dir = temp_project_root / ".claude/runtime/metrics"
    hook.log_file = hook.log_dir / "stop.log"
    return hook
```

#### 3. `active_lock` (pytest fixture)

```python
@pytest.fixture
def active_lock(stop_hook):
    """Create active lock file."""
    stop_hook.lock_flag.touch()
    yield stop_hook.lock_flag
    if stop_hook.lock_flag.exists():
        stop_hook.lock_flag.unlink()
```

#### 4. `custom_prompt` (pytest fixture)

```python
@pytest.fixture
def custom_prompt(stop_hook):
    """Create custom continuation prompt."""
    def _create_prompt(content):
        stop_hook.continuation_prompt_file.write_text(content, encoding="utf-8")
        return stop_hook.continuation_prompt_file
    return _create_prompt
```

#### 5. `captured_subprocess` (pytest fixture)

```python
@pytest.fixture
def captured_subprocess():
    """Run hook as subprocess and capture output."""
    def _run(input_data, lock_active=False):
        # Setup lock if needed
        # Run subprocess
        # Capture stdout, stderr, exit code
        # Return result
        pass
    return _run
```

### Mocks

#### 1. Mock Path.exists()

```python
@patch.object(Path, 'exists')
def test_with_mocked_exists(mock_exists):
    mock_exists.return_value = True  # or False
```

#### 2. Mock Path.read_text()

```python
@patch.object(Path, 'read_text')
def test_with_mocked_read(mock_read):
    mock_read.side_effect = PermissionError("Access denied")
```

#### 3. Mock process() method

```python
@patch.object(StopHook, 'process')
def test_run_with_mocked_process(mock_process):
    mock_process.return_value = {"decision": "block", "reason": "test"}
```

#### 4. Mock save_metric()

```python
@patch.object(StopHook, 'save_metric')
def test_metrics_called(mock_save_metric):
    # Test code
    mock_save_metric.assert_called_once_with("lock_blocks", 1)
```

## Test File Structure

```
tests/
├── unit/
│   ├── test_stop_hook_process.py           # UNIT-PROCESS-* tests
│   ├── test_stop_hook_prompt.py            # UNIT-PROMPT-* tests
│   ├── test_hook_processor_run.py          # UNIT-RUN-* tests
│   ├── test_stop_hook_json.py              # UNIT-JSON-* tests
│   └── test_stop_hook_paths.py             # UNIT-PATH-* tests
├── integration/
│   ├── test_stop_hook_subprocess.py        # INTEG-SUBPROCESS-* tests
│   ├── test_stop_hook_lock_integration.py  # INTEG-LOCK-* tests
│   ├── test_stop_hook_prompt_integration.py # INTEG-PROMPT-* tests
│   └── test_stop_hook_logging.py           # INTEG-LOG-* tests
├── e2e/
│   ├── test_stop_hook_workflows.py         # E2E-WORKFLOW-* tests
│   ├── test_stop_hook_error_recovery.py    # E2E-ERROR-* tests
│   └── test_stop_hook_performance.py       # E2E-PERF-* tests
└── conftest.py                              # Shared fixtures
```

## Performance Testing Requirements

### Performance Criteria

**Critical Performance Requirement**: Hook execution must complete in < 200ms

**Rationale**: The stop hook is called synchronously by Claude Code. Slow hooks
degrade user experience.

### Performance Tests

#### Test: Hook Execution Time (INTEG-SUBPROCESS-005)

```python
def test_hook_execution_time_no_lock(captured_subprocess):
    """Verify hook completes in < 200ms with no lock."""
    input_data = {"session_id": "perf_test"}

    start = time.perf_counter()
    result = captured_subprocess(input_data, lock_active=False)
    duration_ms = (time.perf_counter() - start) * 1000

    assert duration_ms < 200, f"Hook took {duration_ms}ms (limit: 200ms)"
    assert result.exit_code == 0
```

#### Test: Lock Check Performance

```python
def test_lock_check_performance(stop_hook, active_lock):
    """Verify lock checking is fast."""
    timings = []
    for _ in range(100):
        start = time.perf_counter()
        stop_hook.lock_flag.exists()
        timings.append(time.perf_counter() - start)

    avg_ms = (sum(timings) / len(timings)) * 1000
    assert avg_ms < 1, f"Lock check took {avg_ms}ms average"
```

#### Test: Custom Prompt Read Performance

```python
def test_custom_prompt_read_performance(stop_hook, custom_prompt):
    """Verify prompt reading is fast."""
    custom_prompt("Test prompt content")

    timings = []
    for _ in range(100):
        start = time.perf_counter()
        stop_hook.read_continuation_prompt()
        timings.append(time.perf_counter() - start)

    avg_ms = (sum(timings) / len(timings)) * 1000
    assert avg_ms < 10, f"Prompt read took {avg_ms}ms average"
```

### Performance Benchmarking

Create benchmark script `scripts/benchmark_stop_hook.py`:

```python
#!/usr/bin/env python3
"""Benchmark stop hook performance."""
import statistics
import time
from pathlib import Path

def benchmark_stop_hook():
    """Run comprehensive performance benchmark."""
    results = {
        "no_lock": [],
        "with_lock_default": [],
        "with_lock_custom": [],
    }

    # Run each scenario 1000 times
    # Measure min, max, mean, p95, p99
    # Report results

benchmark_stop_hook()
```

## Test Execution Instructions

### Prerequisites

```bash
# Install dependencies
pip install pytest pytest-mock pytest-timeout

# Ensure test directory structure exists
mkdir -p tests/{unit,integration,e2e}
```

### Running Tests

#### Run All Tests

```bash
cd /Users/ryan/src/tempsaturday/worktree-issue-962
pytest tests/
```

#### Run Specific Test Levels

```bash
# Unit tests only (fast, ~2 seconds)
pytest tests/unit/ -v

# Integration tests (medium, ~10 seconds)
pytest tests/integration/ -v --timeout=5

# E2E tests (slow, ~30 seconds)
pytest tests/e2e/ -v --timeout=30
```

#### Run Specific Test IDs

```bash
# Run single test by ID pattern
pytest tests/ -k "UNIT_PROCESS_001" -v

# Run all process tests
pytest tests/unit/test_stop_hook_process.py -v

# Run subprocess integration tests
pytest tests/integration/test_stop_hook_subprocess.py -v
```

#### Run Performance Tests

```bash
# Run performance tests with timing
pytest tests/integration/test_stop_hook_subprocess.py::test_hook_execution_time_no_lock -v -s

# Run benchmark
python scripts/benchmark_stop_hook.py
```

#### Run with Coverage

```bash
# Generate coverage report
pytest tests/ --cov=.claude/tools/amplihack/hooks --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html
```

### Continuous Integration

Add to CI pipeline (`.github/workflows/test.yml`):

```yaml
- name: Run Stop Hook Tests
  run: |
    pytest tests/unit/test_stop_hook_*.py -v
    pytest tests/integration/test_stop_hook_*.py -v --timeout=5
    pytest tests/e2e/test_stop_hook_*.py -v --timeout=30
```

### Test Markers

Define pytest markers in `pytest.ini`:

```ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (moderate speed)
    e2e: End-to-end tests (slow, full workflows)
    performance: Performance and benchmarking tests
    slow: Tests that take > 1 second
```

Usage:

```bash
# Run only unit tests
pytest -m unit

# Run everything except slow tests
pytest -m "not slow"

# Run performance tests
pytest -m performance
```

## Test Coverage Goals

### Minimum Coverage Requirements

- **Line Coverage**: ≥ 90% for stop.py
- **Branch Coverage**: ≥ 85% for stop.py
- **Function Coverage**: 100% for stop.py

### Critical Path Coverage (Must be 100%)

These paths MUST be tested exhaustively:

1. Lock file exists → block decision returned
2. No lock file → empty dict returned
3. Permission error → fail-safe empty dict
4. Invalid JSON input → error response
5. Custom prompt → used in reason field
6. Default prompt → used when custom unavailable

### Coverage Gaps Analysis

After implementation, run coverage and verify:

```bash
pytest --cov=.claude/tools/amplihack/hooks/stop --cov-report=term-missing
```

Expected output:

```
stop.py                         95%    Lines 45, 67 not covered
```

If coverage < 90%, identify untested code paths and add tests.

## Validation Checklist

Before considering tests complete, verify:

- [ ] All 60 tests (36 unit + 18 integration + 6 E2E) pass
- [ ] Line coverage ≥ 90%
- [ ] Branch coverage ≥ 85%
- [ ] All critical paths tested
- [ ] Performance requirement met (< 200ms)
- [ ] Subprocess tests verify no stderr output
- [ ] Subprocess tests verify exit code 0
- [ ] JSON output is valid and parseable
- [ ] Permission errors handled gracefully
- [ ] Corrupted input handled gracefully
- [ ] Continuous work mode tested end-to-end
- [ ] Lock file race conditions handled
- [ ] Custom prompt edge cases tested
- [ ] Logging and metrics verified
- [ ] No regressions from previous tests

## TDD Approach

### Red-Green-Refactor Cycle

1. **Red**: Write failing test first
2. **Green**: Implement minimal code to pass
3. **Refactor**: Improve code while keeping tests green

### Implementation Order

**Phase 1**: Unit tests for process() method

- Implement UNIT-PROCESS-001 to 012
- These guide the core logic implementation

**Phase 2**: Unit tests for read_continuation_prompt()

- Implement UNIT-PROMPT-001 to 009
- These guide prompt handling logic

**Phase 3**: Unit tests for run() lifecycle

- Implement UNIT-RUN-001 to 008
- These verify hook lifecycle correctness

**Phase 4**: Integration tests

- Implement subprocess tests first (critical for API compliance)
- Then lock and prompt integration tests
- Finally logging tests

**Phase 5**: E2E tests

- Implement workflow tests (validate user scenarios)
- Then error recovery tests
- Finally performance tests

### Builder Agent Instructions

When implementing tests:

1. **Start with fixtures** in `conftest.py`
2. **Implement unit tests** in order (PROCESS → PROMPT → RUN → JSON → PATH)
3. **Run tests frequently** after each test file
4. **Fix failures immediately** before moving to next test
5. **Add integration tests** after all unit tests pass
6. **Verify subprocess behavior** matches API spec exactly
7. **Add E2E tests** last to validate complete workflows
8. **Run full suite** before marking task complete

## Success Criteria

Tests are considered complete and successful when:

1. **All 60 tests pass** consistently
2. **Coverage goals met** (≥90% line, ≥85% branch)
3. **Performance requirements met** (< 200ms)
4. **API compliance verified**:
   - Empty dict `{}` when allowing stop
   - Block decision with reason when blocking
   - Exit code 0 always
   - No stderr output during normal operation
5. **Edge cases handled**:
   - Permission errors
   - Corrupted JSON
   - Missing files
   - Race conditions
6. **Continuous work mode validated** end-to-end

## References

- **Issue #962**: https://github.com/[repo]/issues/962
- **Claude Code Hook API**: See official documentation
- **Testing Pyramid**: 60% unit, 30% integration, 10% E2E
- **pytest Documentation**: https://docs.pytest.org/
- **Coverage.py**: https://coverage.readthedocs.io/

---

**Document Version**: 1.0 **Author**: Tester Agent **Date**: 2025-10-20
**Status**: Ready for Implementation
