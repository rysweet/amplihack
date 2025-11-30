# REST API Client Module

A production-ready, async-first REST API client with enterprise-grade reliability features.

## Features

- **Async/await support** - Built on modern Python async patterns
- **Automatic retry** - Configurable exponential backoff with jitter
- **Rate limiting** - Respect API rate limits automatically
- **Type safety** - Full type hints and generic response types
- **Error handling** - Comprehensive exception hierarchy
- **Structured logging** - Debug API interactions easily
- **Context managers** - Proper resource management

## Quick Start

```python
from amplihack.api_client import APIClient

async def fetch_data():
    async with APIClient(base_url="https://api.example.com") as client:
        response = await client.get("/users/123")
        return response.data
```

## Installation

The API client is included with amplihack:

```bash
pip install amplihack
```

## Architecture

```
api_client/
├── __init__.py       # Public API exports
├── client.py         # Main APIClient class
├── models.py         # Request/Response dataclasses
├── exceptions.py     # Exception hierarchy
├── retry.py          # Retry logic and backoff
├── rate_limit.py     # Rate limiting handler
├── config.py         # Configuration classes
└── logging.py        # Structured logging setup
```

## Core Components

### APIClient

The main client class providing HTTP methods with automatic retry and error handling:

```python
from amplihack.api_client import APIClient

client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer token"},
    timeout=30.0
)
```

### Type-Safe Responses

Use generic types for automatic deserialization:

```python
from dataclasses import dataclass
from typing import List

@dataclass
class User:
    id: int
    name: str

response = await client.get("/users", response_type=List[User])
users: List[User] = response.data
```

### Retry Configuration

Customize retry behavior:

```python
from amplihack.api_client import RetryConfig

config = RetryConfig(
    max_retries=5,
    initial_delay=1.0,
    exponential_base=2.0,
    jitter=True
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=config
)
```

### Exception Handling

Comprehensive error types for different failure modes:

```python
from amplihack.api_client import (
    NetworkError,
    RateLimitError,
    HTTPError,
    ValidationError
)

try:
    response = await client.get("/resource")
except NetworkError:
    # Connection failed
    pass
except RateLimitError as e:
    # Rate limited, retry after e.retry_after
    pass
except HTTPError as e:
    # HTTP error (4xx, 5xx)
    if e.status_code == 404:
        # Not found
        pass
```

## Common Patterns

### Authentication

```python
# Bearer token
client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer your-token"}
)

# API key
client = APIClient(
    base_url="https://api.example.com",
    headers={"X-API-Key": "your-key"}
)
```

### Pagination

```python
async def fetch_all_pages():
    all_items = []
    page = 1

    async with APIClient(base_url="https://api.example.com") as client:
        while True:
            response = await client.get(
                "/items",
                params={"page": page, "per_page": 100}
            )

            all_items.extend(response.data["items"])

            if not response.data["has_more"]:
                break
            page += 1

    return all_items
```

### Rate Limit Handling

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

## Testing

### Mocking

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_api_call():
    mock_response = AsyncMock()
    mock_response.data = {"result": "success"}

    with patch('amplihack.api_client.APIClient.get', return_value=mock_response):
        result = await my_function()
        assert result["result"] == "success"
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_real_api():
    async with APIClient(base_url="https://api.example.com") as client:
        response = await client.get("/health")
        assert response.status_code == 200
```

## Best Practices

1. **Always use context managers** - Ensures proper cleanup
2. **Configure appropriate timeouts** - Prevent hanging requests
3. **Handle specific exceptions** - Different errors need different handling
4. **Use type hints** - Leverage type safety with response_type
5. **Log at appropriate levels** - Debug for details, warning for issues
6. **Respect rate limits** - Configure rate limiting for public APIs

## Documentation

- [API Reference](../../docs/reference/api-client.md) - Complete API documentation
- [Usage Guide](../../docs/howto/api-client-usage.md) - Common patterns
- [Configuration](../../docs/howto/api-client-config.md) - All configuration options

## Design Philosophy

This module follows amplihack's core principles:

- **Ruthless simplicity** - Clean, minimal API surface
- **Zero-BS implementation** - Every feature works or doesn't exist
- **Type safety** - Full type hints for IDE support
- **Production-ready** - Comprehensive error handling and logging
- **Async-first** - Built for modern Python applications

## Module Contract

This module is a "brick" in the amplihack architecture:

**Responsibility**: Provide reliable HTTP client functionality with automatic retry and rate limiting

**Public API** (defined in `__init__.py`):

- `APIClient` - Main client class
- `Request` - Request dataclass
- `Response` - Response generic
- `RetryConfig` - Retry configuration
- `RateLimitHandler` - Rate limit handler
- Exception classes

**Dependencies**: Standard library + `httpx` for async HTTP

**Regeneratable**: This module can be rebuilt from this specification without breaking consumers
