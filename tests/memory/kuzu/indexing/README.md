# Blarify Indexing Enhancement Tests

Comprehensive test suite for the blarify indexing enhancements following TDD (Test-Driven Development) approach.

## Test Structure

Tests follow the testing pyramid principle:

- **60% Unit Tests**: Fast, isolated tests for individual modules
- **30% Integration Tests**: Tests for module interactions
- **10% E2E Tests**: Full workflow tests (in `test_blarify_integration.py`)

## Test Files

### Unit Tests (60%)

#### `test_prerequisite_checker.py`

Tests for prerequisite detection:

- Missing scip-python binary
- Missing initialize_params.json for jedi
- Unknown dotnet version 10.0.2
- Missing runtime_dependencies.json for TypeScript
- Partial success (at least one language can proceed)
- Error message reporting

**Coverage**: 12 test cases

#### `test_progress_tracker.py`

Tests for progress tracking:

- Time estimation (within ±20% accuracy)
- Progress updates during indexing
- Completion tracking per language
- Display of current language
- Overall progress calculation
- Concurrent language tracking

**Coverage**: 13 test cases

#### `test_error_handler.py`

Tests for error handling:

- SKIP_LANGUAGE action for missing tools
- RETRY action for timeouts
- ABORT action for critical errors
- User-friendly error messages
- Hang prevention
- Retry with backoff
- Error aggregation

**Coverage**: 14 test cases

#### `test_background_indexer.py`

Tests for background indexing:

- Background process creation
- Job status tracking
- Log file creation
- Process isolation (doesn't block main thread)
- Job completion notification
- Multiple concurrent jobs
- Job cancellation
- Error handling

**Coverage**: 15 test cases

#### `test_orchestrator.py`

Tests for workflow orchestration:

- End-to-end flow with all prerequisites
- Graceful degradation with missing prerequisites
- Background execution option
- Failed language skipping
- Accurate IndexingResult counts
- Progress tracking
- Error aggregation
- Config customization

**Coverage**: 14 test cases

### Integration Tests (30%)

#### `test_blarify_integration.py`

Full workflow integration tests:

- Launcher to Kuzu import workflow
- Missing tools scenario
- Background execution end-to-end
- Prerequisite check integration
- Progress tracking integration
- Error handling integration
- Multi-language indexing
- Incremental updates
- Large codebase performance
- Concurrent processing

**Coverage**: 15 test cases

## Running Tests

### Run all tests

```bash
pytest tests/memory/kuzu/indexing/ -v
```

### Run specific test file

```bash
pytest tests/memory/kuzu/indexing/test_prerequisite_checker.py -v
```

### Run with coverage

```bash
pytest tests/memory/kuzu/indexing/ --cov=amplihack.memory.kuzu.indexing --cov-report=html
```

### Run only unit tests

```bash
pytest tests/memory/kuzu/indexing/ -v -k "not integration"
```

### Run only integration tests

```bash
pytest tests/memory/kuzu/indexing/test_blarify_integration.py -v
```

## Test Coverage Summary

| Module              | Test File                    | Test Count   | Status                      |
| ------------------- | ---------------------------- | ------------ | --------------------------- |
| PrerequisiteChecker | test_prerequisite_checker.py | 12           | FAILING (TDD)               |
| ProgressTracker     | test_progress_tracker.py     | 13           | FAILING (TDD)               |
| ErrorHandler        | test_error_handler.py        | 14           | FAILING (TDD)               |
| BackgroundIndexer   | test_background_indexer.py   | 15           | FAILING (TDD)               |
| Orchestrator        | test_orchestrator.py         | 14           | FAILING (TDD)               |
| Integration         | test_blarify_integration.py  | 15           | FAILING (TDD)               |
| **TOTAL**           |                              | **83 tests** | **All failing (by design)** |

## TDD Workflow

These tests are written **before implementation** following TDD principles:

1. **RED**: All tests currently fail (modules not implemented)
2. **GREEN**: Implement modules to make tests pass
3. **REFACTOR**: Clean up implementation while keeping tests green

## Expected Test Results After Implementation

After implementing the 5 modules, all 83 tests should pass:

```
tests/memory/kuzu/indexing/test_prerequisite_checker.py ............    12 passed
tests/memory/kuzu/indexing/test_progress_tracker.py .............      13 passed
tests/memory/kuzu/indexing/test_error_handler.py ..............        14 passed
tests/memory/kuzu/indexing/test_background_indexer.py ...............  15 passed
tests/memory/kuzu/indexing/test_orchestrator.py ..............         14 passed
tests/memory/kuzu/indexing/test_blarify_integration.py ...............  15 passed

=============================== 83 passed in X.XXs ================================
```

## Test Quality Criteria

All tests follow these quality criteria:

✅ **Fast**: Unit tests complete in <100ms each
✅ **Isolated**: No test dependencies or shared state
✅ **Repeatable**: Consistent results across runs
✅ **Self-Validating**: Clear pass/fail without manual inspection
✅ **Focused**: Single assertion or related group per test

## Mocking Strategy

Tests use appropriate mocking:

- External dependencies (file system, network, subprocess)
- Long-running operations
- Non-deterministic behavior
- Database operations in unit tests

Integration tests use minimal mocking to test real interactions.

## Test Maintenance

When modifying modules:

1. Run tests to ensure no regressions
2. Update tests if API changes
3. Add new tests for new functionality
4. Keep test coverage above 85%

## Architecture Alignment

Tests validate the architecture designed by the architect agent:

- 5 independent modules with clear boundaries
- Orchestrator coordinates workflow
- Error handling prevents hangs
- Background execution for long operations
- Graceful degradation with partial success
