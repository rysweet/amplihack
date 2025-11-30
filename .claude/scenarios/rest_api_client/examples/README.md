# REST API Client - Usage Examples

This directory contains complete, runnable examples demonstrating common usage patterns for the REST API Client.

## Quick Navigation

- [CRUD Operations](./crud_operations.py) - Basic Create, Read, Update, Delete operations
- [Authentication](./authentication.py) - Various authentication methods
- [Error Handling](./error_handling.py) - Comprehensive error handling patterns
- [Pagination](./pagination.py) - Handling paginated API responses
- [Batch Operations](./batch_operations.py) - Efficient batch processing
- [Webhooks](./webhooks.py) - Webhook endpoint implementation
- [Rate Limiting](./rate_limiting.py) - Working with rate-limited APIs
- [File Uploads](./file_uploads.py) - Multipart file uploads
- [Streaming](./streaming.py) - Streaming large responses
- [Testing](./testing_patterns.py) - Unit and integration testing patterns

## Running the Examples

Each example can be run independently:

```bash
# Run a specific example
python examples/crud_operations.py

# Run with your API
API_URL=https://api.example.com python examples/pagination.py
```

## Basic Example

Here's a simple example to get started:

```python
#!/usr/bin/env python3
"""Basic usage example of REST API Client."""

from rest_api_client import APIClient

def main():
    # Initialize client
    client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # GET request
    response = client.get("/posts/1")
    print(f"Post title: {response.data['title']}")

    # POST request
    new_post = {
        "title": "My New Post",
        "body": "This is the content",
        "userId": 1
    }
    response = client.post("/posts", json=new_post)
    print(f"Created post ID: {response.data['id']}")

    # PUT request
    updated_post = {
        "id": 1,
        "title": "Updated Title",
        "body": "Updated content",
        "userId": 1
    }
    response = client.put("/posts/1", json=updated_post)
    print(f"Updated: {response.status_code == 200}")

    # DELETE request
    response = client.delete("/posts/1")
    print(f"Deleted: {response.status_code == 200}")

if __name__ == "__main__":
    main()
```

## Common Patterns

### Pattern: Automatic Retry with Backoff

```python
from rest_api_client import APIClient, RetryConfig

client = APIClient(
    base_url="https://api.example.com",
    retry_config=RetryConfig(
        max_attempts=5,
        initial_delay=1.0,
        exponential_base=2
    )
)

# Automatically retries on failure
response = client.get("/flaky-endpoint")
```

### Pattern: Rate-Limited API Access

```python
from rest_api_client import APIClient, RateLimitConfig

client = APIClient(
    base_url="https://api.example.com",
    rate_limit_config=RateLimitConfig(
        max_requests_per_second=2,
        respect_retry_after=True
    )
)

# Requests are automatically throttled
for item_id in range(100):
    response = client.get(f"/items/{item_id}")
```

### Pattern: Batch Processing with Error Recovery

```python
def process_batch(client, items):
    """Process items with error recovery."""
    results = {"success": [], "failed": []}

    for item in items:
        try:
            response = client.post("/process", json=item)
            results["success"].append(response.data)
        except Exception as e:
            results["failed"].append({"item": item, "error": str(e)})
            continue

    return results
```

### Pattern: Pagination Handling

```python
def fetch_all_pages(client, endpoint):
    """Fetch all pages from a paginated endpoint."""
    all_items = []
    page = 1

    while True:
        response = client.get(endpoint, params={"page": page, "per_page": 100})
        items = response.data.get("items", [])
        all_items.extend(items)

        if len(items) < 100:  # Last page
            break
        page += 1

    return all_items
```

## Advanced Examples

### Custom Authentication

```python
from rest_api_client import APIClient
import jwt
import time

class JWTAuthClient:
    """Client with automatic JWT token refresh."""

    def __init__(self, base_url, client_id, client_secret):
        self.client = APIClient(base_url=base_url)
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expiry = 0

    def _refresh_token(self):
        """Refresh JWT token if expired."""
        if time.time() >= self.token_expiry:
            response = self.client.post("/auth/token", json={
                "client_id": self.client_id,
                "client_secret": self.client_secret
            })
            self.token = response.data["access_token"]
            self.token_expiry = time.time() + response.data["expires_in"] - 60

    def request(self, method, path, **kwargs):
        """Make authenticated request."""
        self._refresh_token()
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {self.token}"
        kwargs["headers"] = headers
        return getattr(self.client, method.lower())(path, **kwargs)
```

### Parallel Requests with asyncio

```python
import asyncio
from rest_api_client.async_client import AsyncAPIClient

async def fetch_user(client, user_id):
    """Fetch a single user."""
    response = await client.get(f"/users/{user_id}")
    return response.data

async def fetch_all_users(user_ids):
    """Fetch multiple users in parallel."""
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        tasks = [fetch_user(client, uid) for uid in user_ids]
        users = await asyncio.gather(*tasks)
    return users

# Usage
user_ids = [1, 2, 3, 4, 5]
users = asyncio.run(fetch_all_users(user_ids))
```

### Circuit Breaker Pattern

```python
from rest_api_client import APIClient
import time

class CircuitBreakerClient:
    """Client with circuit breaker pattern."""

    def __init__(self, base_url, failure_threshold=5, recovery_timeout=60):
        self.client = APIClient(base_url=base_url)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def request(self, method, path, **kwargs):
        """Make request with circuit breaker."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            response = getattr(self.client, method.lower())(path, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return response
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"

            raise e
```

## Testing Examples

See [testing_patterns.py](./testing_patterns.py) for comprehensive testing examples including:

- Unit testing with mocks
- Integration testing with MockServer
- Testing retry logic
- Testing rate limiting
- Testing error handling
- Performance testing

## Best Practices

1. **Always handle errors** - Don't let exceptions crash your application
2. **Use connection pooling** - Use `client.session()` for multiple requests
3. **Configure appropriate timeouts** - Default 30s might be too long/short
4. **Log important operations** - Configure logging for debugging
5. **Respect rate limits** - Configure rate limiting to avoid 429 errors
6. **Test your integration** - Use MockServer for reliable tests
7. **Monitor performance** - Track response times and retry counts

## Environment Setup

Some examples use environment variables for configuration:

```bash
export API_BASE_URL=https://api.example.com
export API_KEY=your-api-key-here
export LOG_LEVEL=DEBUG
```

Or create a `.env` file:

```env
API_BASE_URL=https://api.example.com
API_KEY=your-api-key-here
LOG_LEVEL=DEBUG
```

## Contributing

To add a new example:

1. Create a new Python file in this directory
2. Include a docstring explaining what the example demonstrates
3. Make it runnable with `python examples/your_example.py`
4. Add it to the Quick Navigation section above
5. Test it works with a real or mock API
