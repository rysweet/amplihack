# PM Architect Phase 1 - Test Suite

Comprehensive TDD test suite for the file-based PM system implementation.

## Overview

This test suite provides **95+ failing tests** that define the behavior of the PM Architect Phase 1 system. All tests are written following TDD principles and will pass once the implementation is complete.

### Test Coverage Summary

| Module                  | Tests   | Focus Area                              |
| ----------------------- | ------- | --------------------------------------- |
| `test_pm_state.py`      | ~30     | State management, YAML ops, file I/O    |
| `test_pm_workstream.py` | ~25     | Workstream lifecycle, agent integration |
| `test_pm_cli.py`        | ~25     | CLI commands, user interaction          |
| `test_pm_workflow.py`   | ~15     | End-to-end integration flows            |
| **Total**               | **~95** | Complete system coverage                |

## Test Structure

```
.claude/tools/amplihack/pm/tests/
├── __init__.py              # Package metadata
├── README.md                # This file
├── conftest.py              # Shared fixtures and utilities
├── test_pm_state.py         # Unit: State management tests
├── test_pm_workstream.py    # Unit: Workstream management tests
├── test_pm_cli.py           # Unit: CLI command tests
└── test_pm_workflow.py      # Integration: E2E workflow tests
```

## Running Tests

### All Tests

```bash
# From project root
pytest .claude/tools/amplihack/pm/tests/

# With verbose output
pytest .claude/tools/amplihack/pm/tests/ -v

# Show test names only
pytest .claude/tools/amplihack/pm/tests/ --collect-only
```

### By Test File

```bash
# State tests only
pytest .claude/tools/amplihack/pm/tests/test_pm_state.py

# Workstream tests only
pytest .claude/tools/amplihack/pm/tests/test_pm_workstream.py

# CLI tests only
pytest .claude/tools/amplihack/pm/tests/test_pm_cli.py

# Integration tests only
pytest .claude/tools/amplihack/pm/tests/test_pm_workflow.py
```

### By Test Marker

```bash
# Unit tests only (fast)
pytest .claude/tools/amplihack/pm/tests/ -m unit

# Integration tests only
pytest .claude/tools/amplihack/pm/tests/ -m integration

# Tests requiring agent
pytest .claude/tools/amplihack/pm/tests/ -m requires_agent
```

### By Test Name Pattern

```bash
# All creation tests
pytest .claude/tools/amplihack/pm/tests/ -k "create"

# All error handling tests
pytest .claude/tools/amplihack/pm/tests/ -k "error"

# Specific test
pytest .claude/tools/amplihack/pm/tests/test_pm_state.py::test_should_create_new_state_when_no_file_exists
```

### With Coverage

```bash
# Generate coverage report
pytest .claude/tools/amplihack/pm/tests/ --cov=.claude/tools/amplihack/pm --cov-report=html

# View report
open htmlcov/index.html
```

## Test Categories

### Unit Tests (~80 tests)

**test_pm_state.py** - State Management (30 tests)

- State initialization and loading
- YAML serialization/deserialization
- File I/O with error handling
- Workstream CRUD operations
- Data validation and edge cases

**test_pm_workstream.py** - Workstream Management (25 tests)

- Workstream creation and configuration
- Status transitions and validation
- ClaudeProcess integration (mocked)
- Context management
- Serialization and persistence

**test_pm_cli.py** - CLI Commands (25 tests)

- Command parsing and execution
- User prompts and interaction
- Status reporting and formatting
- Error messages and feedback
- Output formatting (table, JSON)

### Integration Tests (~15 tests)

**test_pm_workflow.py** - End-to-End Flows (15 tests)

- Complete workstream lifecycle
- Multi-workstream scenarios
- State persistence across operations
- Agent integration (mocked)
- Error recovery and resilience
- Performance and scale testing

## Test Philosophy

### Testing Principles

1. **Test Behavior, Not Implementation**
   - Focus on what the code does, not how it does it
   - Tests should survive refactoring

2. **Clear Test Structure (AAA)**
   - **Arrange**: Set up test data and mocks
   - **Act**: Execute the code under test
   - **Assert**: Verify expected behavior

3. **Descriptive Test Names**
   - Format: `test_should_<expected>_when_<condition>`
   - Example: `test_should_create_new_state_when_no_file_exists`

4. **Mock External Dependencies**
   - Mock ClaudeProcess for unit tests
   - Use real file I/O for integration tests
   - Isolate unit tests from external systems

5. **Test Pyramid Distribution**
   - 60% unit tests (fast, isolated)
   - 30% integration tests (realistic)
   - 10% E2E tests (complete workflows)

### Test Coverage Goals

- **Line Coverage**: 80%+ for critical paths
- **Branch Coverage**: 70%+ for conditional logic
- **Edge Cases**: All error conditions tested
- **Happy Paths**: All success scenarios tested

## Fixtures and Utilities

### Common Fixtures (conftest.py)

**Directory Fixtures**

- `temp_pm_dir`: Temporary PM directory structure
- `state_file`: Path to state file
- `sample_state_file`: Pre-populated state file

**Test Data Fixtures**

- `sample_workstream_minimal`: Minimal workstream data
- `sample_workstream_full`: Complete workstream data
- `sample_full_state`: Complete PM state with workstreams
- `invalid_state_data`: Invalid data for error testing

**Mock Fixtures**

- `mock_claude_process`: Mock ClaudeProcess
- `mock_pm_state`: Mock PMState
- `mock_workstream`: Mock Workstream
- `*_factory`: Factory fixtures for creating multiple mocks

**Utility Fixtures**

- `yaml_helper`: YAML load/save utilities
- `json_helper`: JSON conversion utilities
- `state_validator`: State validation helpers
- `performance_timer`: Performance measurement

## Development Workflow

### TDD Cycle

1. **Run Tests** - All should fail (not implemented)

   ```bash
   pytest .claude/tools/amplihack/pm/tests/ -v
   ```

2. **Implement Feature** - Write minimal code to pass one test

   ```bash
   # Edit state.py, workstream.py, or cli.py
   ```

3. **Run Tests Again** - Watch test turn green

   ```bash
   pytest .claude/tools/amplihack/pm/tests/test_pm_state.py::test_should_create_new_state_when_no_file_exists
   ```

4. **Refactor** - Improve code while keeping tests green

5. **Repeat** - Move to next failing test

### Watching Tests

Use pytest-watch for continuous testing:

```bash
# Install
pip install pytest-watch

# Watch all tests
ptw .claude/tools/amplihack/pm/tests/

# Watch specific file
ptw .claude/tools/amplihack/pm/tests/test_pm_state.py
```

## Common Patterns

### Testing File I/O

```python
def test_should_save_state_to_file(temp_pm_dir):
    """Use temp_pm_dir fixture for isolated file testing."""
    state_file = temp_pm_dir / "state.yaml"
    state = PMState(project_name="test")
    state.save(state_file)
    assert state_file.exists()
```

### Testing Async Code

```python
@pytest.mark.asyncio
async def test_should_start_agent(mock_claude_process):
    """Mark async tests with pytest.mark.asyncio."""
    ws = Workstream.create(name="Test", goal="Goal")
    await ws.start_agent()
    mock_claude_process.start.assert_called_once()
```

### Testing Error Cases

```python
def test_should_raise_error_on_invalid_input():
    """Verify exceptions are raised for invalid inputs."""
    with pytest.raises(ValidationError):
        PMState(project_name="")
```

### Testing with Mocks

```python
def test_should_call_save(mock_pm_state):
    """Verify methods are called correctly."""
    cli = PMCli(state=mock_pm_state)
    cli.create_workstream(name="Test", goal="Goal")
    mock_pm_state.save.assert_called_once()
```

## Troubleshooting

### Tests Not Found

```bash
# Ensure you're in project root
cd /path/to/MicrosoftHackathon2025-AgenticCoding

# Verify pytest can find tests
pytest --collect-only .claude/tools/amplihack/pm/tests/
```

### Import Errors

```bash
# Install test dependencies
pip install pytest pytest-asyncio pyyaml

# Add project to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Async Test Failures

```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Tests should be marked with @pytest.mark.asyncio
```

### Mock Issues

```python
# Ensure mocks are patched at the right location
# Patch where the object is USED, not where it's defined
with patch("..workstream.ClaudeProcess", return_value=mock):
    # Not "...orchestration.claude_process.ClaudeProcess"
```

## Contributing

### Adding New Tests

1. **Choose the Right File**
   - Unit test → `test_pm_<module>.py`
   - Integration test → `test_pm_workflow.py`

2. **Follow Naming Convention**
   - `test_should_<expected>_when_<condition>`

3. **Use Existing Fixtures**
   - Check `conftest.py` for available fixtures
   - Add new fixtures if needed

4. **Add Test Documentation**
   - Docstring explaining what's being tested
   - Comments for complex setup

5. **Mark Tests Appropriately**
   - `@pytest.mark.unit` for unit tests
   - `@pytest.mark.integration` for integration tests
   - `@pytest.mark.requires_agent` if agent needed

### Adding New Fixtures

1. **Add to conftest.py**
   - Keep fixtures organized by category
   - Add docstring explaining fixture purpose

2. **Use Composition**
   - Build complex fixtures from simple ones
   - Example: `sample_state_file` uses `sample_full_state`

3. **Consider Scope**
   - Default: `function` (new for each test)
   - `module`: Shared across file
   - `session`: Shared across all tests

## Expected Test Results

### Before Implementation

```bash
$ pytest .claude/tools/amplihack/pm/tests/
============================= test session starts ==============================
collected 95 items

test_pm_state.py ............................s.s.s  [  30/95]  # 30 skipped
test_pm_workstream.py ........................s.s   [  55/95]  # 25 skipped
test_pm_cli.py .........................s.s         [  80/95]  # 25 skipped
test_pm_workflow.py ...............s.s              [  95/95]  # 15 skipped

========================= 95 skipped in 0.50s ==========================
```

All tests are skipped with `pytest.skip("Implementation pending")` until implementation begins.

### After Implementation

```bash
$ pytest .claude/tools/amplihack/pm/tests/
============================= test session starts ==============================
collected 95 items

test_pm_state.py ..............................  [  30/95]  # 30 passed
test_pm_workstream.py .........................  [  55/95]  # 25 passed
test_pm_cli.py ............................     [  80/95]  # 25 passed
test_pm_workflow.py ...............              [  95/95]  # 15 passed

========================= 95 passed in 5.23s ===========================
```

All tests should pass with 80%+ code coverage.

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)

## Questions?

For questions about the test suite:

1. Check test docstrings for detailed explanations
2. Review `conftest.py` for available fixtures
3. Look at similar tests for patterns
4. Consult the project's testing philosophy in `@.claude/context/TRUST.md`

---

**Remember**: These tests define the contract. The implementation must satisfy all tests.
