# How to Configure the REST API Client

This guide covers all configuration options for the amplihack REST API Client.

## Contents

- [Basic Configuration](#basic-configuration)
- [Retry Configuration](#retry-configuration)
- [Rate Limiting](#rate-limiting)
- [Timeout Configuration](#timeout-configuration)
- [Header Management](#header-management)
- [Logging Configuration](#logging-configuration)
- [Environment-Based Config](#environment-based-config)
- [Advanced Patterns](#advanced-patterns)

## Basic Configuration

### Minimal Setup

```python
from amplihack.api_client import APIClient

# Minimum required configuration
client = APIClient(base_url="https://api.example.com")
```

### Standard Setup

```python
from amplihack.api_client import APIClient

client = APIClient(
    base_url="https://api.example.com",
    headers={
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json"
    },
    timeout=30.0
)
```

## Retry Configuration

### Default Retry Behavior

By default, the client retries on these status codes:

- 429 (Too Many Requests)
- 502 (Bad Gateway)
- 503 (Service Unavailable)
- 504 (Gateway Timeout)

```python
from amplihack.api_client import APIClient, RetryConfig

# Default configuration
default_retry = RetryConfig()
# max_retries=3, initial_delay=1.0, max_delay=60.0

client = APIClient(
    base_url="https://api.example.com",
    retry_config=default_retry
)
```

### Custom Retry Strategy

```python
from amplihack.api_client import RetryConfig

# Aggressive retry for critical operations
aggressive_retry = RetryConfig(
    max_retries=10,
    initial_delay=0.5,
    max_delay=120.0,
    exponential_base=2.0,
    jitter=True,  # Add randomness to prevent thundering herd
    retry_on_statuses={429, 500, 502, 503, 504}
)

# Conservative retry for fast-fail scenarios
conservative_retry = RetryConfig(
    max_retries=1,
    initial_delay=1.0,
    max_delay=2.0,
    retry_on_statuses={503}  # Only retry on service unavailable
)

# No retry
no_retry = RetryConfig(max_retries=0)
```

### Exponential Backoff Examples

```python
# Standard exponential backoff: 1s, 2s, 4s, 8s, 16s...
standard = RetryConfig(
    initial_delay=1.0,
    exponential_base=2.0
)

# Slower backoff: 2s, 3s, 4.5s, 6.75s...
slower = RetryConfig(
    initial_delay=2.0,
    exponential_base=1.5
)

# Fast backoff with cap: 0.1s, 0.2s, 0.4s, 0.8s, 1.0s (capped)
fast = RetryConfig(
    initial_delay=0.1,
    exponential_base=2.0,
    max_delay=1.0
)
```

## Rate Limiting

### Basic Rate Limiting

```python
from amplihack.api_client import RateLimitHandler

# 10 requests per second with burst of 20
handler = RateLimitHandler(
    calls_per_second=10,
    burst_size=20
)

client = APIClient(
    base_url="https://api.example.com",
    rate_limit_handler=handler
)
```

### Adaptive Rate Limiting

```python
from amplihack.api_client import RateLimitHandler

# Respects server's Retry-After header
adaptive_handler = RateLimitHandler(
    calls_per_second=100,
    burst_size=200,
    respect_retry_after=True,  # Automatically adjust based on 429 responses
    min_delay=0.01,  # Minimum 10ms between requests
    max_delay=60.0   # Maximum 60s delay
)
```

### Per-Endpoint Rate Limiting

```python
from amplihack.api_client import APIClient, RateLimitHandler

class EndpointAwareClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.handlers = {
            "/search": RateLimitHandler(calls_per_second=1),  # Search is expensive
            "/users": RateLimitHandler(calls_per_second=100),  # Users is fast
            "default": RateLimitHandler(calls_per_second=10)   # Everything else
        }

    def get_handler(self, path: str) -> RateLimitHandler:
        for endpoint, handler in self.handlers.items():
            if path.startswith(endpoint):
                return handler
        return self.handlers["default"]

    async def request(self, method: str, path: str, **kwargs):
        handler = self.get_handler(path)
        async with APIClient(
            base_url=self.base_url,
            rate_limit_handler=handler
        ) as client:
            return await getattr(client, method)(path, **kwargs)
```

## Timeout Configuration

### Per-Request Timeouts

```python
# Global timeout
client = APIClient(
    base_url="https://api.example.com",
    timeout=30.0  # 30 seconds for all requests
)

# Override for specific requests
async with client:
    # Quick timeout for health check
    health = await client.get("/health", timeout=1.0)

    # Long timeout for data export
    export = await client.get("/export/large-dataset", timeout=300.0)
```

### Timeout Strategies

```python
from amplihack.api_client import APIClient
import asyncio

class TimeoutStrategy:
    FAST = 5.0      # For cached/simple queries
    STANDARD = 30.0 # For most API calls
    SLOW = 120.0    # For complex computations
    EXPORT = 600.0  # For large data exports

async def smart_request(client: APIClient, endpoint: str):
    # Choose timeout based on endpoint
    timeouts = {
        "/health": TimeoutStrategy.FAST,
        "/search": TimeoutStrategy.STANDARD,
        "/analytics": TimeoutStrategy.SLOW,
        "/export": TimeoutStrategy.EXPORT
    }

    timeout = timeouts.get(endpoint, TimeoutStrategy.STANDARD)
    return await client.get(endpoint, timeout=timeout)
```

## Header Management

### Static Headers

```python
# Set at client level
client = APIClient(
    base_url="https://api.example.com",
    headers={
        "X-API-Key": "secret-key",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
)
```

### Dynamic Headers

```python
from datetime import datetime
import hashlib

class AuthenticatedClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def generate_signature(self, path: str) -> str:
        timestamp = datetime.utcnow().isoformat()
        message = f"{path}{timestamp}{self.api_key}"
        return hashlib.sha256(message.encode()).hexdigest()

    async def request(self, method: str, path: str, **kwargs):
        headers = kwargs.get("headers", {})
        headers.update({
            "X-Timestamp": datetime.utcnow().isoformat(),
            "X-Signature": self.generate_signature(path)
        })

        async with APIClient(base_url=self.base_url) as client:
            return await getattr(client, method)(path, headers=headers, **kwargs)
```

### Header Priority

Headers are merged in this order (later overrides earlier):

1. Client-level headers (constructor)
2. Method-level headers (get/post/etc.)
3. Request-specific headers

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={"X-Version": "1.0"}  # Lowest priority
)

async with client:
    response = await client.get(
        "/users",
        headers={"X-Version": "2.0"}  # Overrides client-level
    )
```

## Logging Configuration

### Basic Logging

```python
import logging
from amplihack.api_client import APIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Client will automatically log
client = APIClient(base_url="https://api.example.com")
```

### Structured Logging

```python
import structlog
from amplihack.api_client import APIClient

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Logs will be in JSON format
client = APIClient(base_url="https://api.example.com")
```

### Custom Log Levels

```python
import logging

# Different log levels for different components
logging.getLogger("amplihack.api_client.client").setLevel(logging.DEBUG)
logging.getLogger("amplihack.api_client.retry").setLevel(logging.WARNING)
logging.getLogger("amplihack.api_client.ratelimit").setLevel(logging.INFO)
```

## Environment-Based Config

### Using Environment Variables

```python
import os
from amplihack.api_client import APIClient, RetryConfig

class ConfigFromEnv:
    @staticmethod
    def create_client() -> APIClient:
        # Read from environment with defaults
        base_url = os.getenv("API_BASE_URL", "https://api.example.com")
        api_key = os.getenv("API_KEY", "")
        timeout = float(os.getenv("API_TIMEOUT", "30"))
        max_retries = int(os.getenv("API_MAX_RETRIES", "3"))

        retry_config = RetryConfig(max_retries=max_retries)

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        return APIClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            retry_config=retry_config
        )
```

### Configuration File

```python
import yaml
from pathlib import Path
from amplihack.api_client import APIClient, RetryConfig

class ConfigFromFile:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self.load_config(config_path)

    def load_config(self, path: str) -> dict:
        config_file = Path(path)
        if config_file.exists():
            return yaml.safe_load(config_file.read_text())
        return {}

    def create_client(self, profile: str = "default") -> APIClient:
        profile_config = self.config.get(profile, {})

        retry_config = RetryConfig(
            **profile_config.get("retry", {})
        )

        return APIClient(
            base_url=profile_config["base_url"],
            headers=profile_config.get("headers", {}),
            timeout=profile_config.get("timeout", 30),
            retry_config=retry_config
        )
```

Example `config.yaml`:

```yaml
default:
  base_url: https://api.example.com
  timeout: 30
  headers:
    User-Agent: MyApp/1.0
  retry:
    max_retries: 3
    initial_delay: 1.0

production:
  base_url: https://api.production.com
  timeout: 60
  headers:
    User-Agent: MyApp/1.0-prod
  retry:
    max_retries: 5
    initial_delay: 2.0
```

## Advanced Patterns

### Connection Pooling

```python
from amplihack.api_client import APIClient

# Configure connection pool
client = APIClient(
    base_url="https://api.example.com",
    pool_connections=10,  # Maximum number of connections
    pool_maxsize=10,      # Maximum pool size
    pool_block=False      # Don't block when pool is full
)
```

### Proxy Configuration

```python
client = APIClient(
    base_url="https://api.example.com",
    proxies={
        "http": "http://proxy.example.com:8080",
        "https": "https://proxy.example.com:8080"
    }
)
```

### SSL Verification

```python
# Disable SSL verification (not recommended for production)
client = APIClient(
    base_url="https://api.example.com",
    verify_ssl=False
)

# Custom CA bundle
client = APIClient(
    base_url="https://api.example.com",
    ca_bundle="/path/to/ca-bundle.crt"
)
```

### Request Hooks

```python
from amplihack.api_client import APIClient

class HookedClient(APIClient):
    async def before_request(self, request):
        """Called before each request"""
        print(f"Making request to {request.url}")
        return request

    async def after_response(self, response):
        """Called after each response"""
        print(f"Got response: {response.status_code}")
        return response
```

## Configuration Best Practices

### 1. Use Configuration Classes

```python
from dataclasses import dataclass
from amplihack.api_client import APIClient, RetryConfig

@dataclass
class APIConfig:
    base_url: str
    api_key: str
    timeout: float = 30.0
    max_retries: int = 3

    def create_client(self) -> APIClient:
        return APIClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
            retry_config=RetryConfig(max_retries=self.max_retries)
        )
```

### 2. Separate Environments

```python
class EnvironmentConfig:
    DEVELOPMENT = APIConfig(
        base_url="http://localhost:8000",
        api_key="dev-key",
        timeout=60.0
    )

    STAGING = APIConfig(
        base_url="https://staging.api.example.com",
        api_key=os.getenv("STAGING_API_KEY"),
        timeout=30.0
    )

    PRODUCTION = APIConfig(
        base_url="https://api.example.com",
        api_key=os.getenv("PROD_API_KEY"),
        timeout=30.0,
        max_retries=5
    )
```

### 3. Validate Configuration

```python
def validate_config(config: APIConfig) -> None:
    if not config.base_url:
        raise ValueError("base_url is required")

    if not config.api_key:
        raise ValueError("api_key is required")

    if config.timeout <= 0:
        raise ValueError("timeout must be positive")

    if config.max_retries < 0:
        raise ValueError("max_retries must be non-negative")
```

## See Also

- [API Reference](../reference/api-client.md) - Complete API documentation
- [Usage Guide](./api-client-usage.md) - Common usage patterns
- [Error Handling](../concepts/api-client-errors.md) - Understanding exceptions
