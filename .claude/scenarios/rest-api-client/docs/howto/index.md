# How-To Guides

Task-oriented guides for solving specific problems with the REST API Client.

## Configuration

- [Configure the Client](./configure-client.md) - Set up retry logic, rate limiting, and timeouts
- [Environment-Based Configuration](./configure-client.md#environment-based-configuration) - Configure from environment variables

## Error Handling

- [Handle Errors](./error-handling.md) - Implement robust error handling
- [Retry Strategies](./error-handling.md#retry-strategies) - Configure automatic and manual retries
- [Circuit Breaker Pattern](./error-handling.md#circuit-breaker-pattern) - Protect against cascading failures

## Authentication

- [Add API Key Authentication](./configure-client.md#configure-default-headers) - Use API keys in headers
- [Bearer Token Authentication](./configure-client.md#configure-default-headers) - Work with OAuth tokens

## Performance

- [Implement Caching](./best-practices.md#implement-caching-for-expensive-operations) - Cache responses for performance
- [Batch Requests](./best-practices.md#batch-requests-when-possible) - Optimize multiple API calls
- [Handle Pagination](./best-practices.md#use-pagination-for-large-data-sets) - Work with paginated endpoints

## Best Practices

- [Production Best Practices](./best-practices.md) - Guidelines for production use
- [Security Best Practices](./best-practices.md#security-best-practices) - Keep your API usage secure
- [Testing Strategies](./best-practices.md#testing-strategies) - Test your API integrations

## Common Tasks

### Make a Simple Request

```python
from rest_api_client import APIClient

client = APIClient(base_url="https://api.example.com")
response = client.get("/users/123")
print(response.data)
```

### Handle Rate Limiting

```python
from rest_api_client import RateLimitConfig

client = APIClient(
    base_url="https://api.example.com",
    rate_limit_config=RateLimitConfig(
        requests_per_second=10,
        wait_on_limit=True
    )
)
```

### Add Authentication

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer your-token"}
)
```

### Configure Retries

```python
from rest_api_client import RetryConfig

client = APIClient(
    base_url="https://api.example.com",
    retry_config=RetryConfig(
        max_attempts=5,
        backoff_factor=2.0
    )
)
```

## Quick Links

- [API Reference](../reference/api.md) - Complete API documentation
- [Getting Started](../tutorials/getting-started.md) - Learn the basics
- [Architecture](../concepts/architecture.md) - Understand the design
