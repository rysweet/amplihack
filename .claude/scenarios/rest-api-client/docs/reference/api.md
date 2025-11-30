# API Reference

Complete API documentation for the REST API Client library.

## Contents

- [APIClient](#apiclient)
- [Request/Response Types](#types)
- [Exceptions](#exceptions)
- [Configuration Classes](#configuration)

## APIClient

Main client class for making HTTP requests.

### Constructor

```python
APIClient(
    base_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    verify_ssl: bool = True,
    retry_config: Optional[RetryConfig] = None,
    rate_limit_config: Optional[RateLimitConfig] = None,
    log_level: str = "INFO"
)
```

**Parameters:**

- `base_url` (str): Base URL for all requests
- `headers` (dict): Default headers for all requests
- `timeout` (int): Request timeout in seconds (default: 30)
- `verify_ssl` (bool): Verify SSL certificates (default: True)
- `retry_config` (RetryConfig): Retry configuration
- `rate_limit_config` (RateLimitConfig): Rate limiting configuration
- `log_level` (str): Logging level (default: "INFO")

### Methods

#### get()

```python
def get(self, path: str, params: Optional[Dict] = None, **kwargs) -> Response
```

Performs a GET request.

**Parameters:**

- `path` (str): API endpoint path
- `params` (dict): Query parameters
- `**kwargs`: Additional request options

**Returns:** Response object

**Example:**

```python
client = APIClient(base_url="https://api.example.com")
response = client.get("/users", params={"page": 1, "limit": 10})
users = response.data
```

#### post()

```python
def post(self, path: str, json: Optional[Dict] = None, data: Optional[bytes] = None, **kwargs) -> Response
```

Performs a POST request.

**Parameters:**

- `path` (str): API endpoint path
- `json` (dict): JSON data to send
- `data` (bytes): Raw data to send
- `**kwargs`: Additional request options

**Returns:** Response object

**Example:**

```python
client = APIClient(base_url="https://api.example.com")
response = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
created_user = response.data
```

#### put()

```python
def put(self, path: str, json: Optional[Dict] = None, data: Optional[bytes] = None, **kwargs) -> Response
```

Performs a PUT request.

**Parameters:**

- `path` (str): API endpoint path
- `json` (dict): JSON data to send
- `data` (bytes): Raw data to send
- `**kwargs`: Additional request options

**Returns:** Response object

#### patch()

```python
def patch(self, path: str, json: Optional[Dict] = None, **kwargs) -> Response
```

Performs a PATCH request.

**Parameters:**

- `path` (str): API endpoint path
- `json` (dict): JSON data to send
- `**kwargs`: Additional request options

**Returns:** Response object

#### delete()

```python
def delete(self, path: str, **kwargs) -> Response
```

Performs a DELETE request.

**Parameters:**

- `path` (str): API endpoint path
- `**kwargs`: Additional request options

**Returns:** Response object

**Example:**

```python
client = APIClient(base_url="https://api.example.com")
response = client.delete("/users/123")
assert response.status_code == 204
```

## Types

### Request

```python
@dataclass
class Request:
    method: str
    url: str
    headers: Dict[str, str]
    params: Optional[Dict[str, Any]] = None
    json: Optional[Dict[str, Any]] = None
    data: Optional[bytes] = None
    timeout: int = 30
```

Represents an HTTP request.

### Response

```python
@dataclass
class Response:
    status_code: int
    headers: Dict[str, str]
    data: Optional[Union[Dict, List, str]] = None
    raw: Optional[bytes] = None
    request: Optional[Request] = None
    elapsed_time: float = 0.0
```

Represents an HTTP response.

**Properties:**

- `status_code`: HTTP status code
- `headers`: Response headers
- `data`: Parsed response data (JSON or text)
- `raw`: Raw response bytes
- `request`: Original request object
- `elapsed_time`: Request duration in seconds

**Methods:**

```python
def json(self) -> Union[Dict, List]:
    """Parse response as JSON."""

def text(self) -> str:
    """Get response as text."""

def raise_for_status(self) -> None:
    """Raise exception if status indicates error."""
```

## Exceptions

### APIException

```python
class APIException(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Response] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
```

Base exception for all API errors.

### ConnectionException

```python
class ConnectionException(APIException):
    """Raised when connection to API fails."""
```

### TimeoutException

```python
class TimeoutException(APIException):
    """Raised when request times out."""
```

### RateLimitException

```python
class RateLimitException(APIException):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after
```

Raised when rate limit is exceeded.

**Properties:**

- `retry_after`: Seconds to wait before retrying

### ValidationException

```python
class ValidationException(APIException):
    """Raised when request validation fails."""
```

## Configuration

### RetryConfig

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_factor: float = 2.0
    max_backoff: int = 60
    retry_on_status: List[int] = field(default_factory=lambda: [429, 500, 502, 503, 504])
    retry_on_exception: List[Type[Exception]] = field(default_factory=lambda: [ConnectionException, TimeoutException])
```

Configuration for retry logic.

**Fields:**

- `max_attempts`: Maximum retry attempts (default: 3)
- `backoff_factor`: Exponential backoff multiplier (default: 2.0)
- `max_backoff`: Maximum backoff time in seconds (default: 60)
- `retry_on_status`: Status codes to retry (default: 429, 5xx)
- `retry_on_exception`: Exception types to retry

### RateLimitConfig

```python
@dataclass
class RateLimitConfig:
    requests_per_second: float = 10.0
    burst_size: int = 20
    wait_on_limit: bool = True
```

Configuration for rate limiting.

**Fields:**

- `requests_per_second`: Maximum sustained request rate (default: 10.0)
- `burst_size`: Maximum burst capacity (default: 20)
- `wait_on_limit`: Wait when limit reached vs raise exception (default: True)

### Example Configuration

```python
from rest_api_client import APIClient, RetryConfig, RateLimitConfig

# Custom retry configuration
retry_config = RetryConfig(
    max_attempts=5,
    backoff_factor=3.0,
    retry_on_status=[429, 500, 502, 503]
)

# Custom rate limit configuration
rate_limit_config = RateLimitConfig(
    requests_per_second=100,
    burst_size=200,
    wait_on_limit=False  # Raise exception instead of waiting
)

# Initialize client with custom config
client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config,
    rate_limit_config=rate_limit_config
)
```
