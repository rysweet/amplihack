# Utils Module

Self-contained utilities for the amplihack framework.

## Philosophy

This module follows the brick philosophy - each utility is:

- **Self-contained**: No external dependencies beyond standard library (when possible)
- **Single responsibility**: Each utility does one thing well
- **Regeneratable**: Can be rebuilt from specification without breaking contracts

## API Client

Simple, robust HTTP client with exponential backoff retry logic.

```python
from amplihack.utils import APIClient

# Create client
client = APIClient("https://api.example.com")

# Make requests with automatic retries
response = client.execute("GET", "/users")
print(response.data)
```

### Key Features

- **Simple interface**: One `execute()` method for all HTTP requests
- **Exponential backoff**: Automatic retries with increasing delays
- **Rate limit handling**: Respects rate limit headers
- **Clean exceptions**: Only 3 exception types to handle

### Design Decisions

We chose simplicity over features:

- No separate RateLimiter class (built into execute method)
- No middleware or plugins (keeps code understandable)
- No circuit breakers (exponential backoff is sufficient)
- Flat exception hierarchy (3 types instead of 10+)

## Public API

The module exports these utilities through `__all__`:

```python
from amplihack.utils import (
    APIClient,        # HTTP client with retries
    APIRequest,       # Request data class
    APIResponse,      # Response data class
    APIError,         # Base exception
    RateLimitError,   # Rate limit exception
    ValidationError,  # Validation exception
)
```

## Testing

Each utility has comprehensive tests:

```bash
# Run all utils tests
pytest tests/unit/test_utils/

# Run API client tests
pytest tests/unit/test_utils/test_api_client.py
```

## Examples

### Basic API Usage

```python
from amplihack.utils import APIClient, APIError

client = APIClient("https://jsonplaceholder.typicode.com")

try:
    # Fetch data
    response = client.execute("GET", "/posts/1")
    print(f"Title: {response.data['title']}")

    # Create resource
    new_post = {"title": "My Post", "body": "Content", "userId": 1}
    response = client.execute("POST", "/posts", json=new_post)
    print(f"Created ID: {response.data['id']}")

except APIError as e:
    print(f"Request failed: {e.message}")
```

### With Error Recovery

```python
from amplihack.utils import APIClient, RateLimitError
import time

client = APIClient("https://api.github.com")

def fetch_with_retry(endpoint):
    """Fetch with rate limit handling."""
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            return client.execute("GET", endpoint)
        except RateLimitError as e:
            if attempt < max_attempts - 1:
                print(f"Rate limited, waiting {e.retry_after}s...")
                time.sleep(e.retry_after)
            else:
                raise

# Use it
response = fetch_with_retry("/repos/amplihack/amplihack")
print(f"Stars: {response.data['stargazers_count']}")
```

## Adding New Utilities

When adding utilities to this module:

1. **Keep it simple**: Start with minimal functionality
2. **No external dependencies**: Use standard library when possible
3. **Clear contracts**: Define public API in docstrings
4. **Comprehensive tests**: Cover edge cases and errors
5. **Update **all****: Export through module's public API

## Documentation

- [How to Use API Client](../../../docs/howto/use-api-client.md)
- [API Client Reference](../../../docs/reference/api-client.md)
