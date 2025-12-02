# REST API Client

Production-ready HTTP client with built-in resilience, automatic retries, and comprehensive error handling.

## Overview

The API Client provides a robust interface for making HTTP requests with automatic retry logic, rate limit handling, and a clear exception hierarchy. It handles the complexities of API communication so you can focus on your application logic.

### Problem Statement

HTTP APIs fail in predictable ways: network timeouts, rate limits, transient server errors. Without proper handling, these failures cascade into application crashes or silent data loss.

### Solution Approach

A single `APIClient` class that wraps `urllib.request` with:

- Exponential backoff retries (max 3 attempts)
- Automatic rate limit handling (429 + Retry-After)
- Type-safe request/response dataclasses
- Clear exception hierarchy for targeted error handling

### Key Benefits

- **Minimal Dependencies**: Uses only `requests` library (industry-standard HTTP client)
- **Predictable Failure Modes**: Every error type has a specific exception
- **Automatic Recovery**: Transient failures retry transparently
- **Full Observability**: Comprehensive logging at every step

## Prerequisites

- Python 3.8+
- Network access to target API

## Installation

```bash
# No additional installation required - uses Python standard library only
```

## Usage

### Basic Usage

```python
from api_client import APIClient

# Create client with base URL
client = APIClient(base_url="https://api.example.com")

# GET request
response = client.get("/users/123")
print(response.json())

# POST request with JSON body
response = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
print(response.status_code)  # 201
```

### Advanced Usage

```python
from api_client import APIClient
from api_client.exceptions import RateLimitError, ServerError

# Configure client with custom settings
client = APIClient(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=5,
    retry_delay=2.0,
    headers={"Authorization": "Bearer token123"},
)

# Make request with error handling
try:
    response = client.put("/users/123", json={"name": "Bob"})
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ServerError as e:
    print(f"Server error {e.status_code}: {e.message}")
```

### Parameters

| Parameter     | Description                        | Default | Required |
| ------------- | ---------------------------------- | ------- | -------- |
| `base_url`    | API base URL                       | None    | Yes      |
| `api_key`     | Optional API key for auth          | None    | No       |
| `timeout`     | Request timeout seconds            | 30      | No       |
| `headers`     | Default headers for all requests   | {}      | No       |
| `max_retries` | Maximum retry attempts (0=disable) | 3       | No       |
| `retry_delay` | Initial delay between retries      | 1.0     | No       |

## Examples

### Example 1: Simple REST Operations

```python
from api_client import APIClient

client = APIClient(base_url="https://jsonplaceholder.typicode.com")

# GET - Fetch a resource
user = client.get("/users/1")
print(f"User: {user.json()['name']}")
# Output: User: Leanne Graham

# POST - Create a resource
new_post = client.post("/posts", json={
    "title": "Hello World",
    "body": "This is my first post",
    "userId": 1
})
print(f"Created post ID: {new_post.json()['id']}")
# Output: Created post ID: 101

# PUT - Update a resource
updated = client.put("/posts/1", json={"title": "Updated Title"})
print(f"Status: {updated.status_code}")
# Output: Status: 200

# DELETE - Remove a resource
deleted = client.delete("/posts/1")
print(f"Deleted: {deleted.status_code == 200}")
# Output: Deleted: True

# PATCH - Partial update
patched = client.patch("/posts/1", json={"title": "Patched"})
print(f"Patched: {patched.status_code}")
# Output: Patched: 200
```

### Example 2: Error Handling

```python
from api_client import APIClient
from api_client.exceptions import (
    APIClientError,
    ConnectionError,
    TimeoutError,
    RateLimitError,
    ServerError,
    ClientError,
)

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/protected/resource")
except ConnectionError as e:
    # Network unreachable, DNS failure, connection refused
    print(f"Connection failed: {e}")
    # Fallback to cached data or offline mode

except TimeoutError as e:
    # Request took longer than configured timeout
    print(f"Request timed out after {e.timeout}s")
    # Consider increasing timeout or simplifying request

except RateLimitError as e:
    # 429 Too Many Requests
    print(f"Rate limited. Retry after {e.retry_after}s")
    # Queue request for later or back off

except ClientError as e:
    # 4xx errors (except 429)
    print(f"Client error {e.status_code}: {e.message}")
    if e.status_code == 401:
        # Refresh auth token
        pass
    elif e.status_code == 404:
        # Resource not found
        pass

except ServerError as e:
    # 5xx errors after all retries exhausted
    print(f"Server error {e.status_code}: {e.message}")
    # Alert ops team, use fallback service

except APIClientError as e:
    # Catch-all for any API client error
    print(f"API error: {e}")
```

### Example 3: Configuration for Different Use Cases

```python
from api_client import APIClient

# High-reliability configuration for critical APIs
background_client = APIClient(
    base_url="https://analytics.example.com",
    timeout=60,              # Longer timeout for slow APIs
    max_retries=5,           # More retry attempts
    retry_delay=2.0,         # Initial delay between retries
)

# Fast-fail configuration for user-facing requests
user_facing_client = APIClient(
    base_url="https://api.example.com",
    timeout=5,               # Short timeout
    max_retries=1,           # One retry only
    retry_delay=0.5,         # Quick retry
)
```

## Configuration

### APIClient Constructor Options

| Option        | Type  | Default | Description                           |
| ------------- | ----- | ------- | ------------------------------------- |
| `base_url`    | str   | -       | Base URL for all requests (required)  |
| `api_key`     | str   | None    | Optional API key for Bearer auth      |
| `timeout`     | float | 30.0    | Request timeout in seconds            |
| `headers`     | dict  | None    | Default headers for all requests      |
| `max_retries` | int   | 3       | Maximum retry attempts (0 to disable) |
| `retry_delay` | float | 1.0     | Initial delay between retries         |

### Environment Variables

| Variable                 | Description              | Default |
| ------------------------ | ------------------------ | ------- |
| `API_CLIENT_TIMEOUT`     | Override default timeout | 30      |
| `API_CLIENT_MAX_RETRIES` | Override max retries     | 3       |
| `API_CLIENT_LOG_LEVEL`   | Logging level            | INFO    |

## API Reference

### APIClient

```python
class APIClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None: ...

    def get(self, path: str, params: dict | None = None) -> Response: ...
    def post(self, path: str, json: dict | None = None, data: bytes | None = None) -> Response: ...
    def put(self, path: str, json: dict | None = None, data: bytes | None = None) -> Response: ...
    def patch(self, path: str, json: dict | None = None) -> Response: ...
    def delete(self, path: str) -> Response: ...
```

### Response

```python
@dataclass(frozen=True)
class Response:
    status_code: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> dict: ...
    def text(self) -> str: ...
```

### Request

```python
@dataclass(frozen=True)
class Request:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None
```

### Exception Hierarchy

```
APIClientError (base)
├── ConnectionError      # Network/DNS/connection failures
├── TimeoutError         # Request timeout exceeded
├── RateLimitError       # 429 Too Many Requests
│   └── retry_after: int # Seconds to wait (from Retry-After header)
├── ServerError          # 5xx errors
│   └── status_code: int
└── ClientError          # 4xx errors (except 429)
    └── status_code: int
```

## Logging

The client logs at INFO level by default:

```
INFO  api_client: GET https://api.example.com/users/123
INFO  api_client: Response 200 in 0.234s
WARN  api_client: Retry 1/3 after 503 Service Unavailable
INFO  api_client: Response 200 in 0.189s (retry succeeded)
ERROR api_client: Failed after 3 retries: 503 Service Unavailable
```

Configure logging level:

```python
import logging
logging.getLogger("api_client").setLevel(logging.DEBUG)
```

## Troubleshooting

### Common Issues

**Issue**: Requests timing out frequently
**Solution**: Increase timeout in config or check network connectivity

```python
config = APIClientConfig(timeout=60)
```

**Issue**: Rate limit errors despite retry logic
**Solution**: The client respects `Retry-After` headers but cannot predict rate limits. Implement request throttling at the application level.

**Issue**: SSL certificate errors
**Solution**: Ensure system CA certificates are up to date. Do not disable SSL verification in production.

### Error Messages

| Error                    | Cause                    | Solution                         |
| ------------------------ | ------------------------ | -------------------------------- |
| "Connection refused"     | Server not running       | Check server status and URL      |
| "Name resolution failed" | DNS lookup failed        | Verify hostname and network      |
| "Request timed out"      | Server too slow          | Increase timeout or check server |
| "Max retries exceeded"   | Persistent server errors | Check server health, try later   |
| "Rate limit exceeded"    | Too many requests        | Wait for retry_after period      |

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now all requests log full details
client = APIClient(base_url="https://api.example.com")
```

## Architecture

### Components

```
api_client/
├── __init__.py       # Public API exports
├── client.py         # APIClient class - main interface
├── resilience.py     # Retry logic + rate limit handling
├── exceptions.py     # Exception hierarchy
├── models.py         # Request/Response dataclasses
└── tests/            # Test suite
```

### Data Flow

```
User Request
    │
    ▼
APIClient.get/post/put/delete/patch
    │
    ▼
Build Request dataclass
    │
    ▼
Resilience layer (retry loop)
    │
    ├── On success → Return Response
    ├── On 429 → Wait Retry-After, retry
    ├── On 5xx → Exponential backoff, retry
    └── On failure → Raise specific exception
```

### Design Decisions

1. **Standard Library Only**: No httpx/requests/aiohttp dependency - works everywhere Python runs
2. **Frozen Dataclasses**: Immutable Request/Response prevent accidental mutation
3. **Unified Resilience**: Single module handles both retry and rate limiting (simpler than separate components)
4. **Exception Hierarchy**: Specific exceptions enable targeted error handling without parsing strings

## Testing

Run the test suite:

```bash
cd .claude/scenarios/api-client
python -m pytest tests/ -v
```

### Test Categories

```bash
# Unit tests only (fast, mocked)
python -m pytest tests/ -v -m unit

# Integration tests (requires network)
python -m pytest tests/ -v -m integration

# All tests with coverage
python -m pytest tests/ -v --cov=. --cov-report=term-missing
```

### Test Structure

```
tests/
├── test_client.py        # APIClient method tests
├── test_resilience.py    # Retry and rate limit logic
├── test_exceptions.py    # Exception hierarchy tests
├── test_models.py        # Request/Response dataclass tests
└── conftest.py           # Fixtures and mocks
```

## Integration

### With Amplihack Agents

The API Client integrates with:

- **Integration Agent**: For connecting external services
- **Builder Agent**: As a dependency for tools that need HTTP access

### With Workflow

Use in workflow steps:

- **Step 4**: Fetch external data during implementation
- **Step 8**: Integration testing with real APIs

### With User Preferences

Respects these preferences:

- **verbosity**: Adjusts logging detail level

## Performance

### Typical Performance

- **Simple GET**: 50-200ms (network dependent)
- **Retry overhead**: ~1-8s per retry (exponential backoff)
- **Memory footprint**: <1MB for typical usage

### Optimization Tips

- Reuse client instances (connection pooling in future versions)
- Use appropriate timeouts for your use case
- Handle rate limits at the application level for predictable throughput

## Security Considerations

- **No Credential Storage**: Client does not persist credentials
- **SSL/TLS**: Always enabled, no option to disable
- **Header Sanitization**: Sensitive headers redacted from logs
- **Input Validation**: URLs validated before requests

## Contributing

See `HOW_TO_CREATE_YOUR_OWN.md` for guidance on:

- Adding new HTTP methods
- Extending the exception hierarchy
- Creating specialized client subclasses

---

_This tool follows amplihack's philosophy: minimal dependencies, clear failure modes, automatic recovery from transient errors._
