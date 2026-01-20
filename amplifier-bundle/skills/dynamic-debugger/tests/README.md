# Dynamic Debugger Test Suite

Comprehensive test suite for the dynamic-debugger Claude Code skill, following the testing pyramid (60% unit, 30% integration, 10% E2E).

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── pytest.ini                     # Pytest settings and coverage config
├── requirements-test.txt          # Test dependencies
├── test_language_detection.py     # Unit tests for language detection (18 tests)
├── test_config_generation.py      # Unit tests for config generation (18 tests)
├── test_session_monitoring.py     # Unit tests for session monitoring (18 tests)
├── test_integration.py            # Integration tests (9 tests)
├── test_e2e.sh                    # End-to-end shell tests (3 tests)
└── fixtures/                      # Test fixtures (auto-generated via conftest.py)
```

## Testing Pyramid Distribution

| Test Type   | Count | Percentage | Coverage                         |
| ----------- | ----- | ---------- | -------------------------------- |
| Unit        | ~54   | 60%        | Individual functions and modules |
| Integration | ~9    | 30%        | Multi-component workflows        |
| E2E         | ~3    | 10%        | Complete debugging scenarios     |

## Prerequisites

### Required

- Python 3.8+
- pytest
- bash (for E2E tests)

### Optional

- psutil (for full session monitoring tests)
- jq (for E2E shell tests - JSON parsing)

## Installation

Install test dependencies:

```bash
cd tests/
pip install -r requirements-test.txt
```

For E2E tests, install `jq`:

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Fedora/RHEL
sudo dnf install jq
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# E2E tests (shell)
./test_e2e.sh

# Tests requiring psutil
pytest -m requires_psutil
```

### Run Specific Test Files

```bash
# Language detection tests
pytest test_language_detection.py

# Config generation tests
pytest test_config_generation.py

# Session monitoring tests
pytest test_session_monitoring.py

# Integration tests
pytest test_integration.py
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=../scripts --cov-report=html

# View HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Tests

```bash
# Run a specific test function
pytest test_language_detection.py::TestManifestDetection::test_detect_python_from_requirements_txt

# Run all tests in a class
pytest test_config_generation.py::TestTemplateLoading

# Run tests matching a pattern
pytest -k "python"
```

## Test Coverage by Module

### test_language_detection.py (18 unit tests)

**Manifest Detection (6 tests)**

- Python (requirements.txt, pyproject.toml)
- JavaScript (package.json)
- Go (go.mod)
- Rust (Cargo.toml)
- C++ (CMakeLists.txt)

**Extension Analysis (6 tests)**

- Python files
- Mixed languages (Python dominant)
- Equal split detection
- Directory exclusion (.venv, node_modules, **pycache**)
- TypeScript files
- C++ files (multiple extensions)

**Edge Cases (6 tests)**

- Non-existent directory
- Empty directory
- Permission errors
- Manifest precedence over extensions
- Confidence score bounds
- Unknown language handling

### test_config_generation.py (18 unit tests)

**Template Loading (6 tests)**

- Python (debugpy)
- JavaScript/TypeScript (node)
- Go (delve)
- C++ (gdb)
- Missing template error handling

**Variable Substitution (6 tests)**

- Project directory substitution
- Default port substitution
- Custom port substitution
- Entry point substitution
- Recursive nested dict substitution
- List substitution

**Validation (6 tests)**

- Complete config validation
- Missing name field
- Missing type field
- Missing request field
- Empty config
- Extra fields handling

### test_session_monitoring.py (18 unit tests)

**Process Info (6 tests)**

- Valid PID with psutil
- Invalid PID handling
- Without psutil fallback
- Info structure validation
- Memory units (MB)
- Exception handling

**Monitoring Session (6 tests)**

- Missing PID file
- Invalid PID file content
- Without psutil (limited monitoring)
- Process not found
- Memory limit exceeded
- Timeout exceeded

**JSON Output (6 tests)**

- Error message structure
- Warning message structure
- Status update structure
- Numeric precision
- Warnings list format
- JSON parseability

### test_integration.py (9 integration tests)

**Full Workflows (4 tests)**

- Python: detect → config → validate
- JavaScript: detect → config → validate
- Multi-language project
- C++: detect → GDB config → validate

**Server Lifecycle (3 tests)**

- Complete lifecycle (start → status → stop)
- Cleanup workflow
- Status checking

**Error Recovery (2 tests)**

- Missing dap-mcp handling
- Stale PID file recovery

### test_e2e.sh (3 E2E tests)

**Complete Scenarios**

1. Python debugging session (detect → config → cleanup)
2. Multi-language project detection (Python dominant)
3. Error recovery (stale PID → cleanup → retry)

## Test Fixtures

All test fixtures are defined in `conftest.py`:

**Project Fixtures**

- `python_project` - Complete Python project with requirements.txt
- `javascript_project` - Node.js project with package.json
- `go_project` - Go project with go.mod
- `rust_project` - Rust project with Cargo.toml
- `cpp_project` - C++ project with CMakeLists.txt
- `multi_language_project` - Mixed Python/JavaScript
- `empty_project` - Empty directory

**Utility Fixtures**

- `temp_project_dir` - Temporary directory for tests
- `sample_dap_config` - Sample DAP configuration
- `mock_pid_file` - Mock PID file for testing
- `skill_dir` - Skill root directory path
- `configs_dir` - Configs directory path
- `scripts_dir` - Scripts directory path

## Writing New Tests

### Unit Test Template

```python
def test_new_feature(fixture_name):
    """Test description following format: Test X when Y."""
    # Arrange
    input_data = prepare_test_data()

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_value
    assert validate_output(result)
```

### Integration Test Template

```python
def test_workflow_integration(python_project):
    """Test complete workflow: step1 → step2 → step3."""
    # Step 1
    result1 = step1(python_project)
    assert result1 is not None

    # Step 2
    result2 = step2(result1)
    assert validate_step2(result2)

    # Step 3
    final_result = step3(result2)
    assert final_result.success is True
```

### E2E Test Template (Bash)

```bash
test_e2e_new_scenario() {
    log_test "E2E Test: New Scenario Description"

    # Setup
    setup_test_env
    create_test_project

    # Execute workflow
    step1_command
    step2_command
    step3_command

    # Verify results
    if verify_results; then
        log_pass "New scenario workflow"
    else
        log_fail "New scenario failed"
        return 1
    fi
}
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install -r tests/requirements-test.txt
          sudo apt-get install -y jq
      - name: Run pytest
        run: pytest
      - name: Run E2E tests
        run: cd tests && ./test_e2e.sh
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Troubleshooting

### Tests fail with "psutil not available"

Some tests require psutil. Install it:

```bash
pip install psutil
```

Or skip those tests:

```bash
pytest -m "not requires_psutil"
```

### E2E tests fail with "jq: command not found"

Install jq for JSON parsing:

```bash
brew install jq  # macOS
sudo apt-get install jq  # Ubuntu
```

### Permission errors during tests

Ensure test scripts are executable:

```bash
chmod +x test_e2e.sh
```

### Coverage reports not generated

Ensure pytest-cov is installed:

```bash
pip install pytest-cov
```

## Best Practices

1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **One assertion per test**: Focus on single responsibility
3. **Use descriptive names**: `test_detect_python_from_requirements_txt`
4. **Mock external dependencies**: Don't call real servers/services
5. **Clean up after tests**: Use fixtures and cleanup functions
6. **Test edge cases**: Empty inputs, invalid data, permission errors
7. **Keep tests fast**: Unit tests < 100ms, integration tests < 1s

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Maintain testing pyramid ratios (60/30/10)
3. Update this README with new test coverage
4. Ensure all tests pass before submitting PR

## License

Same as parent project (amplihack2).
