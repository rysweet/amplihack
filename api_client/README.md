# API Client

Zero-dependency REST API client with automatic retries, rate limiting, and thread-safe operation.

## Quick Start

```python
from api_client import APIClient, ClientConfig

# Create client with minimal configuration
client = APIClient(ClientConfig(base_url="https://api.example.com"))

# Make requests
response = client.get("/users/123")
print(response.json())
```

## Features

- **Zero Dependencies** - Uses only Python standard library (urllib)
- **Automatic Retry** - Exponential backoff on 5xx errors
- **Rate Limiting** - Default 10 requests/second
- **Thread-Safe** - Safe for concurrent usage
- **Type Hints** - Full type annotations throughout
- **Simple API** - Just get, post, put, delete methods

## Installation

The api_client module is a single directory that can be imported directly:

```python
# From your project
from api_client import APIClient, ClientConfig
```

No pip installation required - it's part of your project.

## Basic Usage

### Simple GET Request

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

# GET request
user = client.get("/users/1")
print(f"User: {user.json()['name']}")
# Output: User: Leanne Graham
```

### POST with Data

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

# POST request with JSON data
new_post = {
    "title": "My Post",
    "body": "Post content here",
    "userId": 1
}
response = client.post("/posts", json=new_post)
created = response.json()
print(f"Created post ID: {created['id']}")
# Output: Created post ID: 101
```

### Authentication

```python
from api_client import APIClient, ClientConfig

# API key authentication
config = ClientConfig(
    base_url="https://api.github.com",
    api_key="ghp_yourtoken123"
)
client = APIClient(config)

# The api_key is automatically added as Bearer token
user = client.get("/user")
print(f"Authenticated as: {user.json()['login']}")
```

## Configuration

### ClientConfig Options

```python
from api_client import ClientConfig

config = ClientConfig(
    base_url="https://api.example.com",  # Required
    timeout=30.0,                         # Request timeout in seconds (default: 30)
    max_retries=3,                        # Retry count for 5xx errors (default: 3)
    api_key=None                          # Optional API key for Authorization header
)
```

### Rate Limiting

The client automatically limits requests to 10 per second by default:

```python
from api_client import APIClient, ClientConfig
import time

config = ClientConfig(base_url="https://api.example.com")
client = APIClient(config)

# These requests are automatically rate-limited
start = time.time()
for i in range(20):
    client.get(f"/endpoint/{i}")
elapsed = time.time() - start
print(f"20 requests took {elapsed:.1f} seconds")
# Output: 20 requests took 2.0 seconds
```

## Error Handling

### HTTP Errors

```python
from api_client import APIClient, ClientConfig, HTTPError

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

try:
    response = client.get("/users/99999")  # Non-existent user
except HTTPError as e:
    print(f"HTTP error: {e.status_code} - {e.message}")
    # Output: HTTP error: 404 - Not Found
```

### API Errors

```python
from api_client import APIClient, ClientConfig, APIError

config = ClientConfig(base_url="https://invalid-domain-xyz.com")
client = APIClient(config)

try:
    response = client.get("/test")
except APIError as e:
    print(f"API error: {e}")
    # Output: API error: Failed to connect to server
```

## Advanced Usage

### Custom Headers

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://api.example.com")
client = APIClient(config)

# Add custom headers to any request
response = client.get(
    "/data",
    headers={
        "Accept": "application/json",
        "X-Custom-Header": "value"
    }
)
```

### Query Parameters

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

# Pass query parameters as a dict
response = client.get("/posts", params={"userId": 1, "limit": 5})
# Makes request to: /posts?userId=1&limit=5
```

### Binary Data

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://httpbin.org")
client = APIClient(config)

# Upload binary data
with open("image.png", "rb") as f:
    response = client.post("/post", data=f.read())

# Download binary data
response = client.get("/image/png")
with open("downloaded.png", "wb") as f:
    f.write(response.content)
```

## Thread Safety

The client is fully thread-safe and can be shared across threads:

```python
from api_client import APIClient, ClientConfig
import threading

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)  # Single shared instance

def fetch_user(user_id):
    response = client.get(f"/users/{user_id}")
    print(f"User {user_id}: {response.json()['name']}")

# Create multiple threads using the same client
threads = []
for i in range(1, 6):
    t = threading.Thread(target=fetch_user, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
```

## Response Object

All methods return a Response object with these attributes:

```python
response = client.get("/endpoint")

response.status_code  # HTTP status code (int)
response.headers      # Response headers (dict)
response.content      # Raw bytes
response.text()       # Decoded string
response.json()       # Parse as JSON
```

## Testing

### Mocking for Tests

```python
import unittest
from unittest.mock import patch, MagicMock
from api_client import APIClient, ClientConfig

class TestMyCode(unittest.TestCase):
    @patch('api_client.client.urlopen')
    def test_api_call(self, mock_urlopen):
        # Setup mock
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"result": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Test your code
        config = ClientConfig(base_url="https://api.test.com")
        client = APIClient(config)
        response = client.get("/test")

        self.assertEqual(response.json()["result"], "success")
```

## Common Patterns

### Pagination

```python
from api_client import APIClient, ClientConfig

config = ClientConfig(base_url="https://api.example.com")
client = APIClient(config)

def fetch_all_pages(endpoint):
    """Fetch all pages of paginated results"""
    results = []
    page = 1

    while True:
        response = client.get(endpoint, params={"page": page, "limit": 100})
        data = response.json()

        if not data["items"]:
            break

        results.extend(data["items"])
        page += 1

    return results

# Usage
all_users = fetch_all_pages("/users")
print(f"Total users: {len(all_users)}")
```

### Batch Operations

```python
from api_client import APIClient, ClientConfig
import concurrent.futures

config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
client = APIClient(config)

def update_post(post_id, data):
    """Update a single post"""
    return client.put(f"/posts/{post_id}", json=data)

# Update multiple posts in parallel
updates = [
    (1, {"title": "Updated Title 1"}),
    (2, {"title": "Updated Title 2"}),
    (3, {"title": "Updated Title 3"}),
]

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(update_post, pid, data) for pid, data in updates]
    results = [f.result() for f in concurrent.futures.as_completed(futures)]

print(f"Updated {len(results)} posts")
```

### Circuit Breaker Pattern

```python
from api_client import APIClient, ClientConfig, APIError
import time

class CircuitBreakerClient:
    """Client with circuit breaker pattern"""

    def __init__(self, config, failure_threshold=5, reset_timeout=60):
        self.client = APIClient(config)
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.last_failure_time = None
        self.circuit_open = False

    def get(self, endpoint, **kwargs):
        if self.circuit_open:
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.circuit_open = False
                self.failures = 0
            else:
                raise APIError("Circuit breaker is open")

        try:
            response = self.client.get(endpoint, **kwargs)
            self.failures = 0
            return response
        except APIError as e:
            self.failures += 1
            self.last_failure_time = time.time()

            if self.failures >= self.failure_threshold:
                self.circuit_open = True

            raise e
```

## Troubleshooting

### Connection Timeouts

If requests are timing out:

```python
# Increase timeout for slow endpoints
config = ClientConfig(
    base_url="https://slow-api.example.com",
    timeout=60.0  # 60 seconds
)
```

### SSL Certificate Errors

For development/testing with self-signed certificates:

```python
import ssl
import urllib.request

# Create custom SSL context (development only!)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Apply to urllib globally
urllib.request.install_opener(
    urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx)
    )
)
```

### Rate Limit Errors

If hitting external rate limits:

```python
from api_client import APIClient, ClientConfig, HTTPError
import time

config = ClientConfig(base_url="https://api.github.com")
client = APIClient(config)

def get_with_backoff(endpoint, max_attempts=5):
    """Handle rate limiting with exponential backoff"""
    for attempt in range(max_attempts):
        try:
            return client.get(endpoint)
        except HTTPError as e:
            if e.status_code == 429:  # Rate limited
                wait_time = 2 ** attempt
                print(f"Rate limited, waiting {wait_time}s")
                time.sleep(wait_time)
            else:
                raise
    raise APIError("Max retry attempts exceeded")
```

## Module Structure

```
api_client/
├── __init__.py       # Main exports
├── client.py         # APIClient implementation
├── config.py         # ClientConfig class
├── exceptions.py     # APIError, HTTPError
├── rate_limiter.py   # Rate limiting logic
└── response.py       # Response class
```

## API Contract

The module guarantees:

- **No external dependencies** - Only Python standard library
- **Thread safety** - All operations are thread-safe
- **Type safety** - Full type hints for IDE support
- **Semantic versioning** - Breaking changes only in major versions
- **Backward compatibility** - Existing interfaces preserved

---

For complete API reference, see [API Reference](./docs/reference/api_client.md).
For more examples, see [Usage Examples](./docs/howto/api_client_examples.md).
