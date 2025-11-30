# REST API Client

A robust, type-safe HTTP client library with automatic retry logic, rate
limiting, and comprehensive error handling.

## Installation

```bash
pip install rest-api-client
```

## Quick Start

```python
from rest_api_client import APIClient

# Create a client instance
client = APIClient(base_url="https://api.example.com")

# Make a simple GET request
response = client.get("/users/123")
print(response.data)
# Output: {"id": 123, "name": "Alice", "email": "alice@example.com"}

# POST with JSON data
user_data = {"name": "Bob", "email": "bob@example.com"}
response = client.post("/users", json=user_data)
print(f"Created user: {response.data['id']}")
# Output: Created user: 124
```

## Features

- **All HTTP Methods**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- **Automatic Retries**: Exponential backoff with configurable attempts
- **Rate Limiting**: Built-in token bucket algorithm for API limits
- **Type Safety**: Full type hints with dataclass models
- **Error Handling**: Comprehensive exception hierarchy
- **Logging**: Structured logging for debugging
- **Async Support**: Both sync and async clients available

## Basic Usage

### Creating a Client

```python
from rest_api_client import APIClient
from rest_api_client.config import APIConfig

# Simple initialization
client = APIClient(base_url="https://api.example.com")

# With configuration
config = APIConfig(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3,
    rate_limit_calls=100,
    rate_limit_period=60
)
client = APIClient(config=config)

# With authentication
client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)
```

### Making Requests

```python
# GET request
users = client.get("/users")

# GET with query parameters
filtered_users = client.get("/users", params={"active": True, "limit": 10})

# POST with JSON
new_user = client.post("/users", json={"name": "Charlie"})

# PUT with data
updated = client.put("/users/123", json={"name": "Charles"})

# DELETE request
client.delete("/users/456")

# Custom headers for a single request
response = client.get(
    "/users/me",
    headers={"X-Custom-Header": "value"}
)
```

### Error Handling

```python
from rest_api_client.exceptions import (
    APIError,
    RateLimitError,
    NetworkError,
    ValidationError
)

try:
    response = client.get("/protected-resource")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ValidationError as e:
    print(f"Invalid request: {e.message}")
except NetworkError as e:
    print(f"Network issue: {e.message}")
except APIError as e:
    print(f"API error: {e.status_code} - {e.message}")
```

### Rate Limiting

The client automatically handles rate limiting:

```python
# Configure rate limits
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=100,  # 100 calls
    rate_limit_period=60    # per 60 seconds
)

# The client will automatically throttle requests
for i in range(200):
    # This will pause when rate limit is reached
    response = client.get(f"/items/{i}")
```

### Retry Configuration

```python
from rest_api_client.config import RetryConfig

# Custom retry configuration
retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=30,
    exponential_base=2,
    retry_on_statuses=[429, 500, 502, 503, 504]
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)
```

## Async Support

```python
import asyncio
from rest_api_client import AsyncAPIClient

async def main():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Parallel requests
        tasks = [
            client.get(f"/users/{i}")
            for i in range(1, 11)
        ]
        responses = await asyncio.gather(*tasks)

        for response in responses:
            print(response.data)

asyncio.run(main())
```

## Advanced Features

### Request/Response Models

```python
from rest_api_client.models import Request, Response

# Inspect request before sending
request = client.prepare_request(
    method="POST",
    endpoint="/users",
    json={"name": "Dave"}
)
print(f"Will send: {request.method} {request.url}")

# Access response details
response = client.send(request)
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Data: {response.data}")
```

### Custom Exception Handling

```python
from rest_api_client import APIClient
from rest_api_client.exceptions import APIError

class MyAPIClient(APIClient):
    def handle_error(self, response):
        """Custom error handling logic."""
        if response.status_code == 402:
            raise PaymentRequiredError("Payment required for this resource")
        super().handle_error(response)

class PaymentRequiredError(APIError):
    """Custom exception for payment required responses."""
    pass
```

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

client = APIClient(base_url="https://api.example.com")
client.get("/users")  # Will log request/response details
```

## Configuration Reference

### APIConfig Options

| Parameter           | Type | Default  | Description                      |
| ------------------- | ---- | -------- | -------------------------------- |
| `base_url`          | str  | Required | Base URL for all requests        |
| `timeout`           | int  | 30       | Request timeout in seconds       |
| `max_retries`       | int  | 3        | Maximum retry attempts           |
| `rate_limit_calls`  | int  | None     | Max calls per period             |
| `rate_limit_period` | int  | 60       | Rate limit period in seconds     |
| `headers`           | dict | {}       | Default headers for all requests |
| `verify_ssl`        | bool | True     | Verify SSL certificates          |

### RetryConfig Options

| Parameter           | Type  | Default                   | Description                    |
| ------------------- | ----- | ------------------------- | ------------------------------ |
| `max_attempts`      | int   | 3                         | Maximum retry attempts         |
| `initial_delay`     | float | 1.0                       | Initial retry delay in seconds |
| `max_delay`         | float | 60.0                      | Maximum retry delay            |
| `exponential_base`  | float | 2.0                       | Exponential backoff base       |
| `retry_on_statuses` | list  | [429, 500, 502, 503, 504] | HTTP statuses to retry         |

## Testing

```python
import unittest
from unittest.mock import Mock, patch
from rest_api_client import APIClient

class TestAPIClient(unittest.TestCase):
    @patch('rest_api_client.client.requests')
    def test_get_request(self, mock_requests):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"test": "data"}
        mock_requests.get.return_value = mock_response

        client = APIClient(base_url="https://test.com")
        response = client.get("/test")

        self.assertEqual(response.data, {"test": "data"})
        mock_requests.get.assert_called_once()
```

## Best Practices

1. **Reuse client instances** - Create once, use many times
2. **Set appropriate timeouts** - Prevent hanging requests
3. **Handle errors gracefully** - Always catch specific exceptions
4. **Use rate limiting** - Be a good API citizen
5. **Enable logging in development** - Easier debugging
6. **Configure retries wisely** - Balance reliability and performance

## Documentation

- [Full Documentation](./docs/index.md)
- [API Reference](./docs/reference/api.md)
- [Examples](./examples/)
- [Contributing](./CONTRIBUTING.md)

## License

MIT License - see LICENSE file for details.
