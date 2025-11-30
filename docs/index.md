# API Client Documentation

Welcome to the API Client documentation. This module provides a zero-dependency REST API client with automatic retries, rate limiting, and thread-safe operation.

## Documentation

### Getting Started

- [Quick Start Tutorial](./tutorials/api_client_quickstart.md) - Learn the basics in 10 minutes
- [API Client README](../api_client/README.md) - Module overview and features

### How-To Guides

- [Usage Examples](./howto/api_client_examples.md) - Practical patterns and recipes

### Reference

- [API Reference](./reference/api_client.md) - Complete API documentation

## Quick Example

```python
from api_client import APIClient, ClientConfig

# Configure and create client
config = ClientConfig(base_url="https://api.example.com")
client = APIClient(config)

# Make requests
response = client.get("/users/123")
user = response.json()
print(f"User: {user['name']}")
```

## Key Features

- **Zero Dependencies** - Uses only Python standard library
- **Automatic Retry** - Exponential backoff on server errors
- **Rate Limiting** - Built-in 10 req/sec limit
- **Thread-Safe** - Safe for concurrent usage
- **Type Hints** - Full type annotations
- **Simple API** - Just get, post, put, delete

## Navigation

| If you want to...             | Read this                                                                 |
| ----------------------------- | ------------------------------------------------------------------------- |
| Learn how to use the client   | [Quick Start Tutorial](./tutorials/api_client_quickstart.md)              |
| See example code              | [Usage Examples](./howto/api_client_examples.md)                          |
| Look up API details           | [API Reference](./reference/api_client.md)                                |
| Understand the implementation | [Module README](../api_client/README.md)                                  |
| Handle errors properly        | [Error Handling](./howto/api_client_examples.md#error-handling-patterns)  |
| Work with authentication      | [Authentication](./howto/api_client_examples.md#authentication-examples)  |
| Make concurrent requests      | [Concurrent Requests](./howto/api_client_examples.md#concurrent-requests) |
| Implement pagination          | [Pagination Patterns](./howto/api_client_examples.md#pagination-patterns) |
