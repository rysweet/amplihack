# API Reference

Complete API reference for the REST API Client library.

## APIClient

The main client class for making HTTP requests.

### Class Definition

```python
class APIClient:
    """HTTP client with retry logic, rate limiting, and error handling."""

    def __init__(
        self,
        base_url: str = None,
        config: APIConfig = None,
        retry_config: RetryConfig = None,
        headers: dict = None,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_calls: int = None,
        rate_limit_period: int = 60,
        verify_ssl: bool = True
    ):
        """
        Initialize the API client.

        Args:
            base_url: Base URL for all requests
            config: APIConfig object with all settings
            retry_config: RetryConfig object for retry behavior
            headers: Default headers for all requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            rate_limit_calls: Maximum calls per period
            rate_limit_period: Rate limit period in seconds
            verify_ssl: Whether to verify SSL certificates
        """
```

### Methods

#### HTTP Methods

```python
def get(
    self,
    endpoint: str,
    params: dict = None,
    headers: dict = None,
    **kwargs
) -> Response:
    """
    Make a GET request.

    Args:
        endpoint: API endpoint path
        params: Query parameters
        headers: Additional headers
        **kwargs: Additional request options

    Returns:
        Response object with data, status_code, and headers

    Raises:
        APIError: On API errors
        NetworkError: On network issues
        TimeoutError: On request timeout
    """

def post(
    self,
    endpoint: str,
    json: dict = None,
    data: any = None,
    files: dict = None,
    headers: dict = None,
    **kwargs
) -> Response:
    """
    Make a POST request.

    Args:
        endpoint: API endpoint path
        json: JSON data to send
        data: Form data to send
        files: Files to upload
        headers: Additional headers
        **kwargs: Additional request options

    Returns:
        Response object
    """

def put(
    self,
    endpoint: str,
    json: dict = None,
    data: any = None,
    headers: dict = None,
    **kwargs
) -> Response:
    """
    Make a PUT request.

    Args:
        endpoint: API endpoint path
        json: JSON data to send
        data: Form data to send
        headers: Additional headers
        **kwargs: Additional request options

    Returns:
        Response object
    """

def patch(
    self,
    endpoint: str,
    json: dict = None,
    data: any = None,
    headers: dict = None,
    **kwargs
) -> Response:
    """
    Make a PATCH request.

    Args:
        endpoint: API endpoint path
        json: JSON data to send
        data: Form data to send
        headers: Additional headers
        **kwargs: Additional request options

    Returns:
        Response object
    """

def delete(
    self,
    endpoint: str,
    headers: dict = None,
    **kwargs
) -> Response:
    """
    Make a DELETE request.

    Args:
        endpoint: API endpoint path
        headers: Additional headers
        **kwargs: Additional request options

    Returns:
        Response object
    """

def head(
    self,
    endpoint: str,
    headers: dict = None,
    **kwargs
) -> Response:
    """
    Make a HEAD request.

    Args:
        endpoint: API endpoint path
        headers: Additional headers
        **kwargs: Additional request options

    Returns:
        Response object (without body)
    """

def options(
    self,
    endpoint: str,
    headers: dict = None,
    **kwargs
) -> Response:
    """
    Make an OPTIONS request.

    Args:
        endpoint: API endpoint path
        headers: Additional headers
        **kwargs: Additional request options

    Returns:
        Response object
    """
```

#### Utility Methods

```python
def prepare_request(
    self,
    method: str,
    endpoint: str,
    **kwargs
) -> Request:
    """
    Prepare a request without sending it.

    Args:
        method: HTTP method
        endpoint: API endpoint
        **kwargs: Request parameters

    Returns:
        Request object ready to be sent
    """

def send(
    self,
    request: Request
) -> Response:
    """
    Send a prepared request.

    Args:
        request: Request object to send

    Returns:
        Response object
    """

def close(self):
    """Close the client and release resources."""

def __enter__(self):
    """Context manager entry."""
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    """Context manager exit."""
    self.close()
```

## AsyncAPIClient

Asynchronous version of the API client.

```python
class AsyncAPIClient:
    """Async HTTP client with retry logic and rate limiting."""

    async def get(
        self,
        endpoint: str,
        params: dict = None,
        headers: dict = None,
        **kwargs
    ) -> Response:
        """Async GET request."""

    async def post(
        self,
        endpoint: str,
        json: dict = None,
        data: any = None,
        files: dict = None,
        headers: dict = None,
        **kwargs
    ) -> Response:
        """Async POST request."""

    # Similar methods for PUT, PATCH, DELETE, HEAD, OPTIONS

    async def close(self):
        """Close async client."""

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
```

## Configuration Classes

### APIConfig

```python
@dataclass
class APIConfig:
    """API client configuration."""

    base_url: str
    timeout: int = 30
    max_retries: int = 3
    rate_limit_calls: Optional[int] = None
    rate_limit_period: int = 60
    headers: dict = field(default_factory=dict)
    verify_ssl: bool = True
    proxy: Optional[str] = None
    proxy_auth: Optional[tuple] = None

    def validate(self):
        """Validate configuration."""
        if not self.base_url:
            raise ValueError("base_url is required")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
```

### RetryConfig

```python
@dataclass
class RetryConfig:
    """Retry behavior configuration."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retry_on_statuses: List[int] = field(
        default_factory=lambda: [429, 500, 502, 503, 504]
    )
    retry_on_exceptions: List[Type[Exception]] = field(
        default_factory=lambda: [ConnectionError, TimeoutError]
    )
    jitter: bool = False
    jitter_range: float = 0.3

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt.

        Args:
            attempt: Attempt number (0-based)

        Returns:
            Delay in seconds
        """
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            import random
            jitter = random.uniform(-self.jitter_range, self.jitter_range)
            delay *= (1 + jitter)

        return delay
```

## Model Classes

### Request

```python
@dataclass
class Request:
    """HTTP request representation."""

    method: str
    url: str
    headers: dict = field(default_factory=dict)
    params: Optional[dict] = None
    json: Optional[dict] = None
    data: Optional[any] = None
    files: Optional[dict] = None
    timeout: int = 30

    def to_dict(self) -> dict:
        """Convert to dictionary for requests library."""
        return {
            'method': self.method,
            'url': self.url,
            'headers': self.headers,
            'params': self.params,
            'json': self.json,
            'data': self.data,
            'files': self.files,
            'timeout': self.timeout
        }
```

### Response

```python
@dataclass
class Response:
    """HTTP response representation."""

    status_code: int
    headers: dict
    data: Optional[any] = None
    text: Optional[str] = None
    elapsed: Optional[float] = None
    request: Optional[Request] = None

    @property
    def ok(self) -> bool:
        """Check if response is successful (2xx)."""
        return 200 <= self.status_code < 300

    @property
    def is_error(self) -> bool:
        """Check if response is an error (4xx or 5xx)."""
        return self.status_code >= 400

    @property
    def is_client_error(self) -> bool:
        """Check if response is a client error (4xx)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response is a server error (5xx)."""
        return self.status_code >= 500

    def json(self) -> any:
        """Parse response as JSON."""
        if isinstance(self.data, str):
            import json
            return json.loads(self.data)
        return self.data

    def raise_for_status(self):
        """Raise exception if response is an error."""
        if self.is_error:
            from rest_api_client.exceptions import APIError
            raise APIError(
                f"HTTP {self.status_code}",
                status_code=self.status_code,
                response=self
            )
```

## Rate Limiter

### RateLimiter

```python
class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        calls: int,
        period: int,
        burst: int = None
    ):
        """
        Initialize rate limiter.

        Args:
            calls: Maximum calls per period
            period: Period in seconds
            burst: Maximum burst size (defaults to calls)
        """
        self.calls = calls
        self.period = period
        self.burst = burst or calls
        self.tokens = self.burst
        self.last_refill = time.time()
        self.lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, blocking if necessary.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            Time waited in seconds
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0

            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = (tokens_needed / self.calls) * self.period

            time.sleep(wait_time)
            self._refill()
            self.tokens -= tokens
            return wait_time

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        new_tokens = (elapsed / self.period) * self.calls

        self.tokens = min(self.burst, self.tokens + new_tokens)
        self.last_refill = now

    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        with self.lock:
            self._refill()
            return self.tokens
```

## Retry Strategy

### RetryStrategy

```python
class RetryStrategy:
    """Base class for retry strategies."""

    def __init__(self, max_attempts: int = 3):
        """
        Initialize retry strategy.

        Args:
            max_attempts: Maximum retry attempts
        """
        self.max_attempts = max_attempts

    def should_retry(
        self,
        response: Response,
        exception: Exception,
        attempt: int
    ) -> bool:
        """
        Determine if request should be retried.

        Args:
            response: Response object (may be None)
            exception: Exception that occurred (may be None)
            attempt: Current attempt number

        Returns:
            True if should retry, False otherwise
        """
        raise NotImplementedError

    def get_delay(self, attempt: int) -> float:
        """
        Get delay before next retry.

        Args:
            attempt: Current attempt number

        Returns:
            Delay in seconds
        """
        raise NotImplementedError
```

## Exception Classes

The library provides a comprehensive exception hierarchy for handling API errors:

### Base Exception

- **APIError**: Base exception for all API-related errors

### Network and Connectivity

- **NetworkError**: Network connectivity issues
- **TimeoutError**: Request timeout exceeded

### Authentication and Authorization

- **AuthenticationError**: 401 Unauthorized responses
- **AuthorizationError**: 403 Forbidden responses

### Client Errors

- **ValidationError**: 400 Bad Request with validation errors
- **RateLimitError**: 429 Too Many Requests

### Server Errors

- **ServerError**: 5xx server error responses

See [Exception Types Reference](./exceptions.md) for complete exception documentation with usage examples.

## Utility Functions

### URL Building

```python
from rest_api_client.utils import urljoin_safe

# Safely join URL parts
url = urljoin_safe("https://api.example.com", "/v1/", "/users/", "123")
# Result: "https://api.example.com/v1/users/123"
```

### Header Utilities

```python
from rest_api_client.utils import merge_headers, case_insensitive_dict

# Merge headers with case-insensitive handling
base_headers = {"Content-Type": "application/json"}
request_headers = {"Authorization": "Bearer token"}
merged = merge_headers(base_headers, request_headers)
# Result: {"Content-Type": "application/json", "Authorization": "Bearer token"}

# Case-insensitive header dictionary
headers = case_insensitive_dict({
    "content-type": "application/json"
})
assert headers["Content-Type"] == "application/json"
```

### Response Parsing

```python
from rest_api_client.utils import parse_json_safe, extract_error_message

# Safe JSON parsing with fallback
data = parse_json_safe('{"valid": "json"}')  # Returns dict
data = parse_json_safe('invalid json')  # Returns None

# Extract error message from various response formats
message = extract_error_message(response)
# Handles: {"error": "..."}, {"message": "..."}, {"detail": "..."}, etc.
```

### Retry Helpers

```python
from rest_api_client.utils import is_retryable_error, calculate_retry_after

# Check if error should be retried
should_retry = is_retryable_error(exception)

# Extract retry-after from headers
retry_after = calculate_retry_after(response.headers)
# Handles both seconds and HTTP-date formats
```

## Type Definitions

The library provides comprehensive type hints for better IDE support and type checking:

### Type Aliases

```python
from typing import Dict, Any, Optional, Union, List
from rest_api_client.typing import (
    Headers,
    JSONData,
    QueryParams,
    RequestData,
    ResponseData,
    HTTPMethod,
    StatusCode
)

# Type definitions
Headers = Dict[str, str]
JSONData = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
QueryParams = Dict[str, Union[str, List[str]]]
RequestData = Union[Dict[str, Any], bytes, str]
ResponseData = Union[JSONData, bytes, str]
HTTPMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
StatusCode = int
```

### Protocol Definitions

```python
from typing import Protocol
from rest_api_client.typing import Requestable, Retriable

class Requestable(Protocol):
    """Protocol for objects that can make requests."""
    def request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Response: ...

class Retriable(Protocol):
    """Protocol for retry strategies."""
    def should_retry(
        self,
        response: Optional[Response],
        exception: Optional[Exception],
        attempt: int
    ) -> bool: ...

    def get_delay(self, attempt: int) -> float: ...
```

### Generic Types

```python
from typing import TypeVar, Generic
from rest_api_client.typing import T, ResponseT

T = TypeVar('T')
ResponseT = TypeVar('ResponseT', bound=Response)

class PaginatedResponse(Generic[T]):
    """Generic paginated response container."""
    items: List[T]
    page: int
    total_pages: int
    total_items: int
```

## Usage Examples

### Basic Usage

```python
from rest_api_client import APIClient

# Create client
client = APIClient(base_url="https://api.example.com")

# Make requests
users = client.get("/users")
user = client.post("/users", json={"name": "Alice"})
updated = client.put("/users/1", json={"name": "Alice Smith"})
client.delete("/users/2")
```

### With Configuration

```python
from rest_api_client import APIClient
from rest_api_client.config import APIConfig, RetryConfig

# Configure client
config = APIConfig(
    base_url="https://api.example.com",
    timeout=60,
    headers={"User-Agent": "MyApp/1.0"}
)

retry_config = RetryConfig(
    max_attempts=5,
    exponential_base=2.0
)

# Create configured client
client = APIClient(config=config, retry_config=retry_config)
```

### Context Manager

```python
from rest_api_client import APIClient

# Automatic cleanup with context manager
with APIClient(base_url="https://api.example.com") as client:
    response = client.get("/users")
    print(response.data)
```

### Async Usage

```python
import asyncio
from rest_api_client import AsyncAPIClient

async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        response = await client.get("/users")
        print(response.data)

asyncio.run(main())
```
