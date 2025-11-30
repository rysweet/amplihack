# API Client Reference

Complete API reference for the api_client module.

## Classes

### APIClient

Main client class for making HTTP requests.

#### Constructor

```python
APIClient(config: ClientConfig)
```

**Parameters:**

- `config` (ClientConfig): Configuration object for the client

**Example:**

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://api.example.com")
client = APIClient(config)
```

#### Methods

##### get

```python
get(endpoint: str, params: dict = None, headers: dict = None) -> Response
```

Perform a GET request.

**Parameters:**

- `endpoint` (str): API endpoint path (e.g., "/users/123")
- `params` (dict, optional): Query parameters
- `headers` (dict, optional): Additional headers

**Returns:**

- Response object

**Raises:**

- `HTTPError`: For HTTP error status codes (4xx, 5xx)
- `APIError`: For connection or other API errors

**Example:**

```python
response = client.get("/users/123", params={"include": "posts"})
user = response.json()
```

##### post

```python
post(endpoint: str, json: dict = None, data: bytes = None, headers: dict = None) -> Response
```

Perform a POST request.

**Parameters:**

- `endpoint` (str): API endpoint path
- `json` (dict, optional): JSON data to send
- `data` (bytes, optional): Raw binary data to send
- `headers` (dict, optional): Additional headers

**Returns:**

- Response object

**Raises:**

- `HTTPError`: For HTTP error status codes
- `APIError`: For connection or other API errors

**Note:** Only one of `json` or `data` should be provided.

**Example:**

```python
response = client.post("/users", json={"name": "John", "email": "john@example.com"})
created_user = response.json()
```

##### put

```python
put(endpoint: str, json: dict = None, data: bytes = None, headers: dict = None) -> Response
```

Perform a PUT request.

**Parameters:**

- `endpoint` (str): API endpoint path
- `json` (dict, optional): JSON data to send
- `data` (bytes, optional): Raw binary data to send
- `headers` (dict, optional): Additional headers

**Returns:**

- Response object

**Raises:**

- `HTTPError`: For HTTP error status codes
- `APIError`: For connection or other API errors

**Example:**

```python
response = client.put("/users/123", json={"name": "Jane"})
updated_user = response.json()
```

##### delete

```python
delete(endpoint: str, headers: dict = None) -> Response
```

Perform a DELETE request.

**Parameters:**

- `endpoint` (str): API endpoint path
- `headers` (dict, optional): Additional headers

**Returns:**

- Response object

**Raises:**

- `HTTPError`: For HTTP error status codes
- `APIError`: For connection or other API errors

**Example:**

```python
response = client.delete("/users/123")
assert response.status_code == 204  # No content
```

### ClientConfig

Configuration class for APIClient.

#### Constructor

```python
ClientConfig(
    base_url: str,
    timeout: float = 30.0,
    max_retries: int = 3,
    api_key: str = None
)
```

**Parameters:**

- `base_url` (str): Base URL for the API (required)
- `timeout` (float): Request timeout in seconds (default: 30.0)
- `max_retries` (int): Maximum retry attempts for 5xx errors (default: 3)
- `api_key` (str, optional): API key for Authorization header

**Example:**

```python
config = ClientConfig(
    base_url="https://api.github.com",
    timeout=60.0,
    max_retries=5,
    api_key="ghp_yourtoken123"
)
```

### Response

Response object returned by all HTTP methods.

#### Attributes

- `status_code` (int): HTTP status code
- `headers` (dict): Response headers
- `content` (bytes): Raw response body

#### Methods

##### text

```python
text(encoding: str = 'utf-8') -> str
```

Get response body as decoded string.

**Parameters:**

- `encoding` (str): Text encoding (default: 'utf-8')

**Returns:**

- Decoded string

**Example:**

```python
html = response.text()
```

##### json

```python
json() -> dict | list
```

Parse response body as JSON.

**Returns:**

- Parsed JSON object (dict or list)

**Raises:**

- `ValueError`: If response is not valid JSON

**Example:**

```python
data = response.json()
```

## Exceptions

### APIError

Base exception for all API-related errors.

```python
class APIError(Exception):
    """Base exception for API errors"""
    pass
```

**Example:**

```python
try:
    response = client.get("/endpoint")
except APIError as e:
    print(f"API error occurred: {e}")
```

### HTTPError

Exception raised for HTTP error status codes (4xx, 5xx).

```python
class HTTPError(APIError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")
```

**Attributes:**

- `status_code` (int): HTTP status code
- `message` (str): Error message from server

**Example:**

```python
try:
    response = client.get("/protected")
except HTTPError as e:
    if e.status_code == 401:
        print("Authentication required")
    elif e.status_code == 404:
        print("Resource not found")
```

## Rate Limiting

The client automatically enforces rate limiting to prevent overwhelming the API server.

### Default Behavior

- **Rate:** 10 requests per second
- **Method:** Token bucket algorithm
- **Scope:** Per APIClient instance

### How It Works

```python
# These requests are automatically spaced out
for i in range(20):
    client.get(f"/users/{i}")  # ~100ms between requests
```

The rate limiter:

1. Allows burst of up to 10 requests instantly
2. Refills tokens at 10 per second
3. Blocks when tokens exhausted until refilled
4. Thread-safe for concurrent requests

## Retry Logic

### Automatic Retries

The client automatically retries on server errors (5xx status codes).

**Default Behavior:**

- Retries on: 500, 502, 503, 504
- Maximum attempts: 3 (configurable via `max_retries`)
- Backoff: Exponential (1s, 2s, 4s)

### Retry Flow

```
Request → 503 Service Unavailable
  ↓ Wait 1 second
Retry 1 → 503 Service Unavailable
  ↓ Wait 2 seconds
Retry 2 → 503 Service Unavailable
  ↓ Wait 4 seconds
Retry 3 → 200 OK (success!)
```

### Disabling Retries

```python
# Disable automatic retries
config = ClientConfig(
    base_url="https://api.example.com",
    max_retries=0
)
```

## Thread Safety

All APIClient operations are thread-safe.

### Safe Operations

- Creating multiple clients
- Sharing single client across threads
- Concurrent requests from same client
- Rate limiting across threads

### Implementation Details

Thread safety is achieved through:

- Immutable configuration
- Thread-local storage for connection pooling
- Thread-safe rate limiter using locks
- No shared mutable state

## Type Hints

The module provides complete type hints for IDE support and type checking.

### Example Type Annotations

```python
from api_client import APIClient, ClientConfig, Response, HTTPError
from typing import Optional, Dict, Any

def fetch_user(client: APIClient, user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch user by ID, return None if not found"""
    try:
        response: Response = client.get(f"/users/{user_id}")
        return response.json()
    except HTTPError as e:
        if e.status_code == 404:
            return None
        raise
```

## Performance Characteristics

### Request Overhead

- **Connection pooling:** Reuses TCP connections
- **DNS caching:** System-level caching
- **Rate limiting overhead:** ~0.1ms per request

### Memory Usage

- **Per client:** ~1KB base + connection pool
- **Per request:** Size of request/response data
- **No memory leaks:** Automatic cleanup

### Benchmarks

```python
# Typical performance (local network)
# GET request: 5-10ms
# POST with 1KB JSON: 10-15ms
# Rate-limited burst: 100ms per request
```

## Version Compatibility

### Python Versions

- Python 3.8+
- No external dependencies
- Uses standard library only

### API Stability

The module follows semantic versioning:

- **Major version:** Breaking API changes
- **Minor version:** New features, backward compatible
- **Patch version:** Bug fixes

### Deprecation Policy

Features are deprecated with warnings for one major version before removal:

```python
# Version 1.0 - Feature available
client.old_method()

# Version 2.0 - Deprecated with warning
client.old_method()  # DeprecationWarning: Use new_method() instead

# Version 3.0 - Removed
client.old_method()  # AttributeError
```
