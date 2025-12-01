# REST API Client

Production-ready HTTP client with intelligent retry logic, rate limiting, and comprehensive error handling.

## Overview

The REST API Client provides a robust, resilient HTTP client for integrating with external REST APIs. Built with production reliability in mind, it handles transient failures automatically, respects rate limits, and provides detailed error information for debugging.

**Key Features:**

- Exponential backoff retry logic with jitter
- Configurable rate limiting (requests per second/minute)
- Comprehensive timeout controls
- Automatic request/response logging
- Detailed error classification and handling
- Connection pooling and keep-alive
- Request/response hooks for customization
- Thread-safe for concurrent use

## Quick Start

### Installation

```bash
# Install from PyPI
pip install amplihack-api-client

# Install from source
git clone https://github.com/amplihack/api-client
cd api-client
pip install -e .
```

### Basic Usage

```python
from amplihack.api_client import RestClient

# Create client
client = RestClient(base_url="https://api.example.com")

# Make a GET request
response = client.get("/users/123")
print(response.json())
# Output: {"id": 123, "name": "Alice", "email": "alice@example.com"}

# Make a POST request
new_user = client.post("/users", json={
    "name": "Bob",
    "email": "bob@example.com"
})
print(f"Created user {new_user.json()['id']}")
# Output: Created user 124
```

## Configuration

### Basic Configuration

```python
from amplihack.api_client import RestClient

# Simple configuration via kwargs
client = RestClient(
    base_url="https://api.example.com",
    timeout=60,
    max_retries=3
)
```

### Advanced Configuration

```python
from amplihack.api_client import RestClient, ClientConfig

# Full configuration object
config = ClientConfig(
    base_url="https://api.example.com",
    timeout=60,
    connect_timeout=10,
    max_retries=3,
    retry_backoff_factor=0.5,
    rate_limit_per_second=10,
    rate_limit_per_minute=500,
    verify_ssl=True,
    default_headers={"User-Agent": "MyApp/1.0"}
)

client = RestClient(config=config)
```

### Configuration from Environment Variables

```python
from amplihack.api_client import RestClient

# Load from environment
client = RestClient.from_env()
```

Required environment variables:

- `API_BASE_URL` - Base URL for API

Optional environment variables:

- `API_TIMEOUT` - Request timeout in seconds (default: 30)
- `API_MAX_RETRIES` - Maximum retry attempts (default: 3)
- `API_VERIFY_SSL` - Enable/disable SSL verification (default: true)
- `API_DEBUG` - Enable debug logging (default: false)

## Authentication

### Bearer Token Authentication

```python
from amplihack.api_client import RestClient, BearerAuth

auth = BearerAuth(token="your-api-token")
client = RestClient(
    base_url="https://api.example.com",
    auth=auth
)

response = client.get("/protected")
```

### API Key Authentication

```python
from amplihack.api_client import RestClient, APIKeyAuth

# API key in header
auth = APIKeyAuth(api_key="your-api-key", location="header", key_name="X-API-Key")
client = RestClient(base_url="https://api.example.com", auth=auth)

# API key in query params
auth = APIKeyAuth(api_key="your-api-key", location="query", key_name="api_key")
client = RestClient(base_url="https://api.example.com", auth=auth)
```

### Basic Authentication

```python
from amplihack.api_client import RestClient

# Pass tuple for HTTP Basic Auth
client = RestClient(
    base_url="https://api.example.com",
    auth=("username", "password")
)

response = client.get("/protected")
```

## Making Requests

### GET Requests

```python
# Simple GET
response = client.get("/users")

# GET with query parameters
response = client.get("/users", params={"role": "admin", "active": True})

# GET with custom headers
response = client.get("/users", headers={"Accept": "application/json"})
```

### POST Requests

```python
# POST with JSON body
response = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})

# POST with form data
response = client.post("/login", data={"username": "alice", "password": "secret"})

# POST with file upload
with open("avatar.png", "rb") as f:
    response = client.post("/upload", files={"avatar": f})
```

### PUT and PATCH Requests

```python
# PUT to replace resource
response = client.put("/users/123", json={"name": "Alice Updated"})

# PATCH to update resource
response = client.patch("/users/123", json={"email": "newemail@example.com"})
```

### DELETE Requests

```python
# Simple DELETE
response = client.delete("/users/123")

# DELETE with query params
response = client.delete("/cache", params={"pattern": "*"})
```

### Generic Request Method

```python
# Custom HTTP method
response = client.request("OPTIONS", "/api")

# With all parameters
response = client.request(
    method="POST",
    path="/users",
    json={"name": "Bob"},
    headers={"X-Custom": "value"},
    timeout=60
)
```

## Error Handling

The client provides specific exception classes for different error scenarios:

```python
from amplihack.api_client import (
    RestClient,
    RequestError,
    ResponseError,
    TimeoutError,
    RateLimitError,
    AuthenticationError,
    NotFoundError,
    ServerError,
    ValidationError,
    RetryExhaustedError
)

client = RestClient(base_url="https://api.example.com")

try:
    response = client.get("/users/123")
except NotFoundError as e:
    print(f"Resource not found: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after}")
except ServerError as e:
    print(f"Server error: {e.status_code}")
except TimeoutError as e:
    print(f"Request timed out: {e}")
except RequestError as e:
    print(f"Request failed: {e}")
```

### Exception Hierarchy

All exceptions inherit from `APIError`:

```
APIError (base)
├── RequestError (connection/request issues)
│   ├── TimeoutError
│   └── RetryExhaustedError
└── ResponseError (HTTP error responses)
    ├── AuthenticationError (401, 403)
    ├── NotFoundError (404)
    ├── RateLimitError (429)
    ├── ServerError (500+)
    └── ValidationError (400)
```

## Retry Logic

The client automatically retries failed requests with exponential backoff:

```python
from amplihack.api_client import RestClient, RetryPolicy

# Custom retry policy
retry_policy = RetryPolicy(
    max_attempts=5,
    backoff_factor=1.0,
    retry_on_statuses=[429, 500, 502, 503, 504]
)

client = RestClient(
    base_url="https://api.example.com",
    retry_policy=retry_policy
)
```

### Retry Callbacks

```python
def on_retry_callback(attempt: int, exception: Exception, wait_time: float):
    print(f"Retry {attempt} after {wait_time}s: {exception}")

client = RestClient(
    base_url="https://api.example.com",
    on_retry=on_retry_callback
)
```

### Custom Retry Logic

```python
def should_retry_custom(response, exception):
    # Retry on specific error codes
    if response and response.status_code == 503:
        return True
    # Don't retry on other errors
    return False

client = RestClient(
    base_url="https://api.example.com",
    should_retry=should_retry_custom
)
```

## Rate Limiting

The client includes built-in rate limiting to prevent overwhelming APIs:

```python
from amplihack.api_client import RestClient

# Rate limit: 10 requests per second, 500 per minute
client = RestClient(
    base_url="https://api.example.com",
    rate_limit_per_second=10,
    rate_limit_per_minute=500
)

# Make requests - automatically throttled
for i in range(100):
    response = client.get(f"/users/{i}")
```

## Timeouts

Configure timeouts at different levels:

```python
from amplihack.api_client import RestClient

# Global timeouts
client = RestClient(
    base_url="https://api.example.com",
    timeout=60,           # Total request timeout
    connect_timeout=10    # Connection establishment timeout
)

# Per-request timeout override
response = client.get("/slow-endpoint", timeout=120)
```

## Debug Logging

Enable debug logging to see detailed request/response information:

```python
from amplihack.api_client import RestClient

client = RestClient(
    base_url="https://api.example.com",
    debug=True
)

# Logs will show:
# - Request method, URL, headers, body
# - Response status, headers, body
# - Retry attempts and backoff times
# - Rate limit enforcement
```

## Security Best Practices

### SSL Verification

**IMPORTANT**: SSL verification is enabled by default and should NEVER be disabled in production:

```python
from amplihack.api_client import RestClient

# ⚠️  INSECURE - Only for development/testing
client = RestClient(
    base_url="https://api.example.com",
    verify_ssl=False  # Logs security warning
)
```

When `verify_ssl=False`, the client logs:

```
⚠️  SSL VERIFICATION DISABLED - INSECURE CONNECTION
This should NEVER be used in production!
```

### Safe Credential Handling

```python
import os
from amplihack.api_client import RestClient, BearerAuth

# ✓ Load credentials from environment
token = os.environ.get("API_TOKEN")
auth = BearerAuth(token=token)

# ✓ Use environment-based configuration
client = RestClient.from_env()

# ✗ Never hardcode credentials
# auth = BearerAuth(token="hardcoded-secret")  # WRONG!
```

## API Reference

### RestClient

```python
RestClient(
    base_url: Optional[str] = None,
    config: Optional[ClientConfig] = None,
    auth: Optional[Union[BearerAuth, APIKeyAuth, tuple]] = None,
    retry_policy: Optional[RetryPolicy] = None,
    on_retry: Optional[Callable] = None,
    should_retry: Optional[Callable] = None,
    **kwargs: Any
)
```

### ClientConfig

```python
ClientConfig(
    base_url: str,
    timeout: int = 30,
    connect_timeout: int = 10,
    max_retries: int = 3,
    retry_backoff_factor: float = 0.5,
    retry_statuses: List[int] = [429, 500, 502, 503, 504],
    rate_limit_per_second: Optional[int] = None,
    rate_limit_per_minute: Optional[int] = None,
    verify_ssl: bool = True,
    default_headers: Dict[str, str] = None,
    allow_redirects: bool = True,
    max_redirects: int = 10,
    debug: bool = False
)
```

### BearerAuth

```python
BearerAuth(token: str)
```

### APIKeyAuth

```python
APIKeyAuth(
    api_key: str,
    location: str = "header",  # "header" or "query"
    key_name: str = "X-API-Key"
)
```

### RetryPolicy

```python
RetryPolicy(
    max_attempts: int = 4,
    backoff_factor: float = 0.5,
    retry_on_statuses: List[int] = [429, 500, 502, 503, 504]
)
```

### RateLimiter

```python
RateLimiter(
    requests_per_second: Optional[int] = None,
    requests_per_minute: Optional[int] = None
)
```

## Common Use Cases

### Integrating with Third-Party APIs

```python
from amplihack.api_client import RestClient, BearerAuth
import os

# GitHub API example
github_token = os.environ.get("GITHUB_TOKEN")
auth = BearerAuth(token=github_token)

client = RestClient(
    base_url="https://api.github.com",
    auth=auth,
    default_headers={"Accept": "application/vnd.github.v3+json"}
)

# Get user repos
repos = client.get("/user/repos").json()
for repo in repos:
    print(f"{repo['name']}: {repo['description']}")
```

### Building Your Own API Client

```python
from amplihack.api_client import RestClient, BearerAuth

class MyAPIClient:
    def __init__(self, api_token: str):
        auth = BearerAuth(token=api_token)
        self.client = RestClient(
            base_url="https://api.myservice.com",
            auth=auth,
            rate_limit_per_second=10
        )

    def get_user(self, user_id: int):
        return self.client.get(f"/users/{user_id}").json()

    def create_user(self, name: str, email: str):
        return self.client.post("/users", json={"name": name, "email": email}).json()

    def update_user(self, user_id: int, **fields):
        return self.client.patch(f"/users/{user_id}", json=fields).json()

    def delete_user(self, user_id: int):
        self.client.delete(f"/users/{user_id}")

# Usage
api = MyAPIClient(api_token="your-token")
user = api.get_user(123)
```

## Testing

Run the test suite:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run specific test file
pytest tests/test_client.py

# Run with coverage
pytest --cov=amplihack.api_client --cov-report=html
```

## Troubleshooting

### Connection Timeouts

If requests are timing out:

1. Increase timeout values:

   ```python
   client = RestClient(
       base_url="https://api.example.com",
       timeout=120,
       connect_timeout=30
   )
   ```

2. Check network connectivity
3. Verify the API is accessible

### Rate Limit Errors

If hitting rate limits:

1. Configure rate limiting:

   ```python
   client = RestClient(
       base_url="https://api.example.com",
       rate_limit_per_second=5
   )
   ```

2. Handle `RateLimitError` and implement backoff:
   ```python
   try:
       response = client.get("/data")
   except RateLimitError as e:
       wait_time = e.retry_after or 60
       time.sleep(wait_time)
       response = client.get("/data")
   ```

### SSL Certificate Errors

If encountering SSL certificate errors:

1. Ensure certificates are up to date
2. Verify the API's certificate is valid
3. Only disable SSL verification for development/testing (never production)

### Debug Mode Not Working

Enable debug logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)

client = RestClient(
    base_url="https://api.example.com",
    debug=True
)
```

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please open an issue or pull request.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:

- GitHub Issues: https://github.com/amplihack/api-client/issues
- Documentation: https://api-client.readthedocs.io
