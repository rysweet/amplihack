# Configuration Options Reference

Complete reference for all configuration options in the REST API Client library.

## APIConfig

Main configuration object for the API client.

### Constructor Parameters

```python
from rest_api_client.config import APIConfig

config = APIConfig(
    base_url="https://api.example.com",     # Required
    timeout=30,                             # Optional, default: 30
    max_retries=3,                          # Optional, default: 3
    rate_limit_calls=100,                   # Optional, default: None
    rate_limit_period=60,                   # Optional, default: 60
    headers={},                             # Optional, default: {}
    verify_ssl=True,                        # Optional, default: True
    proxy=None,                             # Optional, default: None
    proxy_auth=None                         # Optional, default: None
)
```

### Parameter Details

#### base_url

- **Type**: `str`
- **Required**: Yes
- **Description**: Base URL for all API requests
- **Example**: `"https://api.example.com"` or `"https://api.example.com/v2"`

#### timeout

- **Type**: `int`
- **Default**: `30`
- **Description**: Request timeout in seconds
- **Valid Range**: Must be positive
- **Example**: `60` for 60-second timeout

#### max_retries

- **Type**: `int`
- **Default**: `3`
- **Description**: Maximum number of retry attempts
- **Valid Range**: 0 to disable retries, positive for retry count
- **Example**: `5` for up to 5 retry attempts

#### rate_limit_calls

- **Type**: `Optional[int]`
- **Default**: `None` (no rate limiting)
- **Description**: Maximum number of calls allowed per period
- **Example**: `100` for 100 calls per period

#### rate_limit_period

- **Type**: `int`
- **Default**: `60`
- **Description**: Time period for rate limiting in seconds
- **Example**: `3600` for hourly rate limit

#### headers

- **Type**: `dict`
- **Default**: `{}`
- **Description**: Default headers for all requests
- **Example**:
  ```python
  headers={
      "Authorization": "Bearer token123",
      "User-Agent": "MyApp/1.0",
      "Accept": "application/json"
  }
  ```

#### verify_ssl

- **Type**: `bool`
- **Default**: `True`
- **Description**: Whether to verify SSL certificates
- **Warning**: Only set to `False` for development/testing

#### proxy

- **Type**: `Optional[str]`
- **Default**: `None`
- **Description**: Proxy server URL
- **Example**: `"http://proxy.company.com:8080"`

#### proxy_auth

- **Type**: `Optional[tuple]`
- **Default**: `None`
- **Description**: Proxy authentication credentials
- **Example**: `("username", "password")`

### Configuration Examples

#### Basic Configuration

```python
config = APIConfig(base_url="https://api.example.com")
```

#### Production Configuration

```python
config = APIConfig(
    base_url="https://api.production.com",
    timeout=60,
    max_retries=5,
    rate_limit_calls=1000,
    rate_limit_period=3600,
    headers={
        "Authorization": f"Bearer {api_token}",
        "User-Agent": "ProductionApp/2.0"
    },
    verify_ssl=True
)
```

#### Development Configuration

```python
config = APIConfig(
    base_url="http://localhost:8000",
    timeout=120,  # Longer timeout for debugging
    max_retries=0,  # No retries during development
    headers={"X-Debug": "true"},
    verify_ssl=False  # Self-signed certificates
)
```

#### With Proxy

```python
config = APIConfig(
    base_url="https://api.example.com",
    proxy="http://corporate.proxy:3128",
    proxy_auth=("user", "pass")
)
```

## RetryConfig

Configuration for retry behavior.

### Constructor Parameters

```python
from rest_api_client.config import RetryConfig

retry_config = RetryConfig(
    max_attempts=3,                         # Optional, default: 3
    initial_delay=1.0,                      # Optional, default: 1.0
    max_delay=60.0,                         # Optional, default: 60.0
    exponential_base=2.0,                   # Optional, default: 2.0
    retry_on_statuses=[429, 500, 502, 503, 504],  # Optional
    retry_on_exceptions=[ConnectionError, TimeoutError],  # Optional
    jitter=False,                           # Optional, default: False
    jitter_range=0.3                        # Optional, default: 0.3
)
```

### Parameter Details

#### max_attempts

- **Type**: `int`
- **Default**: `3`
- **Description**: Total number of attempts (initial + retries)
- **Example**: `5` means 1 initial attempt + 4 retries

#### initial_delay

- **Type**: `float`
- **Default**: `1.0`
- **Description**: Initial delay between retries in seconds
- **Example**: `0.5` for 500ms initial delay

#### max_delay

- **Type**: `float`
- **Default**: `60.0`
- **Description**: Maximum delay between retries in seconds
- **Example**: `300.0` for 5-minute maximum

#### exponential_base

- **Type**: `float`
- **Default**: `2.0`
- **Description**: Multiplier for exponential backoff
- **Example**: `1.5` for slower backoff, `3.0` for faster

#### retry_on_statuses

- **Type**: `List[int]`
- **Default**: `[429, 500, 502, 503, 504]`
- **Description**: HTTP status codes that trigger retry
- **Example**: `[429, 503]` for only rate limit and service unavailable

#### retry_on_exceptions

- **Type**: `List[Type[Exception]]`
- **Default**: `[ConnectionError, TimeoutError]`
- **Description**: Exception types that trigger retry
- **Example**: `[ConnectionError]` for only connection errors

#### jitter

- **Type**: `bool`
- **Default**: `False`
- **Description**: Whether to add random jitter to delays
- **Purpose**: Prevents thundering herd problem

#### jitter_range

- **Type**: `float`
- **Default**: `0.3`
- **Description**: Jitter range as fraction of delay
- **Example**: `0.5` for ±50% jitter

### Retry Examples

#### Conservative Retry

```python
retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=2.0,
    exponential_base=2.0
)
# Delays: 2s, 4s, 8s
```

#### Aggressive Retry

```python
retry_config = RetryConfig(
    max_attempts=10,
    initial_delay=0.1,
    max_delay=30.0,
    exponential_base=1.5
)
# Many quick retries with gradual backoff
```

#### Rate Limit Focused

```python
retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=5.0,
    retry_on_statuses=[429],  # Only retry rate limits
    exponential_base=1.2  # Slow backoff
)
```

#### With Jitter

```python
retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    jitter=True,
    jitter_range=0.3  # ±30% randomness
)
# Prevents synchronized retries
```

## RateLimiterConfig

Configuration for rate limiting behavior.

### Constructor Parameters

```python
from rest_api_client.config import RateLimiterConfig

rate_config = RateLimiterConfig(
    calls=100,                              # Required
    period=60,                              # Required
    burst=None,                             # Optional, defaults to calls
    refill_rate=None                        # Optional
)
```

### Parameter Details

#### calls

- **Type**: `int`
- **Required**: Yes
- **Description**: Maximum calls allowed per period
- **Example**: `100` for 100 calls

#### period

- **Type**: `int`
- **Required**: Yes
- **Description**: Time period in seconds
- **Example**: `60` for per-minute limiting

#### burst

- **Type**: `Optional[int]`
- **Default**: Same as `calls`
- **Description**: Maximum burst capacity
- **Example**: `10` to allow bursts of 10 requests

#### refill_rate

- **Type**: `Optional[float]`
- **Default**: `calls / period`
- **Description**: Token refill rate per second
- **Example**: `1.67` for 100 calls/minute

### Rate Limiter Examples

#### Simple Rate Limit

```python
rate_config = RateLimiterConfig(
    calls=60,
    period=60  # 60 requests per minute
)
```

#### With Burst Capacity

```python
rate_config = RateLimiterConfig(
    calls=100,
    period=60,
    burst=10  # Allow 10 rapid requests
)
```

## Environment Variables

The client can be configured using environment variables:

### Supported Variables

```bash
# Base configuration
API_BASE_URL="https://api.example.com"
API_TIMEOUT="30"
API_MAX_RETRIES="3"

# Authentication
API_TOKEN="your-api-token"
API_KEY="your-api-key"  # pragma: allowlist secret

# Rate limiting
API_RATE_LIMIT_CALLS="100"
API_RATE_LIMIT_PERIOD="60"

# Proxy
HTTP_PROXY="http://proxy:8080"
HTTPS_PROXY="https://proxy:8443"
PROXY_USERNAME="user"
PROXY_PASSWORD="pass"  # pragma: allowlist secret

# SSL
API_VERIFY_SSL="true"
SSL_CERT_FILE="/path/to/cert.pem"
```

### Loading from Environment

```python
import os
from rest_api_client.config import APIConfig

def load_config_from_env() -> APIConfig:
    """Load configuration from environment variables."""
    return APIConfig(
        base_url=os.getenv("API_BASE_URL"),
        timeout=int(os.getenv("API_TIMEOUT", "30")),
        max_retries=int(os.getenv("API_MAX_RETRIES", "3")),
        rate_limit_calls=int(os.getenv("API_RATE_LIMIT_CALLS", "0")) or None,
        rate_limit_period=int(os.getenv("API_RATE_LIMIT_PERIOD", "60")),
        headers={
            "Authorization": f"Bearer {os.getenv('API_TOKEN')}"
        } if os.getenv("API_TOKEN") else {},
        verify_ssl=os.getenv("API_VERIFY_SSL", "true").lower() == "true",
        proxy=os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    )

# Usage
config = load_config_from_env()
client = APIClient(config=config)
```

## Configuration Files

### JSON Configuration

```json
{
  "base_url": "https://api.example.com",
  "timeout": 30,
  "max_retries": 3,
  "rate_limit": {
    "calls": 100,
    "period": 60
  },
  "headers": {
    "User-Agent": "MyApp/1.0"
  },
  "retry": {
    "max_attempts": 5,
    "initial_delay": 1.0,
    "exponential_base": 2.0
  }
}
```

### YAML Configuration

```yaml
base_url: https://api.example.com
timeout: 30
max_retries: 3
rate_limit:
  calls: 100
  period: 60
headers:
  User-Agent: MyApp/1.0
retry:
  max_attempts: 5
  initial_delay: 1.0
  exponential_base: 2.0
```

### Loading from File

```python
import json
import yaml
from rest_api_client.config import APIConfig, RetryConfig

def load_config_from_json(filepath: str) -> APIConfig:
    """Load configuration from JSON file."""
    with open(filepath) as f:
        data = json.load(f)

    retry_config = None
    if "retry" in data:
        retry_config = RetryConfig(**data["retry"])

    return APIConfig(
        base_url=data["base_url"],
        timeout=data.get("timeout", 30),
        max_retries=data.get("max_retries", 3),
        rate_limit_calls=data.get("rate_limit", {}).get("calls"),
        rate_limit_period=data.get("rate_limit", {}).get("period", 60),
        headers=data.get("headers", {})
    ), retry_config

def load_config_from_yaml(filepath: str) -> APIConfig:
    """Load configuration from YAML file."""
    with open(filepath) as f:
        data = yaml.safe_load(f)
    # Similar to JSON loading
    return load_config_from_json(filepath)  # Reuse logic

# Usage
config, retry_config = load_config_from_json("config.json")
client = APIClient(config=config, retry_config=retry_config)
```

## Configuration Validation

The library validates configuration on initialization:

```python
from rest_api_client.config import APIConfig

# Invalid configuration examples
try:
    config = APIConfig(base_url="")  # Empty base_url
except ValueError as e:
    print(f"Error: {e}")  # Error: base_url is required

try:
    config = APIConfig(
        base_url="https://api.example.com",
        timeout=-1  # Negative timeout
    )
except ValueError as e:
    print(f"Error: {e}")  # Error: timeout must be positive

try:
    config = APIConfig(
        base_url="https://api.example.com",
        max_retries=-5  # Negative retries
    )
except ValueError as e:
    print(f"Error: {e}")  # Error: max_retries must be non-negative
```

## Best Practices

1. **Use configuration objects** - More maintainable than individual parameters
2. **Validate early** - Check configuration at startup
3. **Use environment variables** - For sensitive data like tokens
4. **Document your configuration** - Keep a template file
5. **Test different configurations** - Ensure your app handles various setups
6. **Monitor configuration effectiveness** - Track retry rates, timeouts
7. **Use appropriate defaults** - But allow overrides
8. **Separate environments** - Dev, staging, production configs
