# Stop Hook Test Suite

## Overview

This test suite provides comprehensive validation of the stop hook fix for Issue #962. It includes 60 tests organized according to the testing pyramid:

- **36 Unit Tests (60%)**: Fast, isolated tests of individual functions
- **18 Integration Tests (30%)**: Tests of component interactions and subprocess execution
- **6 E2E Tests (10%)**: Complete workflow tests from user perspective

## Test Structure

```
tests/
├── conftest.py                                 # Shared fixtures
├── pytest.ini                                   # Test configuration
├── unit/                                        # Unit tests (36 tests)
│   ├── test_stop_hook_process.py               # StopHook.process() - 12 tests
│   ├── test_stop_hook_prompt.py                # read_continuation_prompt() - 9 tests
│   ├── test_hook_processor_run.py              # HookProcessor.run() - 8 tests
│   ├── test_stop_hook_json.py                  # JSON serialization - 4 tests
│   └── test_stop_hook_paths.py                 # Path resolution - 3 tests
├── integration/                                 # Integration tests (18 tests)
│   ├── test_stop_hook_subprocess.py            # Subprocess execution - 6 tests
│   ├── test_stop_hook_lock_integration.py      # Lock file integration - 4 tests
│   ├── test_stop_hook_prompt_integration.py    # Prompt integration - 4 tests
│   └── test_stop_hook_logging.py               # Logging/metrics - 4 tests
└── e2e/                                         # E2E tests (6 tests)
    ├── test_stop_hook_workflows.py             # Complete workflows - 3 tests
    ├── test_stop_hook_error_recovery.py        # Error recovery - 2 tests
    └── test_stop_hook_performance.py           # Performance - 1 test
```

## Quick Start

### Prerequisites

```bash
# Install test dependencies
uv pip install pytest pytest-mock pytest-timeout pytest-cov pytest-asyncio
```

### Run All Stop Hook Tests

```bash
cd /Users/ryan/src/tempsaturday/worktree-issue-962

python -m pytest tests/unit/test_stop_hook*.py \
                 tests/unit/test_hook_processor_run.py \
                 tests/integration/test_stop_hook*.py \
                 tests/e2e/test_stop_hook*.py -v
```

Expected output:

```
============================== test session starts ==============================
collected 60 items

tests/unit/test_stop_hook_json.py::test_unit_json_001... PASSED [  2%]
...
============================== 40 passed, 20 failed in 10.03s ====================
```

## Running Tests by Category

### Unit Tests Only (Fast, ~1 second)

```bash
pytest tests/unit/test_stop_hook*.py tests/unit/test_hook_processor_run.py -v

# Or with markers
pytest -m unit -v
```

### Integration Tests (Medium, ~5 seconds)

```bash
pytest tests/integration/test_stop_hook*.py -v

# Or with markers
pytest -m integration -v
```

### E2E Tests (Slow, ~10 seconds)

```bash
pytest tests/e2e/test_stop_hook*.py -v

# Or with markers
pytest -m e2e -v
```

### Performance Tests Only

```bash
pytest -m performance -v
```

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.slow` - Tests taking > 1 second

Examples:

```bash
# Run everything except slow tests
pytest -m "not slow" -v

# Run only performance tests
pytest -m performance -v

# Run unit and integration, but not E2E
pytest -m "unit or integration" -v
```

## Coverage Analysis

### Generate Coverage Report

```bash
pytest tests/unit/ tests/integration/ tests/e2e/ \
  --cov=.claude/tools/amplihack/hooks \
  --cov-report=html \
  --cov-report=term

# View HTML report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

### Coverage Requirements

- **Line Coverage**: ≥ 90% for stop.py
- **Branch Coverage**: ≥ 85% for stop.py
- **Function Coverage**: 100% for stop.py

## Test IDs and Specification

Every test has a unique ID matching the test specification:

### Unit Test IDs

- `UNIT-PROCESS-001` through `UNIT-PROCESS-012` - process() method tests
- `UNIT-PROMPT-001` through `UNIT-PROMPT-009` - prompt reading tests
- `UNIT-RUN-001` through `UNIT-RUN-008` - hook lifecycle tests
- `UNIT-JSON-001` through `UNIT-JSON-004` - JSON serialization tests
- `UNIT-PATH-001` through `UNIT-PATH-003` - path resolution tests

### Integration Test IDs

- `INTEG-SUBPROCESS-001` through `INTEG-SUBPROCESS-006` - subprocess tests
- `INTEG-LOCK-001` through `INTEG-LOCK-004` - lock integration tests
- `INTEG-PROMPT-001` through `INTEG-PROMPT-004` - prompt integration tests
- `INTEG-LOG-001` through `INTEG-LOG-004` - logging/metrics tests

### E2E Test IDs

- `E2E-WORKFLOW-001` through `E2E-WORKFLOW-003` - workflow tests
- `E2E-ERROR-001` through `E2E-ERROR-002` - error recovery tests
- `E2E-PERF-001` - performance test

## Running Specific Tests

### By Test ID Pattern

```bash
# Run all process tests
pytest tests/unit/test_stop_hook_process.py -v

# Run specific test
pytest tests/unit/test_stop_hook_process.py::test_unit_process_001_no_lock_file_exists -v

# Run tests matching pattern
pytest -k "permission_error" -v
pytest -k "lock_file" -v
```

### By Test Number

```bash
# Run UNIT-PROCESS-001
pytest tests/unit/test_stop_hook_process.py::test_unit_process_001_no_lock_file_exists -v
```

## Test Output Options

### Verbose Output

```bash
pytest -v  # Show test names
pytest -vv # Show test names and assertions
```

### Show Print Statements

```bash
pytest -s  # Show print() output
pytest -v -s  # Verbose + print output
```

### Show Only Failures

```bash
pytest --tb=short  # Short traceback
pytest --tb=line   # One line per failure
pytest --tb=no     # No traceback
```

### Stop on First Failure

```bash
pytest -x  # Stop after first failure
pytest --maxfail=3  # Stop after 3 failures
```

## Performance Testing

### Run Performance Tests

```bash
pytest -m performance -v -s

# With timing details
pytest -m performance -v -s --durations=10
```

### Performance Requirements

- **Individual hook execution**: < 200ms (production)
- **Test execution time**: < 250ms (allows CI overhead)
- **Lock check operation**: < 1ms
- **Prompt read operation**: < 10ms
- **Full test suite**: < 10 seconds

## Troubleshooting

### Tests Failing Due to Missing pytest-asyncio

```bash
# Install missing dependency
uv pip install pytest-asyncio
```

### Tests Failing Due to Permission Issues

Some tests require Unix-style permissions and will skip on Windows:

- `test_integ_lock_004_lock_file_permission_changes`
- `test_e2e_error_001_recovery_from_corrupted_lock_file`

This is expected behavior.

### Subprocess Tests Failing

If integration/E2E tests fail with "lock not working", you may need to fix the environment setup. See `TEST_FIXES_NEEDED.md` for details.

### Slow Tests

If tests are too slow:

```bash
# Skip slow tests
pytest -m "not slow" -v

# Show slowest tests
pytest --durations=10
```

## CI Integration

### GitHub Actions Example

```yaml
- name: Run Stop Hook Tests
  run: |
    uv pip install pytest pytest-mock pytest-timeout pytest-cov
    pytest tests/unit/test_stop_hook*.py \
           tests/unit/test_hook_processor_run.py \
           tests/integration/test_stop_hook*.py \
           tests/e2e/test_stop_hook*.py \
           --cov=.claude/tools/amplihack/hooks \
           --cov-report=xml \
           --cov-report=term

- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Test Fixtures

### Available Fixtures

- `temp_project_root` - Temporary project directory with .claude structure
- `stop_hook` - StopHook instance configured for testing
- `active_lock` - Creates and cleans up lock file
- `custom_prompt` - Function to create custom continuation prompts
- `captured_subprocess` - Run hook as subprocess with controlled environment
- `mock_time` - Time tracking for performance tests

### Using Fixtures

```python
def test_example(stop_hook, active_lock):
    """Example test using fixtures."""
    # stop_hook is configured with temp directories
    # active_lock has created a lock file

    result = stop_hook.process({"session_id": "test"})

    assert result["decision"] == "block"
```

## Current Status

**Implementation Status**: ✅ Complete (60/60 tests implemented)
**Pass Rate**: 40/60 (67%)
**Known Issues**: 20 tests require environment setup fixes (see TEST_FIXES_NEEDED.md)

### Passing Test Categories

- ✅ HookProcessor.run() - 8/8 (100%)
- ✅ JSON Serialization - 4/4 (100%)
- ✅ Path Resolution - 3/3 (100%)
- ✅ StopHook.process() - 10/12 (83%)
- ✅ Prompt Reading - 6/9 (67%)

### Categories Needing Fixes

- ⚠️ Subprocess execution with lock - Environment setup needed
- ⚠️ Lock file integration - Environment setup needed
- ⚠️ Prompt integration - Environment setup needed
- ⚠️ Error mocking - Monkeypatch strategy needed

## Resources

- **Test Specification**: `TEST_SPECIFICATION_STOP_HOOK.md`
- **Implementation Summary**: `TEST_IMPLEMENTATION_SUMMARY.md`
- **Fix Guide**: `TEST_FIXES_NEEDED.md`
- **Issue #962**: Original issue for stop hook API compliance

## Support

For questions or issues with the test suite:

1. Review `TEST_FIXES_NEEDED.md` for known issues and solutions
2. Check `TEST_IMPLEMENTATION_SUMMARY.md` for detailed test status
3. Refer to `TEST_SPECIFICATION_STOP_HOOK.md` for test requirements
