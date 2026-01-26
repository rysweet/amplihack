# Security Testing Guide

> [Security](./README.md) > Testing Guide

How to test security features in amplihack, including token sanitization, input validation, and file permissions.

## Contents

- [Testing Pyramid](#testing-pyramid)
- [Running Security Tests](#running-security-tests)
- [Writing Security Tests](#writing-security-tests)
- [Test Coverage Requirements](#test-coverage-requirements)
- [Common Test Patterns](#common-test-patterns)

## Testing Pyramid

Security tests follow the 60/30/10 testing pyramid:

- **60% Unit Tests**: Fast, isolated, heavily mocked
- **30% Integration Tests**: Multiple components, real scenarios
- **10% E2E Tests**: Complete workflows, minimal mocking

### Why This Distribution?

1. **Unit tests (60%)**: Catch bugs early, run in milliseconds
2. **Integration tests (30%)**: Verify component interactions
3. **E2E tests (10%)**: Validate complete user workflows

## Running Security Tests

### All Security Tests

Run the complete security test suite:

```bash
# From project root
pytest tests/proxy/test_security_sanitization.py -v

# Run with coverage
pytest tests/proxy/test_security_sanitization.py --cov=amplihack.proxy.security --cov-report=term-missing
```

Expected output:

```
tests/proxy/test_security_sanitization.py::TestTokenPatternDetection::test_github_token_detection PASSED
tests/proxy/test_security_sanitization.py::TestTokenPatternDetection::test_openai_token_detection PASSED
...
========================= 50 passed in 1.2s =========================
```

### Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/proxy/test_security_sanitization.py::TestTokenPatternDetection -v
pytest tests/proxy/test_security_sanitization.py::TestStringSanitization -v

# Integration tests only
pytest tests/proxy/test_security_sanitization.py::TestRealErrorScenarios -v
pytest tests/proxy/test_security_sanitization.py::TestEdgeCases -v

# E2E tests only
pytest tests/proxy/test_security_sanitization.py::TestEndToEndSanitization -v

# Performance tests
pytest tests/proxy/test_security_sanitization.py::TestPerformance -v
```

### Continuous Integration

Security tests run automatically on:

- Every commit to main branch
- Every pull request
- Pre-commit hooks (optional)

CI configuration includes:

```yaml
# .github/workflows/security-tests.yml
- name: Run security tests
  run: |
    pytest tests/proxy/test_security_sanitization.py \
      --cov=amplihack.proxy.security \
      --cov-fail-under=90
```

## Writing Security Tests

### Test Structure

Security tests follow this structure:

```python
"""Tests for [feature] security.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)
"""

import pytest
from amplihack.proxy.security import TokenSanitizer

# Unit tests (60%)
class TestBasicFunctionality:
    """Test core functionality in isolation."""

    def test_specific_behavior(self):
        sanitizer = TokenSanitizer()
        result = sanitizer.sanitize("test input")
        assert result == "expected output"

# Integration tests (30%)
class TestRealScenarios:
    """Test realistic scenarios with multiple components."""

    def test_real_world_case(self):
        # Test actual usage pattern
        pass

# E2E tests (10%)
class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    def test_full_workflow(self):
        # Test complete user journey
        pass
```

### Unit Test Example

Test token detection in isolation:

```python
def test_github_token_detection():
    """Test detection of GitHub tokens (gho_, ghp_, ghs_, etc.)."""
    sanitizer = TokenSanitizer()

    # Valid tokens
    assert sanitizer.contains_token("gho_1234567890abcdefghij")  # pragma: allowlist secret
    assert sanitizer.contains_token("ghp_1234567890abcdefghij")  # pragma: allowlist secret

    # Invalid tokens
    assert not sanitizer.contains_token("github oauth token")
    assert not sanitizer.contains_token("gho_short")  # Too short
```

**Key points**:

- Clear docstring explaining what's tested
- Test both valid and invalid cases
- Use `# pragma: allowlist secret` for test tokens
- Fast execution (< 1ms)

### Integration Test Example

Test sanitization in real error scenarios:

```python
def test_sanitize_github_api_error():
    """Test sanitizing GitHub API error messages."""
    sanitizer = TokenSanitizer()

    # Real error message format
    error_msg = """
    HTTP 401 Unauthorized
    Request headers:
        Authorization: Bearer gho_1234567890abcdefghij
        X-GitHub-Api-Version: 2023-11-15
    Response: {"message": "Bad credentials"}
    """  # pragma: allowlist secret

    result = sanitizer.sanitize(error_msg)

    # Verify token redacted
    assert "gho_1234567890abcdefghij" not in result
    assert "[REDACTED-GITHUB-TOKEN]" in result

    # Verify other data preserved
    assert "Bad credentials" in result
    assert "X-GitHub-Api-Version" in result
```

**Key points**:

- Use realistic error formats
- Test multiple token types together
- Verify both redaction and preservation
- Check complete error structure

### E2E Test Example

Test complete sanitization workflow:

```python
def test_complete_error_sanitization_workflow():
    """Test sanitizing a complete error report."""
    sanitizer = TokenSanitizer()

    # Complete error report structure
    error_report = {
        "error": "API authentication failed",
        "request": {
            "url": "https://api.github.com/copilot/chat/completions",
            "headers": {
                "Authorization": "Bearer gho_1234567890abcdefghij",  # pragma: allowlist secret
                "Content-Type": "application/json"
            },
            "body": {
                "messages": [{"role": "user", "content": "Hello"}]
            }
        },
        "response": {
            "status": 401,
            "body": {"message": "Bad credentials"}
        },
        "traceback": [
            "File 'proxy/server.py', line 123",
            "  auth_header = f'Bearer {gho_1234567890abcdefghij}'",  # pragma: allowlist secret
            "ConnectionError: Authentication failed"
        ]
    }

    result = sanitizer.sanitize(error_report)

    # Verify complete sanitization
    assert "gho_1234567890abcdefghij" not in str(result)
    assert result["error"] == "API authentication failed"
    assert result["response"]["status"] == 401
```

**Key points**:

- Test complete user workflows
- Use realistic data structures
- Verify end-to-end behavior
- Check data preservation throughout

## Test Coverage Requirements

### Minimum Coverage

Security code requires **90% minimum coverage**:

```bash
pytest tests/proxy/test_security_sanitization.py \
  --cov=amplihack.proxy.security \
  --cov-fail-under=90
```

### Coverage Areas

Must test:

- ✅ All token pattern types (GitHub, OpenAI, Anthropic, Bearer, JWT, Azure)
- ✅ String sanitization (simple, nested, edge cases)
- ✅ Dictionary sanitization (flat, nested, mixed types)
- ✅ List sanitization (flat, nested, mixed types)
- ✅ Error scenarios (API errors, tracebacks, logs)
- ✅ Edge cases (empty, None, unicode, boundaries)
- ✅ Performance (< 1ms for typical operations)
- ✅ False positives (safe text preserved)
- ✅ False negatives (real tokens detected)

### Coverage Report

Generate detailed coverage report:

```bash
pytest tests/proxy/test_security_sanitization.py \
  --cov=amplihack.proxy.security \
  --cov-report=html

# Open in browser
open htmlcov/index.html
```

## Common Test Patterns

### Testing Token Detection

```python
def test_token_type_detection():
    """Test detection of specific token type."""
    sanitizer = TokenSanitizer()

    # Valid tokens (should detect)
    valid_tokens = [
        "gho_1234567890abcdefghij",  # pragma: allowlist secret
        "Bearer gho_1234567890",     # pragma: allowlist secret
    ]

    for token in valid_tokens:
        assert sanitizer.contains_token(token), f"Should detect: {token}"

    # Invalid tokens (should not detect)
    invalid_tokens = [
        "github token",  # No actual token
        "gho_short",     # Too short
        "gho_",          # Prefix only
    ]

    for token in invalid_tokens:
        assert not sanitizer.contains_token(token), f"Should not detect: {token}"
```

### Testing Sanitization

```python
def test_sanitization_behavior():
    """Test sanitization redacts tokens but preserves other data."""
    sanitizer = TokenSanitizer()

    data = {
        "token": "gho_abc123xyz",  # pragma: allowlist secret
        "safe_field": "preserve this",
        "nested": {
            "api_key": "sk-proj-test",  # pragma: allowlist secret
            "name": "test config"
        }
    }

    result = sanitizer.sanitize(data)

    # Tokens redacted
    assert "gho_abc123xyz" not in str(result)
    assert "sk-proj-test" not in str(result)

    # Other data preserved
    assert result["safe_field"] == "preserve this"
    assert result["nested"]["name"] == "test config"
```

### Testing Edge Cases

```python
def test_edge_case():
    """Test behavior with edge case input."""
    sanitizer = TokenSanitizer()

    # Empty
    assert sanitizer.sanitize("") == ""
    assert sanitizer.sanitize({}) == {}
    assert sanitizer.sanitize([]) == []

    # None
    assert sanitizer.sanitize(None) is None

    # Non-string types preserved
    assert sanitizer.sanitize(123) == 123
    assert sanitizer.sanitize(True) is True
```

### Testing Performance

```python
def test_performance_requirement():
    """Test that operation completes within time limit."""
    import time

    sanitizer = TokenSanitizer()
    text = "Token: gho_1234567890abcdefghij"  # pragma: allowlist secret

    # Measure 100 iterations
    start = time.perf_counter()
    for _ in range(100):
        sanitizer.sanitize(text)
    elapsed = time.perf_counter() - start

    # Verify < 1ms average
    avg_time_ms = (elapsed / 100) * 1000
    assert avg_time_ms < 1.0, f"Average time {avg_time_ms:.3f}ms exceeds 1ms"
```

### Testing False Positives

```python
def test_no_false_positives():
    """Test that safe text is not flagged as tokens."""
    sanitizer = TokenSanitizer()

    safe_texts = [
        "Connect to GitHub API",
        "Use github.com for authentication",
        "GitHub token format: gho_...",
        "Set your OpenAI API key",
        "API key format: sk-...",
    ]

    for text in safe_texts:
        result = sanitizer.sanitize(text)
        assert result == text, f"False positive for: {text}"
```

## Security Test Checklist

Before merging security changes:

- [ ] All unit tests pass (60% of tests)
- [ ] All integration tests pass (30% of tests)
- [ ] All E2E tests pass (10% of tests)
- [ ] Coverage ≥ 90%
- [ ] Performance tests pass (< 1ms target)
- [ ] No false positives detected
- [ ] No false negatives detected
- [ ] All token types tested
- [ ] Edge cases covered
- [ ] Real error scenarios tested

## Related Documentation

- [Token Sanitization Guide](./TOKEN_SANITIZATION_GUIDE.md) - Usage examples
- [Security API Reference](./SECURITY_API_REFERENCE.md) - Complete API docs
- [Security README](./README.md) - Security overview

---

**Test Implementation**: See `tests/proxy/test_security_sanitization.py` for complete test suite.
