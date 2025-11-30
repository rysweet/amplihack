# REST API Client

A robust, zero-dependency REST API client library with built-in retry logic, rate limiting, and comprehensive error handling.

## Quick Start

Get started with the REST API Client in under 30 seconds:

```python
from rest_api_client import APIClient

# Initialize client
client = APIClient(base_url="https://api.example.com")

# Make a simple GET request
response = client.get("/users/123")
print(f"User: {response.data['name']}")
# Output: User: John Doe
```

## Features

- **Zero Dependencies**: Uses only Python standard library
- **Automatic Retries**: Configurable exponential backoff for failed requests
- **Rate Limiting**: Built-in rate limiter prevents API throttling
- **Type Safety**: Request/response dataclasses for type hints
- **Security**: SSL verification, header validation, and log sanitization
- **Custom Exceptions**: Clear, actionable error messages

## Installation

Since this is a scenario tool, it's already available in your amplihack installation:

```bash
# Run directly via Python
python .claude/scenarios/rest-api-client/rest_api_client.py

# Or import in your code
from rest_api_client import APIClient
```

## Documentation

- [**Tutorials**](./docs/tutorials/getting-started.md) - Learn the basics step-by-step
- [**How-To Guides**](./docs/howto/index.md) - Solve specific problems
- [**API Reference**](./docs/reference/api.md) - Complete API documentation
- [**Concepts**](./docs/concepts/architecture.md) - Understand the design

## Basic Usage

### Simple GET Request

```python
from rest_api_client import APIClient

client = APIClient(base_url="https://jsonplaceholder.typicode.com")
response = client.get("/posts/1")

print(f"Title: {response.data['title']}")
print(f"Status: {response.status_code}")
# Output: Title: sunt aut facere repellat provident
# Output: Status: 200
```

### POST with JSON Data

```python
from rest_api_client import APIClient

client = APIClient(base_url="https://jsonplaceholder.typicode.com")

new_post = {
    "title": "My New Post",
    "body": "This is the content",
    "userId": 1
}

response = client.post("/posts", json=new_post)
print(f"Created post ID: {response.data['id']}")
# Output: Created post ID: 101
```

### With Authentication

```python
from rest_api_client import APIClient

client = APIClient(
    base_url="https://api.github.com",
    headers={"Authorization": "Bearer your-token-here"}
)

response = client.get("/user")
print(f"Authenticated as: {response.data['login']}")
# Output: Authenticated as: octocat
```

## Error Handling

The client provides clear exceptions for common scenarios:

```python
from rest_api_client import APIClient, APIException, RateLimitException

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/protected-resource")
except RateLimitException as e:
    print(f"Rate limited. Retry after: {e.retry_after} seconds")
except APIException as e:
    print(f"API error: {e.message} (status: {e.status_code})")
```

## Configuration

See the [Configuration Guide](./docs/howto/configure-client.md) for detailed options:

```python
from rest_api_client import APIClient, RetryConfig, RateLimitConfig

client = APIClient(
    base_url="https://api.example.com",
    retry_config=RetryConfig(max_attempts=5, backoff_factor=2.0),
    rate_limit_config=RateLimitConfig(requests_per_second=10),
    timeout=30,
    verify_ssl=True
)
```

## Testing

Run the test suite:

```bash
python -m pytest .claude/scenarios/rest-api-client/tests/
```

## Contributing

This is part of the amplihack framework. See the main project documentation for contribution guidelines.

## License

Part of the amplihack project. See root LICENSE file.
