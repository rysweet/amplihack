# REST API Client - Configuration Guide

Complete guide to configuring the REST API Client for different scenarios and requirements.

## Table of Contents

- [Basic Configuration](#basic-configuration)
- [Retry Configuration](#retry-configuration)
- [Rate Limiting Configuration](#rate-limiting-configuration)
- [Security Configuration](#security-configuration)
- [Logging Configuration](#logging-configuration)
- [Performance Tuning](#performance-tuning)
- [Environment Variables](#environment-variables)
- [Configuration Patterns](#configuration-patterns)

## Basic Configuration

### Minimal Setup

```python
from rest_api_client import APIClient

# Minimal configuration - just base URL
client = APIClient(base_url="https://api.example.com")
```

### Standard Setup

```python
from rest_api_client import APIClient

client = APIClient(
    base_url="https://api.example.com",
    timeout=30,                        # 30 second timeout
    max_retries=3,                     # Retry failed requests up to 3 times
    headers={                           # Default headers for all requests
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json"
    }
)
```

### Full Configuration

```python
from rest_api_client import APIClient, RetryConfig, RateLimitConfig
import logging

client = APIClient(
    # Connection settings
    base_url="https://api.example.com",
    timeout=(5.0, 30.0),               # (connect_timeout, read_timeout)
    verify_ssl=True,
    proxy="http://proxy.example.com:8080",

    # Authentication
    headers={
        "Authorization": "Bearer token-here",
        "X-API-Version": "2.0"
    },

    # Retry behavior
    retry_config=RetryConfig(
        max_attempts=5,
        initial_delay=1.0,
        max_delay=60.0,
        exponential_base=2,
        jitter=True
    ),

    # Rate limiting
    rate_limit_config=RateLimitConfig(
        max_requests_per_second=10,
        respect_retry_after=True
    ),

    # Logging
    log_level=logging.DEBUG,
    log_sanitize_headers=["Authorization", "X-API-Key"],
    log_sanitize_params=["password", "secret"]
)
```

## Retry Configuration

### Default Retry Behavior

By default, the client retries on these status codes:

- 408 (Request Timeout)
- 429 (Too Many Requests)
- 500 (Internal Server Error)
- 502 (Bad Gateway)
- 503 (Service Unavailable)
- 504 (Gateway Timeout)

And these exceptions:

- ConnectionError
- TimeoutError

### Custom Retry Strategy

```python
from rest_api_client import RetryConfig

# Aggressive retry for critical operations
critical_retry = RetryConfig(
    max_attempts=10,
    initial_delay=0.5,
    max_delay=120.0,
    exponential_base=2,
    jitter=True,
    retry_on_status=[408, 429, 500, 502, 503, 504, 520, 521, 522, 523],
    retry_on_exceptions=[ConnectionError, TimeoutError, OSError]
)

# Conservative retry for non-critical operations
conservative_retry = RetryConfig(
    max_attempts=2,
    initial_delay=2.0,
    max_delay=10.0,
    exponential_base=2,
    jitter=False,
    retry_on_status=[500, 503],
    retry_on_exceptions=[ConnectionError]
)

# No retry
no_retry = RetryConfig(max_attempts=1)
```

### Exponential Backoff Examples

```python
# Standard exponential backoff: 1s, 2s, 4s, 8s, 16s
standard_backoff = RetryConfig(
    initial_delay=1.0,
    exponential_base=2,
    max_delay=60.0
)

# Fibonacci-like backoff: 1s, 2s, 3s, 5s, 8s
fibonacci_backoff = RetryConfig(
    initial_delay=1.0,
    exponential_base=1.618,  # Golden ratio
    max_delay=60.0
)

# Linear backoff: 2s, 4s, 6s, 8s, 10s
linear_backoff = RetryConfig(
    initial_delay=2.0,
    exponential_base=1.0,  # No exponential growth
    max_delay=60.0
)
```

## Rate Limiting Configuration

### Basic Rate Limiting

```python
from rest_api_client import RateLimitConfig

# Simple rate limiting
config = RateLimitConfig(
    max_requests_per_second=10,
    respect_retry_after=True
)
```

### Tiered Rate Limiting

```python
# Different limits for different time windows
config = RateLimitConfig(
    max_requests_per_second=10,    # Burst protection
    max_requests_per_minute=100,   # Sustained load limit
    max_requests_per_hour=1000,    # Daily quota management
    respect_retry_after=True,
    backoff_factor=2.0              # Double wait time on each limit hit
)
```

### API-Specific Rate Limiting

```python
# GitHub API style
github_config = RateLimitConfig(
    max_requests_per_hour=5000,
    respect_retry_after=True
)

# Stripe API style
stripe_config = RateLimitConfig(
    max_requests_per_second=100,
    respect_retry_after=True
)

# Twitter API style
twitter_config = RateLimitConfig(
    max_requests_per_minute=15,
    respect_retry_after=True
)
```

## Security Configuration

### SSL/TLS Configuration

```python
# Strict SSL verification (default)
client = APIClient(
    base_url="https://api.example.com",
    verify_ssl=True
)

# Custom CA bundle
client = APIClient(
    base_url="https://api.example.com",
    verify_ssl="/path/to/ca-bundle.crt"
)

# Disable SSL verification (development only!)
client = APIClient(
    base_url="https://api.example.com",
    verify_ssl=False  # WARNING: Insecure!
)
```

### Authentication Methods

```python
# Bearer token
client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer your-token-here"}
)

# API key in header
client = APIClient(
    base_url="https://api.example.com",
    headers={"X-API-Key": "your-api-key"}
)

# Basic authentication
client = APIClient(
    base_url="https://api.example.com",
    auth=("username", "password")
)

# Custom authentication
from rest_api_client import RequestSigner

signer = RequestSigner(
    secret_key="your-secret-key",
    algorithm="HS256"
)
client = APIClient(
    base_url="https://api.example.com",
    request_signer=signer
)
```

### Credential Sanitization

```python
# Prevent sensitive data from appearing in logs
client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer secret-token"},
    log_sanitize_headers=[
        "Authorization",
        "X-API-Key",
        "X-Secret-Token"
    ],
    log_sanitize_params=[
        "password",
        "token",
        "secret",
        "api_key"
    ]
)
```

## Logging Configuration

### Basic Logging

```python
import logging

# Configure Python logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Client will use configured logging
client = APIClient(
    base_url="https://api.example.com",
    log_level=logging.INFO
)
```

### Detailed Debug Logging

```python
import logging

# Enable debug logging for troubleshooting
logging.basicConfig(level=logging.DEBUG)

client = APIClient(
    base_url="https://api.example.com",
    log_level=logging.DEBUG
)

# Debug output includes:
# - Request method and URL
# - Request headers (sanitized)
# - Request body
# - Response status
# - Response headers
# - Response body
# - Retry attempts
# - Rate limit information
```

### Structured Logging

```python
import logging
import json

class StructuredFormatter(logging.Formatter):
    """Format logs as JSON for structured logging systems."""

    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None),
            "request_method": getattr(record, "method", None),
            "request_url": getattr(record, "url", None),
            "response_status": getattr(record, "status_code", None),
            "duration_ms": getattr(record, "duration_ms", None)
        }
        return json.dumps(log_obj)

# Configure structured logging
handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
logging.getLogger("rest_api_client").addHandler(handler)
logging.getLogger("rest_api_client").setLevel(logging.INFO)

client = APIClient(
    base_url="https://api.example.com",
    log_level=logging.INFO
)
```

## Performance Tuning

### Connection Pooling

```python
# Use session for connection reuse
with client.session() as session:
    # All requests in this block share connection pool
    for i in range(100):
        response = session.get(f"/items/{i}")
```

### Timeout Configuration

```python
# Different timeout strategies
quick_timeout = APIClient(
    base_url="https://api.example.com",
    timeout=5.0  # 5 seconds total
)

balanced_timeout = APIClient(
    base_url="https://api.example.com",
    timeout=(3.0, 30.0)  # 3s connect, 30s read
)

patient_timeout = APIClient(
    base_url="https://api.example.com",
    timeout=(10.0, 300.0)  # 10s connect, 5 min read
)
```

### Compression

```python
# Enable compression for large payloads
client = APIClient(
    base_url="https://api.example.com",
    headers={
        "Accept-Encoding": "gzip, deflate",
        "Content-Encoding": "gzip"
    }
)
```

## Environment Variables

### Supported Variables

```bash
# Base configuration
export REST_CLIENT_BASE_URL=https://api.example.com
export REST_CLIENT_TIMEOUT=30
export REST_CLIENT_MAX_RETRIES=3

# Security
export REST_CLIENT_SSL_VERIFY=true
export REST_CLIENT_PROXY=http://proxy:8080

# Authentication
export REST_CLIENT_API_KEY=your-api-key
export REST_CLIENT_AUTH_TOKEN=your-token

# Logging
export REST_CLIENT_LOG_LEVEL=DEBUG

# Rate limiting
export REST_CLIENT_MAX_RPS=10
export REST_CLIENT_MAX_RPM=100
```

### Loading from .env File

```python
import os
from dotenv import load_dotenv
from rest_api_client import APIClient

# Load environment variables
load_dotenv()

client = APIClient(
    base_url=os.getenv("REST_CLIENT_BASE_URL"),
    timeout=int(os.getenv("REST_CLIENT_TIMEOUT", 30)),
    max_retries=int(os.getenv("REST_CLIENT_MAX_RETRIES", 3)),
    headers={
        "Authorization": f"Bearer {os.getenv('REST_CLIENT_AUTH_TOKEN')}"
    }
)
```

## Configuration Patterns

### Pattern: Environment-Specific Configuration

```python
import os

def get_client():
    """Get client configured for current environment."""
    env = os.getenv("ENVIRONMENT", "development")

    configs = {
        "development": {
            "base_url": "http://localhost:8000",
            "timeout": 60,
            "max_retries": 5,
            "verify_ssl": False
        },
        "staging": {
            "base_url": "https://staging-api.example.com",
            "timeout": 30,
            "max_retries": 3,
            "verify_ssl": True
        },
        "production": {
            "base_url": "https://api.example.com",
            "timeout": 15,
            "max_retries": 2,
            "verify_ssl": True
        }
    }

    config = configs.get(env, configs["development"])
    return APIClient(**config)
```

### Pattern: Service-Specific Clients

```python
class APIClientFactory:
    """Factory for creating configured clients for different services."""

    @staticmethod
    def create_payment_client():
        """Client for payment service with strict retry policy."""
        return APIClient(
            base_url="https://payments.example.com",
            retry_config=RetryConfig(
                max_attempts=5,
                retry_on_status=[500, 502, 503, 504]
            )
        )

    @staticmethod
    def create_analytics_client():
        """Client for analytics with relaxed timeouts."""
        return APIClient(
            base_url="https://analytics.example.com",
            timeout=120,  # Analytics queries can be slow
            max_retries=1  # Don't retry analytics
        )

    @staticmethod
    def create_notification_client():
        """Client for notifications with rate limiting."""
        return APIClient(
            base_url="https://notifications.example.com",
            rate_limit_config=RateLimitConfig(
                max_requests_per_second=50,
                respect_retry_after=True
            )
        )
```

### Pattern: Configuration Validation

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ClientConfig:
    """Validated configuration for API client."""
    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    api_key: Optional[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.base_url.startswith("https://"):
            raise ValueError("Base URL must use HTTPS")

        if self.timeout <= 0 or self.timeout > 300:
            raise ValueError("Timeout must be between 0 and 300 seconds")

        if self.max_retries < 0 or self.max_retries > 10:
            raise ValueError("Max retries must be between 0 and 10")

    def create_client(self) -> APIClient:
        """Create client from validated config."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return APIClient(
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            headers=headers
        )

# Usage
config = ClientConfig(
    base_url="https://api.example.com",
    timeout=30.0,
    api_key="secret-key"
)
client = config.create_client()
```

## Default Values Reference

| Parameter           | Default Value | Description                    |
| ------------------- | ------------- | ------------------------------ |
| timeout             | 30            | Request timeout in seconds     |
| max_retries         | 3             | Maximum retry attempts         |
| verify_ssl          | True          | SSL certificate verification   |
| initial_delay       | 1.0           | Initial retry delay in seconds |
| max_delay           | 60.0          | Maximum retry delay            |
| exponential_base    | 2             | Exponential backoff base       |
| jitter              | True          | Add randomness to retry delays |
| log_level           | INFO          | Logging level                  |
| respect_retry_after | True          | Honor Retry-After headers      |
