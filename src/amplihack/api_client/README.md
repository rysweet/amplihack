# REST API Client Module

## Overview

A simple, secure REST API client built on Python's standard library (urllib). Provides SSRF protection, automatic retries with exponential backoff, and SSL verification.

## Philosophy

- **Single responsibility**: HTTP client functionality with security and reliability
- **Standard library only**: Uses urllib for HTTP, no external dependencies for core functionality
- **Self-contained and regeneratable**: Can be rebuilt from this specification

## Public API (the "studs")

### Classes

- **RestApiClient**: Main HTTP client class
- **RestApiConfig**: Configuration dataclass
- **ApiResponse**: Response wrapper with status, body, headers
- **RetryHandler**: Exponential backoff retry logic
- **SecurityValidator**: SSRF and SSL validation

### Exceptions

- **ApiClientError**: Base exception for all client errors
- **SecurityError**: Security validation failures (SSRF, SSL)
- **ValidationError**: Configuration validation errors

## Quick Start

```python
from amplihack.api_client import RestApiClient, RestApiConfig

# Create client
config = RestApiConfig(base_url="https://api.example.com")
client = RestApiClient(config)

# Make requests
response = client.get("/users")
print(response.json())  # Parsed JSON
print(response.status_code)  # HTTP status
```

## Security Features

### SSRF Protection

The client automatically blocks requests to private IP addresses:

- Loopback (127.0.0.0/8)
- Private Class A (10.0.0.0/8)
- Private Class B (172.16.0.0/12)
- Private Class C (192.168.0.0/16)
- Link-local (169.254.0.0/16)

**DNS Rebinding Protection**: The client resolves DNS names and validates the resolved IP address to prevent DNS rebinding attacks where an attacker controls a DNS server that returns a private IP.

```python
# This will raise SecurityError
client.get("http://127.0.0.1/admin")  # Blocked

# This will also raise SecurityError (DNS rebinding protection)
# Assuming evil.com resolves to 127.0.0.1
client.get("http://evil.com/steal-secrets")  # Blocked after DNS resolution
```

### HTTPS Enforcement

HTTPS is enforced by default for production use. Use `allow_private=True` only for testing:

```python
# For testing only
response = client.get("/test", allow_private=True)
```

### Header Sanitization

Sensitive headers (authorization, api-key, token, password) are automatically redacted in logs.

## Retry Logic

Automatic exponential backoff retry on transient failures:

- Max retries: 3 (configurable)
- Base backoff: 1.0 seconds (configurable)
- Exponential backoff with jitter
- Retries on: Network errors, 5xx server errors

```python
config = RestApiConfig(
    base_url="https://api.example.com",
    max_retries=5,
    retry_backoff=2.0,
)
client = RestApiClient(config)
```

## Configuration

### RestApiConfig

```python
@dataclass
class RestApiConfig:
    base_url: str  # Required: must start with http:// or https://
    timeout: float = 30.0  # Request timeout in seconds
    max_retries: int = 3  # Maximum retry attempts
    retry_backoff: float = 1.0  # Base backoff time in seconds
    verify_ssl: bool = True  # Verify SSL certificates
    headers: dict[str, str] | None = None  # Default headers
```

## Usage Examples

### Basic GET Request

```python
config = RestApiConfig(base_url="https://api.example.com")
client = RestApiClient(config)

response = client.get("/users/123")
if response.ok:
    data = response.json()
    print(f"User: {data['name']}")
```

### POST with JSON

```python
import json

data = {"name": "Alice", "email": "alice@example.com"}
body = json.dumps(data).encode('utf-8')

response = client.post(
    "/users",
    body=body,
    headers={"Content-Type": "application/json"}
)
print(f"Created user ID: {response.json()['id']}")
```

### Custom Headers

```python
config = RestApiConfig(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer token123"}
)
client = RestApiClient(config)

# Authorization header included automatically
response = client.get("/protected/resource")
```

## Dependencies

- **Core**: Standard library only (urllib, ssl, json, socket)
- **Testing**: pytest, pytest-httpserver

## Testing Approach

- **Unit tests**: Fast, heavily mocked (60%)
- **Integration tests**: Multiple components (30%)
- **E2E tests**: Complete workflows (10%)

See `tests/` directory for comprehensive test suite.

## Module Structure

```
api_client/
├── __init__.py       # Public interface via __all__
├── README.md         # This file
├── core.py           # Main RestApiClient implementation
├── config.py         # RestApiConfig dataclass
├── response.py       # ApiResponse wrapper
├── retry.py          # RetryHandler with exponential backoff
├── security.py       # SecurityValidator (SSRF, SSL)
├── exceptions.py     # Exception hierarchy
└── tests/            # Test suite
```

## Common Patterns

### Error Handling

```python
from amplihack.api_client import ApiClientError, SecurityError

try:
    response = client.get("/users")
    data = response.json()
except SecurityError as e:
    print(f"Security violation: {e}")
except ApiClientError as e:
    print(f"Request failed after retries: {e}")
```

### Timeout Configuration

```python
config = RestApiConfig(
    base_url="https://slow-api.example.com",
    timeout=60.0  # 60 second timeout
)
```

### Disable SSL Verification (Testing Only)

```python
# WARNING: Only use for testing with self-signed certs
config = RestApiConfig(
    base_url="https://localhost:8443",
    verify_ssl=False
)
```

## Logging

The client uses Python's standard logging module. Enable debug logging to see request/response details:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
# Now all requests will be logged with sanitized headers
```

## API Reference

### RestApiClient

#### `__init__(config: RestApiConfig)`

Initialize client with configuration.

#### `request(method, path, body=None, headers=None, allow_private=False) -> ApiResponse`

Make HTTP request with security and retry.

- **method**: HTTP method (GET, POST, PUT, DELETE, etc)
- **path**: URL path (appended to base_url)
- **body**: Request body as bytes
- **headers**: Additional headers (merged with config.headers)
- **allow_private**: Allow private IPs (for testing only)

#### `get(path, **kwargs) -> ApiResponse`

Make GET request.

#### `post(path, body, **kwargs) -> ApiResponse`

Make POST request with body.

#### `put(path, body, **kwargs) -> ApiResponse`

Make PUT request with body.

#### `delete(path, **kwargs) -> ApiResponse`

Make DELETE request.

### ApiResponse

#### Properties

- **status_code**: HTTP status code (int)
- **body**: Response body (bytes)
- **headers**: Response headers (dict)
- **ok**: True if status_code < 400

#### Methods

- **json()**: Parse body as JSON (returns dict or list)
- **text()**: Decode body as UTF-8 text (returns str)

### SecurityValidator

#### `validate_url(url, allow_private=False)`

Validate URL for security issues. Raises SecurityError if:
- Scheme is not HTTPS (when allow_private=False)
- Hostname resolves to a private IP address (DNS rebinding protection)

#### `sanitize_headers(headers)`

Redact sensitive values from headers for safe logging.

## Implementation Notes

### Why Standard Library?

- No external dependencies = easier deployment
- urllib is battle-tested and maintained
- Sufficient for most API client needs
- Regeneratable from specification

### SSRF Protection Details

The module implements two layers of SSRF protection:

1. **Direct IP blocking**: Block requests to IP addresses in private CIDR ranges
2. **DNS resolution validation**: Resolve hostnames to IPs and block if they resolve to private ranges

This prevents DNS rebinding attacks where `evil.com` initially resolves to a public IP but later rebinds to `127.0.0.1`.

### Retry Strategy

- Retries on: `ApiClientError` (network failures), 5xx status codes
- Does not retry on: 4xx status codes (client errors)
- Exponential backoff with jitter to prevent thundering herd
- Maximum backoff capped at configurable limit

## Version History

- **1.0.0**: Initial release with SSRF protection, retries, logging
