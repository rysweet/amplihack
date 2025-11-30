# How to Use AsyncAPIClient

Learn how to make asynchronous HTTP requests using the AsyncAPIClient.

## When to Use Async

Use `AsyncAPIClient` when:

- Making multiple concurrent requests
- Building async applications (FastAPI, aiohttp)
- Avoiding blocking I/O in async contexts
- Maximizing throughput for batch operations

## Basic Usage

### Simple Async Request

```python
import asyncio
from rest_api_client import AsyncAPIClient

async def fetch_users():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        response = await client.get("/users")
        return response.data

# Run the async function
users = asyncio.run(fetch_users())
print(users)
```

### Multiple Concurrent Requests

```python
import asyncio
from rest_api_client import AsyncAPIClient

async def fetch_all_data():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Launch multiple requests concurrently
        tasks = [
            client.get("/users"),
            client.get("/posts"),
            client.get("/comments")
        ]

        # Wait for all to complete
        responses = await asyncio.gather(*tasks)

        return {
            "users": responses[0].data,
            "posts": responses[1].data,
            "comments": responses[2].data
        }

# Run and get results
data = asyncio.run(fetch_all_data())
```

## Configuration

### Setting Up the Client

```python
from rest_api_client import AsyncAPIClient
from rest_api_client.config import APIConfig, RetryConfig

# Configure the async client
config = APIConfig(
    base_url="https://api.example.com",
    timeout=30,
    headers={"User-Agent": "MyAsyncApp/1.0"}
)

retry_config = RetryConfig(
    max_attempts=3,
    initial_delay=1.0
)

# Create configured client
async def main():
    async with AsyncAPIClient(
        config=config,
        retry_config=retry_config
    ) as client:
        response = await client.get("/data")
        print(response.data)

asyncio.run(main())
```

## Advanced Patterns

### Batch Processing with Rate Limiting

```python
import asyncio
from rest_api_client import AsyncAPIClient

async def process_batch(items, batch_size=10):
    async with AsyncAPIClient(
        base_url="https://api.example.com",
        rate_limit_calls=100,
        rate_limit_period=60
    ) as client:
        results = []

        # Process in batches to respect rate limits
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]

            # Create tasks for current batch
            tasks = [
                client.post("/process", json={"item": item})
                for item in batch
            ]

            # Execute batch concurrently
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

            # Optional: Add delay between batches
            if i + batch_size < len(items):
                await asyncio.sleep(1)

        return results

# Process 100 items in batches of 10
items = list(range(100))
results = asyncio.run(process_batch(items))
```

### Error Handling in Async Context

```python
import asyncio
from rest_api_client import AsyncAPIClient
from rest_api_client.exceptions import RateLimitError, NetworkError

async def safe_fetch(client, endpoint):
    """Fetch with proper error handling."""
    try:
        return await client.get(endpoint)
    except RateLimitError as e:
        print(f"Rate limited, waiting {e.retry_after} seconds")
        await asyncio.sleep(e.retry_after)
        return await safe_fetch(client, endpoint)
    except NetworkError as e:
        print(f"Network error: {e}")
        return None

async def fetch_with_fallback():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Try primary endpoint, fall back to secondary
        response = await safe_fetch(client, "/primary/data")
        if response is None:
            response = await safe_fetch(client, "/fallback/data")
        return response

data = asyncio.run(fetch_with_fallback())
```

### Streaming Responses

```python
import asyncio
from rest_api_client import AsyncAPIClient

async def stream_large_dataset():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        page = 1
        while True:
            response = await client.get(
                "/data",
                params={"page": page, "per_page": 100}
            )

            if not response.data:
                break

            # Process each page as it arrives
            for item in response.data:
                yield item

            page += 1

async def process_stream():
    async for item in stream_large_dataset():
        # Process each item
        print(f"Processing: {item['id']}")

asyncio.run(process_stream())
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from rest_api_client import AsyncAPIClient
from rest_api_client.exceptions import APIError

app = FastAPI()

# Create a shared client instance
api_client = AsyncAPIClient(base_url="https://external-api.com")

@app.on_event("startup")
async def startup_event():
    """Initialize the client on startup."""
    await api_client.__aenter__()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    await api_client.__aexit__(None, None, None)

@app.get("/proxy/{path:path}")
async def proxy_request(path: str):
    """Proxy requests to external API."""
    try:
        response = await api_client.get(f"/{path}")
        return response.data
    except APIError as e:
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=str(e)
        )
```

### Async Context Manager Pattern

```python
class DataService:
    def __init__(self, base_url):
        self.base_url = base_url
        self.client = None

    async def __aenter__(self):
        self.client = AsyncAPIClient(base_url=self.base_url)
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def get_user(self, user_id):
        response = await self.client.get(f"/users/{user_id}")
        return response.data

    async def get_posts(self, user_id):
        response = await self.client.get(
            "/posts",
            params={"user_id": user_id}
        )
        return response.data

# Usage
async def main():
    async with DataService("https://api.example.com") as service:
        user = await service.get_user(123)
        posts = await service.get_posts(123)
        print(f"User {user['name']} has {len(posts)} posts")

asyncio.run(main())
```

## Performance Tips

### Connection Pooling

The AsyncAPIClient automatically manages connection pooling:

```python
# Reuse the same client for multiple requests
async with AsyncAPIClient(base_url="https://api.example.com") as client:
    # All requests share the connection pool
    for i in range(100):
        await client.get(f"/item/{i}")
```

### Timeout Configuration

Set appropriate timeouts for your use case:

```python
# Short timeout for fast endpoints
quick_client = AsyncAPIClient(
    base_url="https://api.example.com",
    timeout=5  # 5 seconds
)

# Longer timeout for slow operations
slow_client = AsyncAPIClient(
    base_url="https://api.example.com",
    timeout=120  # 2 minutes
)
```

### Concurrency Control

Limit concurrent requests to avoid overwhelming the server:

```python
async def controlled_fetch(urls, max_concurrent=5):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_limit(client, url):
        async with semaphore:
            return await client.get(url)

    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        tasks = [
            fetch_with_limit(client, url)
            for url in urls
        ]
        return await asyncio.gather(*tasks)

urls = [f"/item/{i}" for i in range(100)]
results = asyncio.run(controlled_fetch(urls))
```

## Common Pitfalls

### Don't Create Multiple Event Loops

```python
# WRONG - Creates nested event loops
def bad_sync_wrapper():
    return asyncio.run(fetch_data())  # Don't do this inside async context

# RIGHT - Use await in async context
async def good_async_function():
    return await fetch_data()
```

### Remember to Close the Client

```python
# WRONG - Client not properly closed
client = AsyncAPIClient(base_url="https://api.example.com")
response = await client.get("/data")

# RIGHT - Use context manager
async with AsyncAPIClient(base_url="https://api.example.com") as client:
    response = await client.get("/data")
```

### Handle Exceptions Properly

```python
# WRONG - Unhandled exception in gather
results = await asyncio.gather(*tasks)  # One failure fails all

# RIGHT - Handle exceptions
results = await asyncio.gather(*tasks, return_exceptions=True)
for result in results:
    if isinstance(result, Exception):
        print(f"Request failed: {result}")
    else:
        process(result)
```

## Testing Async Code

```python
import pytest
from unittest.mock import AsyncMock
from rest_api_client import AsyncAPIClient

@pytest.mark.asyncio
async def test_async_client():
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Mock the underlying session
        client.session.get = AsyncMock(return_value=MockResponse())

        response = await client.get("/test")
        assert response.status_code == 200

class MockResponse:
    status = 200
    headers = {}

    async def json(self):
        return {"test": "data"}

    async def text(self):
        return '{"test": "data"}'
```

## Summary

The AsyncAPIClient provides:

- Full async/await support for non-blocking I/O
- Automatic connection pooling
- Concurrent request handling
- Same features as sync client (retry, rate limiting, etc.)
- Integration with async frameworks

Use it when building async applications or when you need to make multiple concurrent API calls efficiently.
