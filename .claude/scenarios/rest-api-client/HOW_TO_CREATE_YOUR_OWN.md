# How to Create Your Own REST API Client

This guide shows you how to create a custom REST API client similar to this one, following amplihack's scenario tool patterns.

## Overview

This REST API client demonstrates how to build a production-ready HTTP client using only Python's standard library, with enterprise features like retry logic, rate limiting, SSRF protection, and comprehensive error handling.

## Step-by-Step Guide

### Step 1: Create the Scenario Directory Structure

```bash
.claude/scenarios/your-api-client/
├── README.md                      # Tool overview and usage
├── HOW_TO_CREATE_YOUR_OWN.md      # This guide
├── your_api_client/               # Main package
│   ├── __init__.py               # Package initialization
│   ├── client.py                 # Main client class
│   ├── models.py                 # Request/Response models
│   ├── exceptions.py            # Custom exceptions
│   ├── transport.py             # HTTP transport layer
│   ├── retry.py                 # Retry logic
│   ├── rate_limiter.py          # Rate limiting
│   └── security.py              # SSRF protection
├── tests/                        # Test files
│   ├── test_client.py
│   ├── test_transport.py
│   ├── test_retry.py
│   └── test_security.py
└── examples/                     # Usage examples
    ├── basic_usage.py
    └── advanced_usage.py
```

### Step 2: Define Core Components

#### Models (models.py)

```python
@dataclass
class Request:
    """HTTP request model."""
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    params: Optional[Dict[str, Any]] = None
    json: Optional[Dict[str, Any]] = None
    data: Optional[Union[str, bytes]] = None
    timeout: float = 30.0

@dataclass
class Response:
    """HTTP response model."""
    status_code: int
    headers: Dict[str, str]
    body: bytes
    elapsed_time: float
    request: Optional[Request] = None
```

#### Exceptions (exceptions.py)

```python
class APIClientError(Exception):
    """Base exception for API client errors."""
    pass

class ConfigurationError(APIClientError):
    """Configuration-related errors."""
    pass

class ConnectionError(APIClientError):
    """Connection-related errors."""
    pass
```

### Step 3: Implement Security Features

#### SSRF Protection (security.py)

```python
import ipaddress
from urllib.parse import urlparse

class SSRFProtector:
    """Protect against Server-Side Request Forgery attacks."""

    BLOCKED_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),      # Loopback
        ipaddress.ip_network("10.0.0.0/8"),       # Private
        ipaddress.ip_network("172.16.0.0/12"),    # Private
        ipaddress.ip_network("192.168.0.0/16"),   # Private
        ipaddress.ip_network("169.254.0.0/16"),   # Link-local
        ipaddress.ip_network("::1/128"),          # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),         # IPv6 private
    ]

    def is_safe_url(self, url: str) -> bool:
        """Check if URL is safe from SSRF attacks."""
        parsed = urlparse(url)
        hostname = parsed.hostname

        if not hostname:
            return False

        # Block localhost variations
        if hostname.lower() in ['localhost', '127.0.0.1', '::1']:
            return False

        try:
            # Resolve hostname to IP
            import socket
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            # Check against blocked networks
            for network in self.BLOCKED_NETWORKS:
                if ip_obj in network:
                    return False

        except (socket.gaierror, ValueError):
            # If we can't resolve, be safe and block
            return False

        return True
```

### Step 4: Implement Transport Layer

```python
class HTTPTransport:
    """HTTP transport with size limits and proper error handling."""

    def __init__(self, max_response_size: int = 100 * 1024 * 1024):
        self.max_response_size = max_response_size

    def request(self, method, url, **kwargs):
        """Make HTTP request with size limits."""
        # Check response size before downloading
        response = urllib.request.urlopen(request, timeout=timeout)

        content_length = response.headers.get('Content-Length')
        if content_length and int(content_length) > self.max_response_size:
            raise ValueError(f"Response too large: {content_length} bytes")

        # Read with size limit
        body = b""
        chunk_size = 8192
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            body += chunk
            if len(body) > self.max_response_size:
                raise ValueError(f"Response exceeded {self.max_response_size} bytes")

        return status_code, headers, body, elapsed_time
```

### Step 5: Add Retry Logic

```python
class RetryManager:
    """Manages retry logic with exponential backoff."""

    def execute_with_retry(self, func, *args, **kwargs):
        """Execute function with retry logic."""
        for attempt in range(self.config.max_attempts):
            try:
                result = func(*args, **kwargs)

                # Check if we should retry based on status code
                if hasattr(result, 'status_code'):
                    if self.should_retry(attempt, status_code=result.status_code):
                        wait_time = self.calculate_backoff(attempt + 1)
                        time.sleep(wait_time)
                        continue

                return result

            except (ConnectionError, TimeoutError) as e:
                if attempt < self.config.max_attempts - 1:
                    wait_time = self.calculate_backoff(attempt + 1)
                    time.sleep(wait_time)
                    continue
                raise
```

### Step 6: Build the Main Client

```python
class APIClient:
    """Main REST API client with all features integrated."""

    def __init__(self, base_url, **kwargs):
        self.base_url = base_url
        self.ssrf_protector = SSRFProtector()
        self.transport = HTTPTransport(max_response_size=kwargs.get('max_response_size'))
        self.retry_manager = RetryManager(RetryConfig(**kwargs))

    def _request(self, method, path, **kwargs):
        """Internal request method with all protections."""
        url = urljoin(self.base_url, path)

        # SSRF protection
        if not self.ssrf_protector.is_safe_url(url):
            raise SecurityError(f"URL blocked for security: {url}")

        # Execute with retry
        return self.retry_manager.execute_with_retry(
            self.transport.request, method, url, **kwargs
        )
```

### Step 7: Add Makefile Integration

Add to root Makefile:

```makefile
# REST API Client tool
rest-api-client:
	@if [ -z "$(URL)" ]; then \
		echo "Error: URL parameter is required"; \
		echo "Usage: make rest-api-client URL=<api-url> [METHOD=<method>] [OPTIONS=<opts>]"; \
		exit 1; \
	fi
	@python .claude/scenarios/rest-api-client/tool.py \
		--url "$(URL)" \
		--method "$${METHOD:-GET}" \
		$${OPTIONS}
```

### Step 8: Create the CLI Tool (tool.py)

```python
#!/usr/bin/env python3
"""REST API Client CLI tool."""

import sys
import argparse
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from rest_api_client import APIClient

def main():
    parser = argparse.ArgumentParser(description="REST API Client")
    parser.add_argument("--url", required=True, help="API endpoint URL")
    parser.add_argument("--method", default="GET", help="HTTP method")
    parser.add_argument("--json", help="JSON data to send")
    parser.add_argument("--headers", help="Headers as JSON")
    parser.add_argument("--timeout", type=float, default=30.0)

    args = parser.parse_args()

    # Parse base URL and path
    from urllib.parse import urlparse
    parsed = urlparse(args.url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path

    # Create client and make request
    client = APIClient(base_url, timeout=args.timeout)
    response = client.request(args.method, path, json=args.json)

    # Display response
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")

if __name__ == "__main__":
    main()
```

### Step 9: Write Comprehensive Tests

```python
import unittest
from unittest.mock import patch, MagicMock

class TestAPIClient(unittest.TestCase):
    def test_ssrf_protection(self):
        """Test SSRF protection blocks internal IPs."""
        client = APIClient("https://api.example.com")

        with self.assertRaises(SecurityError):
            client.get("http://127.0.0.1/internal")

    def test_response_size_limit(self):
        """Test response size limiting."""
        client = APIClient("https://api.example.com", max_response_size=1024)

        # Mock large response
        with patch('urllib.request.urlopen') as mock:
            mock.return_value.headers = {'Content-Length': '2048'}
            with self.assertRaises(ValueError):
                client.get("/large")
```

### Step 10: Document Usage Examples

Create `examples/basic_usage.py`:

```python
from rest_api_client import APIClient

# Create client
client = APIClient(
    base_url="https://api.github.com",
    timeout=30,
    max_retries=3,
    max_response_size=10 * 1024 * 1024  # 10MB
)

# Make requests
response = client.get("/users/octocat")
print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")

# With error handling
try:
    response = client.post("/repos", json={"name": "test"})
except APIClientError as e:
    print(f"API error: {e}")
```

## Best Practices

### 1. Security First

- Always validate URLs for SSRF attacks
- Limit response sizes to prevent memory exhaustion
- Sanitize headers to prevent injection
- Use HTTPS by default

### 2. Error Handling

- Never use bare except clauses
- Create specific exception types
- Provide clear error messages
- Log errors appropriately

### 3. Performance

- Implement connection pooling for reuse
- Add caching where appropriate
- Use streaming for large responses
- Implement circuit breakers for failing services

### 4. Testing

- Test all error conditions
- Mock external dependencies
- Test security features explicitly
- Include integration tests

### 5. Documentation

- Document all parameters
- Provide usage examples
- Explain security features
- Include troubleshooting guide

## Common Pitfalls to Avoid

1. **Bare Except Clauses**: Always catch specific exceptions
2. **No Size Limits**: Always limit response sizes
3. **Missing SSRF Protection**: Always validate URLs
4. **No Timeout**: Always set reasonable timeouts
5. **Poor Error Messages**: Provide actionable error information

## Integration Checklist

- [ ] Created directory structure
- [ ] Implemented all core components
- [ ] Added security features (SSRF, size limits)
- [ ] Implemented retry logic
- [ ] Added Makefile target
- [ ] Created CLI tool
- [ ] Wrote comprehensive tests
- [ ] Added usage examples
- [ ] Updated root Makefile
- [ ] Tested via `make rest-api-client`

## Conclusion

This template provides a robust foundation for creating REST API clients. The key principles are:

1. **Security by default** - SSRF protection, size limits, header validation
2. **Robust error handling** - Specific exceptions, clear messages
3. **Production features** - Retry logic, rate limiting, timeouts
4. **Zero dependencies** - Uses only Python standard library
5. **Testable design** - Clear interfaces, mockable components

Follow this pattern to create your own specialized API clients while maintaining amplihack's philosophy of ruthless simplicity and zero-BS implementation.
