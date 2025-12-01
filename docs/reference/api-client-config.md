# API Client Configuration Reference

Complete configuration options for the amplihack REST API Client.

## Configuration Overview

The API Client can be configured through:

1. Constructor parameters
2. Environment variables
3. Configuration objects
4. Runtime updates

## Constructor Parameters

### Required Parameters

```python
from amplihack.utils.api_client import APIClient

client = APIClient(
    base_url="https://api.example.com"  # Required: Base URL for API
)
```

### Optional Parameters

```python
client = APIClient(
    base_url="https://api.example.com",

    # Request Configuration
    headers={                            # Default headers for all requests
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json"
    },
    timeout=30,                         # Request timeout in seconds (default: 30)
    verify_ssl=True,                    # Verify SSL certificates (default: True)

    # Retry Configuration
    max_retries=3,                      # Maximum retry attempts (default: 3)
    backoff_factor=1.0,                 # Exponential backoff multiplier (default: 1.0)
    retry_config=None,                  # Advanced retry config (overrides above)

    # Rate Limiting
    rate_limit_per_second=10,           # Client-side rate limit (default: None)

    # Network Configuration
    proxies={                           # Proxy servers (default: None)
        "http": "http://proxy:8080",
        "https": "https://proxy:8443"
    },

    # Debugging
    debug=False                         # Enable debug logging (default: False)
)
```

## RetryConfig Object

Advanced retry configuration with fine-grained control:

```python
from amplihack.utils.api_client import RetryConfig

retry_config = RetryConfig(
    max_retries=5,                     # Maximum retry attempts
    backoff_factor=2.0,                # Exponential backoff multiplier
    retry_statuses={                   # HTTP statuses that trigger retry
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504   # Gateway Timeout
    },
    retry_methods={                    # HTTP methods eligible for retry
        "GET",
        "PUT",
        "DELETE",
        "HEAD",
        "OPTIONS"
    },
    max_backoff=120.0                  # Maximum delay between retries (seconds)
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)
```

### Retry Configuration Details

#### Exponential Backoff Formula

```
delay = min(backoff_factor * (2 ** attempt), max_backoff)
```

Example with `backoff_factor=2.0`, `max_backoff=60`:

- Attempt 1: 2 seconds
- Attempt 2: 4 seconds
- Attempt 3: 8 seconds
- Attempt 4: 16 seconds
- Attempt 5: 32 seconds
- Attempt 6: 60 seconds (capped at max_backoff)

#### Safe Methods for Retry

By default, only idempotent methods are retried:

- **Safe to retry**: GET, PUT, DELETE, HEAD, OPTIONS
- **Not retried by default**: POST, PATCH (may cause duplicate resources)

## Environment Variables

### HTTP Proxy Configuration

```bash
# HTTP proxy
export HTTP_PROXY=http://proxy.example.com:8080
export http_proxy=http://proxy.example.com:8080

# HTTPS proxy
export HTTPS_PROXY=https://proxy.example.com:8443
export https_proxy=https://proxy.example.com:8443

# No proxy for specific hosts
export NO_PROXY=localhost,127.0.0.1,example.local
export no_proxy=localhost,127.0.0.1,example.local
```

### SSL Certificate Configuration

```bash
# Custom CA bundle for SSL verification
export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.crt
export CURL_CA_BUNDLE=/path/to/ca-bundle.crt

# Disable SSL warnings (development only!)
export PYTHONWARNINGS="ignore:Unverified HTTPS request"
```

### Logging Configuration

```bash
# Set logging level for amplihack
export AMPLIHACK_LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# Python logging configuration
export PYTHONUNBUFFERED=1  # Immediate log output
```

## Rate Limiting Configuration

### Client-Side Rate Limiting

Enforce request rate limits locally:

```python
# Simple rate limit: requests per second
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_per_second=5  # Max 5 requests per second
)

# Advanced rate limiting with custom window
from amplihack.utils.api_client import RateLimiter

rate_limiter = RateLimiter(
    requests_per_second=10,
    burst_size=20,  # Allow bursts up to 20 requests
    window_size=1.0  # Time window in seconds
)

client = APIClient(
    base_url="https://api.example.com",
    rate_limiter=rate_limiter
)
```

### Server-Side Rate Limit Headers

The client automatically respects these headers:

```python
# Standard rate limit headers
X-RateLimit-Limit: 100        # Total requests allowed
X-RateLimit-Remaining: 45     # Requests remaining
X-RateLimit-Reset: 1642000000  # Unix timestamp when limit resets
Retry-After: 60                # Seconds to wait before retry

# GitHub-style headers
X-RateLimit-Limit: 5000
X-RateLimit-Remaining: 4999
X-RateLimit-Reset: 1372700873
X-RateLimit-Used: 1

# Stripe-style headers
Stripe-Rate-Limit: 100
Stripe-Rate-Limit-Remaining: 99
Stripe-Rate-Limit-Reset: 1642000000
```

## Authentication Configuration

### Bearer Token

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={
        "Authorization": "Bearer your-access-token"
    }
)
```

### API Key

```python
# Header-based API key
client = APIClient(
    base_url="https://api.example.com",
    headers={
        "X-API-Key": "your-api-key"
    }
)

# Query parameter API key
class APIKeyClient(APIClient):
    def __init__(self, base_url: str, api_key: str):
        super().__init__(base_url=base_url)
        self.api_key = api_key

    def request(self, method, endpoint, params=None, **kwargs):
        params = params or {}
        params['api_key'] = self.api_key
        return super().request(method, endpoint, params=params, **kwargs)
```

### OAuth 2.0

```python
from amplihack.utils.api_client import APIClient

class OAuthClient:
    def __init__(self, client_id: str, client_secret: str):
        self.auth_client = APIClient(base_url="https://oauth.example.com")
        self.api_client = None
        self.client_id = client_id
        self.client_secret = client_secret

    def authenticate(self):
        response = self.auth_client.post("/token", data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        })

        token = response.json()["access_token"]
        self.api_client = APIClient(
            base_url="https://api.example.com",
            headers={"Authorization": f"Bearer {token}"}
        )
```

## Connection Pool Configuration

### Default Settings

```python
# The client uses these defaults for connection pooling
DEFAULT_POOL_CONNECTIONS = 10  # Number of connection pools
DEFAULT_POOL_MAXSIZE = 10      # Max connections per pool
DEFAULT_MAX_RETRIES = 3        # Retry count for connection errors
DEFAULT_POOL_TIMEOUT = None    # No timeout for getting connection from pool
```

### Custom Connection Pool

```python
from requests.adapters import HTTPAdapter
from amplihack.utils.api_client import APIClient

class CustomPoolClient(APIClient):
    def __init__(self, base_url: str, pool_connections: int = 20,
                 pool_maxsize: int = 20):
        super().__init__(base_url=base_url)

        # Configure custom connection pool
        adapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=3
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
```

## Timeout Configuration

### Simple Timeout

```python
# Single timeout value for both connect and read
client = APIClient(
    base_url="https://api.example.com",
    timeout=30  # 30 seconds for entire request
)
```

### Advanced Timeout

```python
# Separate timeouts for different phases
class AdvancedTimeoutClient(APIClient):
    def request(self, method, endpoint, **kwargs):
        # Override timeout per request
        kwargs['timeout'] = (
            5.0,   # Connection timeout
            30.0   # Read timeout
        )
        return super().request(method, endpoint, **kwargs)

# Per-request timeout override
client = APIClient(base_url="https://api.example.com")
response = client.get("/slow-endpoint", timeout=60)  # Override for slow endpoint
```

## Header Configuration

### Default Headers

```python
client = APIClient(
    base_url="https://api.example.com",
    headers={
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json",
        "Accept-Language": "en-US",
        "X-Request-ID": "unique-id-123"
    }
)
```

### Dynamic Headers

```python
import uuid

class DynamicHeaderClient(APIClient):
    def request(self, method, endpoint, headers=None, **kwargs):
        # Add dynamic headers to each request
        headers = headers or {}
        headers["X-Request-ID"] = str(uuid.uuid4())
        headers["X-Timestamp"] = str(int(time.time()))

        return super().request(method, endpoint, headers=headers, **kwargs)
```

## Proxy Configuration

### Simple Proxy

```python
client = APIClient(
    base_url="https://api.example.com",
    proxies={
        "http": "http://proxy.company.com:8080",
        "https": "https://proxy.company.com:8443"
    }
)
```

### Proxy with Authentication

```python
client = APIClient(
    base_url="https://api.example.com",
    proxies={
        "http": "http://username:password@proxy.company.com:8080",  # pragma: allowlist secret
        "https": "https://username:password@proxy.company.com:8443"  # pragma: allowlist secret
    }
)
```

### SOCKS Proxy

```python
# Requires: pip install requests[socks]
client = APIClient(
    base_url="https://api.example.com",
    proxies={
        "http": "socks5://localhost:1080",
        "https": "socks5://localhost:1080"
    }
)
```

## SSL/TLS Configuration

### Disable SSL Verification (Development Only)

```python
import warnings

client = APIClient(
    base_url="https://self-signed.example.com",
    verify_ssl=False  # INSECURE - Development only!
)

warnings.warn("SSL verification disabled - use only in development!")
```

### Custom CA Bundle

```python
client = APIClient(
    base_url="https://internal.example.com",
    verify_ssl="/path/to/custom-ca-bundle.crt"
)
```

### Client Certificates

```python
class CertificateClient(APIClient):
    def __init__(self, base_url: str, cert_path: str, key_path: str):
        super().__init__(base_url=base_url)
        self.session.cert = (cert_path, key_path)

# Or with combined cert file
client = CertificateClient(
    base_url="https://api.example.com",
    cert_path="/path/to/client.crt",
    key_path="/path/to/client.key"
)
```

## Session Configuration

### Custom Session

```python
import requests
from amplihack.utils.api_client import APIClient

# Create custom session with specific configuration
session = requests.Session()
session.trust_env = False  # Don't read proxy from environment
session.max_redirects = 5  # Limit redirects

class CustomSessionClient(APIClient):
    def __init__(self, base_url: str, session: requests.Session):
        super().__init__(base_url=base_url)
        self.session = session
```

### Session Hooks

```python
class HookedClient(APIClient):
    def __init__(self, base_url: str):
        super().__init__(base_url=base_url)

        # Add response hook
        self.session.hooks['response'] = [self.log_response]

    @staticmethod
    def log_response(response, *args, **kwargs):
        print(f"Response: {response.status_code} from {response.url}")
        return response
```

## Performance Tuning

### Optimize for Throughput

```python
# Configuration for high-throughput scenarios
client = APIClient(
    base_url="https://api.example.com",
    timeout=10,              # Lower timeout for fast failures
    max_retries=1,          # Fewer retries
    rate_limit_per_second=100  # High rate limit
)

# Use with connection pooling
class HighThroughputClient(APIClient):
    def __init__(self, base_url: str):
        super().__init__(base_url=base_url)

        adapter = HTTPAdapter(
            pool_connections=50,  # More connection pools
            pool_maxsize=50,      # More connections per pool
            max_retries=1
        )
        self.session.mount("https://", adapter)
```

### Optimize for Reliability

```python
# Configuration for maximum reliability
retry_config = RetryConfig(
    max_retries=10,         # Many retries
    backoff_factor=2.0,     # Aggressive backoff
    retry_statuses={429, 500, 502, 503, 504, 520, 521, 522, 523, 524},
    max_backoff=300.0       # Long max delay
)

client = APIClient(
    base_url="https://api.example.com",
    timeout=60,             # Long timeout
    retry_config=retry_config,
    rate_limit_per_second=2  # Conservative rate limit
)
```

## Configuration Patterns

### Environment-Based Configuration

```python
import os
from amplihack.utils.api_client import APIClient, RetryConfig

def create_client() -> APIClient:
    """Create client with environment-based configuration."""
    env = os.getenv("ENVIRONMENT", "production")

    configs = {
        "development": {
            "timeout": 60,
            "max_retries": 5,
            "verify_ssl": False,
            "debug": True
        },
        "staging": {
            "timeout": 30,
            "max_retries": 3,
            "verify_ssl": True,
            "debug": True
        },
        "production": {
            "timeout": 15,
            "max_retries": 3,
            "verify_ssl": True,
            "debug": False
        }
    }

    config = configs.get(env, configs["production"])
    return APIClient(
        base_url=os.getenv("API_BASE_URL", "https://api.example.com"),
        **config
    )
```

### Configuration Class

```python
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class APIConfig:
    """Centralized API configuration."""
    base_url: str
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    rate_limit: Optional[int] = None
    debug: bool = False

    def create_client(self) -> APIClient:
        """Create client from configuration."""
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        return APIClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
            max_retries=self.max_retries,
            rate_limit_per_second=self.rate_limit,
            debug=self.debug
        )

# Usage
config = APIConfig(
    base_url="https://api.example.com",
    api_key="secret-key",  # pragma: allowlist secret
    rate_limit=10
)
client = config.create_client()
```

## Monitoring Configuration

### Metrics Collection

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

@dataclass
class MetricsConfig:
    """Configuration for metrics collection."""
    enable_metrics: bool = True
    metrics_interval: int = 60  # Seconds
    metrics_buffer_size: int = 1000

class MetricsClient(APIClient):
    def __init__(self, base_url: str, metrics_config: MetricsConfig):
        super().__init__(base_url=base_url)
        self.metrics_config = metrics_config
        self.metrics = []

    def request(self, method, endpoint, **kwargs):
        if not self.metrics_config.enable_metrics:
            return super().request(method, endpoint, **kwargs)

        start_time = time.time()
        try:
            response = super().request(method, endpoint, **kwargs)
            self.record_metric(method, endpoint, response.status_code,
                             time.time() - start_time, success=True)
            return response
        except Exception as e:
            self.record_metric(method, endpoint, None,
                             time.time() - start_time, success=False)
            raise

    def record_metric(self, method: str, endpoint: str,
                     status_code: Optional[int], duration: float,
                     success: bool):
        """Record request metric."""
        self.metrics.append({
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration": duration,
            "success": success
        })

        # Trim buffer if needed
        if len(self.metrics) > self.metrics_config.metrics_buffer_size:
            self.metrics = self.metrics[-self.metrics_config.metrics_buffer_size:]
```

## Next Steps

- Review [How to Use the API Client](../howto/use-api-client.md)
- Learn about [Error Handling](../howto/handle-api-errors.md)
- See the complete [API Reference](./api-client.md)
