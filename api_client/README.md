# REST API Client

A robust, synchronous HTTP client with automatic retry logic and comprehensive error handling.

## Quick Start

```python
from api_client import APIClient

with APIClient(base_url="https://api.example.com") as client:
    response = client.get("/users/123")
    print(response.json_data)
```

## Installation

### Dependencies

```
requests>=2.28.0
pytest>=7.0.0
pytest-httpserver>=1.0.0
```

Install with pip:

```bash
pip install requests pytest pytest-httpserver
```

Or add to your `pyproject.toml`:

```toml
[project]
dependencies = [
    "requests>=2.28.0",
]

[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-httpserver>=1.0.0",
]
```

## Contents

- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Configuration Options](#configuration-options)
- [Error Handling](#error-handling)
- [Logging](#logging)

## Usage Examples

### Basic GET Request

```python
from api_client import APIClient

def fetch_user():
    with APIClient(base_url="https://api.example.com") as client:
        response = client.get("/users/123")

        if response.ok:
            user = response.json_data
            print(f"User: {user['name']}")

        return response.json_data
```

### POST Request with JSON Body

```python
from api_client import APIClient

def create_user(name: str, email: str):
    with APIClient(base_url="https://api.example.com") as client:
        response = client.post(
            "/users",
            json_data={"name": name, "email": email}
        )
        return response.json_data
```

### PUT and PATCH Requests

```python
from api_client import APIClient

def update_user(user_id: int, updates: dict):
    with APIClient(base_url="https://api.example.com") as client:
        # Full replacement
        response = client.put(f"/users/{user_id}", json_data=updates)

        # Partial update
        response = client.patch(f"/users/{user_id}", json_data={"status": "active"})

        return response.json_data
```

### DELETE Request

```python
from api_client import APIClient

def delete_user(user_id: int):
    with APIClient(base_url="https://api.example.com") as client:
        response = client.delete(f"/users/{user_id}")
        return response.ok
```

### Custom Headers

```python
from api_client import APIClient

def authenticated_request():
    with APIClient(
        base_url="https://api.example.com",
        default_headers={
            "Authorization": "Bearer your-api-token",
            "X-Custom-Header": "custom-value",
        }
    ) as client:
        # All requests include configured headers
        response = client.get("/protected/resource")

        # Override headers per-request
        response = client.get(
            "/another/resource",
            headers={"X-Request-ID": "abc123"}
        )
        return response.json_data
```

### Query Parameters

```python
from api_client import APIClient

def search_users(query: str, limit: int = 10):
    with APIClient(base_url="https://api.example.com") as client:
        response = client.get(
            "/users/search",
            params={"q": query, "limit": limit, "sort": "name"}
        )
        return response.json_data
```

### Error Handling

```python
from api_client import (
    APIClient,
    APIError,
    ClientError,
    ConnectionError,
    RateLimitError,
    RetryExhaustedError,
    ServerError,
    TimeoutError,
)

def robust_fetch(resource_id: int):
    with APIClient(base_url="https://api.example.com") as client:
        try:
            response = client.get(f"/resources/{resource_id}")
            return response.json_data

        except ClientError as e:
            print(f"Client error ({e.status_code}): {e.message}")
            return None

        except RateLimitError as e:
            print(f"Rate limited. Retry after {e.retry_after}s")
            raise

        except ServerError as e:
            print(f"Server error ({e.status_code}): {e.message}")
            raise

        except TimeoutError as e:
            print(f"Request timed out: {e.message}")
            raise

        except ConnectionError as e:
            print(f"Connection failed: {e.message}")
            raise

        except RetryExhaustedError as e:
            print(f"All retries exhausted: {e.message}")
            raise

        except APIError as e:
            print(f"API error: {e.message}")
            raise
```

### Context Manager Usage

The recommended way to use APIClient is with context manager:

```python
from api_client import APIClient

# Recommended: Context manager handles cleanup
def recommended_usage():
    with APIClient(base_url="https://api.example.com") as client:
        response = client.get("/data")
        return response.json_data
    # Session automatically closed

# Alternative: Manual lifecycle management
def manual_usage():
    client = APIClient(base_url="https://api.example.com")
    try:
        response = client.get("/data")
        return response.json_data
    finally:
        client.close()
```

### Retry Configuration

```python
from api_client import APIClient

# Configure retry behavior via APIClient constructor
with APIClient(
    base_url="https://api.example.com",
    max_retries=3,                        # Maximum retry attempts
    retry_backoff_factor=0.5,             # Backoff multiplier
    retry_on_status={429, 500, 502, 503, 504},  # Status codes to retry
) as client:
    # Automatic retries with exponential backoff
    response = client.get("/flaky-endpoint")
```

## API Reference

### APIClient

Main client class for making HTTP requests.

```python
class APIClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_backoff_factor: float = 0.5,
        retry_on_status: Optional[Set[int]] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize API client.

        Args:
            base_url: Base URL for all requests (trailing slash stripped)
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum retry attempts (default: 3)
            retry_backoff_factor: Backoff multiplier (default: 0.5)
            retry_on_status: Status codes to retry (default: {429, 500, 502, 503, 504})
            default_headers: Headers for all requests (default: {})
        """
```

#### Methods

| Method   | Signature                                                                            | Description              |
| -------- | ------------------------------------------------------------------------------------ | ------------------------ |
| `get`    | `def get(path, params=None, headers=None, timeout=None) -> Response`                 | Perform GET request      |
| `post`   | `def post(path, json_data=None, data=None, headers=None, timeout=None) -> Response`  | Perform POST request     |
| `put`    | `def put(path, json_data=None, data=None, headers=None, timeout=None) -> Response`   | Perform PUT request      |
| `patch`  | `def patch(path, json_data=None, data=None, headers=None, timeout=None) -> Response` | Perform PATCH request    |
| `delete` | `def delete(path, headers=None, timeout=None) -> Response`                           | Perform DELETE request   |
| `close`  | `def close() -> None`                                                                | Close the client session |

### Request Dataclass

```python
@dataclass(frozen=True)
class Request:
    """Immutable request representation."""

    method: str                              # HTTP method (GET, POST, etc.)
    url: str                                 # Full URL
    headers: dict[str, str] = field(...)    # Request headers
    params: dict[str, Any] | None = None    # Query parameters
    json_data: Any | None = None            # JSON body
    data: bytes | None = None               # Raw bytes body
```

### Response Dataclass

```python
@dataclass(frozen=True)
class Response:
    """Immutable response wrapper."""

    status_code: int              # HTTP status code
    headers: dict[str, str]       # Response headers
    body: bytes                   # Raw response body
    elapsed_ms: float             # Request duration in milliseconds
    request: Request              # Original request

    @property
    def ok(self) -> bool:
        """Check if response indicates success (2xx status)."""

    @property
    def json_data(self) -> Any | None:
        """Parse body as JSON. Returns None if body is not valid JSON."""

    @property
    def text(self) -> str:
        """Decode body as UTF-8 text."""
```

### Exception Hierarchy

```
APIError (base)
├── ConnectionError
├── TimeoutError
├── RateLimitError
├── ServerError
├── ClientError
└── RetryExhaustedError
```

All exceptions include:

- `message`: Human-readable error description
- `request`: The Request object that triggered the error (when available)
- `response`: The Response object (when available)
- `status_code`: HTTP status code (for HTTP errors)

### RetryStrategy

```python
class RetryStrategy:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,              # Maximum retry attempts
        backoff_factor: float = 0.5,       # Base delay multiplier
        retry_on_status: Set[int] | None = None,  # Status codes to retry
    ):
        """Initialize retry strategy.

        Default retry_on_status: {429, 500, 502, 503, 504}
        """
```

## Configuration Options

| Parameter              | Type             | Default                     | Description                      |
| ---------------------- | ---------------- | --------------------------- | -------------------------------- |
| `base_url`             | `str`            | Required                    | Base URL for all requests        |
| `timeout`              | `float`          | `30.0`                      | Request timeout in seconds       |
| `max_retries`          | `int`            | `3`                         | Maximum retry attempts           |
| `retry_backoff_factor` | `float`          | `0.5`                       | Exponential backoff multiplier   |
| `retry_on_status`      | `Set[int]`       | `{429, 500, 502, 503, 504}` | Status codes that trigger retry  |
| `default_headers`      | `Dict[str, str]` | `{}`                        | Default headers for all requests |

### Configuration Example

```python
from api_client import APIClient

with APIClient(
    base_url="https://api.example.com",
    timeout=60.0,
    max_retries=5,
    retry_backoff_factor=1.0,
    default_headers={"Authorization": "Bearer token"},
) as client:
    response = client.get("/data")
```

## Error Handling

### Exception Types and When They Occur

| Exception             | HTTP Codes | When It Occurs                                                  |
| --------------------- | ---------- | --------------------------------------------------------------- |
| `ClientError`         | 4xx        | Client-side errors (bad request, unauthorized, not found, etc.) |
| `RateLimitError`      | 429        | Too many requests                                               |
| `ServerError`         | 5xx        | Server-side errors                                              |
| `TimeoutError`        | -          | Request exceeded timeout                                        |
| `ConnectionError`     | -          | Connection failures                                             |
| `RetryExhaustedError` | -          | All retry attempts failed                                       |

### Exception Attributes

```python
try:
    response = client.get("/resource")
except RateLimitError as e:
    print(f"Message: {e.message}")
    print(f"Status code: {e.status_code}")  # 429
    print(f"Retry after: {e.retry_after}")  # Seconds to wait
    print(f"Request URL: {e.request.url}")
except APIError as e:
    print(f"Base error: {e.message}")
```

## Logging

### Configure Logging Level

```python
import logging

# Configure Python logging
logging.getLogger("api_client").setLevel(logging.DEBUG)
```

### Log Output Examples

```
INFO - Completed: GET https://api.example.com/users -> 200
WARNING - Rate limited: https://api.example.com/data (retry after 2.00s)
WARNING - Server error 503: https://api.example.com/data (retry 1/3 after 0.50s)
```

## Testing

### Using pytest-httpserver

```python
import pytest
from pytest_httpserver import HTTPServer
from api_client import APIClient, ClientError

@pytest.fixture
def httpserver_listen_address():
    return ("127.0.0.1", 8000)

def test_get_user(httpserver: HTTPServer):
    httpserver.expect_request("/users/1").respond_with_json(
        {"id": 1, "name": "Test User"}
    )

    with APIClient(base_url=httpserver.url_for("")) as client:
        response = client.get("/users/1")

        assert response.status_code == 200
        assert response.json_data["name"] == "Test User"

def test_error_handling(httpserver: HTTPServer):
    httpserver.expect_request("/error").respond_with_json(
        {"error": "not found"}, status=404
    )

    with APIClient(base_url=httpserver.url_for("")) as client:
        with pytest.raises(ClientError):
            client.get("/error")
```

### Mocking for Unit Tests

```python
from unittest.mock import Mock, patch
from api_client import APIClient, Response, Request

def test_with_mock():
    mock_response = Response(
        status_code=200,
        headers={},
        body=b'{"id": 1}',
        elapsed_ms=100.0,
        request=Request(method="GET", url="https://api.example.com/test"),
    )

    with patch.object(APIClient, "request") as mock:
        mock.return_value = mock_response

        with APIClient(base_url="https://api.example.com") as client:
            response = client.get("/test")
            assert response.json_data["id"] == 1
```
