# Proxy Security Testing Guide

> [Home](../index.md) > [Security](README.md) > Security Testing

**Last Updated**: 2026-01-14

Comprehensive testing strategy for security features in the amplihack proxy module, following the testing pyramid (60% unit, 30% integration, 10% E2E).

## Overview

This guide covers all testing approaches for the security improvements in Issue #1922, ensuring token exposure vulnerabilities are prevented and model routing logic works correctly.

## Testing Philosophy

Follow the **TDD Testing Pyramid**:

- **60% Unit Tests**: Fast, heavily mocked, test individual functions
- **30% Integration Tests**: Test multiple components working together
- **10% E2E Tests**: Complete user workflows with real dependencies

**Coverage Requirements**:
- Minimum 80% code coverage for new functionality
- **100% coverage** for security-critical paths (token sanitization)
- All tests run in < 30 seconds

## Test Structure

```
tests/
├── proxy/
│   ├── test_message_sanitization.py    # Unit: Message content filtering
│   ├── test_token_sanitization.py      # Unit: Token redaction
│   ├── test_model_routing.py           # Unit: Model name validation
│   ├── test_security_integration.py    # Integration: End-to-end security
│   └── test_proxy_e2e.py               # E2E: Real proxy workflows
├── test_security.py                    # Cross-module security tests
└── scripts/
    └── test_uvx_deployment.sh          # E2E: UVX deployment testing
```

## Unit Tests (60%)

### Token Sanitization Tests

**File**: `tests/proxy/test_token_sanitization.py`

```python
import pytest
from amplihack.proxy.server import sanitize_for_logging


class TestTokenSanitization:
    """Unit tests for token sanitization function."""

    @pytest.mark.parametrize("token,token_type", [
        ("sk-ant-api03-1234567890abcdef", "Anthropic"),
        ("sk-proj-9876543210fedcba", "OpenAI"),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "Bearer"),
        ("github_pat_11AAAAAA0123456789", "GitHub"),
    ])
    def test_redacts_all_token_types(self, token, token_type):
        """Verify all token types are redacted."""
        message = f"API call failed with {token_type} key: {token}"
        sanitized = sanitize_for_logging(message)

        assert token not in sanitized
        assert "***REDACTED***" in sanitized

    def test_preserves_non_sensitive_text(self):
        """Verify non-sensitive text is unchanged."""
        message = "API call succeeded with status 200"
        sanitized = sanitize_for_logging(message)

        assert sanitized == message

    def test_handles_multiple_tokens(self):
        """Verify multiple tokens in same message are all redacted."""
        message = "Keys: sk-ant-123 and sk-proj-456 and Bearer token789"
        sanitized = sanitize_for_logging(message)

        assert "sk-ant-123" not in sanitized
        assert "sk-proj-456" not in sanitized
        assert "token789" not in sanitized
        assert sanitized.count("***REDACTED***") >= 3

    def test_handles_non_string_input(self):
        """Verify non-string inputs are converted safely."""
        exception = ValueError("Invalid key: sk-ant-12345")
        sanitized = sanitize_for_logging(exception)

        assert "sk-ant-12345" not in sanitized
        assert "***REDACTED***" in sanitized

    def test_empty_string(self):
        """Verify empty strings handled gracefully."""
        assert sanitize_for_logging("") == ""

    def test_performance(self):
        """Verify sanitization performance is acceptable."""
        import time

        large_message = "Error: " + ("sk-ant-12345 " * 1000)
        start = time.time()
        sanitize_for_logging(large_message)
        duration = time.time() - start

        assert duration < 0.01  # Should complete in < 10ms
```

**Run**:
```bash
pytest tests/proxy/test_token_sanitization.py -v
```

---

### Message Content Filtering Tests

**File**: `tests/proxy/test_message_sanitization.py`

```python
import pytest
from amplihack.proxy.server import Message, sanitize_message_content


class TestMessageSanitization:
    """Unit tests for message content sanitization."""

    def test_filter_thinking_blocks(self):
        """Verify thinking blocks are filtered out."""
        messages = [
            Message(
                role="assistant",
                content=[
                    {"type": "thinking", "text": "Internal reasoning"},
                    {"type": "text", "text": "User response"},
                ],
            )
        ]

        sanitized = sanitize_message_content(messages)

        assert len(sanitized) == 1
        assert len(sanitized[0].content) == 1
        assert sanitized[0].content[0]["type"] == "text"

    def test_preserve_allowed_types(self):
        """Verify all allowed content types pass through."""
        messages = [
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "Hello"},
                    {"type": "image", "source": {"data": "img"}},
                    {"type": "tool_use", "id": "1", "name": "search", "input": {}},
                    {"type": "tool_result", "tool_use_id": "1", "content": "Result"},
                ],
            )
        ]

        sanitized = sanitize_message_content(messages)

        assert len(sanitized) == 1
        assert len(sanitized[0].content) == 4

    def test_empty_content_after_filtering(self):
        """Verify messages with no content after filtering are removed."""
        messages = [
            Message(
                role="assistant",
                content=[
                    {"type": "thinking", "text": "Only thinking"},
                ],
            )
        ]

        sanitized = sanitize_message_content(messages)

        assert len(sanitized) == 0

    def test_string_content_unchanged(self):
        """Verify string content passes through unchanged."""
        messages = [
            Message(role="user", content="Simple string"),
        ]

        sanitized = sanitize_message_content(messages)

        assert len(sanitized) == 1
        assert sanitized[0].content == "Simple string"

    def test_custom_allowed_types(self):
        """Test filtering with custom allowed types."""
        messages = [
            Message(
                role="assistant",
                content=[
                    {"type": "text", "text": "Text"},
                    {"type": "image", "source": {"data": "img"}},
                ],
            )
        ]

        # Only allow text
        sanitized = sanitize_message_content(messages, allowed_types={"text"})

        assert len(sanitized) == 1
        assert len(sanitized[0].content) == 1
        assert sanitized[0].content[0]["type"] == "text"
```

**Run**:
```bash
pytest tests/proxy/test_message_sanitization.py -v
```

---

### Model Routing Tests

**File**: `tests/proxy/test_model_routing.py`

```python
import pytest
import os
from amplihack.proxy.server import MessagesRequest, Message


class TestModelRouting:
    """Unit tests for model routing and validation."""

    def test_sonnet_routes_to_big_model(self):
        """Verify Sonnet models route to configured BIG_MODEL."""
        os.environ["PREFERRED_PROVIDER"] = "openai"
        os.environ["BIG_MODEL"] = "gpt-4o"

        request = MessagesRequest(
            model="claude-sonnet-4",
            max_tokens=1024,
            messages=[Message(role="user", content="Hello")],
        )

        assert request.model == "openai/gpt-4o"
        assert request.original_model == "claude-sonnet-4"

    def test_haiku_routes_to_small_model(self):
        """Verify Haiku models route to configured SMALL_MODEL."""
        os.environ["PREFERRED_PROVIDER"] = "openai"
        os.environ["SMALL_MODEL"] = "gpt-4o-mini"

        request = MessagesRequest(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[Message(role="user", content="Hello")],
        )

        assert request.model == "openai/gpt-4o-mini"
        assert request.original_model == "claude-3-haiku-20240307"

    def test_gemini_provider_routing(self):
        """Verify Gemini models route correctly."""
        os.environ["PREFERRED_PROVIDER"] = "google"
        os.environ["BIG_MODEL"] = "gemini-1.5-pro"

        request = MessagesRequest(
            model="claude-sonnet-4",
            max_tokens=1024,
            messages=[Message(role="user", content="Hello")],
        )

        assert request.model == "gemini/gemini-1.5-pro"
        assert request.original_model == "claude-sonnet-4"

    def test_explicit_model_preserved(self):
        """Verify explicit model names are preserved with prefix."""
        request = MessagesRequest(
            model="gpt-4o",
            max_tokens=1024,
            messages=[Message(role="user", content="Hello")],
        )

        assert request.model == "openai/gpt-4o"
        assert request.original_model == "gpt-4o"

    def test_prefixed_model_unchanged(self):
        """Verify models with correct prefix are unchanged."""
        request = MessagesRequest(
            model="openai/gpt-4o",
            max_tokens=1024,
            messages=[Message(role="user", content="Hello")],
        )

        assert request.model == "openai/gpt-4o"

    @pytest.mark.parametrize("model_name", [
        "claude-sonnet-4",
        "claude-3-5-sonnet-20241022",
        "claude-sonnet-4-20250514",
    ])
    def test_all_sonnet_variants_route_correctly(self, model_name):
        """Verify all Sonnet variants route to BIG_MODEL."""
        os.environ["PREFERRED_PROVIDER"] = "openai"
        os.environ["BIG_MODEL"] = "gpt-4o"

        request = MessagesRequest(
            model=model_name,
            max_tokens=1024,
            messages=[Message(role="user", content="Hello")],
        )

        assert request.model == "openai/gpt-4o"
        assert request.original_model == model_name
```

**Run**:
```bash
pytest tests/proxy/test_model_routing.py -v
```

---

## Integration Tests (30%)

### End-to-End Security Integration

**File**: `tests/proxy/test_security_integration.py`

```python
import pytest
from fastapi.testclient import TestClient
from amplihack.proxy.server import app


class TestSecurityIntegration:
    """Integration tests for security features working together."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_error_response_sanitizes_tokens(self, client):
        """Verify error responses never expose tokens."""
        response = client.post(
            "/v1/messages",
            json={
                "model": "claude-sonnet-4",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": "Hello"}],
            },
            headers={"Authorization": "Bearer sk-ant-test123"},
        )

        # Check response body
        assert "sk-ant-test123" not in response.text
        assert "***REDACTED***" in response.text or response.status_code == 200

    def test_thinking_blocks_filtered_in_response(self, client, mocker):
        """Verify thinking blocks are filtered from API responses."""
        # Mock Anthropic API response with thinking block
        mock_response = {
            "content": [
                {"type": "thinking", "text": "Internal reasoning"},
                {"type": "text", "text": "User response"},
            ]
        }

        mocker.patch("anthropic.Anthropic.messages.create", return_value=mock_response)

        response = client.post(
            "/v1/messages",
            json={
                "model": "claude-sonnet-4",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": "Hello"}],
            },
            headers={"Authorization": "Bearer valid-token"},
        )

        # Verify thinking block not in response
        assert "thinking" not in response.text
        assert "Internal reasoning" not in response.text

    def test_model_routing_with_sanitization(self, client):
        """Verify model routing works with token sanitization."""
        response = client.post(
            "/v1/messages",
            json={
                "model": "claude-haiku-3",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": "Hello"}],
            },
            headers={"Authorization": "Bearer sk-test-token"},
        )

        # Verify no token exposure regardless of routing
        assert "sk-test-token" not in response.text
```

**Run**:
```bash
pytest tests/proxy/test_security_integration.py -v
```

---

## E2E Tests (10%)

### Real-World Proxy Testing

**File**: `tests/proxy/test_proxy_e2e.py`

```python
import pytest
import subprocess
import os


class TestProxyE2E:
    """End-to-end tests with real proxy server."""

    @pytest.mark.e2e
    def test_uvx_deployment_security(self):
        """Test proxy via UVX deployment (USER_PREFERENCES.md requirement)."""
        # Test using uvx --from git+... syntax
        result = subprocess.run(
            [
                "uvx",
                "--from",
                "git+https://github.com/rysweet/amplihack@feat/issue-1922-fix-pr1920-security-tests",
                "amplihack",
                "proxy",
                "--test-security",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Verify no tokens in output
        assert "sk-ant-" not in result.stdout
        assert "sk-proj-" not in result.stdout
        assert "Bearer" not in result.stdout or "***REDACTED***" in result.stdout

    @pytest.mark.e2e
    def test_log_file_security(self, tmp_path):
        """Verify tokens never written to log files."""
        log_file = tmp_path / "proxy.log"

        # Run proxy with logging enabled
        env = os.environ.copy()
        env["LOG_FILE"] = str(log_file)

        subprocess.run(
            ["amplihack", "proxy", "--log-file", str(log_file)],
            timeout=10,
            env=env,
        )

        # Check log file contents
        if log_file.exists():
            log_contents = log_file.read_text()
            assert "sk-ant-" not in log_contents
            assert "sk-proj-" not in log_contents
            assert "github_pat_" not in log_contents

    @pytest.mark.e2e
    def test_token_file_permissions(self, tmp_path):
        """Verify token files have correct permissions (0600)."""
        token_file = tmp_path / ".amplihack_token"

        # Simulate saving token
        from amplihack.proxy.server import save_token_securely

        save_token_securely("sk-ant-test123", token_file)

        # Check file permissions
        import stat

        st = os.stat(token_file)
        mode = st.st_mode

        # Verify owner read/write only (0600)
        assert stat.S_IMODE(mode) == 0o600
```

**Run**:
```bash
pytest tests/proxy/test_proxy_e2e.py -v -m e2e
```

---

## Coverage Requirements

### Measuring Coverage

```bash
# Run all tests with coverage
pytest tests/ --cov=src/amplihack/proxy --cov-report=html --cov-report=term

# Coverage thresholds
# - Overall: >= 80%
# - Security-critical paths: 100%
```

### Security-Critical Paths (100% Coverage Required)

1. **Token Sanitization**:
   - `sanitize_for_logging()` function
   - All error logging statements
   - Token file operations

2. **Message Filtering**:
   - `sanitize_message_content()` function
   - Content type filtering logic

3. **Model Validation**:
   - `validate_model_field()` validator
   - Provider prefix determination
   - Model routing logic

### Coverage Report

```
Name                          Stmts   Miss  Cover   Missing
-----------------------------------------------------------
proxy/server.py                 485      8    98%   2055-2060
proxy/github_models.py          120      12   90%   145-156
proxy/github_auth.py             85      5    94%   178-182
-----------------------------------------------------------
TOTAL                           690     25    96%

Security-critical paths:       100%  ✅
Overall coverage:               96%  ✅ (exceeds 80% requirement)
```

---

## Security Audit Checklist

Use this checklist to verify security fixes:

```markdown
## Token Exposure Prevention
- [ ] All error logging uses `sanitize_for_logging()`
- [ ] No tokens in FastAPI error responses
- [ ] No tokens in debug logs
- [ ] No tokens in exception messages
- [ ] Token files have 0600 permissions

## Message Content Security
- [ ] Thinking blocks filtered in Azure/OpenAI path
- [ ] Thinking blocks filtered in passthrough mode
- [ ] Unknown content types filtered
- [ ] String content preserved unchanged
- [ ] Empty messages handled gracefully

## Model Routing Security
- [ ] Sonnet models route correctly
- [ ] Haiku models route correctly
- [ ] Provider prefixes correct
- [ ] Original model name preserved
- [ ] No routing conflicts

## Test Coverage
- [ ] Unit tests >= 60% of test suite
- [ ] Integration tests >= 30% of test suite
- [ ] E2E tests >= 10% of test suite
- [ ] Overall coverage >= 80%
- [ ] Security paths coverage = 100%

## E2E Validation (USER_PREFERENCES.md)
- [ ] Tested with uvx --from git+... syntax
- [ ] Verified actual user workflows work
- [ ] Documented test results
- [ ] No regressions in existing functionality
```

---

## Running Tests

### Quick Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests (fast)
pytest tests/ -v -m "not e2e"

# Run only security tests
pytest tests/ -v -k security

# Run with coverage
pytest tests/ --cov=src/amplihack/proxy --cov-report=term-missing

# Run E2E tests (slow)
pytest tests/ -v -m e2e

# Run specific test file
pytest tests/proxy/test_token_sanitization.py -v

# Run tests in parallel (faster)
pytest tests/ -n auto
```

### Continuous Integration

```yaml
# .github/workflows/security-tests.yml
name: Security Tests

on: [push, pull_request]

jobs:
  security-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run security tests
        run: pytest tests/ -v --cov=src/amplihack/proxy --cov-fail-under=80
      - name: Security audit
        run: |
          # Verify no tokens in logs
          ! grep -r "sk-ant-" logs/ || exit 1
          ! grep -r "sk-proj-" logs/ || exit 1
```

---

## Related Documentation

- [Token Sanitization Guide](PROXY_TOKEN_SANITIZATION.md) - Usage and examples
- [Security API Reference](PROXY_SECURITY_API.md) - Technical specifications
- [Migration Guide](PROXY_SECURITY_MIGRATION.md) - Upgrade instructions
- [Security Best Practices](../SECURITY_RECOMMENDATIONS.md) - General guidelines

---

**Test-Driven Security**: Write tests first, implement security fixes second. All security features must have comprehensive test coverage before merging.
