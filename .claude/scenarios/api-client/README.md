# Simple API Client

A lightweight HTTP client for JSON APIs using only Python standard library.

## Overview

The Simple API Client provides GET and POST methods for interacting with JSON APIs. Built with zero external dependencies, it works anywhere Python runs without installation complexity.

**Key Features**:

- Standard library only (urllib, json)
- Clean error hierarchy (APIError, RequestTimeoutError, HTTPError)
- Automatic JSON encoding/decoding
- Configurable timeouts
- Works with any JSON API

## Quick Start

```python
from api_client import APIClient

# Create client with base URL
client = APIClient("https://jsonplaceholder.typicode.com")

# GET request
posts = client.get("/posts")
print(f"Found {len(posts)} posts")

# POST request
new_post = client.post("/posts", {
    "title": "Hello World",
    "body": "This is my first post",
    "userId": 1
})
print(f"Created post with id: {new_post['id']}")
```

## Installation

No installation required. Copy `api_client.py` to your project:

```bash
cp .claude/scenarios/api-client/api_client.py your_project/
```

Or import directly from the scenarios directory:

```python
import sys
sys.path.insert(0, ".claude/scenarios/api-client")
from api_client import APIClient
```

## API Reference

### APIClient

The main client class for making HTTP requests.

```python
APIClient(base_url: str, timeout: int = 30)
```

**Parameters**:

| Parameter  | Type | Default | Description                |
| ---------- | ---- | ------- | -------------------------- |
| `base_url` | str  | -       | Base URL for all requests  |
| `timeout`  | int  | 30      | Request timeout in seconds |

**Methods**:

#### get(endpoint: str) -> dict | list

Make a GET request to the specified endpoint.

```python
client = APIClient("https://api.example.com")

# Get a list
users = client.get("/users")

# Get a single item
user = client.get("/users/1")
```

**Returns**: Parsed JSON response (dict or list)

**Raises**: `HTTPError` on 4xx/5xx responses, `RequestTimeoutError` on timeout

#### post(endpoint: str, data: dict) -> dict

Make a POST request with JSON body.

```python
client = APIClient("https://api.example.com")

result = client.post("/users", {
    "name": "John Doe",
    "email": "john@example.com"
})
```

**Parameters**:

| Parameter  | Type | Description          |
| ---------- | ---- | -------------------- |
| `endpoint` | str  | API endpoint path    |
| `data`     | dict | Data to send as JSON |

**Returns**: Parsed JSON response (dict)

**Raises**: `HTTPError` on 4xx/5xx responses, `RequestTimeoutError` on timeout

### Exception Classes

All exceptions inherit from `APIError` for easy catching.

```python
from api_client import APIClient, APIError, HTTPError, RequestTimeoutError
```

#### APIError

Base exception for all API client errors.

```python
try:
    result = client.get("/endpoint")
except APIError as e:
    print(f"API error: {e}")
```

#### HTTPError

Raised when server returns 4xx or 5xx status code.

```python
try:
    result = client.get("/nonexistent")
except HTTPError as e:
    print(f"HTTP {e.status_code}: {e.message}")
```

**Attributes**:

- `status_code` (int): HTTP status code
- `message` (str): Error description

#### RequestTimeoutError

Raised when request exceeds timeout.

```python
client = APIClient("https://slow-api.example.com", timeout=5)

try:
    result = client.get("/slow-endpoint")
except RequestTimeoutError as e:
    print(f"Request timed out: {e}")
```

## Error Handling

### Handling All Errors

```python
from api_client import APIClient, APIError

client = APIClient("https://jsonplaceholder.typicode.com")

try:
    result = client.get("/posts/1")
    print(f"Got post: {result['title']}")
except APIError as e:
    print(f"Request failed: {e}")
```

### Handling Specific Errors

```python
from api_client import APIClient, HTTPError, RequestTimeoutError

client = APIClient("https://jsonplaceholder.typicode.com", timeout=10)

try:
    result = client.post("/posts", {"title": "Test"})
except HTTPError as e:
    if e.status_code == 404:
        print("Endpoint not found")
    elif e.status_code >= 500:
        print("Server error - try again later")
    else:
        print(f"HTTP error {e.status_code}: {e.message}")
except RequestTimeoutError:
    print("Request timed out - check your connection")
```

### Retry Pattern

```python
import time
from api_client import APIClient, APIError

def request_with_retry(client, endpoint, max_retries=3):
    """Make request with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return client.get(endpoint)
        except APIError as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt
            print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
            time.sleep(wait_time)

client = APIClient("https://jsonplaceholder.typicode.com")
posts = request_with_retry(client, "/posts")
```

## Integration with Amplihack Scenarios

### Using from Other Scenarios

Import the client in your scenario tool:

```python
# In your scenario's tool.py
import sys
from pathlib import Path

# Add api-client to path
scenarios_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scenarios_dir / "api-client"))

from api_client import APIClient, APIError

def fetch_external_data(api_url: str):
    """Fetch data from external API."""
    client = APIClient(api_url)
    return client.get("/data")
```

### Makefile Integration

Run the demo:

```bash
make api-client-demo
```

Or use in your own Makefile target:

```makefile
my-tool:
	@python .claude/scenarios/my-tool/tool.py
```

## Examples

See `examples/demo.py` for a complete working demonstration:

```bash
python .claude/scenarios/api-client/examples/demo.py
```

## Testing

Run the test suite:

```bash
python -m pytest .claude/scenarios/api-client/tests/
```

## Limitations

- **JSON only**: Designed for JSON APIs; does not handle XML, form data, or file uploads
- **No authentication**: Add headers manually via subclassing if needed
- **Synchronous**: Uses blocking I/O; for async, consider aiohttp

## Troubleshooting

### Connection Refused

```
urllib.error.URLError: <urlopen error [Errno 111] Connection refused>
```

**Cause**: Server not running or wrong URL.
**Fix**: Verify the base URL and that the server is accessible.

### SSL Certificate Error

```
ssl.SSLCertificateVerifyError: certificate verify failed
```

**Cause**: Invalid or self-signed SSL certificate.
**Fix**: For development only, you can disable verification (not recommended for production).

### Timeout on Large Responses

**Cause**: Default 30s timeout too short.
**Fix**: Increase timeout when creating client:

```python
client = APIClient("https://api.example.com", timeout=120)
```

---

**Philosophy**: This tool follows amplihack's ruthless simplicity - one file, standard library only, does exactly what's needed without unnecessary abstraction.
