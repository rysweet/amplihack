# Using the API Client

Learn how to make reliable HTTP requests with built-in retry logic and error handling.

## Quick Start

Make your first API request in 3 lines:

```python
from amplihack.utils import APIClient

client = APIClient("https://api.example.com")
response = client.execute("GET", "/users")
```

## Setup

### Installation

The API client is included with amplihack:

```bash
pip install amplihack
```

### Basic Configuration

Create a client with your API base URL:

```python
from amplihack.utils import APIClient

# Minimal setup
client = APIClient("https://api.example.com")

# With configuration
client = APIClient(
    base_url="https://api.example.com",
    timeout=30,
    max_retries=3
)
```

## Common Tasks

### Making GET Requests

Fetch data from an API endpoint:

```python
from amplihack.utils import APIClient

client = APIClient("https://jsonplaceholder.typicode.com")

# Simple GET request
response = client.execute("GET", "/posts/1")
print(f"Status: {response.status_code}")
print(f"Title: {response.data['title']}")
# Output: Status: 200
# Output: Title: sunt aut facere repellat provident occaecati excepturi optio reprehenderit
```

### Making POST Requests

Send data to create resources:

```python
from amplihack.utils import APIClient

client = APIClient("https://jsonplaceholder.typicode.com")

# POST with JSON data
new_post = {
    "title": "My Post",
    "body": "This is the content",
    "userId": 1
}

response = client.execute("POST", "/posts", json=new_post)
print(f"Created post ID: {response.data['id']}")
# Output: Created post ID: 101
```

### Adding Headers

Include authentication or custom headers:

```python
from amplihack.utils import APIClient

client = APIClient("https://api.github.com")

# Add authorization header
headers = {
    "Authorization": "Bearer your-token-here",
    "Accept": "application/vnd.github.v3+json"
}

response = client.execute("GET", "/user", headers=headers)
print(f"User: {response.data.get('login', 'Anonymous')}")
# Output: User: octocat
```

### Handling Errors

Catch and handle specific error types:

```python
from amplihack.utils import APIClient, APIError, RateLimitError

client = APIClient("https://api.example.com")

try:
    response = client.execute("GET", "/protected-resource")
    print(f"Data: {response.data}")
except RateLimitError as e:
    print(f"Rate limited. Retry after: {e.retry_after} seconds")
except APIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

### Configuring Retries

Customize retry behavior for your use case:

```python
from amplihack.utils import APIClient

# More aggressive retries for critical operations
client = APIClient(
    base_url="https://api.critical-service.com",
    max_retries=5,
    retry_delay=2.0  # Start with 2 second delay
)

# No retries for fast-fail scenarios
client = APIClient(
    base_url="https://api.fast-service.com",
    max_retries=0
)
```

## Examples

### Paginated API Fetching

Fetch all pages from a paginated API:

```python
from amplihack.utils import APIClient

def fetch_all_users(api_url: str):
    """Fetch all users from paginated API."""
    client = APIClient(api_url)
    users = []
    page = 1

    while True:
        response = client.execute("GET", "/users", params={"page": page})
        batch = response.data.get("users", [])

        if not batch:
            break

        users.extend(batch)
        page += 1

    return users

# Usage
all_users = fetch_all_users("https://api.example.com")
print(f"Total users: {len(all_users)}")
```

### Batch Processing with Error Recovery

Process multiple API calls with resilient error handling:

```python
from amplihack.utils import APIClient, APIError

def process_batch(items: list, api_url: str):
    """Process items through API with error tracking."""
    client = APIClient(api_url, max_retries=2)
    results = {"success": [], "failed": []}

    for item in items:
        try:
            response = client.execute("POST", "/process", json=item)
            results["success"].append(response.data)
        except APIError as e:
            results["failed"].append({
                "item": item,
                "error": str(e)
            })

    return results

# Usage
items = [{"id": 1}, {"id": 2}, {"id": 3}]
results = process_batch(items, "https://api.example.com")
print(f"Processed: {len(results['success'])}, Failed: {len(results['failed'])}")
```

## Troubleshooting

### Connection Timeouts

If requests are timing out:

```python
# Increase timeout for slow APIs
client = APIClient("https://slow-api.com", timeout=60)

# Or handle timeout errors
from amplihack.utils import APIError

try:
    response = client.execute("GET", "/slow-endpoint")
except APIError as e:
    if "timeout" in str(e).lower():
        print("Request timed out, try again later")
```

### SSL Certificate Issues

For development/testing with self-signed certificates:

```python
# Note: Only for development - never in production!
import warnings
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

client = APIClient("https://dev-server.local")
# Client will work with self-signed certificates
```

### Rate Limit Handling

When hitting rate limits:

```python
from amplihack.utils import APIClient, RateLimitError
import time

client = APIClient("https://api.github.com")

try:
    response = client.execute("GET", "/search/repositories",
                            params={"q": "python"})
except RateLimitError as e:
    print(f"Rate limited. Waiting {e.retry_after} seconds...")
    time.sleep(e.retry_after)
    # Retry the request
    response = client.execute("GET", "/search/repositories",
                            params={"q": "python"})
```

## See Also

- [API Client Reference](../reference/api-client.md) - Complete API documentation
- [Error Handling Guide](../concepts/error-handling.md) - Understanding error types
