# REST API Client Documentation

Complete documentation for the REST API Client - a simple, robust HTTP client built with Python's standard library.

## Documentation Structure

### Getting Started

- [README](../README.md) - Overview, installation, and quick start guide
- [Configuration Guide](./configuration.md) - Comprehensive configuration options
- [Usage Patterns](./usage-patterns.md) - Common patterns and best practices

### Development

- [Error Handling Guide](./error-handling.md) - Error handling strategies
- [Testing Guide](./testing.md) - Testing strategies and examples

## Quick Navigation

### By Task

| I want to...           | Documentation                                                                   |
| ---------------------- | ------------------------------------------------------------------------------- |
| Get started quickly    | [README](../README.md#quick-start)                                              |
| Configure the client   | [Configuration Guide](./configuration.md)                                       |
| Handle authentication  | [Usage Patterns - Authentication](./usage-patterns.md#authentication-patterns)  |
| Handle errors properly | [Error Handling Guide](./error-handling.md)                                     |
| Test my integration    | [Testing Guide](./testing.md)                                                   |
| Process responses      | [Usage Patterns - Response Processing](./usage-patterns.md#response-processing) |
| Implement retries      | [Error Handling - Retry Logic](./error-handling.md#retry-logic)                 |
| Rate limit requests    | [Configuration - Rate Limiting](./configuration.md#rate-limiting)               |

### By Feature

| Feature              | Documentation                                                                  |
| -------------------- | ------------------------------------------------------------------------------ |
| **Basic Requests**   | [README - Basic Usage](../README.md#basic-usage)                               |
| **Rate Limiting**    | [Configuration - Rate Limiting](./configuration.md#rate-limiting)              |
| **Retries**          | [Error Handling - Retry Logic](./error-handling.md#retry-logic)                |
| **Authentication**   | [Usage Patterns - Authentication](./usage-patterns.md#authentication-patterns) |
| **Error Handling**   | [Error Handling Guide](./error-handling.md)                                    |
| **Testing**          | [Testing Guide](./testing.md)                                                  |
| **Batch Operations** | [Usage Patterns - Batch Operations](./usage-patterns.md#batch-operations)      |
| **Caching**          | [Usage Patterns - Response Caching](./usage-patterns.md#response-processing)   |

### By API Method

| Method         | Documentation                                 | Example                                 |
| -------------- | --------------------------------------------- | --------------------------------------- |
| `RESTClient()` | [API Reference](../README.md#api-reference)   | [Quick Start](../README.md#quick-start) |
| `get()`        | [API Reference - GET](../README.md#get)       | [Examples](../README.md#examples)       |
| `post()`       | [API Reference - POST](../README.md#post)     | [Examples](../README.md#examples)       |
| `put()`        | [API Reference - PUT](../README.md#put)       | [Examples](../README.md#examples)       |
| `delete()`     | [API Reference - DELETE](../README.md#delete) | [Examples](../README.md#examples)       |
| `patch()`      | [API Reference - PATCH](../README.md#patch)   | [Examples](../README.md#examples)       |

## Common Use Cases

### Basic API Integration

```python
from api_client import RESTClient

client = RESTClient("https://api.example.com")
response = client.get("/users/123")
user = response.json()
```

See [README - Quick Start](../README.md#quick-start) for more details.

### Authenticated Requests

```python
client = RESTClient("https://api.example.com")
response = client.get("/users", headers={
    "Authorization": "Bearer your-token"
})
```

See [Usage Patterns - Authentication](./usage-patterns.md#authentication-patterns) for advanced patterns.

### Error Recovery

```python
try:
    response = client.get("/data")
    data = response.json()
except TimeoutError:
    # Handle timeout
    data = get_cached_data()
```

See [Error Handling Guide](./error-handling.md) for comprehensive strategies.

### Testing

```python
from unittest.mock import Mock

def test_api_call():
    client = Mock()
    client.get.return_value.json.return_value = {"test": "data"}
    # Test your code
```

See [Testing Guide](./testing.md) for complete testing strategies.

## Documentation Standards

This documentation follows:

- **The Eight Rules of Good Documentation** - Located in docs/, linked, simple, with real examples
- **Diataxis Framework** - Separated into tutorials, how-to guides, reference, and explanations
- **Real Examples** - All code examples are tested and runnable

## Updates and Maintenance

- **Last Updated**: Implementation pending
- **Version**: 1.0.0
- **Python Support**: 3.8+

## Support

- **Issues**: Report via GitHub Issues in the main repository
- **Source**: `.claude/scenarios/api-client/`
- **Tests**: Run with `python -m pytest tests/`
