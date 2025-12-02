# API Client

Simple, reliable HTTP client with automatic retry and rate limiting.

## Quick Start

```python
from api_client import APIClient, APIClientError

with APIClient(base_url="https://api.example.com") as client:
    response = client.get("/users/1")
    if response.status_code == 200:
        print(response.body)
```

## Installation

```bash
pip install requests  # Only external dependency
```

## API Reference

### APIClient

```python
APIClient(
    base_url: str,
    timeout_seconds: float = 30.0,
    max_retries: int = 3,
    rate_limit_per_second: float = 10.0,
)
```

| Parameter               | Type  | Default  | Description                           |
| ----------------------- | ----- | -------- | ------------------------------------- |
| `base_url`              | str   | required | Base URL for all requests             |
| `timeout_seconds`       | float | 30.0     | Request timeout                       |
| `max_retries`           | int   | 3        | Retry attempts for transient failures |
| `rate_limit_per_second` | float | 10.0     | Max requests per second               |

#### Methods

```python
client.get(path, params=None)    -> APIResponse
client.post(path, json=None)     -> APIResponse
client.put(path, json=None)      -> APIResponse
client.delete(path)              -> APIResponse
```

### APIResponse

```python
@dataclass
class APIResponse:
    status_code: int           # HTTP status (200, 404, etc.)
    body: dict | list | str    # Parsed JSON or raw text
    headers: dict[str, str]    # Response headers
    elapsed_ms: float          # Request duration
```

### APIClientError

Single exception class for all errors. Check `error_type` for specific handling:

```python
@dataclass
class APIClientError(Exception):
    message: str
    error_type: str       # See table below
    status_code: int | None
    response_body: str | None
```

| error_type     | When Raised                          |
| -------------- | ------------------------------------ |
| `"connection"` | Network unreachable, DNS failure     |
| `"timeout"`    | Request/read timeout exceeded        |
| `"rate_limit"` | 429 response after retries exhausted |
| `"http"`       | Non-2xx response (4xx, 5xx)          |
| `"validation"` | Invalid request parameters           |

## Error Handling

```python
from api_client import APIClient, APIClientError

try:
    response = client.get("/users/1")
except APIClientError as e:
    if e.error_type == "timeout":
        print(f"Request timed out: {e.message}")
    elif e.error_type == "rate_limit":
        print(f"Rate limited. Retry after: {e.retry_after}s")
    elif e.error_type == "http":
        print(f"HTTP {e.status_code}: {e.response_body}")
    else:
        print(f"Error: {e.message}")
```

## Retry Behavior

Automatic retry with exponential backoff for transient failures:

| Attempt | Delay | Retries On                  |
| ------- | ----- | --------------------------- |
| 1       | 0.5s  | Connection errors, timeouts |
| 2       | 1.0s  | 429 (rate limit)            |
| 3       | 2.0s  | 500, 502, 503, 504          |

**Not retried:** 4xx errors (except 429), validation errors.

### Customization

```python
client = APIClient(
    base_url="https://api.example.com",
    max_retries=5,        # More retries
    timeout_seconds=60,   # Longer timeout
)
```

## Rate Limiting

Built-in rate limiting prevents 429 errors:

```python
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_per_second=5.0,  # Max 5 requests/second
)
```

When server returns 429, the client:

1. Parses `Retry-After` header if present
2. Waits the specified time
3. Retries the request

## Logging

Uses Python's `logging` module:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

| Level   | Events                           |
| ------- | -------------------------------- |
| DEBUG   | Request/response details         |
| WARNING | Retry attempts, rate limit waits |
| ERROR   | Final failures                   |

**Security:** Authorization headers are automatically sanitized in logs.

## Thread Safety

The client is designed for single-threaded use in v1. For concurrent requests, create separate client instances.

## Dependencies

- `requests` (only external dependency)
- Python 3.10+
