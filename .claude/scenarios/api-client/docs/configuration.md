# Configuration Guide

Comprehensive guide for configuring the REST API Client to meet your specific requirements.

## Contents

- [Client Configuration](#client-configuration)
- [Environment Variables](#environment-variables)
- [Request Defaults](#request-defaults)
- [Timeout Configuration](#timeout-configuration)
- [Rate Limiting](#rate-limiting)
- [Retry Configuration](#retry-configuration)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Proxy Configuration](#proxy-configuration)

## Client Configuration

### Basic Configuration

The REST API Client accepts configuration during initialization:

```python
from api_client import RESTClient

client = RESTClient(
    base_url="https://api.example.com",
    timeout=30,           # Request timeout in seconds
    max_retries=3,        # Number of retry attempts
    rate_limit=10         # Requests per second
)
```

### Configuration Parameters

| Parameter     | Type  | Default  | Description                      |
| ------------- | ----- | -------- | -------------------------------- |
| `base_url`    | str   | Required | Base URL for all API requests    |
| `timeout`     | int   | 30       | Request timeout in seconds       |
| `max_retries` | int   | 3        | Maximum number of retry attempts |
| `rate_limit`  | float | 10       | Maximum requests per second      |

### Dynamic Configuration

Change configuration after initialization:

```python
client = RESTClient("https://api.example.com")

# Update configuration
client.timeout = 60
client.rate_limit = 5
client.max_retries = 5
```

## Environment Variables

Configure defaults using environment variables:

```bash
# Set defaults via environment
export API_CLIENT_TIMEOUT=60
export API_CLIENT_MAX_RETRIES=5
export API_CLIENT_RATE_LIMIT=20

# Run your application
python app.py
```

### Available Environment Variables

| Variable                 | Description                 | Example     |
| ------------------------ | --------------------------- | ----------- |
| `API_CLIENT_TIMEOUT`     | Default timeout in seconds  | `60`        |
| `API_CLIENT_MAX_RETRIES` | Default retry attempts      | `5`         |
| `API_CLIENT_RATE_LIMIT`  | Default requests per second | `20`        |
| `API_CLIENT_USER_AGENT`  | Default User-Agent header   | `MyApp/1.0` |
| `API_CLIENT_DEBUG`       | Enable debug logging        | `true`      |

### Loading Environment Configuration

```python
import os
from api_client import RESTClient

def create_configured_client(base_url: str) -> RESTClient:
    """Create client with environment-based configuration."""
    return RESTClient(
        base_url=base_url,
        timeout=int(os.getenv("API_CLIENT_TIMEOUT", "30")),
        max_retries=int(os.getenv("API_CLIENT_MAX_RETRIES", "3")),
        rate_limit=float(os.getenv("API_CLIENT_RATE_LIMIT", "10"))
    )

# Usage
client = create_configured_client("https://api.example.com")
```

## Request Defaults

### Default Headers

Set headers that apply to all requests:

```python
from api_client import RESTClient

class ConfiguredClient(RESTClient):
    """Client with default headers."""

    def __init__(self, base_url: str, default_headers: dict = None):
        super().__init__(base_url)
        self.default_headers = default_headers or {}

    def request(self, method: str, path: str, headers: dict = None, **kwargs):
        """Apply default headers to all requests."""
        final_headers = self.default_headers.copy()
        if headers:
            final_headers.update(headers)
        return super().request(method, path, headers=final_headers, **kwargs)

# Usage
client = ConfiguredClient(
    "https://api.example.com",
    default_headers={
        "Accept": "application/json",
        "User-Agent": "MyApp/1.0",
        "X-API-Version": "2"
    }
)
```

### Default Parameters

Set parameters that apply to all requests:

```python
class ParameterizedClient(RESTClient):
    """Client with default parameters."""

    def __init__(self, base_url: str, default_params: dict = None):
        super().__init__(base_url)
        self.default_params = default_params or {}

    def get(self, path: str, params: dict = None, **kwargs):
        """Apply default parameters to GET requests."""
        final_params = self.default_params.copy()
        if params:
            final_params.update(params)
        return super().get(path, params=final_params, **kwargs)

# Usage
client = ParameterizedClient(
    "https://api.example.com",
    default_params={
        "format": "json",
        "version": "v2"
    }
)
```

## Timeout Configuration

### Request Timeout

Configure different timeout values for different types of operations:

```python
from api_client import RESTClient

class TimeoutClient(RESTClient):
    """Client with configurable timeouts per operation type."""

    def __init__(self, base_url: str):
        super().__init__(base_url, timeout=30)
        self.timeout_config = {
            "GET": 10,      # Fast reads
            "POST": 30,     # Standard writes
            "PUT": 30,      # Updates
            "DELETE": 10,   # Quick deletes
            "upload": 300,  # Large uploads
            "download": 300 # Large downloads
        }

    def request(self, method: str, path: str, timeout: int = None, **kwargs):
        """Use configured timeout for method if not specified."""
        if timeout is None:
            timeout = self.timeout_config.get(method, self.timeout)
        return super().request(method, path, timeout=timeout, **kwargs)

# Usage
client = TimeoutClient("https://api.example.com")
# GET uses 10 second timeout
response = client.get("/users")
# Override with custom timeout
response = client.get("/slow-endpoint", timeout=60)
```

### Connection Timeout vs Read Timeout

```python
import urllib.request
import socket

class AdvancedTimeoutClient(RESTClient):
    """Client with separate connection and read timeouts."""

    def __init__(self, base_url: str, connect_timeout: int = 10,
                 read_timeout: int = 30):
        super().__init__(base_url)
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

    def request(self, method: str, path: str, **kwargs):
        """Make request with separate timeout handling."""
        # Set socket timeout for connection
        socket.setdefaulttimeout(self.connect_timeout)

        try:
            # Make request with read timeout
            return super().request(method, path, timeout=self.read_timeout, **kwargs)
        finally:
            # Reset socket timeout
            socket.setdefaulttimeout(None)
```

## Rate Limiting

### Static Rate Limiting

Configure fixed rate limits:

```python
from api_client import RESTClient
import time

# 10 requests per second
client = RESTClient("https://api.example.com", rate_limit=10)

# 100 requests per minute (1.67 per second)
client = RESTClient("https://api.example.com", rate_limit=100/60)

# 5000 requests per hour (1.39 per second)
client = RESTClient("https://api.example.com", rate_limit=5000/3600)
```

### Dynamic Rate Limiting

Adjust rate limits based on usage:

```python
class DynamicRateLimitClient(RESTClient):
    """Client that adjusts rate limit dynamically."""

    def __init__(self, base_url: str):
        super().__init__(base_url, rate_limit=10)
        self.rate_limit_schedule = {
            "peak": 5,      # 9am-5pm
            "normal": 10,   # 5pm-12am
            "off_peak": 20  # 12am-9am
        }

    def get_current_rate_limit(self) -> float:
        """Determine rate limit based on time of day."""
        from datetime import datetime
        hour = datetime.now().hour

        if 9 <= hour < 17:
            return self.rate_limit_schedule["peak"]
        elif 17 <= hour < 24:
            return self.rate_limit_schedule["normal"]
        else:
            return self.rate_limit_schedule["off_peak"]

    def request(self, method: str, path: str, **kwargs):
        """Apply dynamic rate limit."""
        self.rate_limit = self.get_current_rate_limit()
        return super().request(method, path, **kwargs)
```

## Retry Configuration

### Retry Strategy

Configure when and how to retry failed requests:

```python
from api_client import RESTClient

class RetryClient(RESTClient):
    """Client with configurable retry strategy."""

    def __init__(self, base_url: str):
        super().__init__(base_url, max_retries=3)
        # Status codes that trigger retry
        self.retry_on_status = {408, 429, 500, 502, 503, 504}
        # Backoff multiplier for each retry
        self.backoff_factor = 2.0
        # Maximum backoff time
        self.max_backoff = 60

    def should_retry(self, response) -> bool:
        """Determine if request should be retried."""
        return response.status_code in self.retry_on_status

    def calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff time for retry attempt."""
        backoff = self.backoff_factor ** attempt
        return min(backoff, self.max_backoff)

# Usage
client = RetryClient("https://api.example.com")
```

### Exponential Backoff Configuration

```python
import time
import random

class ExponentialBackoffClient(RESTClient):
    """Client with exponential backoff and jitter."""

    def __init__(self, base_url: str):
        super().__init__(base_url)
        self.base_delay = 1.0  # Initial delay
        self.max_delay = 60.0   # Maximum delay
        self.jitter = True      # Add randomness

    def retry_with_backoff(self, method: str, path: str, **kwargs):
        """Retry with exponential backoff and jitter."""
        delay = self.base_delay

        for attempt in range(self.max_retries):
            try:
                response = self.request(method, path, **kwargs)
                if response.status_code < 500:
                    return response
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise

            # Calculate next delay
            if self.jitter:
                actual_delay = delay * (0.5 + random.random())
            else:
                actual_delay = delay

            print(f"Retrying after {actual_delay:.2f} seconds...")
            time.sleep(actual_delay)

            # Exponential increase
            delay = min(delay * 2, self.max_delay)

        raise Exception(f"Max retries ({self.max_retries}) exceeded")
```

## SSL/TLS Configuration

### SSL Verification

```python
import ssl
import urllib.request

class SSLConfiguredClient(RESTClient):
    """Client with SSL/TLS configuration."""

    def __init__(self, base_url: str, verify_ssl: bool = True,
                 ca_bundle: str = None):
        super().__init__(base_url)
        self.verify_ssl = verify_ssl
        self.ca_bundle = ca_bundle

    def create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with configuration."""
        if not self.verify_ssl:
            # Disable SSL verification (not recommended for production)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx

        # Create secure context
        ctx = ssl.create_default_context()

        if self.ca_bundle:
            # Use custom CA bundle
            ctx.load_verify_locations(self.ca_bundle)

        return ctx

    def request(self, method: str, path: str, **kwargs):
        """Make request with SSL configuration."""
        ssl_context = self.create_ssl_context()
        # Apply SSL context to request
        # (Implementation depends on urllib configuration)
        return super().request(method, path, **kwargs)

# Usage
# Production - verify SSL
secure_client = SSLConfiguredClient("https://api.example.com")

# Development - skip SSL verification (not recommended)
dev_client = SSLConfiguredClient("https://localhost:8443", verify_ssl=False)

# Custom CA bundle
custom_ca_client = SSLConfiguredClient(
    "https://internal-api.company.com",
    ca_bundle="/path/to/ca-bundle.crt"
)
```

## Proxy Configuration

### HTTP Proxy

```python
import urllib.request

class ProxyClient(RESTClient):
    """Client with proxy support."""

    def __init__(self, base_url: str, proxy_url: str = None):
        super().__init__(base_url)
        self.proxy_url = proxy_url

    def configure_proxy(self):
        """Configure proxy for urllib."""
        if self.proxy_url:
            proxy_handler = urllib.request.ProxyHandler({
                "http": self.proxy_url,
                "https": self.proxy_url
            })
            opener = urllib.request.build_opener(proxy_handler)
            urllib.request.install_opener(opener)

    def request(self, method: str, path: str, **kwargs):
        """Make request through proxy."""
        self.configure_proxy()
        return super().request(method, path, **kwargs)

# Usage
# Direct connection
client = ProxyClient("https://api.example.com")

# Through HTTP proxy
proxy_client = ProxyClient(
    "https://api.example.com",
    proxy_url="http://proxy.company.com:8080"
)

# Through SOCKS proxy (requires additional setup)
socks_client = ProxyClient(
    "https://api.example.com",
    proxy_url="socks5://localhost:1080"
)
```

### Proxy with Authentication

```python
import base64

class AuthProxyClient(ProxyClient):
    """Client with authenticated proxy support."""

    def __init__(self, base_url: str, proxy_url: str,
                 proxy_user: str = None, proxy_pass: str = None):
        super().__init__(base_url, proxy_url)
        self.proxy_auth = None

        if proxy_user and proxy_pass:
            # Create basic auth header for proxy
            credentials = f"{proxy_user}:{proxy_pass}"
            encoded = base64.b64encode(credentials.encode()).decode()
            self.proxy_auth = f"Basic {encoded}"

    def request(self, method: str, path: str, headers: dict = None, **kwargs):
        """Add proxy authentication if configured."""
        if self.proxy_auth:
            headers = headers or {}
            headers["Proxy-Authorization"] = self.proxy_auth

        return super().request(method, path, headers=headers, **kwargs)

# Usage
auth_proxy_client = AuthProxyClient(
    "https://api.example.com",
    proxy_url="http://proxy.company.com:8080",
    proxy_user="username",
    proxy_pass="password"
)
```

## Configuration Best Practices

1. **Use environment variables** for sensitive configuration
2. **Set reasonable timeouts** - Never wait indefinitely
3. **Configure rate limits** based on API provider limits
4. **Enable SSL verification** in production
5. **Use exponential backoff** for retries
6. **Log configuration** for debugging
7. **Validate configuration** at startup
8. **Document defaults** in your application
