# APIClient Module

A robust, async HTTP client with automatic retry logic, exponential backoff, rate limit handling, and comprehensive error context for resilient API integrations.

## Features

- **Automatic retry with exponential backoff**: Configurable retry behavior for transient failures
- **Rate limit handling**: Automatic 429 response handling with Retry-After header support
- **Rich exception hierarchy**: Typed exceptions with full request/response context
- **Header sanitization**: Automatic masking of sensitive headers in logs
- **Type-safe**: Full type hints compatible with mypy --strict
- **Async context manager**: Lazy session initialization with proper cleanup

## Quick Start

```python
from amplihack.api_client import APIClient, RetryConfig

# Basic usage
async with APIClient(base_url="https://api.example.com") as client:
    response = await client.get("/users/123")
    print(f"User: {response.body}")

# Custom retry configuration
config = RetryConfig(max_attempts=5, base_delay=0.5, max_delay=30.0)

async with APIClient(
    base_url="https://api.example.com",
    retry_config=config,
    default_headers={"X-API-Key": "your-api-key"}
) as client:
    response = await client.post("/data", body={"key": "value"})
```

## Exception Handling

```python
from amplihack.api_client import (
    APIClient, APIClientError, RateLimitError, RetryExhaustedError
)

async with APIClient(base_url="https://api.example.com") as client:
    try:
        response = await client.get("/resource")
    except RateLimitError as e:
        print(f"Rate limited. Retry after: {e.retry_after} seconds")
    except RetryExhaustedError as e:
        print(f"All {e.attempts} retries failed: {e.last_error}")
    except APIClientError as e:
        print(f"API error [{e.error_code}]: {e.message}")
```

## Configuration

### RetryConfig

| Field           | Type  | Default                   | Description             |
| --------------- | ----- | ------------------------- | ----------------------- |
| max_attempts    | int   | 3                         | Maximum retry attempts  |
| base_delay      | float | 1.0                       | Initial delay (seconds) |
| multiplier      | float | 2.0                       | Backoff multiplier      |
| max_delay       | float | 60.0                      | Maximum delay cap       |
| jitter          | float | 0.1                       | Random jitter factor    |
| retry_on_status | tuple | (429, 500, 502, 503, 504) | Status codes to retry   |

## Module Structure

```
api_client/
├── __init__.py      # Public exports
├── client.py        # Main APIClient class
├── models.py        # Dataclasses (HTTPMethod, RetryConfig, etc.)
├── exceptions.py    # Exception hierarchy
├── rate_limiter.py  # Rate limit handling
├── retry.py         # Exponential backoff
└── logging.py       # Header sanitization
```
