# Token Sanitization Guide

> [Security](./README.md) > Token Sanitization Guide

## Quick Start

Prevent token exposure in logs, errors, and debug output with automatic sanitization.

```python
from amplihack.proxy.security import TokenSanitizer

sanitizer = TokenSanitizer()

# Sanitize error messages before logging
error_msg = "Authentication failed with token: gho_abc123xyz"
safe_msg = sanitizer.sanitize(error_msg)
print(safe_msg)
# Output: "Authentication failed with token: [REDACTED-GITHUB-TOKEN]"
```

## Contents

- [What Gets Sanitized](#what-gets-sanitized)
- [Common Use Cases](#common-use-cases)
- [Integration Examples](#integration-examples)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)

## What Gets Sanitized

TokenSanitizer detects and redacts these token types:

| Token Type | Pattern | Redaction Marker |
|-----------|---------|------------------|
| GitHub tokens | `gho_*`, `ghp_*`, `ghs_*`, `ghu_*`, `ghr_*` | `[REDACTED-GITHUB-TOKEN]` |
| OpenAI keys | `sk-*`, `sk-proj-*` | `[REDACTED-OPENAI-KEY]` |
| Anthropic keys | `sk-ant-*` | `[REDACTED-ANTHROPIC-KEY]` |
| Bearer tokens | `Bearer <token>` | `[REDACTED-BEARER-TOKEN]` |
| JWT tokens | `eyJ*.eyJ*.*` | `[REDACTED-JWT-TOKEN]` |
| Azure keys | `azure-key-*` | `[REDACTED-AZURE-KEY]` |
| Azure connections | `DefaultEndpointsProtocol=...` | `[REDACTED-AZURE-CONNECTION]` |

## Common Use Cases

### Sanitizing API Errors

When API calls fail, error messages often contain authentication tokens:

```python
from amplihack.proxy.security import TokenSanitizer

sanitizer = TokenSanitizer()

try:
    # API call that might fail
    response = github_api.chat_completion(token="gho_abc123xyz")
except Exception as e:
    # Sanitize before logging
    safe_error = sanitizer.sanitize(str(e))
    logger.error(f"API call failed: {safe_error}")
```

**Output**:
```
API call failed: Authentication failed with [REDACTED-GITHUB-TOKEN]
```

### Sanitizing Configuration Dumps

When debugging configuration, sanitize before printing:

```python
from amplihack.proxy.security import TokenSanitizer

config = {
    "github_token": "gho_1234567890abcdefghij",
    "openai_key": "sk-proj-abc123xyz",
    "endpoint": "https://api.github.com"
}

sanitizer = TokenSanitizer()
safe_config = sanitizer.sanitize(config)
print(safe_config)
# Output: {'github_token': '[REDACTED-GITHUB-TOKEN]', 'openai_key': '[REDACTED-OPENAI-KEY]', 'endpoint': 'https://api.github.com'}
```

### Sanitizing Log Files

Process existing log files to remove tokens:

```python
from amplihack.proxy.security import TokenSanitizer
from pathlib import Path

sanitizer = TokenSanitizer()
log_file = Path("debug.log")

# Read, sanitize, and overwrite
content = log_file.read_text()
sanitized = sanitizer.sanitize(content)
log_file.write_text(sanitized)
```

### Checking for Tokens Before Logging

Conditionally sanitize only when tokens are detected:

```python
from amplihack.proxy.security import TokenSanitizer

sanitizer = TokenSanitizer()
message = "Debug info: connection established"

if sanitizer.contains_token(message):
    message = sanitizer.sanitize(message)

logger.debug(message)
```

## Integration Examples

### FastAPI Error Handler

Sanitize errors before returning to clients:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from amplihack.proxy.security import TokenSanitizer

app = FastAPI()
sanitizer = TokenSanitizer()

@app.exception_handler(Exception)
async def sanitize_errors(request: Request, exc: Exception):
    error_detail = str(exc)
    safe_detail = sanitizer.sanitize(error_detail)

    return JSONResponse(
        status_code=500,
        content={"detail": safe_detail}
    )
```

### Logging Wrapper

Create a logging wrapper that auto-sanitizes:

```python
import logging
from amplihack.proxy.security import TokenSanitizer

class SanitizingLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.sanitizer = TokenSanitizer()

    def debug(self, msg: str, *args, **kwargs):
        safe_msg = self.sanitizer.sanitize(msg)
        self.logger.debug(safe_msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        safe_msg = self.sanitizer.sanitize(msg)
        self.logger.error(safe_msg, *args, **kwargs)

# Usage
logger = SanitizingLogger(__name__)
logger.debug(f"Token: {github_token}")  # Automatically sanitized
```

### Request/Response Interceptor

Sanitize all HTTP traffic logs:

```python
from amplihack.proxy.security import TokenSanitizer
import httpx

sanitizer = TokenSanitizer()

async def log_request(request: httpx.Request):
    # Sanitize headers before logging
    safe_headers = sanitizer.sanitize(dict(request.headers))
    print(f"Request headers: {safe_headers}")

async def log_response(response: httpx.Response):
    # Sanitize response body
    safe_body = sanitizer.sanitize(response.text)
    print(f"Response: {safe_body}")
```

## Performance

TokenSanitizer is optimized for production use:

- **Simple strings**: < 1ms per sanitization
- **Small dicts**: < 1ms per sanitization
- **1000 strings**: < 1 second total
- **Compiled regex**: Patterns compiled once at initialization

### Performance Tips

1. **Reuse instances**: Create one TokenSanitizer and reuse it
   ```python
   # Good - reuse instance
   sanitizer = TokenSanitizer()
   for log in logs:
       sanitizer.sanitize(log)

   # Bad - creates new instance each time
   for log in logs:
       TokenSanitizer().sanitize(log)
   ```

2. **Check before sanitizing**: Use `contains_token()` to skip clean data
   ```python
   if sanitizer.contains_token(data):
       data = sanitizer.sanitize(data)
   ```

3. **Batch processing**: Sanitize in batches for large datasets
   ```python
   results = []
   for item in large_dataset:
       results.append(sanitizer.sanitize(item))
   ```

## Troubleshooting

### False Positives

If safe text is being redacted, check pattern lengths:

**Problem**: Short strings like `"sk-short"` shouldn't match
**Solution**: Patterns require 6+ characters after prefix

```python
# These are NOT detected as tokens (too short)
safe_texts = [
    "gho_",      # Prefix only
    "sk-",       # Prefix only
    "sk-short",  # Too short (< 6 chars after prefix)
]
```

### False Negatives

If real tokens aren't detected, verify token format:

**Problem**: Token not being redacted
**Solution**: Check token format matches known patterns

```python
# Supported GitHub token prefixes
valid_prefixes = ["gho_", "ghp_", "ghs_", "ghu_", "ghr_"]

# Supported OpenAI key formats
valid_openai = ["sk-", "sk-proj-"]

# Supported Anthropic format
valid_anthropic = ["sk-ant-"]
```

### Performance Issues

If sanitization is slow:

1. **Profile token density**: Are most strings clean?
   ```python
   # Check before sanitizing
   if sanitizer.contains_token(text):
       text = sanitizer.sanitize(text)
   ```

2. **Reduce nested depth**: Very deep nesting (10+ levels) impacts performance
   ```python
   # Consider flattening deeply nested structures
   flat_data = flatten_dict(nested_data)
   sanitized = sanitizer.sanitize(flat_data)
   ```

3. **Batch processing**: Process in chunks for huge datasets
   ```python
   CHUNK_SIZE = 1000
   for i in range(0, len(items), CHUNK_SIZE):
       chunk = items[i:i+CHUNK_SIZE]
       sanitized_chunk = [sanitizer.sanitize(item) for item in chunk]
   ```

## Best Practices

1. **Sanitize at boundaries**: Sanitize data when it crosses trust boundaries (logging, errors, API responses)

2. **Don't sanitize business logic**: Only sanitize for output/logging, not internal processing

3. **Use in exception handlers**: Always sanitize exceptions before displaying

4. **Test with real tokens**: Use actual token formats in tests (with pragma comments)

5. **Check before expensive operations**: Use `contains_token()` before deep sanitization

## Related Documentation

- [Security API Reference](./SECURITY_API_REFERENCE.md) - Complete API documentation
- [Security Testing Guide](./SECURITY_TESTING_GUIDE.md) - How to test security features
- [Security README](./README.md) - Security overview

---

**Remember**: TokenSanitizer protects against accidental token exposure. It's not a replacement for proper secret management, secure storage, or encryption.
