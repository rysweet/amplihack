# Proxy Security Migration Guide

> [Home](../index.md) > [Security](README.md) > Migration Guide

**Last Updated**: 2026-01-14

Guide for developers migrating existing code to use the security improvements from Issue #1922.

## Overview

This guide helps you upgrade existing proxy code to incorporate:

1. Token sanitization for log security
2. Message content filtering for API compatibility
3. Improved model routing logic
4. Secure file permissions for tokens

**Breaking Changes**: None - all improvements are backward compatible

**Estimated Migration Time**: 15-30 minutes

## Quick Migration Checklist

```markdown
- [ ] Import `sanitize_for_logging` function
- [ ] Wrap all error logging with sanitization
- [ ] Update custom validators for model routing
- [ ] Review token file operations for permissions
- [ ] Run security test suite
- [ ] Update documentation
```

## Step-by-Step Migration

### Step 1: Update Imports

Add the security utilities to your imports:

```python
# Before
import logging
from amplihack.proxy.server import app, Message

# After
import logging
from amplihack.proxy.server import app, Message, sanitize_for_logging, sanitize_message_content

logger = logging.getLogger(__name__)
```

**What changed**: Added security utility imports

**Required**: Yes (if using custom error handling)

---

### Step 2: Sanitize Error Logging

Wrap all logging statements that might contain tokens:

```python
# Before (VULNERABLE)
try:
    response = api_call(api_key=api_key)
except Exception as e:
    logger.error(f"API call failed: {e}")  # ❌ Token exposed
    raise HTTPException(status_code=500, detail=str(e))

# After (SECURE)
try:
    response = api_call(api_key=api_key)
except Exception as e:
    logger.error(f"API call failed: {sanitize_for_logging(str(e))}")  # ✅ Token redacted
    raise HTTPException(
        status_code=500,
        detail=sanitize_for_logging(str(e))
    )
```

**What changed**: All logging and error messages sanitized

**Required**: Yes (critical security fix)

**Automated Fix**: Use search-and-replace:

```bash
# Find all logger.error() calls
grep -rn "logger.error" src/ | grep -v "sanitize_for_logging"

# Replace pattern (use your editor's find-replace)
# Find: logger.error(f"(.*?){(.+?)}")
# Replace: logger.error(f"$1{sanitize_for_logging($2)}")
```

---

### Step 3: Update Custom Model Validators

If you have custom model validation logic, update to avoid routing conflicts:

```python
# Before (CONFLICTING)
@field_validator("model")
def validate_model(cls, v):
    if "sonnet" in v.lower():
        return "gpt-4o"  # ❌ Conflicts with claude-sonnet-4 routing
    return v

# After (SAFE)
@field_validator("model")
def validate_model(cls, v):
    # Remove provider prefix for matching
    clean_v = v
    if clean_v.startswith("anthropic/"):
        clean_v = clean_v[10:]
    elif clean_v.startswith(("openai/", "gemini/")):
        clean_v = clean_v[7:]

    # Apply specific mappings
    if "haiku" in clean_v.lower():
        return f"openai/{SMALL_MODEL}"
    elif "sonnet" in clean_v.lower():
        return f"openai/{BIG_MODEL}"

    # Preserve explicit model names
    return v
```

**What changed**: More precise model matching, respects provider prefixes

**Required**: Yes (if you have custom validators)

**Testing**: Run `pytest tests/proxy/test_model_routing.py` to verify

---

### Step 4: Secure Token File Operations

Update token file operations to use secure permissions:

```python
# Before (INSECURE)
def save_token(token: str, token_file: Path):
    token_file.write_text(token)  # ❌ Default permissions (0644)

# After (SECURE)
import os
from pathlib import Path

def save_token(token: str, token_file: Path):
    token_file.write_text(token)
    os.chmod(token_file, 0o600)  # ✅ Owner read/write only

    logger.info(f"Token saved securely to {token_file}")
```

**What changed**: File permissions set to 0600 (owner only)

**Required**: Yes (security hardening)

**Verification**:

```bash
# Check token file permissions
ls -l ~/.amplihack_token
# Should show: -rw------- (0600)
```

---

### Step 5: Filter Message Content

If you process Anthropic API responses, filter unsupported content types:

```python
# Before (BREAKS OpenAI API)
def convert_messages(messages):
    # Passes thinking blocks to OpenAI API
    return messages  # ❌ OpenAI doesn't support thinking blocks

# After (COMPATIBLE)
from amplihack.proxy.server import sanitize_message_content

def convert_messages(messages):
    # Filter out unsupported content types
    return sanitize_message_content(messages)  # ✅ Only supported types
```

**What changed**: Filters content types for API compatibility

**Required**: Yes (if converting between API formats)

**Use Cases**:
- Azure/OpenAI conversion
- Passthrough mode to standard Anthropic API
- Custom API integrations

---

### Step 6: Update Environment Variables

Add new configuration options to your environment:

```bash
# Before
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-proj-..."

# After - Add model routing config
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-proj-..."
export PREFERRED_PROVIDER="openai"  # NEW: openai | google | anthropic
export BIG_MODEL="gpt-4o"           # NEW: Model for Sonnet requests
export SMALL_MODEL="gpt-4o-mini"    # NEW: Model for Haiku requests
```

**What changed**: Added provider routing configuration

**Required**: No (defaults work for most users)

**When to configure**:
- Using Google Gemini as preferred provider
- Custom model mappings
- Testing specific routing scenarios

---

### Step 7: Run Security Tests

Verify your migration with the security test suite:

```bash
# Run all security tests
pytest tests/proxy/ -v -k security

# Run token sanitization tests
pytest tests/proxy/test_token_sanitization.py -v

# Run model routing tests
pytest tests/proxy/test_model_routing.py -v

# Check coverage
pytest tests/proxy/ --cov=src/amplihack/proxy --cov-report=term-missing

# E2E test (USER_PREFERENCES.md requirement)
uvx --from git+https://github.com/rysweet/amplihack@feat/issue-1922-fix-pr1920-security-tests amplihack proxy --test
```

**Expected Results**:
- All tests pass
- Coverage >= 80%
- No tokens in log output
- E2E test successful

---

## Migration Examples

### Example 1: Simple Error Handler

**Before**:
```python
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )
```

**After**:
```python
from amplihack.proxy.server import sanitize_for_logging

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error(f"Validation error: {sanitize_for_logging(str(exc))}")
    return JSONResponse(
        status_code=400,
        content={"error": sanitize_for_logging(str(exc))}
    )
```

**Changes**: 2 lines (sanitize logger and response)

---

### Example 2: Custom Authentication

**Before**:
```python
def authenticate(api_key: str) -> bool:
    try:
        validate_api_key(api_key)
        return True
    except Exception as e:
        logger.error(f"Auth failed for key {api_key}: {e}")
        return False
```

**After**:
```python
def authenticate(api_key: str) -> bool:
    try:
        validate_api_key(api_key)
        return True
    except Exception as e:
        logger.error(f"Auth failed for key {sanitize_for_logging(api_key)}: {sanitize_for_logging(str(e))}")
        return False
```

**Changes**: 1 line (sanitize both key and error)

---

### Example 3: Message Conversion

**Before**:
```python
def convert_to_openai_format(anthropic_messages):
    """Convert Anthropic messages to OpenAI format."""
    openai_messages = []
    for msg in anthropic_messages:
        openai_messages.append({
            "role": msg.role,
            "content": msg.content  # ❌ May contain thinking blocks
        })
    return openai_messages
```

**After**:
```python
from amplihack.proxy.server import sanitize_message_content

def convert_to_openai_format(anthropic_messages):
    """Convert Anthropic messages to OpenAI format."""
    # Filter unsupported content types first
    filtered_messages = sanitize_message_content(anthropic_messages)

    openai_messages = []
    for msg in filtered_messages:
        openai_messages.append({
            "role": msg.role,
            "content": msg.content  # ✅ Only supported types
        })
    return openai_messages
```

**Changes**: 2 lines (import and filter call)

---

## Rollback Instructions

If you need to rollback:

```bash
# Revert to previous version
git revert <commit-hash>

# Or checkout previous version
git checkout <previous-tag>

# Reinstall
pip install -e .
```

**When to rollback**:
- Unexpected test failures
- Performance issues (though none expected)
- Integration problems with custom code

**Note**: Rollback removes security fixes - use only temporarily

---

## Common Migration Issues

### Issue 1: Import Error

**Error**:
```
ImportError: cannot import name 'sanitize_for_logging' from 'amplihack.proxy.server'
```

**Cause**: Old version of amplihack installed

**Fix**:
```bash
pip install --upgrade amplihack
# Or for development:
pip install -e .
```

---

### Issue 2: Model Routing Changed

**Error**:
```
ValueError: Unsupported model: claude-sonnet-4
```

**Cause**: Custom validator conflict

**Fix**: Update custom validator to use new routing logic (see Step 3)

---

### Issue 3: Tests Failing

**Error**:
```
AssertionError: Expected token to be redacted
```

**Cause**: Not all logging sanitized

**Fix**: Search for all `logger.error/info/warning` calls and add sanitization

---

### Issue 4: Performance Degradation

**Error**: Slow response times after migration

**Cause**: Excessive sanitization in hot path

**Fix**: Only sanitize log output, not data processing:

```python
# BAD - Sanitizes every message
for msg in messages:
    msg.content = sanitize_for_logging(msg.content)  # ❌ Too much work

# GOOD - Only sanitize log output
logger.debug(f"Processing {len(messages)} messages")  # ✅ No sanitization needed
# ... process messages normally ...
logger.error(f"Error: {sanitize_for_logging(error)}")  # ✅ Only logs sanitized
```

---

## Verification Steps

After migration, verify security improvements:

### 1. Token Exposure Check

```bash
# Run proxy with logging
amplihack proxy --log-file proxy.log

# Check log file (should find nothing)
grep -E "sk-ant-|sk-proj-|github_pat_" proxy.log && echo "❌ TOKENS FOUND" || echo "✅ No tokens"
```

### 2. Model Routing Check

```bash
# Test Sonnet routing
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-key" \
  -d '{
    "model": "claude-sonnet-4",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Check logs - should show mapping to gpt-4o
grep "MODEL MAPPING" proxy.log
```

### 3. Content Filtering Check

```bash
# Test thinking block filtering
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-key" \
  -d '{
    "model": "claude-sonnet-4",
    "max_tokens": 1024,
    "messages": [
      {
        "role": "assistant",
        "content": [
          {"type": "thinking", "text": "Should be filtered"},
          {"type": "text", "text": "Should remain"}
        ]
      }
    ]
  }'

# Response should not contain thinking block
```

---

## Performance Impact

**Expected Performance Changes**:

| Operation | Before | After | Change |
|-----------|--------|-------|--------|
| Token sanitization | N/A | < 1ms | +1ms |
| Message filtering | N/A | 1-5ms | +1-5ms |
| Model validation | < 0.1ms | < 0.1ms | No change |
| Overall request | 100-500ms | 100-506ms | < 2% |

**Impact**: Negligible (< 2% overhead)

**Mitigation**: Security is always applied, no opt-out

---

## Getting Help

If you encounter migration issues:

1. **Check documentation**:
   - [Token Sanitization Guide](PROXY_TOKEN_SANITIZATION.md)
   - [Security API Reference](PROXY_SECURITY_API.md)
   - [Testing Guide](PROXY_SECURITY_TESTING.md)

2. **Run diagnostics**:
   ```bash
   pytest tests/proxy/ -v --tb=short
   amplihack proxy --self-test
   ```

3. **File an issue**:
   - GitHub Issues: https://github.com/rysweet/amplihack/issues
   - Include: Error message, code snippet, environment details

---

## Related Documentation

- [Token Sanitization Guide](PROXY_TOKEN_SANITIZATION.md) - How to use sanitization
- [Security API Reference](PROXY_SECURITY_API.md) - Technical specifications
- [Security Testing Guide](PROXY_SECURITY_TESTING.md) - Test your migration
- [Security Best Practices](../SECURITY_RECOMMENDATIONS.md) - General guidelines

---

**Migration Checklist**:

```markdown
- [ ] Step 1: Updated imports
- [ ] Step 2: Sanitized error logging
- [ ] Step 3: Updated custom validators
- [ ] Step 4: Secured token files
- [ ] Step 5: Filtered message content
- [ ] Step 6: Updated environment variables
- [ ] Step 7: Ran security tests
- [ ] Verified token exposure check
- [ ] Verified model routing
- [ ] Verified content filtering
- [ ] Updated team documentation
```

**Migration complete when all checks pass!**
