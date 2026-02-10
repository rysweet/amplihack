# Platform Bridge Test Suite

Comprehensive TDD test suite for the platform bridge module following the testing pyramid principle (60% unit, 30% integration, 10% E2E).

## Test Files

### 1. `conftest.py` - Shared Test Fixtures

**Purpose**: Provides common test data, mocks, and utilities for all test modules.

**Key Fixtures**:

- Platform URLs (GitHub, Azure DevOps, unknown platforms)
- Success/error response examples
- Mock subprocess results
- Security test data (injection attempts, oversized inputs)
- Git remote output examples
- CLI argument examples
- Azure DevOps configuration examples
- Expected command structures

**Usage**: All fixtures are automatically available to all test files via pytest's fixture discovery.

### 2. `test_detector.py` - Platform Detection Tests

**Coverage**: 100+ test cases

**Test Categories**:

- Platform enum values (GitHub, AzDO, Unknown)
- PlatformDetector initialization
- GitHub URL detection (HTTPS, SSH, git://, shorthand)
- Azure DevOps URL detection (dev.azure.com, visualstudio.com, SSH)
- Unknown platform detection (GitLab, Bitbucket, custom servers)
- Error handling (missing repo, no remotes, timeout, git not found)
- Multiple remotes (origin priority, upstream fallback, first remote)
- Remote URL extraction
- Caching behavior
- Subprocess call format validation

**Key Test Patterns**:

```python
@patch("subprocess.run")
def test_detect_github_https_url(self, mock_run, git_remote_output_github):
    """Should detect GitHub from HTTPS URL."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=git_remote_output_github,
        stderr=""
    )

    detector = PlatformDetector()
    platform = detector.detect()

    assert platform == Platform.GITHUB
```

### 3. `test_github_bridge.py` - GitHub Bridge Tests

**Coverage**: 70+ test cases

**Test Categories**:

- Bridge initialization
- `create_issue` operation (success, failure, command construction, labels support)
- `create_draft_pr` operation (draft flag, base branch support)
- `mark_pr_ready` operation (nonexistent PRs, already ready PRs)
- `add_pr_comment` operation (multiline comments, invalid PRs)
- `check_ci_status` operation (passing, failing, in-progress, no checks)
- Response format consistency
- JSON parsing (valid, invalid, empty responses)
- Timeout configuration
- gh CLI not installed handling

**Key Test Patterns**:

```python
@patch("subprocess.run")
def test_create_issue_success(self, mock_run):
    """Should create issue and return success dict."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"number": 123, "url": "https://github.com/owner/repo/issues/123"}',
        stderr=""
    )

    bridge = GitHubBridge()
    result = bridge.create_issue(title="Test Issue", body="Issue description")

    assert result["success"] is True
    assert result["issue_number"] == 123
```

### 4. `test_azdo_bridge.py` - Azure DevOps Bridge Tests

**Coverage**: 75+ test cases

**Test Categories**:

- Bridge initialization with config
- Environment variable loading
- `create_issue` operation (work item terminology, org/project config)
- `create_draft_pr` operation (repository config, target branch)
- `mark_pr_ready` operation (draft flag update)
- `add_pr_comment` operation (multiline support)
- `check_ci_status` operation (build status parsing, no builds)
- Configuration management (validation, URL formatting, overrides)
- Response format consistency
- JSON parsing
- az CLI not installed handling

**Key Test Patterns**:

```python
@patch("subprocess.run")
def test_create_issue_uses_config_org_and_project(self, mock_run, azdo_config_complete):
    """Should use organization and project from config."""
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout=json.dumps({"id": 789}),
        stderr=""
    )

    bridge = AzureDevOpsBridge(config=azdo_config_complete)
    bridge.create_issue(title="Test", body="Test")

    args = mock_run.call_args[0][0]
    org_index = args.index("--org")
    assert "myorg" in args[org_index + 1]
```

### 5. `test_cli.py` - CLI Interface Tests

**Coverage**: 85+ test cases

**Test Categories**:

- CLI initialization
- `create-issue` command (argument parsing, JSON output, labels, missing args)
- `create-pr` command (draft default, base branch, JSON output)
- `mark-pr-ready` command (PR number parsing, invalid numbers)
- `add-pr-comment` command (stdin reading, multiline comments)
- `check-ci-status` command (ref parsing, check details output)
- Platform auto-detection integration
- Platform override with --platform flag
- Error handling (bridge errors, invalid commands, exceptions)
- Help text generation (usage, command-specific help, command list)
- main() entry point
- JSON output consistency (valid JSON, pretty-printing)

**Key Test Patterns**:

```python
@patch("..cli.GitHubBridge")
def test_create_issue_parses_arguments(self, mock_bridge_class):
    """Should parse create-issue command arguments."""
    mock_bridge = MagicMock()
    mock_bridge_class.return_value = mock_bridge
    mock_bridge.create_issue.return_value = {"success": True, "issue_number": 123}

    cli = CLI(platform="github")
    args = ["create-issue", "--title", "Test Issue", "--body", "Issue description"]

    result = cli.run(args)

    assert result == 0
    mock_bridge.create_issue.assert_called_once_with(
        title="Test Issue",
        body="Issue description"
    )
```

### 6. `test_security.py` - Security Tests

**Coverage**: 65+ test cases

**Test Categories**:

- Command injection prevention (PR titles, branch names, comments, issue bodies)
- Input validation (PR numbers, empty inputs, type checking)
- Length limits (titles, bodies, comments, branch names)
- Special character handling (Unicode, newlines, null bytes, quotes)
- Error message sanitization (token leakage, password leakage, path leakage)
- Subprocess argument escaping (list args, shell=False, command chaining prevention)
- Branch name validation (special chars, path traversal)
- Azure DevOps security parity (injection prevention, input validation)
- CLI security integration (PR number validation, dangerous platform names, stdin sanitization)
- Timeout configuration (DoS prevention, reasonable limits)

**Key Test Patterns**:

```python
@patch("subprocess.run")
def test_pr_title_injection_prevented(self, mock_run, malicious_pr_title):
    """Should prevent command injection via PR title."""
    mock_run.return_value = MagicMock(returncode=0, stdout='{"number": 123}', stderr="")

    bridge = GitHubBridge()
    result = bridge.create_draft_pr(
        title=malicious_pr_title,
        body="Normal body",
        branch="feature/test"
    )

    # Verify subprocess.run was called with list, not shell=True
    args = mock_run.call_args[0][0]
    assert isinstance(args, list)

    kwargs = mock_run.call_args[1]
    assert kwargs.get("shell") is not True
```

## Running Tests

### Run all tests

```bash
pytest .claude/tools/platform_bridge/tests/
```

### Run specific test file

```bash
pytest .claude/tools/platform_bridge/tests/test_detector.py
pytest .claude/tools/platform_bridge/tests/test_github_bridge.py
pytest .claude/tools/platform_bridge/tests/test_azdo_bridge.py
pytest .claude/tools/platform_bridge/tests/test_cli.py
pytest .claude/tools/platform_bridge/tests/test_security.py
```

### Run specific test class

```bash
pytest .claude/tools/platform_bridge/tests/test_detector.py::TestGitHubURLDetection
pytest .claude/tools/platform_bridge/tests/test_security.py::TestCommandInjectionPrevention
```

### Run specific test

```bash
pytest .claude/tools/platform_bridge/tests/test_detector.py::TestGitHubURLDetection::test_detect_github_https_url
```

### Run with coverage

```bash
pytest --cov=.claude/tools/platform_bridge --cov-report=html .claude/tools/platform_bridge/tests/
```

### Run with verbose output

```bash
pytest -v .claude/tools/platform_bridge/tests/
```

## Test Philosophy

### TDD Approach

All tests are written **before** implementation. Tests will fail until corresponding implementation is complete.

### Testing Pyramid

- **60% Unit tests**: Fast, isolated, heavily mocked
- **30% Integration tests**: Multiple components working together
- **10% E2E tests**: Complete workflows

### Arrange-Act-Assert Pattern

All tests follow AAA pattern:

```python
def test_example(self):
    # Arrange - Set up test data and mocks
    mock_run.return_value = MagicMock(returncode=0, stdout='{"number": 123}')

    # Act - Execute the functionality
    result = bridge.create_issue(title="Test", body="Test")

    # Assert - Verify the outcome
    assert result["success"] is True
```

### Clear Test Names

Test names describe behavior being tested:

- ✅ `test_create_issue_success` - Clear what's being tested
- ✅ `test_pr_title_injection_prevented` - Describes security behavior
- ❌ `test_case_1` - Unclear purpose

### Mock External Dependencies

All external dependencies are mocked:

- `subprocess.run` - Mock CLI tool calls
- Platform detection - Mock git commands
- File system operations - Use tmp_path fixtures

## Expected Test Failures (TDD)

Until implementation is complete, expect these import failures:

```python
# Module not implemented yet
from ..detector import PlatformDetector, Platform  # ImportError
from ..github_bridge import GitHubBridge  # ImportError
from ..azdo_bridge import AzureDevOpsBridge  # ImportError
from ..cli import CLI, main  # ImportError
```

After implementation, expect these test failures:

1. **detector.py**: Missing Platform enum, PlatformDetector class, detection logic
2. **github_bridge.py**: Missing GitHubBridge class, 5 operations methods
3. **azdo_bridge.py**: Missing AzureDevOpsBridge class, config loading, 5 operations
4. **cli.py**: Missing CLI class, argument parsing, command routing
5. **Security**: Missing input validation, sanitization, escaping logic

## Test Coverage Goals

- **Line coverage**: 90%+
- **Branch coverage**: 85%+
- **Function coverage**: 95%+

## Security Test Importance

Security tests are **critical** and must pass before any production use:

- Command injection prevention (highest priority)
- Input validation (required)
- Error message sanitization (required)
- Subprocess escaping (required)

## Contributing

When adding new functionality:

1. Write tests first (TDD)
2. Ensure tests fail without implementation
3. Implement functionality
4. Verify tests pass
5. Check coverage remains >90%

## Test Data

All test data is centralized in `conftest.py`:

- Realistic URLs for both platforms
- Example API responses
- Security attack vectors
- Configuration examples

This ensures consistency across all test files and makes it easy to update test data.
