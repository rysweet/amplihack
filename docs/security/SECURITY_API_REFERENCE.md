# Security API Reference

> [Security](./README.md) > API Reference

Complete reference for `amplihack.proxy.security` module.

## Contents

- [TokenSanitizer Class](#tokensanitizer-class)
- [Token Patterns](#token-patterns)
- [Performance Characteristics](#performance-characteristics)
- [Thread Safety](#thread-safety)

## TokenSanitizer Class

**Module**: `amplihack.proxy.security`

```python
from amplihack.proxy.security import TokenSanitizer

sanitizer = TokenSanitizer()
```

### Overview

TokenSanitizer detects and redacts sensitive tokens from strings and data structures. Designed for production use with < 1ms performance for typical operations.

**Philosophy**:

- Single responsibility: Token detection and sanitization
- Zero-BS: Fully functional with no stubs
- Performance-first: Compiled regex, minimal overhead

### Constructor

```python
TokenSanitizer()
```

Initializes TokenSanitizer with compiled regex patterns for all supported token types.

**Arguments**: None

**Returns**: TokenSanitizer instance

**Example**:

```python
from amplihack.proxy.security import TokenSanitizer

sanitizer = TokenSanitizer()
```

**Thread Safety**: Yes - patterns are immutable after initialization

**Performance**: O(1) - patterns compiled once

---

### contains_token

```python
sanitizer.contains_token(text: str) -> bool
```

Check if text contains any sensitive tokens.

**Arguments**:

- `text` (str): Text to check for tokens

**Returns**: `bool`

- `True` if tokens detected
- `False` otherwise

**Raises**: None

**Example**:

```python
sanitizer = TokenSanitizer()

# Check before expensive sanitization
if sanitizer.contains_token(log_message):
    log_message = sanitizer.sanitize(log_message)

print(sanitizer.contains_token("gho_abc123xyz"))  # True
print(sanitizer.contains_token("no tokens here"))  # False
```

**Performance**: O(n) where n is text length

- Average: < 0.1ms for 1KB text
- Worst case: < 0.5ms for 10KB text

**Thread Safety**: Yes - read-only operation

---

### sanitize

```python
sanitizer.sanitize(data: Any) -> Any
```

Sanitize tokens from data structure. Recursively processes strings, dicts, and lists. Preserves non-sensitive data and structure.

**Arguments**:

- `data` (Any): Data to sanitize (str, dict, list, or other types)

**Returns**: `Any`

- Sanitized copy with tokens redacted
- Same type as input
- Non-token data preserved

**Raises**: None

**Examples**:

**String sanitization**:

```python
sanitizer = TokenSanitizer()

result = sanitizer.sanitize("Token: gho_abc123xyz")
print(result)
# Output: "Token: [REDACTED-GITHUB-TOKEN]"
```

**Dictionary sanitization**:

```python
data = {
    "github_token": "gho_1234567890",
    "openai_key": "sk-proj-abc123",
    "safe_field": "public data"
}

result = sanitizer.sanitize(data)
print(result)
# Output: {
#     'github_token': '[REDACTED-GITHUB-TOKEN]',
#     'openai_key': '[REDACTED-OPENAI-KEY]',
#     'safe_field': 'public data'
# }
```

**List sanitization**:

```python
logs = [
    "2024-01-14 INFO Server started",
    "2024-01-14 DEBUG Token: gho_abc123",
    "2024-01-14 ERROR Auth failed"
]

sanitized_logs = sanitizer.sanitize(logs)
# Token in second entry is redacted, others preserved
```

**Nested structure sanitization**:

```python
config = {
    "auth": {
        "github": {"token": "gho_abc123"},
        "openai": {"key": "sk-xyz789"}
    },
    "server": {"port": 8000}
}

safe_config = sanitizer.sanitize(config)
# All tokens redacted, structure preserved
```

**Performance**:

- Strings: O(n) where n is string length
- Dicts: O(k\*v) where k is keys, v is average value size
- Lists: O(n\*m) where n is items, m is average item size
- Average: < 1ms for typical data structures

**Thread Safety**: Yes - creates new objects, doesn't modify input

---

## Token Patterns

TokenSanitizer uses compiled regex patterns to detect tokens. All patterns are immutable after initialization.

### Supported Token Types

#### GitHub Tokens

**Prefixes**: `gho_`, `ghp_`, `ghs_`, `ghu_`, `ghr_`

**Pattern**: `gh[opsuhr]_[A-Za-z0-9]{6,100}`

**Redaction**: `[REDACTED-GITHUB-TOKEN]`

**Examples**:

```python
# Detected
"gho_1234567890abcdefghij"  # OAuth token
"ghp_1234567890abcdefghij"  # Personal access token
"ghs_1234567890abcdefghij"  # App token
"ghu_1234567890abcdefghij"  # User token
"ghr_1234567890abcdefghij"  # Refresh token

# Not detected (too short)
"gho_"       # Prefix only
"gho_short"  # < 6 chars after prefix
```

#### OpenAI API Keys

**Prefixes**: `sk-`, `sk-proj-`

**Pattern**: `sk-(?:proj-)?[A-Za-z0-9]{6,100}`

**Redaction**: `[REDACTED-OPENAI-KEY]`

**Examples**:

```python
# Detected
"sk-1234567890abcdefghij"       # Standard key
"sk-proj-1234567890abcdefghij"  # Project key

# Not detected
"sk-"       # Prefix only
"sk-short"  # < 6 chars after prefix
```

#### Anthropic API Keys

**Prefix**: `sk-ant-`

**Pattern**: `sk-ant-[A-Za-z0-9]{6,100}`

**Redaction**: `[REDACTED-ANTHROPIC-KEY]`

**Examples**:

```python
# Detected
"sk-ant-1234567890abcdefghij"

# Not detected
"sk-ant-"       # Prefix only
"sk-ant-short"  # < 6 chars after prefix
```

#### Bearer Tokens

**Pattern**: `Bearer\s+[A-Za-z0-9_\-]{6,500}(?:\.[A-Za-z0-9_\-]+)*`

**Redaction**: `[REDACTED-BEARER-TOKEN]`

**Examples**:

```python
# Detected
"Bearer abc123xyz"
"Authorization: Bearer longtoken123"

# Not detected
"Bearer"        # No token
"Bearer short"  # < 6 chars
```

#### JWT Tokens

**Pattern**: `eyJ[A-Za-z0-9_\-]+\.eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+`

**Redaction**: `[REDACTED-JWT-TOKEN]`

**Examples**:

```python
# Detected (header.payload.signature)
"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"

# Not detected
"not.a.jwt"       # Wrong format
"eyJ.eyJ"         # Too short
```

#### Azure Keys

**Pattern**: `azure-key-[A-Za-z0-9]{6,100}`

**Redaction**: `[REDACTED-AZURE-KEY]`

**Examples**:

```python
# Detected
"azure-key-1234567890abcdefghij"

# Not detected
"azure-key-"       # Prefix only
"azure-key-short"  # < 6 chars
```

#### Azure Connection Strings

**Pattern**: `DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[^;]+;[^\s]+`

**Redaction**: `[REDACTED-AZURE-CONNECTION]`

**Examples**:

```python
# Detected
"DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=abc123==;EndpointSuffix=core.windows.net"

# Not detected
"DefaultEndpointsProtocol=https"  # Incomplete
```

### Pattern Characteristics

#### Length Limits

All patterns enforce length limits to prevent matching entire files:

- **Minimum**: 6 characters after prefix (prevents false positives)
- **Maximum**: 100-500 characters (prevents performance issues)

#### Case Sensitivity

- Token prefixes are case-sensitive (lowercase only)
- Token bodies are case-insensitive (match A-Za-z0-9)

#### Boundary Detection

Patterns match tokens even when embedded in text:

```python
# All detected
"Token: gho_abc123 End"      # Middle of string
"gho_abc123"                 # Entire string
"Bearer gho_abc123"          # With prefix
"auth=gho_abc123&next=true"  # In query string
```

## Performance Characteristics

### Time Complexity

| Operation              | Complexity | Average Time | Notes                        |
| ---------------------- | ---------- | ------------ | ---------------------------- |
| `__init__()`           | O(1)       | < 0.01ms     | Patterns compiled once       |
| `contains_token(text)` | O(n)       | < 0.1ms      | n = text length              |
| `sanitize(str)`        | O(n)       | < 1ms        | n = string length            |
| `sanitize(dict)`       | O(k\*v)    | < 1ms        | k = keys, v = avg value size |
| `sanitize(list)`       | O(n\*m)    | < 1ms        | n = items, m = avg item size |

### Space Complexity

| Operation               | Complexity | Notes                                |
| ----------------------- | ---------- | ------------------------------------ |
| TokenSanitizer instance | O(1)       | Fixed pattern storage                |
| `sanitize()`            | O(n)       | Creates new objects, input preserved |

### Benchmark Results

From `tests/proxy/test_security_sanitization.py`:

```python
# Simple string: 100 iterations
Average: 0.8ms per sanitization

# Small dict: 100 iterations
Average: 0.9ms per sanitization

# 1000 strings: Batch processing
Total: 950ms (< 1s)
Average: 0.95ms per item
```

### Performance Tips

1. **Reuse instances**: Create once, use many times
2. **Check before sanitizing**: Use `contains_token()` for clean data
3. **Avoid deep nesting**: Flatten structures when possible
4. **Batch processing**: Process in chunks for large datasets

## Thread Safety

TokenSanitizer is thread-safe for all operations:

### Safe Operations

- **Constructor**: Thread-safe - patterns immutable after init
- **contains_token()**: Thread-safe - read-only operation
- **sanitize()**: Thread-safe - creates new objects, doesn't modify input

### Shared Instance Pattern

Safe to share one instance across threads:

```python
# Module-level instance (shared)
sanitizer = TokenSanitizer()

def worker_thread(data):
    # Safe - sanitize() doesn't modify shared state
    return sanitizer.sanitize(data)

# Use in multiple threads
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=10) as executor:
    results = executor.map(worker_thread, dataset)
```

## Related Documentation

- [Token Sanitization Guide](./TOKEN_SANITIZATION_GUIDE.md) - Usage examples and patterns
- [Security Testing Guide](./SECURITY_TESTING_GUIDE.md) - How to test security features
- [Security README](./README.md) - Security overview

---

**Implementation**: See `src/amplihack/proxy/security.py` for complete source code.
