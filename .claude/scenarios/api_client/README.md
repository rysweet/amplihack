# APIClient

Async HTTP client with automatic retry, exponential backoff, and rate limiting support.

## Installation

The APIClient is included with amplihack scenarios. No additional installation required.

```python
from api_client import APIClient, Request, Response
```

## Quick Start

```python
import asyncio
from api_client import APIClient

async def main():
    async with APIClient("https://api.example.com") as client:
        response = await client.get("/users")
        users = response.json()
        print(f"Found {len(users)} users")

asyncio.run(main())
```

## API Reference

### APIClient

The main HTTP client class. Use as an async context manager.

```python
APIClient(
    base_url: str,
    timeout: float = 30.0,
    max_retries: int = 3,
    headers: dict[str, str] | None = None,
)
```

**Parameters:**

| Parameter     | Type    | Default | Description                      |
| ------------- | ------- | ------- | -------------------------------- |
| `base_url`    | `str`   | -       | Base URL for all requests        |
| `timeout`     | `float` | `30.0`  | Request timeout in seconds       |
| `max_retries` | `int`   | `3`     | Maximum retry attempts           |
| `headers`     | `dict`  | `None`  | Default headers for all requests |

**Methods:**

```python
async def get(path: str, **kwargs) -> Response
async def post(path: str, **kwargs) -> Response
async def put(path: str, **kwargs) -> Response
async def delete(path: str, **kwargs) -> Response
async def request(request: Request) -> Response
```

### Request

Dataclass representing an HTTP request.

```python
@dataclass
class Request:
    method: str
    path: str
    headers: dict[str, str] = {}
    params: dict[str, str] = {}
    json_body: Any | None = None
    body: bytes | None = None
```

### Response

Dataclass representing an HTTP response.

```python
@dataclass
class Response:
    status_code: int
    body: bytes
    headers: dict[str, str]
    elapsed_ms: float

    def json(self) -> Any: ...
    def text(self) -> str: ...
```

### Exceptions

Three-class exception hierarchy:

```
APIClientError (base)
├── NetworkError    # Connection failures, timeouts, DNS errors (retriable)
└── HTTPError       # HTTP status errors (4xx, 5xx)
    └── is_retriable property - True for 429 and 5xx
```

## Error Handling

```python
from api_client import APIClient, NetworkError, HTTPError

async with APIClient("https://api.example.com") as client:
    try:
        response = await client.get("/users/123")
        user = response.json()
    except NetworkError as e:
        print(f"Connection failed: {e}")
    except HTTPError as e:
        if e.status_code == 404:
            print("User not found")
        elif e.status_code >= 500:
            print(f"Server error: {e.status_code}")
```

## Retry Behavior

The client automatically retries on:

- Network errors (connection refused, timeout, DNS failure)
- HTTP 429 (Too Many Requests)
- HTTP 500, 502, 503, 504 (Server errors)

Non-retriable errors (400, 401, 403, 404) raise immediately.

**Exponential Backoff:**

| Attempt | Delay |
| ------- | ----- |
| 1       | 1s    |
| 2       | 2s    |
| 3       | 4s    |
| 4       | 8s    |
| ...     | ...   |
| max     | 30s   |

## Public API

```python
__all__ = [
    "APIClient",
    "Request",
    "Response",
    "APIClientError",
    "NetworkError",
    "HTTPError",
]
```
