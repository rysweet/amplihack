# REST API Client

A production-ready HTTP client with automatic retry handling, rate limiting, and structured logging.

## Overview

The API client provides a reliable foundation for making HTTP requests with built-in resilience patterns:

- **Automatic retries** with exponential backoff and jitter for transient failures
- **Per-host rate limiting** with thread-safe implementation for 429 handling
- **Structured logging** with automatic credential sanitization
- **Timeout enforcement** on all requests to prevent hanging connections

## Installation

The API client is included as part of the project. No separate installation required.

```python
from api_client import APIClient, RetryPolicy, RateLimiter
```

## Quick Start

### Basic Usage

```python
from api_client import APIClient

# Create a client with default settings
client = APIClient(base_url="https://api.example.com")

# Make requests
response = client.get("/users/123")
print(response.json())

# POST with JSON body
response = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
print(response.status_code)  # 201
```

### With Custom Retry Policy

```python
from api_client import APIClient, RetryPolicy

# Configure retry behavior
retry_policy = RetryPolicy(
    max_retries=5,
    base_delay=1.0,
    max_delay=60.0
)

client = APIClient(
    base_url="https://api.example.com",
    retry_policy=retry_policy
)

# Requests automatically retry on transient failures
response = client.get("/flaky-endpoint")
```

### Thread-Safe Client

```python
from api_client import APIClient

# Enable thread safety for concurrent usage
client = APIClient(
    base_url="https://api.example.com",
    thread_safe=True
)

# Safe to use from multiple threads
import concurrent.futures
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(client.get, f"/items/{i}") for i in range(100)]
    results = [f.result() for f in futures]
```

## API Reference

### APIClient

The main HTTP client class.

```python
class APIClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        retry_policy: RetryPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
        thread_safe: bool = False,
        headers: dict[str, str] | None = None
    ):
        """
        Create an API client.

        Args:
            base_url: Base URL for all requests (e.g., "https://api.example.com")
            timeout: Request timeout in seconds (default: 30.0)
            retry_policy: Custom retry configuration (default: 3 retries)
            rate_limiter: Custom rate limiter (default: None)
            thread_safe: Enable thread-safe operations (default: False)
            headers: Default headers for all requests
        """
```

**Methods:**

| Method   | Signature                                                 | Description         |
| -------- | --------------------------------------------------------- | ------------------- |
| `get`    | `get(path, params=None, **kwargs) -> Response`            | HTTP GET request    |
| `post`   | `post(path, json=None, data=None, **kwargs) -> Response`  | HTTP POST request   |
| `put`    | `put(path, json=None, data=None, **kwargs) -> Response`   | HTTP PUT request    |
| `patch`  | `patch(path, json=None, data=None, **kwargs) -> Response` | HTTP PATCH request  |
| `delete` | `delete(path, **kwargs) -> Response`                      | HTTP DELETE request |

All methods return a `requests.Response` object directly.

**Additional Parameters:**

All HTTP methods accept `**kwargs` which are passed directly to the underlying `requests` library.
Common options include:

- `headers`: Additional headers for this request only
- `auth`: Authentication tuple
- `files`: File uploads

**URL Handling:**

The `base_url` should not include a trailing slash. The client handles path joining:

- `base_url="https://api.example.com"` + `path="/users"` = `https://api.example.com/users`

**Context Manager Support:**

```python
with APIClient(base_url="https://api.example.com") as client:
    response = client.get("/users")
# Connection pool properly cleaned up
```

### RetryPolicy

Configures retry behavior with exponential backoff.

```python
class RetryPolicy:
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        retryable_status_codes: set[int] | None = None
    ):
        """
        Configure retry behavior.

        Args:
            max_retries: Maximum retry attempts (default: 3)
            base_delay: Initial delay in seconds (default: 1.0)
            max_delay: Maximum delay cap in seconds (default: 60.0)
            retryable_status_codes: HTTP codes to retry (default: {429, 500, 502, 503, 504})
        """
```

**Retry Delay Calculation:**

The client uses exponential backoff with full jitter:

```
delay = random(0, min(max_delay, base_delay * 2^attempt))
```

When the server returns a `Retry-After` header, the client respects it:

- Supports seconds format: `Retry-After: 120`
- Supports HTTP-date format: `Retry-After: Wed, 21 Oct 2025 07:28:00 GMT`

### RateLimiter

Thread-safe per-host rate limiting.

```python
class RateLimiter:
    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int | None = None
    ):
        """
        Configure rate limiting.

        Args:
            requests_per_second: Maximum sustained request rate (default: 10.0)
            burst_size: Maximum burst allowance (default: requests_per_second)
        """
```

**Usage:**

```python
from api_client import APIClient, RateLimiter

# Limit to 5 requests per second with burst of 10
rate_limiter = RateLimiter(requests_per_second=5.0, burst_size=10)

client = APIClient(
    base_url="https://api.example.com",
    rate_limiter=rate_limiter
)

# Requests automatically throttled to respect limits
for i in range(100):
    client.get(f"/items/{i}")  # Automatically rate-limited
```

### Exceptions

```python
from api_client import APIClientError, NetworkError, HTTPError

class APIClientError(Exception):
    """Base exception for all API client errors."""

    @property
    def retryable(self) -> bool:
        """Whether this error is retryable."""

class NetworkError(APIClientError):
    """Connection or timeout errors. Always retryable."""

    @property
    def retryable(self) -> bool:
        """Always True for network errors."""

class HTTPError(APIClientError):
    """HTTP response errors. Retryable based on status code."""

    @property
    def status_code(self) -> int:
        """The HTTP status code that caused this error."""

    @property
    def response(self) -> Response:
        """The full response object."""

    @property
    def retryable(self) -> bool:
        """True for 429, 500, 502, 503, 504 status codes."""
```

## Configuration Options

### Default Configuration

```python
# These are the defaults when no configuration is provided
client = APIClient(
    base_url="https://api.example.com",
    timeout=30.0,              # 30 second timeout
    retry_policy=RetryPolicy(  # Default retry settings
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        retryable_status_codes={429, 500, 502, 503, 504}
    ),
    rate_limiter=None,         # No rate limiting by default
    thread_safe=False,         # Single-threaded by default
    headers=None               # No default headers
)
```

### Production Configuration Example

```python
from api_client import APIClient, RetryPolicy, RateLimiter

client = APIClient(
    base_url="https://api.production.com",
    timeout=10.0,  # Fail fast in production
    retry_policy=RetryPolicy(
        max_retries=5,
        base_delay=0.5,
        max_delay=30.0
    ),
    rate_limiter=RateLimiter(
        requests_per_second=20.0,
        burst_size=50
    ),
    thread_safe=True,
    headers={
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json"
    }
)
```

## Error Handling

### Basic Error Handling

```python
from api_client import APIClient, NetworkError, HTTPError

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/users/123")
    user = response.json()
except NetworkError as e:
    # Connection failed, DNS resolution failed, or timeout
    print(f"Network error: {e}")
except HTTPError as e:
    # Server returned an error status code
    if e.status_code == 404:
        print("User not found")
    elif e.status_code == 401:
        print("Authentication required")
    else:
        print(f"HTTP {e.status_code}: {e.response.text}")
```

### Handling Rate Limits

```python
from api_client import APIClient, HTTPError

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/resource")
except HTTPError as e:
    if e.status_code == 429:
        # Rate limited - check Retry-After header
        retry_after = e.response.headers.get("Retry-After", "unknown")
        print(f"Rate limited. Retry after: {retry_after}")
    raise
```

### Automatic Retry Behavior

The client automatically retries on:

| Error Type        | Retried | Notes                            |
| ----------------- | ------- | -------------------------------- |
| Connection errors | Yes     | Network unreachable, DNS failure |
| Timeout errors    | Yes     | Read/connect timeouts            |
| HTTP 429          | Yes     | Rate limit exceeded              |
| HTTP 500          | Yes     | Internal server error            |
| HTTP 502          | Yes     | Bad gateway                      |
| HTTP 503          | Yes     | Service unavailable              |
| HTTP 504          | Yes     | Gateway timeout                  |
| HTTP 4xx (other)  | No      | Client errors are not retried    |

## Logging Configuration

The client uses Python's standard `logging` module.

### Enable Debug Logging

```python
import logging

# Enable debug logging for the API client
logging.getLogger("api_client").setLevel(logging.DEBUG)

# Or configure with a handler
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logger = logging.getLogger("api_client")
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
```

### Log Output Example

```
2024-01-15 10:30:45 - api_client - DEBUG - GET https://api.example.com/users/123
2024-01-15 10:30:45 - api_client - DEBUG - Response: 200 OK (235ms)
2024-01-15 10:30:46 - api_client - WARNING - Request failed (attempt 1/3): Connection timeout
2024-01-15 10:30:47 - api_client - DEBUG - Retrying after 1.2s delay
2024-01-15 10:30:48 - api_client - DEBUG - GET https://api.example.com/users/123
2024-01-15 10:30:48 - api_client - DEBUG - Response: 200 OK (189ms)
```

### Credential Sanitization

Authorization headers are automatically sanitized in logs:

```
# What gets logged
Authorization: Bearer [REDACTED]
X-API-Key: [REDACTED]

# Never logged
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Thread Safety

### Single-Threaded (Default)

```python
# Default - not thread-safe, but faster
client = APIClient(base_url="https://api.example.com")
```

### Multi-Threaded

```python
# Enable thread safety for concurrent usage
client = APIClient(
    base_url="https://api.example.com",
    thread_safe=True
)
```

When `thread_safe=True`:

- Rate limiter uses thread-safe token bucket
- Internal state protected by locks
- Safe to share single client across threads

### Per-Thread Clients

For maximum performance with many threads, consider per-thread clients:

```python
import threading

_thread_local = threading.local()

def get_client() -> APIClient:
    if not hasattr(_thread_local, "client"):
        _thread_local.client = APIClient(
            base_url="https://api.example.com",
            thread_safe=False  # No locking needed
        )
    return _thread_local.client
```

## Security Considerations

### SSL/TLS Verification

SSL certificate verification is always enabled and cannot be disabled. This prevents man-in-the-middle attacks.

```python
# Certificate verification is automatic
client = APIClient(base_url="https://api.example.com")

# This will raise an error if the certificate is invalid
response = client.get("/secure-endpoint")
```

### Credential Handling

1. **Never log credentials**: Authorization headers are automatically redacted
2. **Use environment variables**: Store API keys in environment, not code
3. **Rotate regularly**: Change API keys periodically

```python
import os

client = APIClient(
    base_url="https://api.example.com",
    headers={
        "Authorization": f"Bearer {os.environ['API_TOKEN']}"
    }
)
```

### Timeout Enforcement

All requests have enforced timeouts to prevent resource exhaustion:

```python
# Timeout is always enforced
client = APIClient(
    base_url="https://api.example.com",
    timeout=30.0  # 30 seconds max per request
)
```

## Module Structure

```
src/api_client/
├── __init__.py      # Public API exports
├── client.py        # APIClient implementation
├── retry.py         # RetryPolicy with backoff logic
├── rate_limiter.py  # Thread-safe rate limiting
├── types.py         # Exception definitions
└── tests/           # Test suite
```
