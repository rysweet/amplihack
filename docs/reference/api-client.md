# REST API Client Reference

The amplihack REST API Client provides a robust, async-first HTTP client with enterprise-grade features for reliable API interactions.

## Quick Start

```python
from amplihack.api_client import APIClient

async with APIClient(base_url="https://api.example.com") as client:
    response = await client.get("/users/123")
    user = response.data
```

## Contents

- [Installation](#installation)
- [Core Components](#core-components)
- [APIClient Class](#apiclient-class)
- [Request and Response Models](#request-and-response-models)
- [Exception Hierarchy](#exception-hierarchy)
- [Configuration](#configuration)
- [Advanced Features](#advanced-features)

## Installation

The API client is included with amplihack:

```bash
pip install amplihack
```

## Core Components

### APIClient

The main client class providing async HTTP methods with automatic retry, rate limiting, and error handling.

**Location**: `src/amplihack/api_client/client.py`

### Request Dataclass

Immutable request representation with builder pattern support.

**Location**: `src/amplihack/api_client/models.py`

### Response[T] Generic

Type-safe response wrapper with automatic deserialization.

**Location**: `src/amplihack/api_client/models.py`

### RetryConfig

Configuration for retry behavior and backoff strategies.

**Location**: `src/amplihack/api_client/config.py`

## APIClient Class

### Constructor

```python
APIClient(
    base_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 30.0,
    retry_config: Optional[RetryConfig] = None,
    rate_limit_handler: Optional[RateLimitHandler] = None
)
```

**Parameters:**

- `base_url` (str): Base URL for all requests
- `headers` (Dict[str, str], optional): Default headers for all requests
- `timeout` (float): Request timeout in seconds (default: 30.0)
- `retry_config` (RetryConfig, optional): Custom retry configuration
- `rate_limit_handler` (RateLimitHandler, optional): Custom rate limit handler

### HTTP Methods

#### get()

```python
async def get(
    self,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    response_type: Optional[Type[T]] = None
) -> Response[T]
```

Performs a GET request.

**Parameters:**

- `path`: API endpoint path
- `params`: Query parameters
- `headers`: Request-specific headers
- `response_type`: Expected response type for deserialization

**Returns:** `Response[T]` containing the parsed response

#### post()

```python
async def post(
    self,
    path: str,
    json: Optional[Any] = None,
    data: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    response_type: Optional[Type[T]] = None
) -> Response[T]
```

Performs a POST request.

**Parameters:**

- `path`: API endpoint path
- `json`: JSON body (automatically serialized)
- `data`: Form data or raw body
- `headers`: Request-specific headers
- `response_type`: Expected response type

**Returns:** `Response[T]` containing the parsed response

#### put()

```python
async def put(
    self,
    path: str,
    json: Optional[Any] = None,
    data: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    response_type: Optional[Type[T]] = None
) -> Response[T]
```

Performs a PUT request with same parameters as `post()`.

#### patch()

```python
async def patch(
    self,
    path: str,
    json: Optional[Any] = None,
    data: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    response_type: Optional[Type[T]] = None
) -> Response[T]
```

Performs a PATCH request with same parameters as `post()`.

#### delete()

```python
async def delete(
    self,
    path: str,
    headers: Optional[Dict[str, str]] = None,
    response_type: Optional[Type[T]] = None
) -> Response[T]
```

Performs a DELETE request.

**Parameters:**

- `path`: API endpoint path
- `headers`: Request-specific headers
- `response_type`: Expected response type

**Returns:** `Response[T]` containing the parsed response

## Request and Response Models

### Request Dataclass

```python
@dataclass(frozen=True)
class Request:
    method: str
    url: str
    headers: Dict[str, str]
    params: Optional[Dict[str, Any]]
    json: Optional[Any]
    data: Optional[Any]
    timeout: float
```

Immutable request representation with builder pattern:

```python
request = (
    Request.builder()
    .method("GET")
    .url("https://api.example.com/users")
    .header("Authorization", "Bearer token")
    .param("page", 1)
    .build()
)
```

### Response[T] Generic

```python
@dataclass
class Response[T]:
    status_code: int
    headers: Dict[str, str]
    data: Optional[T]
    raw_text: str
    elapsed: timedelta
    request: Request
```

Type-safe response wrapper:

```python
from typing import List
from amplihack.api_client import Response

@dataclass
class User:
    id: int
    name: str

response: Response[List[User]] = await client.get(
    "/users",
    response_type=List[User]
)
users = response.data  # Type: List[User]
```

## Exception Hierarchy

### Base Exception

```python
class APIError(Exception):
    """Base exception for all API client errors"""
    def __init__(self, message: str, request: Optional[Request] = None):
        self.request = request
        super().__init__(message)
```

### Derived Exceptions

#### NetworkError

Raised for connection failures, timeouts, and DNS errors.

```python
class NetworkError(APIError):
    """Network-level errors (connection, timeout, DNS)"""
```

#### RateLimitError

Raised when rate limits are exceeded (HTTP 429).

```python
class RateLimitError(APIError):
    """Rate limit exceeded (429 response)"""
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        request: Optional[Request] = None
    ):
        self.retry_after = retry_after
        super().__init__(message, request)
```

#### ValidationError

Raised for request validation failures.

```python
class ValidationError(APIError):
    """Request validation error"""
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        request: Optional[Request] = None
    ):
        self.field = field
        super().__init__(message, request)
```

#### HTTPError

Raised for HTTP error responses (4xx, 5xx).

```python
class HTTPError(APIError):
    """HTTP error response (4xx, 5xx)"""
    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: Optional[str] = None,
        request: Optional[Request] = None
    ):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message, request)
```

## Configuration

### RetryConfig

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_statuses: Set[int] = field(
        default_factory=lambda: {429, 502, 503, 504}
    )
```

Configure retry behavior:

```python
from amplihack.api_client import APIClient, RetryConfig

retry_config = RetryConfig(
    max_retries=5,
    initial_delay=0.5,
    max_delay=30.0,
    retry_on_statuses={429, 500, 502, 503, 504}
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)
```

### Rate Limit Configuration

```python
from amplihack.api_client import RateLimitHandler

handler = RateLimitHandler(
    calls_per_second=10,
    burst_size=20,
    respect_retry_after=True
)

client = APIClient(
    base_url="https://api.example.com",
    rate_limit_handler=handler
)
```

## Advanced Features

### Custom Headers

Add headers at multiple levels:

```python
# Client-level (all requests)
client = APIClient(
    base_url="https://api.example.com",
    headers={"X-API-Key": "secret"}
)

# Request-level (single request)
response = await client.get(
    "/users",
    headers={"X-Request-ID": "unique-id"}
)
```

### Logging

The client uses structured logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Logs include:
# - Request details (method, URL, headers)
# - Response status and timing
# - Retry attempts and delays
# - Rate limit handling
```

### Context Manager

Always use the client as a context manager:

```python
async with APIClient(base_url="https://api.example.com") as client:
    # Client session is properly managed
    response = await client.get("/users")
# Session automatically closed
```

### Type Safety

Full type hint support with generics:

```python
from typing import List, TypeVar
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class Product:
    id: int
    name: str
    price: float

# Type-safe response
products: Response[List[Product]] = await client.get(
    "/products",
    response_type=List[Product]
)

# IDE knows products.data is List[Product]
for product in products.data:
    print(f"{product.name}: ${product.price}")
```

## See Also

- [Usage Guide](../howto/api-client-usage.md) - Common usage patterns
- [Configuration Guide](../howto/api-client-config.md) - Detailed configuration
- [Error Handling](../concepts/api-client-errors.md) - Understanding exceptions
