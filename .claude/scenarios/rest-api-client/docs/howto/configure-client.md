# How to Configure the REST API Client

Configure retry logic, rate limiting, timeouts, and other client behaviors.

## Basic Configuration

### Set Base URL and Timeout

```python
from rest_api_client import APIClient

client = APIClient(
    base_url="https://api.example.com",
    timeout=60  # 60 second timeout
)
```

### Configure Default Headers

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json",
        "X-API-Version": "v2"
    }
)
```

## Retry Configuration

### Enable Automatic Retries

```python
from rest_api_client import APIClient, RetryConfig

retry_config = RetryConfig(
    max_attempts=5,              # Try up to 5 times
    backoff_factor=2.0,          # Double wait time between retries
    max_backoff=30,              # Maximum 30 seconds between retries
    retry_on_status=[429, 500, 502, 503, 504]  # Which status codes to retry
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)

# This request will automatically retry on failure
response = client.get("/flaky-endpoint")
```

### Custom Retry Logic Example

```python
from rest_api_client import APIClient, RetryConfig, ConnectionException, TimeoutException

# Retry only on network errors, not server errors
retry_config = RetryConfig(
    max_attempts=3,
    backoff_factor=1.5,
    retry_on_status=[],  # Don't retry based on status codes
    retry_on_exception=[ConnectionException, TimeoutException]  # Only retry network issues
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)
```

### Disable Retries

```python
# Set max_attempts to 1 to disable retries
retry_config = RetryConfig(max_attempts=1)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)
```

## Rate Limiting Configuration

### Basic Rate Limiting

```python
from rest_api_client import APIClient, RateLimitConfig

# Allow 10 requests per second with burst of 20
rate_limit_config = RateLimitConfig(
    requests_per_second=10.0,
    burst_size=20,
    wait_on_limit=True  # Wait when limit reached
)

client = APIClient(
    base_url="https://api.example.com",
    rate_limit_config=rate_limit_config
)

# These requests will be rate limited automatically
for i in range(100):
    response = client.get(f"/item/{i}")
    print(f"Got item {i}")
```

### Strict Rate Limiting (No Waiting)

```python
from rest_api_client import RateLimitConfig, RateLimitException

# Raise exception instead of waiting
rate_limit_config = RateLimitConfig(
    requests_per_second=5.0,
    burst_size=10,
    wait_on_limit=False  # Raise exception instead
)

client = APIClient(
    base_url="https://api.example.com",
    rate_limit_config=rate_limit_config
)

try:
    for i in range(100):
        response = client.get(f"/item/{i}")
except RateLimitException as e:
    print(f"Rate limited! Wait {e.retry_after} seconds")
```

### API-Specific Rate Limits

```python
# GitHub API: 5000 requests per hour = ~1.4 per second
github_client = APIClient(
    base_url="https://api.github.com",
    rate_limit_config=RateLimitConfig(
        requests_per_second=1.3,  # Stay under limit
        burst_size=10
    )
)

# Twitter API: 300 requests per 15 minutes = 0.33 per second
twitter_client = APIClient(
    base_url="https://api.twitter.com",
    rate_limit_config=RateLimitConfig(
        requests_per_second=0.3,
        burst_size=5
    )
)
```

## SSL Configuration

### Disable SSL Verification (Development Only)

```python
# WARNING: Only use in development/testing
client = APIClient(
    base_url="https://self-signed.local",
    verify_ssl=False
)
```

### Custom SSL Certificate

```python
import ssl

# Create custom SSL context
ssl_context = ssl.create_default_context()
ssl_context.load_cert_chain(
    certfile="/path/to/client.crt",
    keyfile="/path/to/client.key"
)

client = APIClient(
    base_url="https://secure-api.example.com",
    ssl_context=ssl_context
)
```

## Logging Configuration

### Set Log Level

```python
client = APIClient(
    base_url="https://api.example.com",
    log_level="DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
)

# Debug logs will show:
# - Request details (sanitized)
# - Retry attempts
# - Rate limit status
# - Response times
```

### Custom Logger

```python
import logging

# Configure custom logger
logger = logging.getLogger("my_api_client")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("api_requests.log")
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

client = APIClient(
    base_url="https://api.example.com",
    logger=logger
)
```

## Complete Configuration Example

```python
from rest_api_client import APIClient, RetryConfig, RateLimitConfig

def create_production_client():
    """Create a fully configured production client."""

    # Retry configuration for resilience
    retry_config = RetryConfig(
        max_attempts=3,
        backoff_factor=2.0,
        max_backoff=30,
        retry_on_status=[429, 500, 502, 503, 504]
    )

    # Rate limiting to respect API limits
    rate_limit_config = RateLimitConfig(
        requests_per_second=50.0,
        burst_size=100,
        wait_on_limit=True
    )

    # Create client with all configurations
    client = APIClient(
        base_url="https://api.production.com",
        headers={
            "User-Agent": "MyApp/2.0",
            "X-API-Key": "secret-key-from-env"
        },
        timeout=30,
        verify_ssl=True,
        retry_config=retry_config,
        rate_limit_config=rate_limit_config,
        log_level="INFO"
    )

    return client

# Use the configured client
client = create_production_client()
response = client.get("/users/me")
print(f"Authenticated as: {response.data['username']}")
```

## Environment-Based Configuration

```python
import os
from rest_api_client import APIClient, RetryConfig, RateLimitConfig

def create_client_from_env():
    """Create client configured from environment variables."""

    # Read from environment
    base_url = os.environ.get("API_BASE_URL", "https://api.example.com")
    api_key = os.environ.get("API_KEY", "")
    timeout = int(os.environ.get("API_TIMEOUT", "30"))
    max_retries = int(os.environ.get("API_MAX_RETRIES", "3"))
    rate_limit = float(os.environ.get("API_RATE_LIMIT", "10.0"))

    # Build configuration
    retry_config = RetryConfig(max_attempts=max_retries) if max_retries > 1 else None
    rate_limit_config = RateLimitConfig(requests_per_second=rate_limit)

    # Create client
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    return APIClient(
        base_url=base_url,
        headers=headers,
        timeout=timeout,
        retry_config=retry_config,
        rate_limit_config=rate_limit_config
    )

# Usage
client = create_client_from_env()
```

## Configuration Validation

```python
from rest_api_client import APIClient, RetryConfig, RateLimitConfig

def validate_and_create_client(config_dict):
    """Validate configuration before creating client."""

    # Validate retry config
    if "retry_config" in config_dict:
        retry = config_dict["retry_config"]
        if retry["max_attempts"] < 1:
            raise ValueError("max_attempts must be at least 1")
        if retry["backoff_factor"] < 1.0:
            raise ValueError("backoff_factor should be >= 1.0")

    # Validate rate limit config
    if "rate_limit_config" in config_dict:
        rate = config_dict["rate_limit_config"]
        if rate["requests_per_second"] <= 0:
            raise ValueError("requests_per_second must be positive")
        if rate["burst_size"] < 1:
            raise ValueError("burst_size must be at least 1")

    # Validate timeout
    if config_dict.get("timeout", 30) <= 0:
        raise ValueError("timeout must be positive")

    return APIClient(**config_dict)

# Example usage
try:
    client = validate_and_create_client({
        "base_url": "https://api.example.com",
        "timeout": 45,
        "retry_config": RetryConfig(max_attempts=5, backoff_factor=2.0),
        "rate_limit_config": RateLimitConfig(requests_per_second=100)
    })
    print("Client created successfully")
except ValueError as e:
    print(f"Configuration error: {e}")
```

## Next Steps

- [Error Handling Guide](./error-handling.md) - Handle errors gracefully
- [Authentication Guide](./authentication.md) - Work with different auth methods
- [Advanced Features Tutorial](../tutorials/advanced-features.md) - Deep dive into retry and rate limiting
