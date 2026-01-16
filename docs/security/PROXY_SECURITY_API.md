# Proxy Security API Reference

> [Home](../index.md) > [Security](README.md) > Security API Reference

**Last Updated**: 2026-01-14

Complete API reference for security components in the amplihack proxy module.

## Overview

This document provides technical specifications for all security-related functions, classes, and utilities in the proxy module.

## Core Security Functions

### `sanitize_for_logging(text: str) -> str`

Sanitize sensitive tokens from text before logging.

**Location**: `src/amplihack/proxy/server.py`

**Parameters**:
- `text` (str): Text potentially containing sensitive tokens

**Returns**:
- `str`: Sanitized text with tokens replaced by `***REDACTED***`

**Token Patterns Sanitized**:
- Anthropic API keys (`sk-ant-*`)
- OpenAI API keys (`sk-*`)
- Bearer tokens (`Bearer *`)
- GitHub tokens (`github_pat_*`)

**Example**:
```python
from amplihack.proxy.server import sanitize_for_logging

message = "API key: sk-ant-1234567890abcdef"
safe_message = sanitize_for_logging(message)
print(safe_message)
# Output: "API key: ***REDACTED***"
```

**Thread Safety**: Yes (pure function, no state)

**Performance**: O(n) where n = text length (~0.1-1ms for typical log messages)

---

### `sanitize_message_content(messages, allowed_types) -> list[Message]`

Filter unsupported content block types from messages.

**Location**: `src/amplihack/proxy/server.py`

**Parameters**:
- `messages` (list[Message]): List of messages to sanitize
- `allowed_types` (set[str], optional): Allowed content block types.
  Default: `{"text", "image", "tool_use", "tool_result"}`

**Returns**:
- `list[Message]`: Messages with only allowed content types

**Behavior**:
- Filters out unsupported block types (e.g., `thinking` blocks)
- Preserves string content unchanged
- Removes messages with no content after filtering
- Preserves message roles and allowed blocks

**Example**:
```python
from amplihack.proxy.server import Message, sanitize_message_content

messages = [
    Message(
        role="assistant",
        content=[
            {"type": "thinking", "text": "Internal reasoning"},
            {"type": "text", "text": "User response"}
        ]
    )
]

sanitized = sanitize_message_content(messages)
# Result: Only text block remains, thinking block removed
```

**Use Cases**:
1. **Azure/OpenAI conversion**: Remove thinking blocks unsupported by OpenAI API
2. **Passthrough mode**: Filter extended thinking for standard Anthropic API
3. **Custom filtering**: Restrict to specific content types

**Thread Safety**: Yes (pure function)

**Performance**: O(n*m) where n = messages, m = content blocks per message

---

## Model Validation

### `validate_model_field(v, info) -> str`

Pydantic validator for model name field with provider routing.

**Location**: `src/amplihack/proxy/server.py` (in `MessagesRequest` class)

**Parameters**:
- `v` (str): Model name to validate
- `info` (ValidationInfo): Pydantic validation context

**Returns**:
- `str`: Validated model name with correct provider prefix

**Validation Logic**:
1. **Extract base model name**: Remove provider prefixes (`anthropic/`, `openai/`, `gemini/`)
2. **Apply mapping rules**:
   - `haiku` → `SMALL_MODEL` (configurable)
   - `sonnet` → `BIG_MODEL` (configurable)
   - Exact model names → Preserve with correct prefix
3. **Add provider prefix**: Based on model and `PREFERRED_PROVIDER` setting
4. **Store original model**: Saved to `original_model` field

**Configuration**:
```python
# Environment variables
PREFERRED_PROVIDER = os.getenv("PREFERRED_PROVIDER", "openai")  # openai | google
BIG_MODEL = os.getenv("BIG_MODEL", "gpt-4o")
SMALL_MODEL = os.getenv("SMALL_MODEL", "gpt-4o-mini")
```

**Example**:
```python
# Input: "claude-sonnet-4"
# Output: "openai/gpt-4o" (if PREFERRED_PROVIDER=openai, BIG_MODEL=gpt-4o)

# Input: "anthropic/claude-3-haiku-20240307"
# Output: "openai/gpt-4o-mini" (if PREFERRED_PROVIDER=openai, SMALL_MODEL=gpt-4o-mini)

# Input: "gemini-1.5-pro"
# Output: "gemini/gemini-1.5-pro" (adds prefix, no mapping)
```

**Logging**:
- Debug: Model mapping decisions
- Warning: Models without prefix or mapping rules

---

## Data Models

### `Message`

Pydantic model representing a conversation message.

**Fields**:
- `role` (Literal["user", "assistant"]): Message role
- `content` (str | list[ContentBlock]): Message content

**Content Block Types**:
- `ContentBlockText`: Plain text
- `ContentBlockImage`: Image data
- `ContentBlockToolUse`: Tool invocation
- `ContentBlockToolResult`: Tool response

**Example**:
```python
from amplihack.proxy.server import Message

# String content
msg1 = Message(role="user", content="Hello")

# Structured content
msg2 = Message(
    role="assistant",
    content=[
        {"type": "text", "text": "I'll help with that"},
        {"type": "tool_use", "id": "1", "name": "search", "input": {}}
    ]
)
```

---

### `MessagesRequest`

Pydantic model for Anthropic Messages API requests.

**Fields**:
- `model` (str): Model identifier (validated and routed)
- `max_tokens` (int): Maximum tokens to generate
- `messages` (list[Message]): Conversation history
- `system` (str | list[SystemContent], optional): System prompt
- `stream` (bool, optional): Enable streaming (default: False)
- `temperature` (float, optional): Sampling temperature (default: 1.0)
- `top_p` (float, optional): Nucleus sampling parameter
- `top_k` (int, optional): Top-k sampling parameter
- `tools` (list[Tool], optional): Available tools
- `tool_choice` (dict, optional): Tool selection strategy
- `thinking` (ThinkingConfig, optional): Extended thinking configuration
- `original_model` (str, optional): Original model name before routing

**Validators**:
- `validate_model_field`: Model routing and validation

**Example**:
```python
from amplihack.proxy.server import MessagesRequest, Message

request = MessagesRequest(
    model="claude-sonnet-4",
    max_tokens=1024,
    messages=[
        Message(role="user", content="Hello")
    ]
)

# After validation:
# request.model = "openai/gpt-4o"
# request.original_model = "claude-sonnet-4"
```

---

## Constants

### Supported Models

```python
# Claude Models
CLAUDE_MODELS = {
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20240620",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
}

# OpenAI Models
OPENAI_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "o1-preview",
    "o1-mini",
}

# Gemini Models
GEMINI_MODELS = {
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash-exp",
}
```

### Provider Prefixes

```python
PROVIDER_PREFIXES = {
    "anthropic/",   # Direct Anthropic API
    "openai/",      # OpenAI API (or Azure OpenAI)
    "gemini/",      # Google Gemini API
    "github_copilot/",  # GitHub Copilot API
}
```

---

## Security Utilities

### File Permission Management

```python
def save_token_securely(token: str, token_file: Path) -> None:
    """Save token with secure file permissions (0600)."""
    token_file.write_text(token)
    os.chmod(token_file, 0o600)  # Read/write owner only
```

**Permissions**:
- `0600` = `-rw-------` (owner read/write only)
- No group access
- No world access

**Platform Support**:
- Linux/macOS: Full support
- Windows: Best-effort (ACL-based permissions)

---

## Error Handling

### Security-Related Exceptions

```python
# Token validation error
raise ValueError(f"Invalid API key format: {sanitize_for_logging(api_key)}")

# Model routing error
raise HTTPException(
    status_code=400,
    detail=f"Unsupported model: {sanitize_for_logging(model_name)}"
)

# Authentication error
raise HTTPException(
    status_code=401,
    detail="Authentication failed: Invalid or missing API key"
)
```

**Best Practices**:
- Always sanitize error messages before raising
- Use specific HTTP status codes (400, 401, 403, 500)
- Provide actionable error messages (without exposing tokens)

---

## Testing APIs

### Test Utilities

```python
def test_sanitization(text: str, expected_redactions: list[str]) -> bool:
    """Test that all sensitive patterns are redacted."""
    sanitized = sanitize_for_logging(text)
    return all(pattern not in sanitized for pattern in expected_redactions)

def test_message_filtering(messages: list[Message], expected_types: set[str]) -> bool:
    """Test that only allowed content types remain."""
    sanitized = sanitize_message_content(messages, allowed_types=expected_types)
    for msg in sanitized:
        if isinstance(msg.content, list):
            for block in msg.content:
                block_type = block.type if hasattr(block, "type") else block.get("type")
                if block_type not in expected_types:
                    return False
    return True
```

---

## Performance Characteristics

| Function | Time Complexity | Space Complexity | Typical Latency |
|----------|----------------|------------------|-----------------|
| `sanitize_for_logging` | O(n) | O(n) | < 1ms |
| `sanitize_message_content` | O(n*m) | O(n*m) | 1-5ms |
| `validate_model_field` | O(1) | O(1) | < 0.1ms |

**Where**:
- n = number of messages
- m = average content blocks per message

---

## Configuration

### Environment Variables

```bash
# Model Routing
export PREFERRED_PROVIDER="openai"  # openai | google | anthropic
export BIG_MODEL="gpt-4o"
export SMALL_MODEL="gpt-4o-mini"

# Authentication
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-proj-..."
export GOOGLE_API_KEY="AIza..."
export GITHUB_API_KEY="github_pat_..."

# Logging
export LOG_LEVEL="INFO"  # DEBUG | INFO | WARNING | ERROR
```

---

## Migration Notes

### Upgrading from Pre-Security Version

**Breaking Changes**: None (sanitization is additive)

**Required Actions**:
1. Update imports if using custom logging:
   ```python
   from amplihack.proxy.server import sanitize_for_logging
   ```

2. Wrap existing error logging:
   ```python
   # Before
   logger.error(f"Error: {error_message}")

   # After
   logger.error(f"Error: {sanitize_for_logging(error_message)}")
   ```

3. Review custom validators for model routing conflicts

**Deprecations**: None

---

## Related Documentation

- [Token Sanitization Guide](PROXY_TOKEN_SANITIZATION.md) - Usage examples and best practices
- [Security Testing Guide](PROXY_SECURITY_TESTING.md) - Comprehensive test coverage
- [Migration Guide](PROXY_SECURITY_MIGRATION.md) - Upgrade instructions
- [Security Best Practices](../SECURITY_RECOMMENDATIONS.md) - General security guidelines

---

**API Stability**: These APIs are **stable** and follow semantic versioning. Breaking changes will be announced with major version bumps.
