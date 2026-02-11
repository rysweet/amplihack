# How to Run Integration Tests

## Overview

This guide explains how to run amplihack's integration tests, including the security test suite for shell injection prevention.

## Quick Start

```bash
# Run all tests
pytest

# Run security tests only
pytest tests/unit/test_process_security.py

# Run with verbose output
pytest tests/unit/test_process_security.py -v

# Run specific test class
pytest tests/unit/test_process_security.py::TestShellInjectionPrevention -v
```

## Test Organization

### Test Structure

```
tests/
├── unit/                           # Unit tests
│   ├── test_process_security.py    # Shell injection prevention tests
│   └── ...                         # Other unit tests
├── integration/                    # Integration tests
└── conftest.py                     # Pytest configuration
```

### Test Categories

| Test File | Purpose | Run Command |
|-----------|---------|-------------|
| `test_process_security.py` | Shell injection prevention | `pytest tests/unit/test_process_security.py` |

## Running Security Tests

### Full Security Test Suite

```bash
# Run all security tests with detailed output
pytest tests/unit/test_process_security.py -v --tb=short

# Run with coverage report
pytest tests/unit/test_process_security.py --cov=amplihack.utils.process --cov-report=term-missing
```

### Test Classes

#### TestShellInjectionPrevention

Tests that `shell=True` is never used:

```bash
pytest tests/unit/test_process_security.py::TestShellInjectionPrevention -v
```

**Tests included**:
- `test_run_command_never_uses_shell_true_on_unix`
- `test_run_command_never_uses_shell_true_on_windows`
- `test_windows_npm_uses_resolved_path`
- `test_windows_npx_uses_resolved_path`
- `test_windows_node_uses_resolved_path`

#### TestShellInjectionAttackVectors

Tests specific injection payloads:

```bash
pytest tests/unit/test_process_security.py::TestShellInjectionAttackVectors -v
```

**Attack vectors tested**:
- `; rm -rf /` (command separator)
- `& del C:\\Windows\\System32` (Windows separator)
- `| cat /etc/passwd` (pipe)
- `$(whoami)` (command substitution)
- `` `whoami` `` (backtick substitution)
- `\n rm -rf /` (newline injection)
- `&& echo pwned` (logical AND)
- `|| echo pwned` (logical OR)

### Running Individual Tests

```bash
# Run specific test
pytest tests/unit/test_process_security.py::TestShellInjectionPrevention::test_run_command_never_uses_shell_true_on_windows -v

# Run parametrized test with specific parameter
pytest tests/unit/test_process_security.py::TestShellInjectionAttackVectors::test_injection_in_npm_install_argument["; rm -rf /"] -v
```

## Test Output

### Successful Test Run

```bash
$ pytest tests/unit/test_process_security.py -v

tests/unit/test_process_security.py::TestShellInjectionPrevention::test_run_command_never_uses_shell_true_on_unix PASSED
tests/unit/test_process_security.py::TestShellInjectionPrevention::test_run_command_never_uses_shell_true_on_windows PASSED
tests/unit/test_process_security.py::TestShellInjectionPrevention::test_windows_npm_uses_resolved_path PASSED
tests/unit/test_process_security.py::TestShellInjectionAttackVectors::test_injection_in_npm_install_argument["; rm -rf /"] PASSED
tests/unit/test_process_security.py::TestShellInjectionAttackVectors::test_injection_in_npm_install_argument["& del C:\\Windows\\System32"] PASSED

========================= 286 passed in 2.35s =========================
```

### Failed Test Example

```bash
$ pytest tests/unit/test_process_security.py::TestShellInjectionPrevention::test_run_command_never_uses_shell_true_on_windows -v

FAILED tests/unit/test_process_security.py::TestShellInjectionPrevention::test_run_command_never_uses_shell_true_on_windows

________________________________ test_run_command_never_uses_shell_true_on_windows ________________________________

    def test_run_command_never_uses_shell_true_on_windows():
        """Verify shell=True is never passed to subprocess.run on Windows."""
        with (
            patch.object(ProcessManager, "is_windows", return_value=True),
            patch("amplihack.utils.process.shutil.which", return_value="C:\\npm.cmd"),
            patch("subprocess.run") as mock_run,
        ):
            ProcessManager.run_command(["npm", "install"])

            call_kwargs = mock_run.call_args.kwargs
>           assert "shell" not in call_kwargs or call_kwargs.get("shell") is False
E           AssertionError: shell=True was passed for command: ['npm', 'install'] on Windows

========================= 1 failed in 0.52s =========================
```

## Platform-Specific Testing

### Testing Windows Behavior on Unix

The tests use mocking to simulate Windows behavior:

```python
with patch.object(ProcessManager, "is_windows", return_value=True):
    # Test Windows-specific logic
    ProcessManager.run_command(["npm", "install"])
```

### Testing Unix Behavior on Windows

```python
with patch.object(ProcessManager, "is_windows", return_value=False):
    # Test Unix-specific logic
    ProcessManager.run_command(["npm", "install"])
```

## CI Integration

### GitHub Actions

Security tests run automatically in CI:

```yaml
name: Security Tests

on: [push, pull_request]

jobs:
  security:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-2019, windows-2022]
        python-version: ['3.10', '3.11', '3.12']

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-cov

      - name: Run security tests
        run: pytest tests/unit/test_process_security.py -v
```

### Local Pre-commit Testing

Run tests before committing:

```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
pytest tests/unit/test_process_security.py --tb=short
if [ $? -ne 0 ]; then
    echo "Security tests failed. Commit aborted."
    exit 1
fi
```

## Troubleshooting

### Tests Fail on Windows

**Problem**: Tests pass on Unix but fail on Windows.

**Solution**: Ensure Node.js is installed and npm/npx are in PATH:

```powershell
# Check npm installation
npm --version

# Check npm location
where npm

# Expected output: C:\Program Files\nodejs\npm.cmd
```

### Mock Warnings

**Problem**: `pytest` shows warnings about mock usage.

**Solution**: Use context managers for patches:

```python
# ✅ CORRECT: Context manager
with patch("subprocess.run") as mock_run:
    ProcessManager.run_command(["npm", "install"])

# ❌ WRONG: Decorator without cleanup
@patch("subprocess.run")
def test_something(mock_run):
    ProcessManager.run_command(["npm", "install"])
```

### Coverage Not 100%

**Problem**: Code coverage report shows missing lines.

**Solution**: Ensure all code paths are tested:

```bash
# Generate detailed coverage report
pytest tests/unit/test_process_security.py --cov=amplihack.utils.process --cov-report=html

# Open htmlcov/index.html to see missing lines
```

## Advanced Usage

### Running Tests with Debugging

```bash
# Drop into debugger on failure
pytest tests/unit/test_process_security.py --pdb

# Print output from tests
pytest tests/unit/test_process_security.py -s

# Stop on first failure
pytest tests/unit/test_process_security.py -x
```

### Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest tests/unit/test_process_security.py -n 4
```

### Continuous Test Running

```bash
# Install pytest-watch
pip install pytest-watch

# Watch for changes and re-run tests
ptw tests/unit/test_process_security.py
```

## Related Documentation

- [Shell Injection Prevention Guide](../security/shell-injection-prevention.md) - Security patterns and migration
- [Security Testing Guide](../security/SECURITY_TESTING_GUIDE.md) - Comprehensive testing strategies
- [Windows CI Matrix Guide](../reference/windows-ci-matrix.md) - CI configuration

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
