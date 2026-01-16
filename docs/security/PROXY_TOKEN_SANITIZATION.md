# Proxy Token Sanitization

> [Home](../index.md) > [Security](README.md) > Token Sanitization

**Last Updated**: 2026-01-14

Comprehensive guide to token sanitization in the amplihack proxy module, preventing API token exposure in logs and error messages.

## Overview

The proxy token sanitization system automatically redacts sensitive authentication tokens from all log output, error messages, and debug information. This prevents accidental token exposure through log aggregation systems, error reports, or development environments.

**Security Impact**: HIGH - Prevents API token leakage in logs

## Quick Start

Token sanitization is **automatic** and **always enabled**. No configuration required.

```python
from amplihack.proxy.server import sanitize_for_logging

# Example: Safe error logging
try:
    api_call_with_token(api_key="sk-ant-1234567890abcdef")
except Exception as e:
    # Tokens automatically sanitized
    logger.error(f"API call failed: {sanitize_for_logging(str(e))}")
    # Output: "API call failed: API key ***REDACTED***"
```

## How It Works

### Automatic Token Detection

The sanitization system detects and redacts multiple token formats:

| Token Type | Pattern | Example | Redacted As |
|------------|---------|---------|-------------|
| Anthropic API Key | `sk-ant-*` | `sk-ant-api03-1234...` | `***REDACTED***` |
| OpenAI API Key | `sk-*` | `sk-proj-1234...` | `***REDACTED***` |
| Generic Bearer Token | `Bearer *` | `Bearer eyJhbGc...` | `Bearer ***REDACTED***` |
| GitHub Token | `github_pat_*` | `github_pat_11A...` | `***REDACTED***` |

### Sanitization Points

Token sanitization occurs at **three critical points**:

1. **Error Logging** (lines 2048-2082 in `proxy_server.py`)
   - All exceptions sanitized before logging
   - Stack traces cleaned of sensitive data

2. **Debug Output** (throughout `proxy_server.py`)
   - Request/response logging sanitized
   - Model mapping logs sanitized

3. **User-Facing Error Messages**
   - HTTP error responses sanitized
   - Validation error messages sanitized

### Implementation

The sanitization function uses regex patterns to identify and redact tokens:

```python
def sanitize_for_logging(text: str) -> str:
    """Sanitize sensitive tokens from text before logging.

    Replaces API keys and bearer tokens with '***REDACTED***'.
    """
    if not isinstance(text, str):
        text = str(text)

    # Redact Anthropic API keys (sk-ant-*)
    text = re.sub(r'sk-ant-[a-zA-Z0-9_-]+', '***REDACTED***', text)

    # Redact OpenAI API keys (sk-*)
    text = re.sub(r'sk-[a-zA-Z0-9_-]+', '***REDACTED***', text)

    # Redact Bearer tokens
    text = re.sub(r'Bearer\s+[a-zA-Z0-9_.-]+', 'Bearer ***REDACTED***', text)

    # Redact GitHub tokens
    text = re.sub(r'github_pat_[a-zA-Z0-9_]+', '***REDACTED***', text)

    return text
```

## Usage Examples

### Safe Error Handling

```python
from amplihack.proxy.server import sanitize_for_logging
import logging

logger = logging.getLogger(__name__)

# BAD - Token exposed in logs
try:
    result = anthropic_api_call(api_key="sk-ant-1234567890")
except Exception as e:
    logger.error(f"Failed: {e}")  # ❌ Token visible in logs

# GOOD - Token automatically sanitized
try:
    result = anthropic_api_call(api_key="sk-ant-1234567890")
except Exception as e:
    logger.error(f"Failed: {sanitize_for_logging(str(e))}")  # ✅ Token redacted
```

### Safe Request Logging

```python
# BAD - Authorization header exposed
logger.debug(f"Request headers: {request.headers}")
# Output: Authorization: Bearer sk-ant-1234567890

# GOOD - Headers sanitized
logger.debug(f"Request headers: {sanitize_for_logging(str(request.headers))}")
# Output: Authorization: Bearer ***REDACTED***
```

### Safe Exception Messages

```python
# BAD - Token in exception message
raise ValueError(f"Invalid API key: {api_key}")

# GOOD - Sanitized exception message
raise ValueError(f"Invalid API key: {sanitize_for_logging(api_key)}")
```

## Security Testing

### Verify Token Sanitization

The proxy includes comprehensive tests to verify tokens never appear in logs:

```python
def test_token_sanitization():
    """Verify API tokens are never exposed in logs."""
    sensitive_tokens = [
        "sk-ant-api03-1234567890abcdef",
        "sk-proj-9876543210fedcba",
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "github_pat_11AAAAAA0123456789",
    ]

    for token in sensitive_tokens:
        error_message = f"API call failed with key: {token}"
        sanitized = sanitize_for_logging(error_message)

        # Verify token is redacted
        assert token not in sanitized
        assert "***REDACTED***" in sanitized
```

### Security Audit Commands

Run security tests to verify token protection:

```bash
# Run token sanitization tests
pytest tests/proxy/test_message_sanitization.py -v

# Run full security test suite
pytest tests/test_security.py -v

# Check for token exposure in logs (should return nothing)
grep -r "sk-ant-" logs/ && echo "❌ SECURITY VIOLATION" || echo "✅ No tokens found"
```

## Token File Permissions

Token files stored on disk use **restrictive permissions** (0600) to prevent unauthorized access:

```python
def save_token(token: str, token_file: Path) -> None:
    """Save token with secure file permissions."""
    token_file.write_text(token)

    # Set file permissions to 0600 (read/write owner only)
    os.chmod(token_file, 0o600)

    logger.info(f"Token saved to {token_file} (permissions: 0600)")
```

**File Permission Breakdown**:
- `0600` = Owner read/write only
- No group access
- No world access
- Prevents token theft from multi-user systems

## Security Best Practices

### DO

✅ **Always sanitize** before logging any user input or API responses
✅ **Use `sanitize_for_logging()`** for all error messages containing tokens
✅ **Test token sanitization** when adding new logging statements
✅ **Set file permissions to 0600** for any files storing tokens
✅ **Use environment variables** for token configuration (not hardcoded)

### DON'T

❌ **Never log raw API keys** without sanitization
❌ **Never commit tokens** to version control
❌ **Never expose tokens** in user-facing error messages
❌ **Never store tokens** in world-readable files
❌ **Never disable** token sanitization for "debugging"

## Troubleshooting

### Problem: Token Still Visible in Logs

**Cause**: Logging before sanitization applied

**Solution**: Wrap all logging with `sanitize_for_logging()`:

```python
# Before (vulnerable)
logger.error(f"Error: {exception_message}")

# After (secure)
logger.error(f"Error: {sanitize_for_logging(exception_message)}")
```

### Problem: Custom Token Format Not Redacted

**Cause**: Custom token format not in regex patterns

**Solution**: Add custom pattern to `sanitize_for_logging()`:

```python
# Add custom token pattern
text = re.sub(r'custom_token_[a-zA-Z0-9_-]+', '***REDACTED***', text)
```

### Problem: Performance Impact from Sanitization

**Impact**: Negligible (< 1ms per call for typical log messages)

**Mitigation**: Sanitization only applied to log output, not data processing

## Related Documentation

- [Security Best Practices](../SECURITY_RECOMMENDATIONS.md) - General security guidelines
- [Proxy Security API Reference](PROXY_SECURITY_API.md) - Technical API documentation
- [Security Testing Guide](PROXY_SECURITY_TESTING.md) - Comprehensive test strategy
- [Migration Guide](PROXY_SECURITY_MIGRATION.md) - Updating existing code

---

**Security First**: Token sanitization is **non-negotiable**. All log output MUST be sanitized.
