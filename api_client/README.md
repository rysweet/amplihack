# REST API Client

A simple, type-safe HTTP client library with built-in retry logic, rate limiting, and comprehensive error handling. Zero external dependencies beyond the standard `requests` library.

## Quick Start

```python
from api_client import HTTPClient, Request

# Create client with sensible defaults
client = HTTPClient()

# Make a simple GET request
response = client.send(Request(
    url="https://api.example.com/users",
    method="GET"
))

print(f"Status: {response.status_code}")
print(f"Body: {response.body}")
```

## Installation

```bash
pip install api-client
```

## Features

- **Simple HTTP operations**: GET, POST, PUT, DELETE with clean API
- **Type-safe**: All data structures are type-checked dataclasses
- **Automatic retries**: Exponential backoff with configurable max retries (default: 3)
- **Built-in rate limiting**: Token bucket algorithm (default: 10 requests/second)
- **Timeout support**: Configurable request timeouts (default: 30 seconds)
- **SSRF protection**: Optional host allowlist for security
- **Comprehensive error handling**: 3 exception types with helper methods
- **Standard logging**: Uses Python's built-in logging module
- **Zero dependencies**: Only requires the `requests` library

## Contents

- [Usage Examples](#usage-examples)
  - [Basic Requests](#basic-requests)
  - [Error Handling](#error-handling)
  - [Configuration](#configuration)
- [API Reference](#api-reference)
  - [HTTPClient](#httpclient)
  - [Request](#request)
  - [Response](#response)
  - [Exceptions](#exceptions)
  - [RateLimiter](#ratelimiter)
  - [RetryPolicy](#retrypolicy)
- [Testing Your Code](#testing-your-code)
- [Design Philosophy](#design-philosophy)

## Usage Examples

### Basic Requests

#### GET Request

```python
from api_client import HTTPClient, Request

client = HTTPClient()

# Simple GET
response = client.send(Request(
    url="https://api.example.com/users/123",
    method="GET"
))

print(f"User data: {response.body}")
# Output: User data: {'id': 123, 'name': 'Alice', 'email': 'alice@example.com'}
```

#### POST with JSON Body

```python
from api_client import HTTPClient, Request

client = HTTPClient()

# Create a new user
response = client.send(Request(
    url="https://api.example.com/users",
    method="POST",
    headers={"Content-Type": "application/json"},
    body={"name": "Bob", "email": "bob@example.com"}
))

print(f"Created user ID: {response.body['id']}")
# Output: Created user ID: 124
```

#### PUT Update

```python
from api_client import HTTPClient, Request

client = HTTPClient()

# Update existing user
response = client.send(Request(
    url="https://api.example.com/users/123",
    method="PUT",
    headers={"Content-Type": "application/json"},
    body={"name": "Alice Updated", "email": "alice.new@example.com"}
))

print(f"Updated: {response.status_code == 200}")
# Output: Updated: True
```

#### DELETE

```python
from api_client import HTTPClient, Request

client = HTTPClient()

# Delete user
response = client.send(Request(
    url="https://api.example.com/users/123",
    method="DELETE"
))

print(f"Deleted: {response.status_code == 204}")
# Output: Deleted: True
```

### Error Handling

The library provides 3 exception types for different error scenarios:

```python
from api_client import HTTPClient, Request
from api_client import APIError, ClientError, ServerError

client = HTTPClient()

try:
    response = client.send(Request(
        url="https://api.example.com/protected",
        method="GET"
    ))
except ClientError as e:
    # 4xx errors (client mistakes)
    if e.status_code == 401:
        print("Authentication required")
    elif e.status_code == 404:
        print("Resource not found")
    elif e.is_rate_limited():
        print(f"Rate limited, retry after: {e.response.headers.get('Retry-After')}")
    else:
        print(f"Client error: {e.status_code}")

except ServerError as e:
    # 5xx errors (server problems)
    print(f"Server error {e.status_code}, retrying...")

except APIError as e:
    # Catch-all for other API errors
    if e.is_timeout():
        print("Request timed out")
    else:
        print(f"API error: {e}")
```

### Configuration

#### Custom Rate Limiting

```python
from api_client import HTTPClient, RateLimiter

# Limit to 5 requests per second
client = HTTPClient(
    rate_limiter=RateLimiter(requests_per_second=5.0)
)

# Rate limiter uses token bucket algorithm
# Requests are automatically throttled to stay within limit
for i in range(20):
    response = client.send(Request(
        url=f"https://api.example.com/items/{i}",
        method="GET"
    ))
    # Requests 0-4: immediate
    # Requests 5+: throttled to 5/second
```

#### Custom Retry Policy

```python
from api_client import HTTPClient, RetryPolicy

# Retry up to 5 times with exponential backoff
client = HTTPClient(
    retry_policy=RetryPolicy(max_retries=5)
)

# Retry behavior:
# - Attempt 1: immediate
# - Attempt 2: wait 1 second
# - Attempt 3: wait 2 seconds
# - Attempt 4: wait 4 seconds
# - Attempt 5: wait 8 seconds
# - Attempt 6: wait 16 seconds
```

#### SSRF Protection

```python
from api_client import HTTPClient

# Only allow requests to specific hosts
client = HTTPClient(
    allowed_hosts=["api.example.com", "cdn.example.com"]
)

# This works
response = client.send(Request(
    url="https://api.example.com/users",
    method="GET"
))

# This raises ClientError
try:
    response = client.send(Request(
        url="https://malicious.com/steal-data",
        method="GET"
    ))
except ClientError as e:
    print(f"Blocked: {e}")
    # Output: Blocked: Host 'malicious.com' not in allowed hosts
```

#### Timeout Configuration

```python
from api_client import HTTPClient

# Set custom timeout (default is 30 seconds)
client = HTTPClient(timeout=60)

# Per-request timeout override
response = client.send(
    Request(url="https://api.example.com/slow", method="GET"),
    timeout=120  # 2 minutes for this specific request
)
```

#### Complete Configuration Example

```python
from api_client import HTTPClient, RateLimiter, RetryPolicy

client = HTTPClient(
    rate_limiter=RateLimiter(requests_per_second=5.0),
    retry_policy=RetryPolicy(max_retries=5),
    timeout=60,
    allowed_hosts=["api.example.com"],
    default_headers={
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json"
    }
)
```

## API Reference

### HTTPClient

The main HTTP client class with automatic retry, rate limiting, and error handling.

```python
class HTTPClient:
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        retry_policy: Optional[RetryPolicy] = None,
        timeout: int = 30,
        allowed_hosts: Optional[List[str]] = None,
        default_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize HTTP client.

        Args:
            rate_limiter: Rate limiter instance (default: 10 req/sec)
            retry_policy: Retry policy instance (default: 3 retries)
            timeout: Request timeout in seconds (default: 30)
            allowed_hosts: List of allowed hostnames for SSRF protection
            default_headers: Headers included in every request
        """
```

#### Methods

**send(request: Request, timeout: Optional[int] = None) -> Response**

Send an HTTP request with automatic retry and rate limiting.

```python
response = client.send(
    Request(url="https://api.example.com/users", method="GET"),
    timeout=60  # Optional per-request timeout override
)
```

**Raises:**

- `ClientError`: For 4xx HTTP errors
- `ServerError`: For 5xx HTTP errors
- `APIError`: For other errors (network, timeout, etc.)

### Request

Immutable dataclass representing an HTTP request.

```python
@dataclass(frozen=True)
class Request:
    url: str
    method: str  # "GET", "POST", "PUT", "DELETE"
    headers: Optional[Dict[str, str]] = None
    body: Optional[Union[Dict, str, bytes]] = None
    params: Optional[Dict[str, str]] = None
```

**Example:**

```python
request = Request(
    url="https://api.example.com/users",
    method="POST",
    headers={"Content-Type": "application/json", "Authorization": "Bearer token123"},
    body={"name": "Charlie", "email": "charlie@example.com"},
    params={"notify": "true"}
)
# Sends POST to: https://api.example.com/users?notify=true
```

### Response

Immutable dataclass representing an HTTP response.

```python
@dataclass(frozen=True)
class Response:
    status_code: int
    headers: Dict[str, str]
    body: Union[Dict, str, bytes]
    request: Request  # Original request
```

**Example:**

```python
response = client.send(Request(url="https://api.example.com/users/123", method="GET"))

print(f"Status: {response.status_code}")  # 200
print(f"Content-Type: {response.headers['Content-Type']}")  # application/json
print(f"Body: {response.body}")  # {'id': 123, 'name': 'Alice'}
print(f"Original URL: {response.request.url}")  # https://api.example.com/users/123
```

**Note**: Response bodies are automatically parsed:

- `application/json`: Parsed to Dict
- Other content-types: Returned as str or bytes

### Exceptions

All exceptions inherit from `APIError` and include status code and response information.

```python
class APIError(Exception):
    """Base exception for all API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Response] = None):
        self.message = message
        self.status_code = status_code
        self.response = response

    def is_timeout(self) -> bool:
        """Returns True if error was caused by timeout (status 408)."""
        return self.status_code == 408

    def is_rate_limited(self) -> bool:
        """Returns True if error was caused by rate limiting (status 429)."""
        return self.status_code == 429

class ClientError(APIError):
    """Exception for 4xx HTTP errors (client mistakes)."""
    pass

class ServerError(APIError):
    """Exception for 5xx HTTP errors (server problems)."""
    pass
```

**Exception Hierarchy:**

```
APIError (status_code, response, is_timeout(), is_rate_limited())
├── ClientError (4xx errors: 400, 401, 403, 404, 429, etc.)
└── ServerError (5xx errors: 500, 502, 503, 504, etc.)
```

**Usage:**

```python
try:
    response = client.send(request)
except ClientError as e:
    if e.status_code == 401:
        print("Need to authenticate")
    elif e.is_rate_limited():
        print(f"Rate limited: {e.response.headers.get('Retry-After')} seconds")
except ServerError as e:
    print(f"Server error {e.status_code}, try again later")
except APIError as e:
    if e.is_timeout():
        print("Request timed out")
    else:
        print(f"Unexpected error: {e.message}")
```

### RateLimiter

Token bucket rate limiter that controls request throughput.

```python
class RateLimiter:
    def __init__(self, requests_per_second: float = 10.0):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second (default: 10.0)
        """
```

**Example:**

```python
# 5 requests per second
limiter = RateLimiter(requests_per_second=5.0)

# Pass to HTTPClient
client = HTTPClient(rate_limiter=limiter)

# Client automatically throttles requests to stay within limit
```

**Algorithm**: Token bucket with 1-second refill interval. Allows bursts up to the rate limit, then throttles subsequent requests.

**Thread Safety**: The RateLimiter is thread-safe and can be shared across multiple threads safely.

### RetryPolicy

Exponential backoff retry policy for handling transient failures.

```python
class RetryPolicy:
    def __init__(self, max_retries: int = 3):
        """
        Initialize retry policy.

        Args:
            max_retries: Maximum number of retry attempts (default: 3)
        """
```

**Example:**

```python
# Retry up to 5 times
policy = RetryPolicy(max_retries=5)

# Pass to HTTPClient
client = HTTPClient(retry_policy=policy)

# Client automatically retries failed requests with exponential backoff
```

**Retry Behavior:**

- Retries only on server errors (5xx) and network errors
- Does NOT retry on client errors (4xx)
- Exponential backoff: 1s, 2s, 4s, 8s, 16s, ...
- Jitter added (±25% randomization) to prevent thundering herd when many clients retry simultaneously

## Testing Your Code

### Unit Testing with Mocks

```python
import unittest
from unittest.mock import Mock, patch
from api_client import HTTPClient, Request, Response

class TestMyAPI(unittest.TestCase):
    def test_get_user(self):
        # Mock the HTTPClient
        mock_client = Mock(spec=HTTPClient)
        mock_client.send.return_value = Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            body={"id": 123, "name": "Alice"},
            request=Request(url="https://api.example.com/users/123", method="GET")
        )

        # Test your code
        response = mock_client.send(Request(
            url="https://api.example.com/users/123",
            method="GET"
        ))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["name"], "Alice")
```

### Integration Testing with Real Requests

```python
import unittest
from api_client import HTTPClient, Request, ClientError

class TestRealAPI(unittest.TestCase):
    def setUp(self):
        self.client = HTTPClient()

    def test_get_public_api(self):
        # Test against a real public API
        response = self.client.send(Request(
            url="https://jsonplaceholder.typicode.com/users/1",
            method="GET"
        ))

        self.assertEqual(response.status_code, 200)
        self.assertIn("name", response.body)

    def test_handles_404_error(self):
        with self.assertRaises(ClientError) as ctx:
            self.client.send(Request(
                url="https://jsonplaceholder.typicode.com/users/99999",
                method="GET"
            ))

        self.assertEqual(ctx.exception.status_code, 404)
```

### Testing Rate Limiting

```python
import unittest
import time
from api_client import HTTPClient, RateLimiter, Request

class TestRateLimiting(unittest.TestCase):
    def test_rate_limiter_throttles_requests(self):
        # 2 requests per second
        client = HTTPClient(rate_limiter=RateLimiter(requests_per_second=2.0))

        start_time = time.time()

        # Make 6 requests
        for i in range(6):
            try:
                client.send(Request(
                    url="https://jsonplaceholder.typicode.com/users/1",
                    method="GET"
                ))
            except Exception:
                pass  # Ignore errors, we're testing timing

        elapsed = time.time() - start_time

        # Should take at least 2.5 seconds (6 requests at 2/sec = 3 seconds)
        # Allow some tolerance for actual HTTP request time
        self.assertGreater(elapsed, 2.0)
```

### Testing Retry Logic

```python
import unittest
from unittest.mock import Mock, patch
from api_client import HTTPClient, RetryPolicy, Request, ServerError

class TestRetryLogic(unittest.TestCase):
    @patch('requests.request')
    def test_retries_on_server_error(self, mock_request):
        # Simulate server errors then success
        mock_request.side_effect = [
            Mock(status_code=503, text="Service Unavailable"),
            Mock(status_code=503, text="Service Unavailable"),
            Mock(status_code=200, text='{"success": true}', json=lambda: {"success": True})
        ]

        client = HTTPClient(retry_policy=RetryPolicy(max_retries=3))

        response = client.send(Request(
            url="https://api.example.com/endpoint",
            method="GET"
        ))

        # Should succeed after retries
        self.assertEqual(response.status_code, 200)
        # Should have made 3 attempts
        self.assertEqual(mock_request.call_count, 3)
```

## Design Philosophy

This library follows the **ruthless simplicity** philosophy:

### Core Principles

1. **Type Safety**: All data structures are type-checked dataclasses for compile-time safety
2. **Zero-BS Implementation**: Every function works or doesn't exist—no stubs or placeholders
3. **Simplicity First**: Start with the simplest solution that works, add complexity only when justified
4. **Standard Library**: Uses only Python's `requests` library, no exotic dependencies
5. **Fail Fast**: Errors are explicit and visible—no silent failures

### What We Avoid

- **Over-abstraction**: No unnecessary layers or interfaces
- **Future-proofing**: We solve today's problems, not hypothetical future ones
- **Configuration complexity**: Sensible defaults, minimal knobs
- **Magic**: Explicit is better than implicit

### Modular Design

The library is organized as self-contained "bricks":

- **models.py**: Pure dataclasses (Request, Response)
- **exceptions.py**: 3 exception types with helper methods
- **rate_limiter.py**: Token bucket rate limiting
- **retry.py**: Exponential backoff retry logic
- **client.py**: Main HTTP client orchestration

Each module has ONE clear responsibility and can be understood independently.

### Validation Strategy

All input validation happens in `client.py` at the entry point:

- URL format validation (scheme, host)
- SSRF protection (allowed_hosts check)
- Method validation (GET, POST, PUT, DELETE)
- Header and body type checking

This centralized validation makes the system easier to test and maintain.

### Error Handling

We provide **3 exception types** (not 6, not 12):

- `APIError`: Base exception with status code and helper methods
- `ClientError`: 4xx errors (your code's fault)
- `ServerError`: 5xx errors (their server's fault)

This covers 95% of use cases without overwhelming users with exception hierarchies.

### Defaults

We choose sensible defaults based on real-world usage:

- **10 requests/second**: Reasonable rate for most APIs
- **3 retries**: Balance between reliability and speed
- **30 second timeout**: Long enough for slow endpoints, short enough to fail fast
- **Exponential backoff**: Standard retry pattern

Users can customize everything, but defaults work out of the box.

---

**Version**: 1.0.0
**Last Updated**: 2025-12-01
**License**: MIT

For bugs or feature requests, see the GitHub issues page.
