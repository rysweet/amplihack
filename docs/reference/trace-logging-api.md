# Trace Logging API Reference

**Complete technical reference for native binary trace logging architecture, modules, and APIs**

## Architecture Overview

Native binary trace logging uses a modular architecture with four main components:

```
┌─────────────────────────────────────────────────────────┐
│                    amplihack Session                     │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              LiteLLM Callback Manager                    │
│  • litellm.success_callback = trace_logger.log_success  │
│  • litellm.failure_callback = trace_logger.log_failure  │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    TraceLogger                           │
│  • Checks AMPLIHACK_TRACE_LOGGING                       │
│  • Creates session-scoped JSONL files                   │
│  • Manages file lifecycle                               │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  TokenSanitizer                          │
│  • Removes API keys and secrets                         │
│  • Redacts sensitive headers                            │
│  • Preserves structure for debugging                    │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              JSONL Trace File Writer                     │
│  .claude/runtime/amplihack-traces/                      │
│    trace_YYYYMMDD_HHMMSS_SESSION.jsonl                  │
└─────────────────────────────────────────────────────────┘
```

## Module Reference

### TraceLogger

**Location**: `src/trace/trace_logger.py`

**Purpose**: Main trace logging coordinator.

#### Class: `TraceLogger`

```python
class TraceLogger:
    """
    Session-scoped trace logger for Claude API calls.

    Automatically creates JSONL trace files when AMPLIHACK_TRACE_LOGGING=true.
    Uses LiteLLM callbacks to capture request/response pairs.
    """

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize trace logger.

        Args:
            session_id: Unique session identifier (auto-generated if None)
        """
        pass

    def is_enabled(self) -> bool:
        """
        Check if trace logging is enabled.

        Returns:
            True if AMPLIHACK_TRACE_LOGGING environment variable is set to 'true'

        Example:
            logger = TraceLogger()
            if logger.is_enabled():
                print("Trace logging active")
            # Output: Trace logging active
        """
        pass

    def log_request(self, request: Dict[str, Any]) -> None:
        """
        Log Claude API request.

        Args:
            request: API request dictionary containing model, messages, etc.

        Example:
            request = {
                "model": "claude-sonnet-4-5-20250929",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 1024
            }
            logger.log_request(request)
            # Writes sanitized request to JSONL file
        """
        pass

    def log_response(self, response: Dict[str, Any]) -> None:
        """
        Log Claude API response.

        Args:
            response: API response dictionary containing content, usage, etc.

        Example:
            response = {
                "id": "msg_abc123",
                "content": [{"type": "text", "text": "Hello! How can I help?"}],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 8,
                    "total_tokens": 20
                }
            }
            logger.log_response(response)
            # Writes sanitized response to JSONL file
        """
        pass

    def log_error(self, error: Exception, context: Optional[Dict] = None) -> None:
        """
        Log API error.

        Args:
            error: Exception that occurred
            context: Optional context dictionary

        Example:
            try:
                response = call_claude_api(request)
            except RateLimitError as e:
                logger.log_error(e, {"request_id": "req_123"})
            # Writes error entry to JSONL file
        """
        pass

    def close(self) -> None:
        """
        Close trace logger and flush file.

        Example:
            logger = TraceLogger()
            # ... logging operations ...
            logger.close()
            # File handle closed, all data flushed
        """
        pass

    @property
    def trace_file_path(self) -> Optional[Path]:
        """
        Get current trace file path.

        Returns:
            Path to trace file, or None if logging disabled

        Example:
            logger = TraceLogger()
            print(logger.trace_file_path)
            # Output: .claude/runtime/amplihack-traces/trace_20260122_143022_a3f9d8.jsonl
        """
        pass
```

#### Configuration

```python
# Environment variables
AMPLIHACK_TRACE_LOGGING = os.getenv("AMPLIHACK_TRACE_LOGGING", "false")
AMPLIHACK_TRACE_DIR = os.getenv(
    "AMPLIHACK_TRACE_DIR",
    ".claude/runtime/amplihack-traces"
)
AMPLIHACK_TRACE_RETENTION_DAYS = int(
    os.getenv("AMPLIHACK_TRACE_RETENTION_DAYS", "30")
)

# File naming
TRACE_FILE_PATTERN = "trace_{date}_{time}_{session}.jsonl"
# Example: trace_20260122_143022_a3f9d8.jsonl

# Date format: YYYYMMDD
# Time format: HHMMSS
# Session: 6-character hex ID
```

---

### TokenSanitizer

**Location**: `src/trace/token_sanitizer.py`

**Purpose**: Remove sensitive data from trace logs.

#### Class: `TokenSanitizer`

```python
class TokenSanitizer:
    """
    Sanitizes sensitive tokens and credentials from trace data.

    Removes API keys, bearer tokens, and other sensitive information
    while preserving structure for debugging.
    """

    REDACTED = "[REDACTED]"

    # Patterns to redact
    API_KEY_PATTERNS = [
        r'sk-ant-api\d{2}-[\w-]+',  # Anthropic API keys
        r'sk-proj-[\w-]+',           # OpenAI project keys
        r'sk-[\w-]+',                # Generic API keys
    ]

    HEADER_KEYS = [
        'x-api-key',
        'authorization',
        'x-auth-token',
        'cookie',
    ]

    def sanitize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize dictionary recursively.

        Args:
            data: Input dictionary to sanitize

        Returns:
            Sanitized copy of data

        Example:
            sanitizer = TokenSanitizer()

            data = {
                "headers": {"x-api-key": "sk-ant-api03-abc123..."},
                "body": {"prompt": "Hello"}
            }

            sanitized = sanitizer.sanitize(data)
            print(sanitized)
            # Output: {'headers': {'x-api-key': '[REDACTED]'}, 'body': {'prompt': 'Hello'}}
        """
        pass

    def sanitize_string(self, text: str) -> str:
        """
        Sanitize string by replacing sensitive patterns.

        Args:
            text: Input string

        Returns:
            Sanitized string

        Example:
            sanitizer = TokenSanitizer()

            text = "API key: sk-ant-api03-abc123def456"
            sanitized = sanitizer.sanitize_string(text)
            print(sanitized)
            # Output: API key: [REDACTED]
        """
        pass

    def is_sensitive_key(self, key: str) -> bool:
        """
        Check if dictionary key contains sensitive data.

        Args:
            key: Dictionary key to check

        Returns:
            True if key is sensitive

        Example:
            sanitizer = TokenSanitizer()

            print(sanitizer.is_sensitive_key("x-api-key"))
            # Output: True

            print(sanitizer.is_sensitive_key("content-type"))
            # Output: False
        """
        pass
```

#### Sanitization Rules

```python
# Headers sanitized
SANITIZED_HEADERS = [
    'x-api-key',
    'authorization',
    'x-auth-token',
    'cookie',
    'set-cookie',
]

# Patterns sanitized
SANITIZED_PATTERNS = [
    r'sk-ant-api\d{2}-[\w-]+',      # Anthropic: sk-ant-api03-...
    r'sk-proj-[\w-]+',               # OpenAI: sk-proj-...
    r'sk-[\w-]+',                    # Generic: sk-...
    r'Bearer\s+[\w\-\.]+',           # Bearer tokens
    r'Basic\s+[\w\-\.]+',            # Basic auth
    r'[A-Za-z0-9+/]{40,}={0,2}',    # Base64 tokens (40+ chars)
]

# Environment variables sanitized
SANITIZED_ENV_VARS = [
    'ANTHROPIC_API_KEY',
    'OPENAI_API_KEY',
    'CLAUDE_API_KEY',
    'API_KEY',
    'SECRET_KEY',
    'PASSWORD',
    'TOKEN',
]
```

---

### LiteLLM Integration

**Location**: `src/trace/litellm_callbacks.py`

**Purpose**: Hook into LiteLLM for automatic trace logging.

#### Functions

```python
def setup_trace_callbacks(logger: TraceLogger) -> None:
    """
    Configure LiteLLM to use trace logger.

    Args:
        logger: TraceLogger instance

    Example:
        from trace.trace_logger import TraceLogger
        from trace.litellm_callbacks import setup_trace_callbacks

        logger = TraceLogger()
        setup_trace_callbacks(logger)

        # Now all LiteLLM calls are automatically traced
        import litellm
        response = litellm.completion(
            model="claude-sonnet-4-5-20250929",
            messages=[{"role": "user", "content": "Hello"}]
        )
        # Request and response automatically logged
    """
    import litellm

    def on_success(response, **kwargs):
        if logger.is_enabled():
            logger.log_response(response)

    def on_failure(exception, **kwargs):
        if logger.is_enabled():
            logger.log_error(exception, kwargs)

    litellm.success_callback = [on_success]
    litellm.failure_callback = [on_failure]
```

---

### File Writer

**Location**: `src/trace/file_writer.py`

**Purpose**: Atomic JSONL file operations.

#### Class: `JSONLWriter`

```python
class JSONLWriter:
    """
    Atomic JSONL file writer with automatic directory creation.

    Thread-safe writes with file locking.
    """

    def __init__(self, file_path: Path):
        """
        Initialize JSONL writer.

        Args:
            file_path: Path to JSONL file

        Example:
            from pathlib import Path
            from trace.file_writer import JSONLWriter

            writer = JSONLWriter(Path(".claude/runtime/amplihack-traces/trace.jsonl"))
        """
        pass

    def write(self, data: Dict[str, Any]) -> None:
        """
        Write dictionary as JSONL line.

        Args:
            data: Dictionary to write

        Example:
            writer = JSONLWriter(Path("trace.jsonl"))

            entry = {
                "timestamp": "2026-01-22T14:30:22.451Z",
                "event": "request",
                "data": {"model": "claude-sonnet-4-5-20250929"}
            }

            writer.write(entry)
            # Appends JSON line to file
        """
        pass

    def close(self) -> None:
        """
        Close file handle and flush.

        Example:
            writer = JSONLWriter(Path("trace.jsonl"))
            writer.write({"event": "test"})
            writer.close()
            # File handle closed, data flushed
        """
        pass
```

---

## Trace Entry Schema

### Request Entry

```json
{
  "timestamp": "2026-01-22T14:30:22.451Z",
  "session_id": "a3f9d8",
  "event": "request",
  "request": {
    "model": "claude-sonnet-4-5-20250929",
    "messages": [
      {
        "role": "user",
        "content": "Hello, Claude!"
      }
    ],
    "max_tokens": 1024,
    "temperature": 1.0,
    "system": "You are a helpful assistant."
  }
}
```

### Response Entry

```json
{
  "timestamp": "2026-01-22T14:30:23.102Z",
  "session_id": "a3f9d8",
  "event": "response",
  "response": {
    "id": "msg_abc123def456",
    "type": "message",
    "role": "assistant",
    "content": [
      {
        "type": "text",
        "text": "Hello! How can I help you today?"
      }
    ],
    "model": "claude-sonnet-4-5-20250929",
    "stop_reason": "end_turn",
    "usage": {
      "prompt_tokens": 12,
      "completion_tokens": 8,
      "total_tokens": 20
    }
  }
}
```

### Error Entry

```json
{
  "timestamp": "2026-01-22T14:30:24.789Z",
  "session_id": "a3f9d8",
  "event": "error",
  "error": {
    "type": "rate_limit_error",
    "message": "Rate limit exceeded. Please retry after 30 seconds.",
    "code": 429,
    "retry_after": 30
  },
  "context": {
    "request_id": "req_abc123",
    "model": "claude-sonnet-4-5-20250929"
  }
}
```

---

## Performance Characteristics

### Overhead Measurements

```python
# Disabled (AMPLIHACK_TRACE_LOGGING=false)
def measure_disabled_overhead():
    """
    Measure overhead when trace logging is disabled.

    Returns:
        ~0.05ms per API call (environment variable check only)
    """
    pass

# Enabled (AMPLIHACK_TRACE_LOGGING=true)
def measure_enabled_overhead():
    """
    Measure overhead when trace logging is enabled.

    Returns:
        ~8-10ms per API call:
          - 2ms: Sanitization
          - 3ms: JSON serialization
          - 4ms: File I/O (buffered)
    """
    pass
```

### Optimization Techniques

```python
# 1. Lazy initialization
class TraceLogger:
    def __init__(self):
        self._file_writer = None  # Only created if enabled

    @property
    def file_writer(self):
        if self._file_writer is None and self.is_enabled():
            self._file_writer = JSONLWriter(self.trace_file_path)
        return self._file_writer

# 2. Buffered writes
class JSONLWriter:
    def __init__(self, file_path):
        self.file = open(file_path, 'a', buffering=8192)  # 8KB buffer

# 3. Early exit on disabled
def log_request(self, request):
    if not self.is_enabled():
        return  # <0.1ms exit

    # ... logging logic ...
```

---

## Error Handling

### File System Errors

```python
class TraceLogger:
    def log_request(self, request):
        try:
            self._write_entry(request)
        except OSError as e:
            # Disk full, permission denied, etc.
            logging.warning(f"Trace logging failed: {e}")
            # Continue execution - trace failure should not break system

        except Exception as e:
            # Unexpected error
            logging.error(f"Unexpected trace error: {e}", exc_info=True)
            # Continue execution
```

### Sanitization Errors

```python
class TokenSanitizer:
    def sanitize(self, data):
        try:
            return self._recursive_sanitize(data)
        except Exception as e:
            logging.warning(f"Sanitization failed: {e}")
            # Return redacted placeholder instead of failing
            return {"error": "[SANITIZATION_FAILED]"}
```

---

## Testing

### Unit Tests

```python
# tests/trace/test_trace_logger.py

def test_trace_logger_disabled():
    """Verify zero overhead when disabled."""
    os.environ["AMPLIHACK_TRACE_LOGGING"] = "false"
    logger = TraceLogger()

    assert not logger.is_enabled()
    assert logger.trace_file_path is None

    # Should not create files
    logger.log_request({"model": "claude"})
    assert not Path(".claude/runtime/amplihack-traces").exists()


def test_trace_logger_enabled():
    """Verify logging when enabled."""
    os.environ["AMPLIHACK_TRACE_LOGGING"] = "true"
    logger = TraceLogger(session_id="test123")

    assert logger.is_enabled()
    assert logger.trace_file_path is not None

    # Should create trace file
    logger.log_request({"model": "claude"})

    assert logger.trace_file_path.exists()
    lines = logger.trace_file_path.read_text().strip().split("\n")
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["event"] == "request"
    assert entry["session_id"] == "test123"


def test_token_sanitizer():
    """Verify sensitive data removal."""
    sanitizer = TokenSanitizer()

    data = {
        "headers": {
            "x-api-key": "sk-ant-api03-abc123",
            "content-type": "application/json"
        }
    }

    sanitized = sanitizer.sanitize(data)

    assert sanitized["headers"]["x-api-key"] == "[REDACTED]"
    assert sanitized["headers"]["content-type"] == "application/json"
```

### Integration Tests

```python
# tests/integration/test_trace_integration.py

def test_end_to_end_trace_logging():
    """Test complete trace logging flow."""
    os.environ["AMPLIHACK_TRACE_LOGGING"] = "true"

    # Initialize components
    logger = TraceLogger()
    setup_trace_callbacks(logger)

    # Make API call
    response = litellm.completion(
        model="claude-sonnet-4-5-20250929",
        messages=[{"role": "user", "content": "Test"}]
    )

    # Verify trace file
    assert logger.trace_file_path.exists()

    entries = [
        json.loads(line)
        for line in logger.trace_file_path.read_text().strip().split("\n")
    ]

    # Should have request and response
    assert len(entries) >= 2
    assert entries[0]["event"] == "request"
    assert entries[1]["event"] == "response"

    # Verify sanitization
    request_entry = entries[0]
    assert "x-api-key" not in request_entry.get("request", {}).get("headers", {})

    logger.close()
```

---

## Extension Points

### Custom Sanitizers

```python
class CustomSanitizer(TokenSanitizer):
    """Add custom sanitization rules."""

    def sanitize(self, data):
        # Call parent sanitization
        sanitized = super().sanitize(data)

        # Add custom rules
        if "email" in sanitized:
            sanitized["email"] = self._redact_email(sanitized["email"])

        return sanitized

    def _redact_email(self, email: str) -> str:
        """Redact email addresses."""
        if "@" in email:
            local, domain = email.split("@")
            return f"{local[0]}***@{domain}"
        return email
```

### Custom Trace Formats

```python
class CSVTraceWriter(JSONLWriter):
    """Write traces in CSV format instead of JSONL."""

    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self._write_header()

    def _write_header(self):
        """Write CSV header."""
        self.file.write("timestamp,session_id,event,model,tokens\n")

    def write(self, data: Dict[str, Any]):
        """Write as CSV row."""
        row = f"{data['timestamp']},{data['session_id']},{data['event']},"
        row += f"{data.get('request', {}).get('model', 'N/A')},"
        row += f"{data.get('response', {}).get('usage', {}).get('total_tokens', 0)}\n"
        self.file.write(row)
```

---

## Security Considerations

### File Permissions

```python
# Trace files created with owner-only permissions
def create_trace_file(path: Path):
    """Create trace file with restricted permissions."""
    # Touch file
    path.touch()

    # Set permissions: rw------- (600)
    os.chmod(path, 0o600)

    return path
```

### API Key Redaction

```python
# Multiple layers of protection
class TokenSanitizer:
    # 1. Pattern matching
    API_KEY_PATTERNS = [r'sk-ant-api\d{2}-[\w-]+', ...]

    # 2. Header filtering
    SENSITIVE_HEADERS = ['x-api-key', 'authorization', ...]

    # 3. Environment variable filtering
    SENSITIVE_ENV_VARS = ['ANTHROPIC_API_KEY', ...]

    # All applied recursively to nested structures
```

---

## Next Steps

- [Feature Overview: Trace Logging](../features/trace-logging.md) - High-level feature description
- [How-To: Trace Logging](../howto/trace-logging.md) - Practical recipes
- [Troubleshooting: Trace Logging](../troubleshooting/trace-logging.md) - Fix common issues
- [Migration Guide: claude-trace to Native](../migration/claude-trace-to-native.md) - Upgrade path
