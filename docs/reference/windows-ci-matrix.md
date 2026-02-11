# Windows CI Matrix Reference

## Overview

amplihack uses a comprehensive Windows CI testing matrix to validate cross-platform compatibility, especially for shell injection fixes in ProcessManager.

## CI Matrix Configuration

### Platform Matrix

```yaml
strategy:
  matrix:
    os:
      - ubuntu-latest
      - macos-latest
      - windows-2019
      - windows-2022
    python-version:
      - '3.10'
      - '3.11'
      - '3.12'
```

### Coverage

| Platform | Versions Tested | Purpose |
|----------|----------------|---------|
| **Ubuntu** | latest | Validate Unix behavior, Linux-specific paths |
| **macOS** | latest | Validate Unix behavior, BSD differences |
| **Windows Server 2019** | 2019 | Legacy Windows support, older Node.js versions |
| **Windows Server 2022** | 2022 | Modern Windows, latest Node.js, PowerShell 7 |

**Total Test Combinations**: 4 OS × 3 Python versions = **12 test environments**

## Windows-Specific Tests

### Why Windows CI Matters

The shell injection fix specifically affects Windows behavior:

1. **Previous Implementation**: Used `shell=True` for npm/npx/node on Windows
2. **Current Implementation**: Uses `shutil.which()` to resolve .cmd paths
3. **Critical Validation**: Ensure npm commands still work without `shell=True`

### Windows Test Scenarios

#### Scenario 1: npm Command Resolution

```python
# Test that npm.cmd is resolved correctly
def test_windows_npm_resolution():
    """Verify npm.cmd is found via shutil.which() on Windows."""
    with patch.object(ProcessManager, "is_windows", return_value=True):
        result = shutil.which("npm")
        assert result is not None
        assert result.endswith(".cmd") or result.endswith(".bat")
```

**What CI Validates**:
- `npm.cmd` exists in PATH on Windows 2019/2022
- `shutil.which("npm")` returns correct path
- Resolved path is executable

#### Scenario 2: Shell Injection Prevention

```python
# Test that injection payloads don't execute
@pytest.mark.parametrize("malicious_arg", [
    "; del C:\\Windows\\System32",
    "& echo pwned",
    "|| echo pwned",
])
def test_windows_injection_prevention(malicious_arg):
    """Verify Windows-specific injection attacks are neutralized."""
    with patch.object(ProcessManager, "is_windows", return_value=True):
        # Should NOT execute malicious command
        ProcessManager.run_command(["npm", "install", malicious_arg])
```

**What CI Validates**:
- Windows command separators (`&`, `&&`, `||`, `;`) treated as literals
- PowerShell injection vectors neutralized
- cmd.exe batch script exploits blocked

#### Scenario 3: NPM Install Works

```python
# Integration test - actual npm command
def test_windows_npm_install_works():
    """Verify npm install executes successfully on Windows."""
    if not ProcessManager.is_windows():
        pytest.skip("Windows-only test")

    result = ProcessManager.run_command([
        "npm", "install", "--global", "npm@latest"
    ])
    assert result.returncode == 0
```

**What CI Validates**:
- Real npm commands execute successfully
- No regression from removing `shell=True`
- Windows PATH resolution works correctly

## CI Workflow Details

### Test Execution Flow

```yaml
name: Cross-Platform Security Tests

on:
  push:
    branches: [ main, fix/* ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false  # Continue testing other platforms on failure
      matrix:
        os: [ubuntu-latest, windows-2019, windows-2022, macos-latest]
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install Node.js (for npm tests)
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .
          pip install pytest pytest-cov

      - name: Run security tests
        run: |
          pytest tests/unit/test_process_security.py -v --tb=short

      - name: Run integration tests (Windows only)
        if: runner.os == 'Windows'
        shell: pwsh
        run: |
          pytest tests/integration/test_windows_npm.py -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: ${{ matrix.os }}-py${{ matrix.python-version }}
```

### Key CI Features

| Feature | Configuration | Purpose |
|---------|--------------|---------|
| **fail-fast: false** | Continue on failure | Test all platforms even if one fails |
| **Node.js setup** | node-version: '20' | Ensure npm/npx available for tests |
| **Platform-specific tests** | `if: runner.os == 'Windows'` | Run Windows integration tests only on Windows |
| **Coverage upload** | codecov flags | Track coverage by platform |

## Windows-Specific CI Considerations

### PowerShell vs CMD

Windows CI uses PowerShell by default:

```yaml
# Explicitly use PowerShell
- name: Test with PowerShell
  shell: pwsh
  run: |
    pytest tests/unit/test_process_security.py

# Use CMD explicitly (if needed)
- name: Test with CMD
  shell: cmd
  run: |
    pytest tests\unit\test_process_security.py
```

### PATH Differences

Windows PATH handling in CI:

```yaml
# Windows: Verify npm in PATH
- name: Check npm PATH (Windows)
  if: runner.os == 'Windows'
  shell: pwsh
  run: |
    Write-Output "NPM Location: $(Get-Command npm).Path"
    npm --version

# Unix: Verify npm in PATH
- name: Check npm PATH (Unix)
  if: runner.os != 'Windows'
  shell: bash
  run: |
    echo "NPM Location: $(which npm)"
    npm --version
```

### File Path Separators

```python
# Cross-platform path handling in tests
import os

def get_npm_path():
    """Get npm path for current platform."""
    if ProcessManager.is_windows():
        return "C:\\Program Files\\nodejs\\npm.cmd"
    else:
        return "/usr/local/bin/npm"

# Better: Use os.path.join
npm_path = os.path.join("C:\\", "Program Files", "nodejs", "npm.cmd")
```

## Monitoring CI Results

### GitHub Actions UI

View test results at:
```
https://github.com/rysweet/amplihack/actions
```

**Key Metrics to Monitor**:
- ✅ All 12 matrix combinations passing
- ⏱️ Windows tests complete in < 5 minutes
- 📊 Coverage maintained above 80% on all platforms

### Interpreting Failures

#### Windows-Specific Failure

```
FAILED tests/unit/test_process_security.py::test_windows_npm_uses_resolved_path
Platform: windows-2022, Python 3.11
```

**Debug Steps**:
1. Check if npm is in PATH: `where npm`
2. Verify `shutil.which("npm")` returns correct path
3. Check Windows PATH environment variable
4. Review Node.js installation in CI logs

#### Cross-Platform Failure

```
FAILED tests/unit/test_process_security.py::test_injection_in_npm_install_argument
Platform: ALL
```

**Debug Steps**:
1. Review test implementation (likely regression in ProcessManager)
2. Check if `shell=True` was accidentally re-introduced
3. Verify command list formatting

## Local Windows Testing

### Testing Without CI

Simulate CI environment locally on Windows:

```powershell
# PowerShell - Simulate CI environment
$env:GITHUB_ACTIONS = "true"
$env:RUNNER_OS = "Windows"

# Install dependencies
python -m pip install -e .
pip install pytest pytest-cov

# Run tests as CI would
pytest tests/unit/test_process_security.py -v --tb=short

# Check npm resolution
python -c "import shutil; print(f'npm: {shutil.which(\"npm\")}')"
```

### Windows Subsystem for Linux (WSL)

Test Unix behavior from Windows:

```bash
# In WSL
cd /mnt/c/path/to/amplihack
python -m pip install -e .
pytest tests/unit/test_process_security.py -v

# This tests Unix behavior (not Windows)
```

## Troubleshooting CI Issues

### Issue 1: npm Not Found on Windows

**Symptom**: `shutil.which("npm")` returns `None` in CI.

**Solution**:
```yaml
- name: Install Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '20'

- name: Verify npm installation (Windows)
  if: runner.os == 'Windows'
  shell: pwsh
  run: |
    npm --version
    Write-Output "NPM: $(Get-Command npm).Path"
```

### Issue 2: Tests Pass Locally, Fail in CI

**Symptom**: Tests work on local Windows but fail on windows-2019/2022.

**Causes**:
- Node.js version differences
- PATH configuration
- PowerShell version (5.1 vs 7)

**Debug**:
```yaml
- name: Debug Environment (Windows)
  if: runner.os == 'Windows'
  shell: pwsh
  run: |
    Write-Output "=== Environment ==="
    Write-Output "OS: $env:OS"
    Write-Output "PowerShell: $PSVersionTable.PSVersion"
    Write-Output "Python: $(python --version)"
    Write-Output "Node: $(node --version)"
    Write-Output "NPM: $(npm --version)"
    Write-Output "PATH: $env:PATH"
```

### Issue 3: Timeout on Windows

**Symptom**: Windows tests timeout after 60 minutes.

**Solution**: Optimize test execution:
```yaml
- name: Run tests with timeout
  timeout-minutes: 10
  run: pytest tests/unit/test_process_security.py -v --timeout=300
```

## Best Practices

### 1. Test Platform-Specific Code Explicitly

```python
@pytest.mark.skipif(not ProcessManager.is_windows(), reason="Windows-only test")
def test_windows_specific_behavior():
    """Test Windows .cmd resolution."""
    result = shutil.which("npm")
    assert result.endswith(".cmd")
```

### 2. Use Matrix to Cover Edge Cases

```yaml
matrix:
  include:
    # Legacy Windows
    - os: windows-2019
      python-version: '3.10'
      node-version: '16'

    # Modern Windows
    - os: windows-2022
      python-version: '3.12'
      node-version: '20'
```

### 3. Monitor Performance by Platform

```yaml
- name: Benchmark tests
  run: pytest tests/unit/test_process_security.py --benchmark-only --benchmark-json=output.json

- name: Upload benchmark results
  uses: benchmark-action/github-action-benchmark@v1
  with:
    tool: 'pytest'
    output-file-path: output.json
```

## Related Documentation

- [Shell Injection Prevention Guide](../security/shell-injection-prevention.md) - Security patterns
- [How to Run Integration Tests](../howto/run-integration-tests.md) - Local test execution
- [Security Testing Guide](../security/SECURITY_TESTING_GUIDE.md) - Comprehensive testing

## References

- [GitHub Actions - Matrix Strategy](https://docs.github.com/en/actions/using-jobs/using-a-matrix-for-your-jobs)
- [GitHub Actions - Windows Runners](https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners#supported-runners-and-hardware-resources)
- [Pytest Documentation](https://docs.pytest.org/)
- [Python shutil.which Documentation](https://docs.python.org/3/library/shutil.html#shutil.which)
