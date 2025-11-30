# REST API Client

A robust, production-ready HTTP client for REST APIs with built-in retry logic, rate limiting, comprehensive error handling, and security features.

## Overview

The REST API Client provides a modular, type-safe interface for interacting with REST APIs. It handles common challenges like transient failures, rate limits, and authentication while maintaining a clean, simple API.

**Key Features:**

- Automatic retry with exponential backoff
- Intelligent rate limit handling
- Comprehensive error handling with custom exception hierarchy
- Request/response dataclasses for type safety
- Built-in logging
- SSL/TLS enforcement
- Input validation and credential protection

## Quick Start

### Installation

```bash
pip install amplihack
```

### Basic Usage

```python
from amplihack.utils.api_client import APIClient

# Create a client
client = APIClient(base_url="https://api.example.com")

# Make a GET request
response = client.get("/users/123")
print(response.data)  # Parsed JSON data
print(response.status_code)  # 200

# Make a POST request
response = client.post(
    "/users",
    json={"name": "Alice", "email": "alice@example.com"}
)
```

### Using Context Manager

The `APIClient` supports Python's context manager protocol for automatic session cleanup:

```python
# Automatically closes session when done
with APIClient(base_url="https://api.example.com") as client:
    response = client.get("/resource")
    print(f"Status: {response.status_code}")
    print(f"Data: {response.json}")
# Session automatically closed here

# Equivalent to:
client = APIClient(base_url="https://api.example.com")
try:
    response = client.get("/resource")
finally:
    client.close()  # Explicit cleanup
```

**When to Use**:

- Short-lived operations (single script execution)
- One-off requests
- Testing scenarios

**When NOT to Use**:

- Long-running services (create once, reuse)
- Multiple requests over time
- Connection pooling scenarios

## Contents

- [Features](#features)
- [Configuration](#configuration)
- [Making Requests](#making-requests)
- [Error Handling](#error-handling)
- [Retry Logic](#retry-logic)
- [Rate Limiting](#rate-limiting)
- [Authentication](#authentication)
- [Security](#security)
- [Logging](#logging)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Examples](#examples)

## Features

### Supported HTTP Methods

The client supports all standard REST operations:

- **GET**: Retrieve resources
- **POST**: Create resources
- **PUT**: Update resources (full replacement)
- **DELETE**: Remove resources

### Automatic Retry with Exponential Backoff

Transient failures are handled automatically with configurable retry logic:

```python
from amplihack.utils.api_client import APIClient, RetryConfig

# Configure custom retry behavior
retry_config = RetryConfig(
    max_retries=3,           # Maximum retry attempts
    base_delay=1.0,          # Initial delay in seconds
    max_delay=60.0,          # Maximum delay between retries
    exponential_base=2.0     # Backoff multiplier
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)
```

**Default Retry Behavior:**

- Max retries: 3
- Base delay: 1 second
- Max delay: 60 seconds
- Exponential base: 2.0 (delays: 1s, 2s, 4s)

### Rate Limit Handling

The client automatically detects and handles HTTP 429 (Too Many Requests) responses:

```python
from amplihack.utils.api_client import APIClient, RateLimitConfig

# Configure rate limit behavior
rate_limit_config = RateLimitConfig(
    max_wait_time=300.0,     # Maximum time to wait (seconds)
    respect_retry_after=True # Honor Retry-After header
)

client = APIClient(
    base_url="https://api.example.com",
    rate_limit_config=rate_limit_config
)

# Client automatically waits when rate limited
response = client.get("/resource")
```

**Rate Limit Features:**

- Respects `Retry-After` header (both seconds and HTTP-date formats)
- Configurable maximum wait time for security
- Automatic backoff when header is missing
- Detailed logging of rate limit events

### Comprehensive Error Handling

Custom exception hierarchy for precise error handling:

```python
from amplihack.utils.api_client import (
    APIClient,
    APIClientError,      # Base exception
    RequestError,        # Request construction/network errors
    HTTPError,           # HTTP error responses (4xx, 5xx)
    RateLimitError,      # Rate limit exceeded
    RetryExhaustedError  # All retries failed
)

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/resource")
except RateLimitError as e:
    print(f"Rate limited: {e.wait_time}s")
    print(f"Retry after: {e.retry_after}")
except HTTPError as e:
    print(f"HTTP {e.status_code}: {e.message}")
except RequestError as e:
    print(f"Request failed: {e}")
except RetryExhaustedError as e:
    print(f"All retries failed after {e.attempts} attempts")
except APIClientError as e:
    print(f"API client error: {e}")
```

### Type-Safe Requests and Responses

Dataclasses provide type safety and clear interfaces:

```python
from amplihack.utils.api_client import APIClient, APIRequest, APIResponse

# Create a structured request
request = APIRequest(
    method="POST",
    url="/users",
    headers={"Authorization": "Bearer token123"},
    params={"include": "profile"},
    json={"name": "Bob", "email": "bob@example.com"}
)

client = APIClient(base_url="https://api.example.com")
response = client.execute(request)

# Response provides structured access
print(response.status_code)    # int
print(response.headers)        # dict
print(response.data)          # parsed JSON (dict or list)
print(response.text)          # raw text
print(response.elapsed_time)  # float (seconds)
```

## Configuration

### APIClient Configuration

```python
from amplihack.utils.api_client import APIClient, RetryConfig, RateLimitConfig

client = APIClient(
    base_url="https://api.example.com",
    timeout=30.0,                        # Request timeout (seconds)
    verify_ssl=True,                     # SSL certificate verification
    default_headers={                    # Headers for all requests
        "User-Agent": "MyApp/1.0"
    },
    retry_config=RetryConfig(
        max_retries=3,
        base_delay=1.0
    ),
    rate_limit_config=RateLimitConfig(
        max_wait_time=300.0,
        respect_retry_after=True
    )
)
```

**💡 Timeout Behavior:**

- `timeout` in `__init__()`: Sets **default** timeout for **all** requests
- `timeout` in request methods (`.get()`, `.post()`, etc.): **Overrides** default for **that specific request**

```python
# Set default 30s timeout
client = APIClient("https://api.example.com", timeout=30.0)

# Use default (30s)
client.get("/fast-endpoint")

# Override to 120s for this request only
client.get("/slow-endpoint", timeout=120.0)

# Use default again (30s)
client.get("/another-endpoint")
```

### RetryConfig Options

```python
from amplihack.utils.api_client import RetryConfig

retry_config = RetryConfig(
    max_retries=3,           # Maximum retry attempts (default: 3)
    base_delay=1.0,          # Initial delay in seconds (default: 1.0)
    max_delay=60.0,          # Maximum delay between retries (default: 60.0)
    exponential_base=2.0,    # Backoff multiplier (default: 2.0)
    retry_on_status=[500, 502, 503, 504]  # Status codes to retry
)
```

### RateLimitConfig Options

```python
from amplihack.utils.api_client import RateLimitConfig

rate_limit_config = RateLimitConfig(
    max_wait_time=300.0,      # Maximum wait time in seconds (default: 300.0)
    respect_retry_after=True, # Honor Retry-After header (default: True)
    default_backoff=60.0      # Default wait when no Retry-After (default: 60.0)
)
```

## Making Requests

### GET Requests

```python
# Simple GET
response = client.get("/users")

# GET with query parameters
response = client.get("/users", params={"page": 2, "limit": 50})

# GET with custom headers
response = client.get(
    "/users/123",
    headers={"Authorization": "Bearer token123"}
)
```

### POST Requests

```python
# POST with JSON body
response = client.post(
    "/users",
    json={"name": "Alice", "email": "alice@example.com"}
)

# POST with form data
response = client.post(
    "/users",
    data={"name": "Alice", "email": "alice@example.com"}
)

# POST with custom headers
response = client.post(
    "/users",
    json={"name": "Alice"},
    headers={"Content-Type": "application/json"}
)
```

### PUT Requests

```python
# PUT to update resource
response = client.put(
    "/users/123",
    json={"name": "Alice Updated", "email": "alice.new@example.com"}
)
```

### DELETE Requests

```python
# DELETE resource
response = client.delete("/users/123")

# DELETE with confirmation parameter
response = client.delete("/users/123", params={"confirm": "true"})
```

### Using APIRequest Dataclass

```python
from amplihack.utils.api_client import APIRequest

# Create structured request
request = APIRequest(
    method="POST",
    url="/users",
    headers={"Authorization": "Bearer token123"},
    params={"notify": "true"},
    json={"name": "Bob"}
)

# Execute request
response = client.execute(request)
```

## Error Handling

### Exception Hierarchy

```
APIClientError (base)
├── RequestError          # Network, DNS, connection errors
├── HTTPError             # HTTP 4xx/5xx responses
├── RateLimitError        # HTTP 429 responses
└── RetryExhaustedError   # All retries failed
```

### Handling Specific Errors

```python
from amplihack.utils.api_client import (
    APIClient,
    RequestError,
    HTTPError,
    RateLimitError,
    RetryExhaustedError
)

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/resource")

except RateLimitError as e:
    # Handle rate limiting
    print(f"Rate limited. Wait {e.wait_time} seconds")
    if e.retry_after:
        print(f"Retry-After header: {e.retry_after}")

except HTTPError as e:
    # Handle HTTP errors
    if e.status_code == 404:
        print("Resource not found")
    elif e.status_code >= 500:
        print(f"Server error: {e.message}")
    else:
        print(f"Client error {e.status_code}: {e.message}")

except RequestError as e:
    # Handle network/connection errors
    print(f"Request failed: {e}")
    # Check if it was a timeout
    if "timeout" in str(e).lower():
        print("Request timed out")

except RetryExhaustedError as e:
    # All retries failed
    print(f"Failed after {e.attempts} attempts")
    print(f"Last error: {e.last_error}")
```

### Error Attributes

```python
# HTTPError attributes
try:
    response = client.get("/resource")
except HTTPError as e:
    print(e.status_code)   # int: HTTP status code
    print(e.message)       # str: Error message
    print(e.response_data) # dict/str: Response body (if available)

# RateLimitError attributes
try:
    response = client.get("/resource")
except RateLimitError as e:
    print(e.wait_time)     # float: Seconds to wait
    print(e.retry_after)   # str: Retry-After header value
    print(e.status_code)   # int: 429

# RetryExhaustedError attributes
try:
    response = client.get("/resource")
except RetryExhaustedError as e:
    print(e.attempts)      # int: Number of attempts made
    print(e.last_error)    # Exception: Last error encountered
```

## Retry Logic

### How Retry Works

The client automatically retries failed requests with exponential backoff:

1. Request fails with retryable error (network issue, 500/502/503/504)
2. Wait for calculated delay: `base_delay * (exponential_base ** attempt)`
3. Retry the request
4. Repeat up to `max_retries` times
5. If all retries fail, raise `RetryExhaustedError`

### Retry Configuration Examples

**Conservative (production):**

```python
retry_config = RetryConfig(
    max_retries=5,
    base_delay=2.0,
    max_delay=120.0,
    exponential_base=2.0
)
# Delays: 2s, 4s, 8s, 16s, 32s
```

**Aggressive (development):**

```python
retry_config = RetryConfig(
    max_retries=2,
    base_delay=0.5,
    max_delay=5.0,
    exponential_base=2.0
)
# Delays: 0.5s, 1s
```

**Linear backoff:**

```python
retry_config = RetryConfig(
    max_retries=3,
    base_delay=5.0,
    max_delay=5.0,
    exponential_base=1.0
)
# Delays: 5s, 5s, 5s
```

### Which Errors Trigger Retry

**Automatically retried:**

- Network errors (DNS, connection refused, timeout)
- HTTP 500 (Internal Server Error)
- HTTP 502 (Bad Gateway)
- HTTP 503 (Service Unavailable)
- HTTP 504 (Gateway Timeout)

**Not retried:**

- HTTP 4xx errors (client errors) except 429
- HTTP 429 (handled by rate limit logic)
- Successful responses (2xx, 3xx)

## Rate Limiting

### Rate Limit Detection

The client detects rate limiting via HTTP 429 responses and automatically handles them according to configuration.

### Retry-After Header Support

The client respects the `Retry-After` header in two formats:

**Seconds format:**

```
Retry-After: 120
```

**HTTP-date format:**

```
Retry-After: Wed, 21 Oct 2025 07:28:00 GMT
```

### Rate Limit Behavior

```python
from amplihack.utils.api_client import APIClient, RateLimitConfig

# Conservative: Wait up to 10 minutes
rate_limit_config = RateLimitConfig(
    max_wait_time=600.0,
    respect_retry_after=True,
    default_backoff=120.0
)

client = APIClient(
    base_url="https://api.example.com",
    rate_limit_config=rate_limit_config
)

# Client automatically waits when rate limited
try:
    response = client.get("/resource")
except RateLimitError as e:
    # Only raised if wait_time > max_wait_time
    print(f"Rate limit wait time ({e.wait_time}s) exceeds maximum")
```

### Rate Limit Security

**Maximum wait time enforcement:**

```python
# Prevent indefinite waits from malicious APIs
rate_limit_config = RateLimitConfig(
    max_wait_time=300.0  # Never wait more than 5 minutes
)
```

If the API requests a wait time longer than `max_wait_time`, the client raises `RateLimitError` instead of waiting.

## Authentication

### API Key Authentication

```python
# API key in header
client = APIClient(
    base_url="https://api.example.com",
    default_headers={"X-API-Key": "your-api-key"}
)

# API key in query parameter
response = client.get("/resource", params={"api_key": "your-api-key"})
```

### Bearer Token Authentication

```python
# Bearer token
client = APIClient(
    base_url="https://api.example.com",
    default_headers={"Authorization": "Bearer your-token"}
)
```

### Basic Authentication

```python
import base64

# Encode credentials
credentials = base64.b64encode(b"username:password").decode("ascii")
auth_header = f"Basic {credentials}"

client = APIClient(
    base_url="https://api.example.com",
    default_headers={"Authorization": auth_header}
)
```

### Using Environment Variables

```python
import os
from amplihack.utils.api_client import APIClient

# Load API key from environment
api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError("API_KEY environment variable not set")

client = APIClient(
    base_url="https://api.example.com",
    default_headers={"X-API-Key": api_key}
)
```

## Security

### ⚠️ **CRITICAL: SSL/TLS Verification**

**NEVER disable SSL verification in production!**

```python
# ❌ DANGEROUS - Only for local development/testing
client = APIClient("https://api.example.com", verify_ssl=False)

# ✅ SAFE - Always use SSL verification (default)
client = APIClient("https://api.example.com")  # verify_ssl=True by default
```

**Why This Matters**:

- Disabling SSL verification exposes you to **man-in-the-middle attacks**
- Attackers can intercept and modify API responses
- Credentials and sensitive data can be stolen
- Your application becomes vulnerable to impersonation attacks

**When `verify_ssl=False` Might Be Acceptable** (with extreme caution):

- Local development against self-signed certificates
- Testing environments with mock servers
- **NEVER** in production
- **NEVER** with real credentials
- **NEVER** with sensitive data

### SSRF (Server-Side Request Forgery) Considerations

When using this client in server-side applications, be aware of potential SSRF risks:

- **Validate User Input**: Always validate and sanitize user-provided URLs before passing to the client
- **Consider Allowlisting**: For production use, consider allowlisting destination hosts
- **Timeout Awareness**: Timeouts apply per-request, not per-connection. Multiple retry attempts could extend total execution time.

**Example - Safe URL Validation**:

```python
from urllib.parse import urlparse

ALLOWED_HOSTS = ["api.example.com", "api-staging.example.com"]

def is_safe_url(url: str) -> bool:
    """Validate URL is safe for use"""
    parsed = urlparse(url)
    return parsed.netloc in ALLOWED_HOSTS

# Use validation before creating client
if is_safe_url(user_provided_url):
    client = APIClient(base_url=user_provided_url)
else:
    raise ValueError("Untrusted URL rejected")
```

### Input Validation

The client validates all inputs to prevent common security issues:

**URL Validation:**

```python
# Only HTTP/HTTPS URLs allowed
client = APIClient(base_url="https://api.example.com")  # ✓ Valid
client = APIClient(base_url="file:///etc/passwd")       # ✗ Raises ValueError
```

**Header Validation:**

```python
# Headers must be strings
client.get("/resource", headers={"X-Custom": "value"})  # ✓ Valid
client.get("/resource", headers={"X-Custom": 123})      # ✗ Raises ValueError
```

**Parameter Validation:**

```python
# Parameters must be strings or convertible to strings
client.get("/resource", params={"page": 1})           # ✓ Valid
client.get("/resource", params={"page": [1, 2, 3]})  # ✗ Raises ValueError
```

### Credential Protection

**Error messages are sanitized** to prevent credential leakage:

```python
# Credentials in headers are not logged or included in error messages
client = APIClient(
    base_url="https://api.example.com",
    default_headers={"Authorization": "Bearer secret-token"}
)

try:
    response = client.get("/resource")
except Exception as e:
    # Error message will NOT contain "secret-token"
    print(e)
```

**Best practices:**

- Store credentials in environment variables
- Never hardcode credentials in source code
- Use separate credentials for development/production
- Rotate credentials regularly

### Rate Limit Security Bounds

```python
# Prevent malicious APIs from forcing long waits
rate_limit_config = RateLimitConfig(
    max_wait_time=300.0,      # Maximum 5 minutes
    respect_retry_after=True
)

# Limit retry attempts to prevent resource exhaustion
retry_config = RetryConfig(
    max_retries=3,            # Maximum 3 retries
    max_delay=60.0            # Maximum 60 seconds between retries
)
```

## Logging

### Default Logging

The client uses Python's standard logging module:

```python
import logging
from amplihack.utils.api_client import APIClient

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

client = APIClient(base_url="https://api.example.com")
response = client.get("/resource")
# Logs: Request method, URL, status code, response time
```

### Log Levels

**INFO level logs:**

- Request initiated (method, URL)
- Response received (status code, elapsed time)
- Rate limit encountered (wait time)
- Retry attempts (attempt number, delay)

**DEBUG level logs:**

- Request headers (sanitized)
- Request parameters
- Response headers
- Response body (truncated)

**WARNING level logs:**

- SSL verification disabled
- Rate limit approaching max wait time
- Retry nearing max attempts

**ERROR level logs:**

- Request failures
- HTTP error responses
- Retry exhausted

### Custom Logging

```python
import logging
from amplihack.utils.api_client import APIClient

# Configure custom logger
logger = logging.getLogger("my_app.api_client")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("api_client.log")
handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
))
logger.addHandler(handler)

# Client uses your logger
client = APIClient(
    base_url="https://api.example.com",
    logger=logger
)
```

### Disable Logging

```python
import logging
from amplihack.utils.api_client import APIClient

# Disable logging
logging.getLogger("amplihack.utils.api_client").setLevel(logging.CRITICAL)

client = APIClient(base_url="https://api.example.com")
```

## API Reference

### APIClient

**Constructor:**

```python
APIClient(
    base_url: str,
    timeout: float = 30.0,
    verify_ssl: bool = True,
    default_headers: Optional[Dict[str, str]] = None,
    retry_config: Optional[RetryConfig] = None,
    rate_limit_config: Optional[RateLimitConfig] = None,
    logger: Optional[logging.Logger] = None
)
```

**Methods:**

```python
def get(
    self,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> APIResponse

def post(
    self,
    path: str,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> APIResponse

def put(
    self,
    path: str,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> APIResponse

def delete(
    self,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None
) -> APIResponse

def execute(self, request: APIRequest) -> APIResponse
```

### RetryConfig

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retry_on_status: List[int] = field(default_factory=lambda: [500, 502, 503, 504])
```

### RateLimitConfig

```python
@dataclass
class RateLimitConfig:
    max_wait_time: float = 300.0
    respect_retry_after: bool = True
    default_backoff: float = 60.0
```

### APIRequest

```python
@dataclass
class APIRequest:
    method: str
    url: str
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    json: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
```

### APIResponse

```python
@dataclass
class APIResponse:
    status_code: int
    headers: Dict[str, str]
    data: Union[Dict, List, str, None]
    text: str
    elapsed_time: float
```

### Exceptions

```python
class APIClientError(Exception):
    """Base exception for API client errors"""
    pass

class RequestError(APIClientError):
    """Request construction or network errors"""
    pass

class HTTPError(APIClientError):
    """HTTP error responses (4xx, 5xx)"""
    def __init__(self, status_code: int, message: str, response_data: Any = None)

class RateLimitError(HTTPError):
    """Rate limit exceeded (HTTP 429)"""
    def __init__(self, wait_time: float, retry_after: Optional[str] = None)

class RetryExhaustedError(APIClientError):
    """All retry attempts failed"""
    def __init__(self, attempts: int, last_error: Exception)
```

## Testing

### Unit Testing with Mock Server

The API client is designed to be easily testable using mock servers:

```python
import pytest
from unittest.mock import Mock, patch
from amplihack.utils.api_client import APIClient, HTTPError

def test_successful_get_request():
    """Test successful GET request"""
    client = APIClient(base_url="https://api.example.com")

    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "name": "Alice"}
        mock_response.text = '{"id": 123, "name": "Alice"}'
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.elapsed.total_seconds.return_value = 0.123
        mock_get.return_value = mock_response

        response = client.get("/users/123")

        assert response.status_code == 200
        assert response.data == {"id": 123, "name": "Alice"}
        assert response.elapsed_time == 0.123

def test_http_error_handling():
    """Test HTTP error handling"""
    client = APIClient(base_url="https://api.example.com")

    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status.side_effect = HTTPError(404, "Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(HTTPError) as exc_info:
            client.get("/users/999")

        assert exc_info.value.status_code == 404
```

### Integration Testing

```python
import pytest
from amplihack.utils.api_client import APIClient, RetryConfig, RateLimitConfig

@pytest.mark.integration
def test_real_api_endpoint():
    """Test against real API endpoint (requires network)"""
    client = APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        retry_config=RetryConfig(max_retries=2),
        rate_limit_config=RateLimitConfig(max_wait_time=60.0)
    )

    # Test GET
    response = client.get("/users/1")
    assert response.status_code == 200
    assert "name" in response.data

    # Test POST
    response = client.post(
        "/users",
        json={"name": "Test User", "email": "test@example.com"}
    )
    assert response.status_code in [200, 201]
```

### Testing Retry Logic

```python
from amplihack.utils.api_client import APIClient, RetryExhaustedError, RetryConfig

def test_retry_exhausted():
    """Test retry exhaustion"""
    client = APIClient(
        base_url="https://api.example.com",
        retry_config=RetryConfig(max_retries=2, base_delay=0.1)
    )

    with patch("requests.get") as mock_get:
        # All attempts fail
        mock_get.side_effect = ConnectionError("Connection failed")

        with pytest.raises(RetryExhaustedError) as exc_info:
            client.get("/resource")

        assert exc_info.value.attempts == 2
```

### Testing Rate Limiting

```python
from amplihack.utils.api_client import APIClient, RateLimitError, RateLimitConfig

def test_rate_limit_handling():
    """Test rate limit handling"""
    client = APIClient(
        base_url="https://api.example.com",
        rate_limit_config=RateLimitConfig(
            max_wait_time=5.0,  # Short timeout for testing
            respect_retry_after=True
        )
    )

    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "10"}  # Exceeds max_wait_time
        mock_get.return_value = mock_response

        with pytest.raises(RateLimitError) as exc_info:
            client.get("/resource")

        assert exc_info.value.wait_time == 10.0
        assert exc_info.value.retry_after == "10"
```

## Examples

### Complete Working Example

See [examples/basic_usage.py](examples/basic_usage.py) for a comprehensive working example demonstrating:

- GET/POST/PUT/DELETE requests
- Custom retry configuration
- Rate limiting configuration
- Error handling with custom exceptions
- Authentication setup
- Logging configuration

### Advanced Patterns

**Pagination handling:**

```python
def fetch_all_pages(client, endpoint, page_size=100):
    """Fetch all pages from a paginated endpoint"""
    page = 1
    all_items = []

    while True:
        response = client.get(endpoint, params={"page": page, "limit": page_size})
        items = response.data.get("items", [])

        if not items:
            break

        all_items.extend(items)
        page += 1

    return all_items

# Usage
client = APIClient(base_url="https://api.example.com")
all_users = fetch_all_pages(client, "/users")
```

**Batch operations with rate limiting:**

```python
from amplihack.utils.api_client import APIClient, RateLimitError
import time

def batch_create_users(client, users):
    """Create multiple users with rate limit handling"""
    results = []

    for user in users:
        while True:
            try:
                response = client.post("/users", json=user)
                results.append({"success": True, "data": response.data})
                break
            except RateLimitError as e:
                print(f"Rate limited. Waiting {e.wait_time}s...")
                time.sleep(e.wait_time)
                # Retry after waiting
                continue
            except Exception as e:
                results.append({"success": False, "error": str(e)})
                break

    return results
```

**Circuit breaker pattern:**

```python
from amplihack.utils.api_client import APIClient, HTTPError
import time

class CircuitBreaker:
    def __init__(self, client, failure_threshold=5, timeout=60):
        self.client = client
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False

    def call(self, method, *args, **kwargs):
        # Check if circuit is open
        if self.is_open:
            if time.time() - self.last_failure_time > self.timeout:
                self.is_open = False
                self.failures = 0
            else:
                raise Exception("Circuit breaker is open")

        try:
            response = getattr(self.client, method)(*args, **kwargs)
            self.failures = 0  # Reset on success
            return response
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.is_open = True

            raise

# Usage
client = APIClient(base_url="https://api.example.com")
breaker = CircuitBreaker(client, failure_threshold=5, timeout=60)

response = breaker.call("get", "/resource")
```

## Troubleshooting

### Common Issues

**SSL Certificate Errors:**

```python
# Temporary fix (not recommended for production)
client = APIClient(base_url="https://api.example.com", verify_ssl=False)

# Better: Update SSL certificates
# On Ubuntu/Debian: sudo apt-get install ca-certificates
# On macOS: Install certifi package
```

**Timeout Errors:**

```python
# Increase timeout for slow APIs
client = APIClient(
    base_url="https://api.example.com",
    timeout=60.0  # 60 seconds
)
```

**Rate Limiting Too Aggressive:**

```python
# Adjust rate limit configuration
rate_limit_config = RateLimitConfig(
    max_wait_time=600.0,      # Allow longer waits
    default_backoff=120.0     # Wait longer between requests
)
```

**Retry Logic Too Aggressive:**

```python
# Reduce retries for faster failure
retry_config = RetryConfig(
    max_retries=1,
    base_delay=0.5
)
```

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Now all API calls will be logged in detail
```

## Related Documentation

- [amplihack.utils Documentation](../README.md)
- [Error Handling Patterns](../../docs/patterns/error-handling.md)
- [Testing Strategies](../../docs/testing/integration-tests.md)

## Support

For issues, questions, or contributions:

- GitHub Issues: https://github.com/yourusername/amplihack/issues
- Documentation: https://amplihack.readthedocs.io
- Examples: See [examples/](examples/) directory

---

**Last Updated**: 2025-11-30
**Version**: 1.0.0
**Status**: Production Ready
