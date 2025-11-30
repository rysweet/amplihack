# REST API Client - API Reference

Complete reference documentation for all classes, methods, and configuration options.

## Table of Contents

- [Core Classes](#core-classes)
- [Configuration Classes](#configuration-classes)
- [Exception Classes](#exception-classes)
- [Utility Classes](#utility-classes)
- [Type Definitions](#type-definitions)

## Core Classes

### APIClient

**Module**: `client.py`
**Import**: `from rest_api_client import APIClient`

Main client class for making HTTP requests.

```python
class APIClient:
    """HTTP client with automatic retry logic and rate limiting.

    Args:
        base_url: Base URL for all requests (must be HTTPS)
        timeout: Default timeout in seconds (default: 30)
        max_retries: Maximum number of retry attempts (default: 3)
        headers: Default headers for all requests
        auth: Tuple of (username, password) for basic auth
        retry_config: Custom retry configuration
        rate_limit_config: Custom rate limiting configuration
        log_level: Logging level (default: logging.INFO)
        log_sanitize_headers: Headers to redact in logs
        log_sanitize_params: Query parameters to redact in logs
        verify_ssl: Whether to verify SSL certificates (default: True)
        proxy: Proxy URL for requests
        request_signer: Optional request signer for HMAC/JWT signing

    Raises:
        ValueError: If base_url is not HTTPS
    """
```

#### Methods

##### get(path, \*\*kwargs)

```python
def get(self, path: str, **kwargs) -> Response:
    """Perform GET request.

    Args:
        path: API endpoint path (relative to base_url)
        params: Query parameters as dict
        headers: Additional headers to merge with defaults
        timeout: Override default timeout for this request

    Returns:
        Response object with status_code, headers, data, elapsed_time

    Raises:
        APIError: Base exception for all API errors
        NetworkError: Connection or network issues
        TimeoutError: Request timeout
        AuthenticationError: 401/403 responses
        RateLimitError: 429 response
        ClientError: Other 4xx responses
        ServerError: 5xx responses

    Example:
        response = client.get("/users", params={"page": 1})
    """
```

##### post(path, \*\*kwargs)

```python
def post(self, path: str, **kwargs) -> Response:
    """Perform POST request.

    Args:
        path: API endpoint path
        json: JSON-serializable data for request body
        data: Form data or raw string for request body
        files: Files to upload as multipart/form-data
        headers: Additional headers
        timeout: Override default timeout

    Returns:
        Response object

    Example:
        response = client.post("/users", json={"name": "John"})
    """
```

##### put(path, \*\*kwargs)

```python
def put(self, path: str, **kwargs) -> Response:
    """Perform PUT request.

    Args:
        path: API endpoint path
        json: JSON data for request body
        data: Form data or raw string
        headers: Additional headers
        timeout: Override default timeout

    Returns:
        Response object

    Example:
        response = client.put("/users/123", json={"name": "Jane"})
    """
```

##### patch(path, \*\*kwargs)

```python
def patch(self, path: str, **kwargs) -> Response:
    """Perform PATCH request.

    Args:
        path: API endpoint path
        json: JSON data for partial updates
        headers: Additional headers
        timeout: Override default timeout

    Returns:
        Response object

    Example:
        response = client.patch("/users/123", json={"email": "new@example.com"})
    """
```

##### delete(path, \*\*kwargs)

```python
def delete(self, path: str, **kwargs) -> Response:
    """Perform DELETE request.

    Args:
        path: API endpoint path
        headers: Additional headers
        timeout: Override default timeout

    Returns:
        Response object

    Example:
        response = client.delete("/users/123")
    """
```

##### execute(request)

```python
def execute(self, request: Request) -> Response:
    """Execute a Request object.

    Args:
        request: Request object with method, url, headers, body

    Returns:
        Response object

    Example:
        request = Request(method="GET", url="/users")
        response = client.execute(request)
    """
```

##### session()

```python
def session(self) -> ContextManager['SessionClient']:
    """Create a session for connection pooling.

    Returns:
        Context manager yielding SessionClient

    Example:
        with client.session() as session:
            for i in range(100):
                session.get(f"/users/{i}")
    """
```

### Request

**Module**: `models.py`
**Import**: `from rest_api_client import Request`

Dataclass representing an HTTP request.

```python
@dataclass
class Request:
    """HTTP request representation.

    Attributes:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        url: Full URL or path relative to base_url
        headers: Request headers as dict
        params: Query parameters as dict
        json: JSON-serializable data for body
        data: Raw data or form data for body
        files: Files for multipart upload
        timeout: Request timeout in seconds
        metadata: Optional metadata dict for tracking
        correlation_id: Optional request correlation ID
    """
```

### Response

**Module**: `models.py`
**Import**: `from rest_api_client import Response`

Dataclass representing an HTTP response.

```python
@dataclass
class Response:
    """HTTP response representation.

    Attributes:
        status_code: HTTP status code
        headers: Response headers as dict
        data: Parsed response body (JSON or text)
        raw: Raw response bytes
        elapsed_time: Request duration in seconds
        request: Original Request object
        retries: Number of retry attempts made
        rate_limit_info: RateLimitInfo if applicable
    """
```

#### Methods

##### json()

```python
def json(self) -> Any:
    """Parse response as JSON.

    Returns:
        Parsed JSON data

    Raises:
        ValueError: If response is not valid JSON
    """
```

##### text()

```python
def text(self) -> str:
    """Get response as text.

    Returns:
        Response body as string
    """
```

##### raise_for_status()

```python
def raise_for_status(self) -> None:
    """Raise exception if status indicates error.

    Raises:
        Appropriate APIError subclass based on status code
    """
```

## Configuration Classes

### RetryConfig

**Module**: `config.py`
**Import**: `from rest_api_client import RetryConfig`

Configuration for retry behavior.

```python
@dataclass
class RetryConfig:
    """Retry configuration.

    Attributes:
        max_attempts: Maximum retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2)
        jitter: Add random jitter to delays (default: True)
        retry_on_status: Status codes triggering retry (default: [408, 429, 500, 502, 503, 504])
        retry_on_exceptions: Exceptions triggering retry (default: [ConnectionError, TimeoutError])

    Example:
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            exponential_base=3
        )
    """
```

### RateLimitConfig

**Module**: `config.py`
**Import**: `from rest_api_client import RateLimitConfig`

Configuration for rate limiting.

```python
@dataclass
class RateLimitConfig:
    """Rate limiting configuration.

    Attributes:
        max_requests_per_second: Max requests per second (default: None)
        max_requests_per_minute: Max requests per minute (default: None)
        max_requests_per_hour: Max requests per hour (default: None)
        respect_retry_after: Honor Retry-After headers (default: True)
        backoff_factor: Multiplier for backoff on rate limit (default: 1.5)

    Example:
        config = RateLimitConfig(
            max_requests_per_second=10,
            respect_retry_after=True
        )
    """
```

### RateLimitInfo

**Module**: `rate_limiter.py`
**Import**: `from rest_api_client import RateLimitInfo`

Information about current rate limit status.

```python
@dataclass
class RateLimitInfo:
    """Rate limit information from response.

    Attributes:
        limit: Maximum requests allowed
        remaining: Requests remaining in window
        reset_at: Timestamp when limit resets
        retry_after: Seconds to wait before retry
    """
```

## Exception Classes

**Module**: `exceptions.py`
**Import**: `from rest_api_client import APIError, NetworkError, ...`

### Exception Hierarchy

```
APIError (base exception)
├── NetworkError (connection issues)
│   ├── ConnectionError
│   ├── TimeoutError
│   └── SSLError
├── HTTPError (HTTP status errors)
│   ├── ClientError (4xx)
│   │   ├── BadRequestError (400)
│   │   ├── AuthenticationError (401, 403)
│   │   ├── NotFoundError (404)
│   │   ├── ConflictError (409)
│   │   └── RateLimitError (429)
│   └── ServerError (5xx)
│       ├── InternalServerError (500)
│       ├── BadGatewayError (502)
│       ├── ServiceUnavailableError (503)
│       └── GatewayTimeoutError (504)
└── ValidationError (client-side validation)
```

### APIError

Base exception for all API-related errors.

```python
class APIError(Exception):
    """Base exception for API errors.

    Attributes:
        message: Error message
        request: Request that caused the error
        response: Response if available
        cause: Original exception if wrapped
    """
```

### NetworkError

Network and connection errors.

```python
class NetworkError(APIError):
    """Network-related errors.

    Attributes:
        message: Error description
        request: Failed request
        cause: Underlying network exception
    """
```

### TimeoutError

Request timeout errors.

```python
class TimeoutError(NetworkError):
    """Request timeout error.

    Attributes:
        timeout: Timeout value in seconds
        request: Timed out request
    """
```

### AuthenticationError

Authentication and authorization errors.

```python
class AuthenticationError(ClientError):
    """Authentication/authorization error (401, 403).

    Attributes:
        status_code: 401 or 403
        message: Error message from server
        response: Full response object
    """
```

### RateLimitError

Rate limiting errors.

```python
class RateLimitError(ClientError):
    """Rate limit exceeded (429).

    Attributes:
        retry_after: Seconds to wait before retry
        limit_info: RateLimitInfo if available
        response: Full response object
    """
```

## Utility Classes

### RequestSigner

**Module**: `auth.py`
**Import**: `from rest_api_client import RequestSigner`

Signs requests for authentication.

```python
class RequestSigner:
    """Sign requests with HMAC or JWT.

    Args:
        secret_key: Secret key for signing
        algorithm: Signing algorithm (default: "HS256")

    Methods:
        sign(request: Request) -> Request:
            Add signature headers to request
    """
```

### MockServer

**Module**: `testing/mock_server.py`
**Import**: `from rest_api_client import MockServer`

Test server for integration testing.

```python
class MockServer:
    """Mock HTTP server for testing.

    Args:
        port: Server port (default: random free port)
        host: Server host (default: "localhost")

    Methods:
        add_response(method, path, status, json=None, text=None, headers=None)
        add_response_sequence(method, path, responses)
        start()
        stop()
        request_count(path) -> int
        get_requests(path) -> List[Request]

    Example:
        server = MockServer()
        server.add_response("GET", "/test", 200, json={"ok": True})
        server.start()
        # ... run tests ...
        server.stop()
    """
```

### SessionClient

**Module**: `session.py`
**Import**: Created via `client.session()` context manager

Client with connection pooling.

```python
class SessionClient:
    """API client with connection pooling.

    Inherits all methods from APIClient.
    Maintains persistent connections for performance.

    Note: Created via client.session() context manager.
    """
```

## Type Definitions

### Type Aliases

```python
# HTTP methods
HTTPMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

# Headers type
Headers = Dict[str, str]

# Query parameters
Params = Dict[str, Union[str, int, float, bool, List[str]]]

# JSON data
JSONData = Union[Dict[str, Any], List[Any], str, int, float, bool, None]

# Request body
RequestBody = Union[JSONData, bytes, str, IO[bytes]]

# Timeout
Timeout = Union[float, Tuple[float, float]]  # (connect_timeout, read_timeout)
```

### Protocols

```python
class Retryable(Protocol):
    """Protocol for retryable operations."""

    def should_retry(self, response: Response) -> bool:
        """Determine if request should be retried."""
        ...

    def get_retry_delay(self, attempt: int) -> float:
        """Calculate delay before next retry."""
        ...
```

## Constants

```python
# Default configuration values
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_STATUSES = [408, 429, 500, 502, 503, 504]
DEFAULT_USER_AGENT = "amplihack-rest-client/1.0.0"

# Rate limit headers
RATE_LIMIT_HEADERS = {
    "limit": ["X-RateLimit-Limit", "X-Rate-Limit-Limit"],
    "remaining": ["X-RateLimit-Remaining", "X-Rate-Limit-Remaining"],
    "reset": ["X-RateLimit-Reset", "X-Rate-Limit-Reset"],
    "retry_after": ["Retry-After", "X-Retry-After"]
}

# Status code categories
INFORMATIONAL = range(100, 200)
SUCCESSFUL = range(200, 300)
REDIRECTION = range(300, 400)
CLIENT_ERROR = range(400, 500)
SERVER_ERROR = range(500, 600)
```

## Environment Variables

```python
# Recognized environment variables
REST_CLIENT_BASE_URL      # Default base URL
REST_CLIENT_TIMEOUT        # Default timeout (seconds)
REST_CLIENT_MAX_RETRIES    # Default max retries
REST_CLIENT_LOG_LEVEL      # Logging level
REST_CLIENT_SSL_VERIFY     # SSL verification (true/false)
REST_CLIENT_PROXY          # Proxy URL
REST_CLIENT_API_KEY        # Default API key
REST_CLIENT_AUTH_TOKEN     # Default auth token
```

## Thread Safety

All classes are thread-safe except:

- `SessionClient` - Use one per thread
- `MockServer` - Not thread-safe for configuration changes

For multi-threaded applications:

```python
import threading

# Thread-local storage for sessions
local = threading.local()

def get_session():
    if not hasattr(local, 'session'):
        local.session = client.session().__enter__()
    return local.session
```

## Async Support

For async/await support, use the async variant:

```python
from rest_api_client.async_client import AsyncAPIClient

async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        response = await client.get("/users")
        print(response.data)
```

See [Async API Reference](./async_api_reference.md) for complete async documentation.

## Architecture & Module Design

For complete information about the modular brick architecture and how modules are organized:

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Internal architecture and brick philosophy
- Each module can be regenerated independently
- Public interfaces are stable connection points
- Tests verify contracts, not implementations
