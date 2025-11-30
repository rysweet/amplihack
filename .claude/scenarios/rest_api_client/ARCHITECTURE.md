# REST API Client Architecture

This document describes the internal modular architecture of the REST API Client, following the amplihack "brick philosophy" for AI-regeneratable components.

## Module Architecture

The REST API Client is built as a collection of self-contained "bricks" - modules that can be independently regenerated from their specifications while maintaining stable interfaces.

### Module Structure

```
rest-api-client/
├── __init__.py         # Public API exports via __all__
├── client.py           # APIClient implementation (main brick)
├── retry.py            # Retry logic module (brick)
├── rate_limiter.py     # Rate limiting module (brick)
├── exceptions.py       # Exception hierarchy (brick)
├── models.py           # Request/Response dataclasses (brick)
├── config.py           # Configuration classes (brick)
├── auth.py             # Authentication handlers (brick)
├── logging_utils.py    # Structured logging utilities (brick)
├── session.py          # Session management (brick)
└── testing/            # Testing utilities (brick)
    ├── __init__.py     # Test utilities exports
    ├── mock_server.py  # Mock server implementation
    └── fixtures.py     # Test fixtures
```

## The Brick Philosophy

Each module follows the brick philosophy from amplihack:

### What is a Brick?

- **Self-contained**: Each module has ONE clear responsibility
- **Regeneratable**: Can be rebuilt from its specification without breaking connections
- **Isolated**: All code, tests, and fixtures inside the module's boundary
- **Stable Interface**: Public API defined via `__all__` acts as "studs" for connections

### Module Independence

Each module can be regenerated independently because:

1. **Clear Contracts**: Each module defines its public interface through `__all__`
2. **Single Responsibility**: Each brick handles one aspect of functionality
3. **Minimal Dependencies**: Modules depend only on stable interfaces
4. **Standard Patterns**: Consistent structure across all modules

## Core Modules

### client.py - Main API Client Brick

**Responsibility**: Orchestrates HTTP requests using other bricks

**Public Interface (Studs)**:

```python
__all__ = ["APIClient"]
```

**Dependencies**:

- Uses `retry.py` for retry logic
- Uses `rate_limiter.py` for rate limiting
- Uses `exceptions.py` for error handling
- Uses `models.py` for Request/Response types
- Uses `config.py` for configuration

**Regeneration Contract**:

- Must provide GET, POST, PUT, PATCH, DELETE methods
- Must integrate retry and rate limiting
- Must return Response objects
- Must handle all exception types

### retry.py - Retry Logic Brick

**Responsibility**: Implements exponential backoff retry strategies

**Public Interface (Studs)**:

```python
__all__ = ["RetryHandler", "RetryConfig", "should_retry"]
```

**Dependencies**:

- Uses `exceptions.py` for specific error types
- Uses `models.py` for Response type

**Regeneration Contract**:

- Must implement exponential backoff with jitter
- Must respect retry_on_status codes
- Must handle retry_on_exceptions
- Must calculate proper delays

### rate_limiter.py - Rate Limiting Brick

**Responsibility**: Enforces rate limits and respects API throttling

**Public Interface (Studs)**:

```python
__all__ = ["RateLimiter", "RateLimitConfig", "RateLimitInfo"]
```

**Dependencies**:

- Uses `models.py` for Response type

**Regeneration Contract**:

- Must track requests per second/minute/hour
- Must respect Retry-After headers
- Must implement token bucket algorithm
- Must provide wait time calculations

### exceptions.py - Exception Hierarchy Brick

**Responsibility**: Defines all exception types for error handling

**Public Interface (Studs)**:

```python
__all__ = [
    "APIError",
    "NetworkError",
    "TimeoutError",
    "AuthenticationError",
    "RateLimitError",
    "ClientError",
    "ServerError",
    # ... all exception classes
]
```

**Dependencies**: None (foundation brick)

**Regeneration Contract**:

- Must maintain exception hierarchy
- Must include status_code, message, response attributes
- Must be compatible with Python's exception system

### models.py - Data Models Brick

**Responsibility**: Defines Request and Response dataclasses

**Public Interface (Studs)**:

```python
__all__ = ["Request", "Response"]
```

**Dependencies**: None (foundation brick)

**Regeneration Contract**:

- Request must have: method, url, headers, params, body, timeout
- Response must have: status_code, headers, data, elapsed_time
- Must be serializable/deserializable

### config.py - Configuration Brick

**Responsibility**: Configuration dataclasses for all modules

**Public Interface (Studs)**:

```python
__all__ = ["RetryConfig", "RateLimitConfig", "ClientConfig"]
```

**Dependencies**: None (foundation brick)

**Regeneration Contract**:

- Must provide sensible defaults
- Must validate configuration values
- Must be immutable after creation

### auth.py - Authentication Brick

**Responsibility**: Handles various authentication methods

**Public Interface (Studs)**:

```python
__all__ = [
    "BasicAuth",
    "BearerAuth",
    "APIKeyAuth",
    "RequestSigner"
]
```

**Dependencies**:

- Uses `models.py` for Request type

**Regeneration Contract**:

- Must add appropriate headers to requests
- Must support basic, bearer, API key auth
- Must provide request signing capability

### logging_utils.py - Logging Brick

**Responsibility**: Structured logging with sanitization

**Public Interface (Studs)**:

```python
__all__ = [
    "get_logger",
    "sanitize_headers",
    "sanitize_params",
    "log_request",
    "log_response"
]
```

**Dependencies**:

- Uses `models.py` for Request/Response types

**Regeneration Contract**:

- Must sanitize sensitive data
- Must provide correlation IDs
- Must use structured logging format

### session.py - Session Management Brick

**Responsibility**: Connection pooling and session management

**Public Interface (Studs)**:

```python
__all__ = ["SessionClient", "SessionPool"]
```

**Dependencies**:

- Extends `client.py` APIClient
- Uses connection pooling libraries

**Regeneration Contract**:

- Must maintain connection pools
- Must be thread-safe
- Must support context manager protocol

### testing/ - Testing Utilities Brick

**Responsibility**: Mock servers and test fixtures

**Public Interface (Studs)**:

```python
__all__ = [
    "MockServer",
    "create_mock_response",
    "create_mock_request"
]
```

**Dependencies**:

- Uses `models.py` for Request/Response types

**Regeneration Contract**:

- Must provide HTTP mock server
- Must track requests
- Must support response sequences

## Module Regeneration Guide

To regenerate any module:

1. **Read the specification** in this document
2. **Preserve the public interface** defined in `__all__`
3. **Maintain the contract** as specified
4. **Test against the interface** not implementation
5. **Update only the implementation** inside the module

Example regeneration command:

```bash
# To regenerate the retry module while preserving interfaces
python -m amplihack.regenerate rest-api-client/retry.py \
  --preserve-interface \
  --spec "Implement exponential backoff with jitter"
```

## Testing Strategy

Each brick has its own tests that verify:

1. **Contract Compliance**: Public interface works as specified
2. **Boundary Testing**: Module boundaries are respected
3. **Integration Points**: Connections to other bricks work
4. **Regeneration Safety**: Tests pass after regeneration

### Test Structure

```
tests/
├── test_client.py      # Tests for client.py brick
├── test_retry.py       # Tests for retry.py brick
├── test_rate_limit.py  # Tests for rate_limiter.py brick
├── test_exceptions.py  # Tests for exceptions.py brick
├── test_models.py      # Tests for models.py brick
├── test_config.py      # Tests for config.py brick
├── test_auth.py        # Tests for auth.py brick
├── test_logging.py     # Tests for logging_utils.py brick
├── test_session.py     # Tests for session.py brick
└── test_integration.py # Cross-brick integration tests
```

## Design Principles

### Ruthless Simplicity

- Each brick does ONE thing well
- No premature abstractions
- Clear over clever code

### Explicit Interfaces

- All public APIs defined in `__all__`
- Type hints for all public methods
- Comprehensive docstrings

### Fail-Safe Regeneration

- Tests verify contracts, not implementations
- Dependencies only on stable interfaces
- Backward compatibility maintained

## Dependencies

### Internal Dependencies

The dependency graph between bricks:

```
client.py
├── retry.py
├── rate_limiter.py
├── exceptions.py
├── models.py
├── config.py
├── auth.py
├── logging_utils.py
└── session.py

session.py
└── client.py (extends)

retry.py
├── exceptions.py
└── models.py

rate_limiter.py
└── models.py

auth.py
└── models.py

logging_utils.py
└── models.py

testing/
└── models.py
```

### External Dependencies

Minimal external dependencies:

- `requests` or `httpx` for HTTP (abstracted)
- `dataclasses` (Python 3.7+ stdlib)
- `typing` for type hints (stdlib)
- `logging` for structured logs (stdlib)

## Future Extensibility

New bricks can be added without modifying existing ones:

- **caching.py**: Response caching brick
- **metrics.py**: Performance metrics brick
- **tracing.py**: Distributed tracing brick
- **async_client.py**: Async/await variant brick

Each new brick follows the same pattern:

1. Single responsibility
2. Public interface via `__all__`
3. Stable contracts
4. Independent testing

## Conclusion

This architecture ensures that:

1. **Any module can be regenerated** without breaking the system
2. **AI can understand and modify** individual bricks safely
3. **Testing validates contracts** not implementations
4. **New features are additive** not modifying

The brick philosophy enables both human and AI developers to work with confidence, knowing that module boundaries protect system integrity while allowing innovation within each brick.
