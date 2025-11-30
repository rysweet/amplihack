# Usage Patterns

Common patterns and best practices for using the REST API Client effectively.

## Contents

- [Authentication Patterns](#authentication-patterns)
- [Batch Operations](#batch-operations)
- [Retry Strategies](#retry-strategies)
- [Rate Limiting Patterns](#rate-limiting-patterns)
- [Response Processing](#response-processing)
- [Error Recovery](#error-recovery)
- [Testing Patterns](#testing-patterns)

## Authentication Patterns

### Bearer Token Authentication

```python
from api_client import RESTClient

class AuthenticatedClient(RESTClient):
    """Client with automatic bearer token authentication."""

    def __init__(self, base_url: str, token: str, **kwargs):
        super().__init__(base_url, **kwargs)
        self.token = token
        self.default_headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    def request(self, method: str, path: str, headers: dict = None, **kwargs):
        """Add auth headers to all requests."""
        final_headers = self.default_headers.copy()
        if headers:
            final_headers.update(headers)
        return super().request(method, path, headers=final_headers, **kwargs)

# Usage
client = AuthenticatedClient(
    "https://api.example.com",
    token="your_secret_token"
)
response = client.get("/protected-resource")
```

### API Key Authentication

```python
from api_client import RESTClient

class APIKeyClient(RESTClient):
    """Client with API key authentication."""

    def __init__(self, base_url: str, api_key: str, key_param: str = "api_key"):
        super().__init__(base_url)
        self.api_key = api_key
        self.key_param = key_param

    def get(self, path: str, params: dict = None, **kwargs):
        """Add API key to all GET requests."""
        final_params = params or {}
        final_params[self.key_param] = self.api_key
        return super().get(path, params=final_params, **kwargs)

# Usage
weather_client = APIKeyClient(
    "https://api.openweathermap.org/data/2.5",
    api_key="your_api_key"
)
response = weather_client.get("/weather", params={"q": "London"})
```

## Batch Operations

### Parallel Requests with Thread Pool

```python
from api_client import RESTClient
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_user(client: RESTClient, user_id: int):
    """Fetch single user details."""
    response = client.get(f"/users/{user_id}")
    return response.json()

# Fetch multiple users in parallel
client = RESTClient("https://api.example.com", rate_limit=20)
user_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {
        executor.submit(fetch_user, client, uid): uid
        for uid in user_ids
    }

    users = {}
    for future in as_completed(futures):
        user_id = futures[future]
        try:
            users[user_id] = future.result()
        except Exception as e:
            print(f"Failed to fetch user {user_id}: {e}")

print(f"Fetched {len(users)} users successfully")
```

### Sequential Batch Processing

```python
from api_client import RESTClient
import time

def process_batch(client: RESTClient, items: list, batch_size: int = 100):
    """Process items in batches with progress tracking."""
    total = len(items)
    processed = 0

    for i in range(0, total, batch_size):
        batch = items[i:i + batch_size]

        # Send batch request
        response = client.post("/batch-process", json={"items": batch})

        if response.status_code == 200:
            processed += len(batch)
            print(f"Progress: {processed}/{total} ({100*processed/total:.1f}%)")
        else:
            print(f"Batch failed at items {i}-{i+len(batch)}")

        # Small delay between batches
        time.sleep(0.1)

    return processed

# Usage
client = RESTClient("https://api.example.com", rate_limit=5)
items = [f"item_{i}" for i in range(1000)]
total_processed = process_batch(client, items, batch_size=50)
```

## Retry Strategies

### Custom Retry Logic

```python
from api_client import RESTClient
import time

def resilient_request(client: RESTClient, method: str, path: str,
                       max_attempts: int = 5, **kwargs):
    """Request with custom retry logic and backoff."""
    backoff_seconds = 1

    for attempt in range(max_attempts):
        try:
            response = getattr(client, method)(path, **kwargs)

            # Success
            if 200 <= response.status_code < 300:
                return response

            # Client error - don't retry
            if 400 <= response.status_code < 500:
                return response

            # Server error - retry with backoff
            if attempt < max_attempts - 1:
                print(f"Attempt {attempt + 1} failed, retrying in {backoff_seconds}s...")
                time.sleep(backoff_seconds)
                backoff_seconds *= 2

        except Exception as e:
            if attempt < max_attempts - 1:
                print(f"Request failed: {e}, retrying...")
                time.sleep(backoff_seconds)
                backoff_seconds *= 2
            else:
                raise

    raise Exception(f"Failed after {max_attempts} attempts")

# Usage
client = RESTClient("https://api.example.com")
response = resilient_request(client, "get", "/unstable-endpoint")
```

## Rate Limiting Patterns

### Adaptive Rate Limiting

```python
from api_client import RESTClient
import time

class AdaptiveRateLimitClient(RESTClient):
    """Client that adapts rate limit based on server responses."""

    def __init__(self, base_url: str, initial_rate: float = 10):
        super().__init__(base_url, rate_limit=initial_rate)
        self.min_rate = 1
        self.max_rate = 100

    def request(self, method: str, path: str, **kwargs):
        """Make request and adjust rate based on response."""
        response = super().request(method, path, **kwargs)

        # Check rate limit headers
        if "X-RateLimit-Remaining" in response.headers:
            remaining = int(response.headers["X-RateLimit-Remaining"])
            if remaining < 10:
                # Slow down
                self.rate_limit = max(self.min_rate, self.rate_limit * 0.5)
                print(f"Slowing down to {self.rate_limit} req/s")
            elif remaining > 100:
                # Speed up
                self.rate_limit = min(self.max_rate, self.rate_limit * 1.5)
                print(f"Speeding up to {self.rate_limit} req/s")

        # Check for rate limit errors
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            print(f"Rate limited, waiting {retry_after} seconds")
            time.sleep(retry_after)
            return self.request(method, path, **kwargs)

        return response
```

## Response Processing

### Stream Processing Large Responses

```python
from api_client import RESTClient
import json

def process_streaming_response(client: RESTClient, endpoint: str):
    """Process large JSON array responses efficiently."""
    response = client.get(endpoint)

    # For large arrays, process items one at a time
    data = response.json()

    if isinstance(data, list):
        for item in data:
            # Process each item immediately
            process_item(item)
            # Free memory by not keeping all items
    else:
        # Handle single object
        process_item(data)

def process_item(item: dict):
    """Process single item from response."""
    print(f"Processing: {item.get('id', 'unknown')}")
```

### Response Caching

```python
from api_client import RESTClient
from functools import lru_cache
import hashlib
import json

class CachedClient(RESTClient):
    """Client with response caching."""

    def __init__(self, base_url: str, cache_size: int = 128):
        super().__init__(base_url)
        self.cache_size = cache_size
        self._cache = {}

    def _cache_key(self, method: str, path: str, params: dict = None):
        """Generate cache key from request parameters."""
        key_data = f"{method}:{path}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, path: str, params: dict = None, use_cache: bool = True, **kwargs):
        """GET with optional caching."""
        if use_cache:
            cache_key = self._cache_key("GET", path, params)
            if cache_key in self._cache:
                print(f"Cache hit for {path}")
                return self._cache[cache_key]

        response = super().get(path, params=params, **kwargs)

        if use_cache and response.status_code == 200:
            # Maintain cache size limit
            if len(self._cache) >= self.cache_size:
                # Remove oldest entry (simple FIFO)
                self._cache.pop(next(iter(self._cache)))
            self._cache[cache_key] = response

        return response

# Usage
cached_client = CachedClient("https://api.example.com")
# First call hits API
response1 = cached_client.get("/users/123")
# Second call uses cache
response2 = cached_client.get("/users/123")
```

## Error Recovery

### Circuit Breaker Pattern

```python
from api_client import RESTClient
import time

class CircuitBreakerClient(RESTClient):
    """Client with circuit breaker for failing endpoints."""

    def __init__(self, base_url: str, failure_threshold: int = 5):
        super().__init__(base_url)
        self.failure_threshold = failure_threshold
        self.failures = {}
        self.circuit_open_until = {}

    def request(self, method: str, path: str, **kwargs):
        """Check circuit breaker before making request."""
        # Check if circuit is open
        if path in self.circuit_open_until:
            if time.time() < self.circuit_open_until[path]:
                raise Exception(f"Circuit breaker open for {path}")
            else:
                # Reset circuit
                del self.circuit_open_until[path]
                self.failures[path] = 0

        try:
            response = super().request(method, path, **kwargs)

            if response.status_code >= 500:
                self._record_failure(path)
            else:
                # Reset failure count on success
                self.failures[path] = 0

            return response

        except Exception as e:
            self._record_failure(path)
            raise

    def _record_failure(self, path: str):
        """Record failure and open circuit if threshold exceeded."""
        self.failures[path] = self.failures.get(path, 0) + 1

        if self.failures[path] >= self.failure_threshold:
            # Open circuit for 60 seconds
            self.circuit_open_until[path] = time.time() + 60
            print(f"Circuit breaker opened for {path}")
```

## Testing Patterns

### Mock Client for Testing

```python
from api_client import RESTClient
from dataclasses import dataclass

class MockClient(RESTClient):
    """Mock client for testing without real API calls."""

    def __init__(self):
        # Don't call super().__init__ to avoid real connection
        self.responses = {}
        self.call_history = []

    def set_response(self, method: str, path: str, response_data: dict,
                      status_code: int = 200):
        """Configure mock response for specific endpoint."""
        key = f"{method}:{path}"
        self.responses[key] = (response_data, status_code)

    def request(self, method: str, path: str, **kwargs):
        """Return mock response."""
        self.call_history.append((method, path, kwargs))

        key = f"{method}:{path}"
        if key in self.responses:
            data, status = self.responses[key]
            return Response(
                status_code=status,
                headers={},
                body=json.dumps(data).encode(),
                url=f"mock://{path}"
            )

        # Default 404 response
        return Response(
            status_code=404,
            headers={},
            body=b'{"error": "Not found"}',
            url=f"mock://{path}"
        )

# Usage in tests
def test_user_fetch():
    # Setup
    client = MockClient()
    client.set_response("GET", "/users/123",
                        {"id": 123, "name": "Alice"})

    # Test
    response = client.get("/users/123")
    assert response.status_code == 200
    assert response.json()["name"] == "Alice"

    # Verify calls
    assert len(client.call_history) == 1
    assert client.call_history[0][0] == "GET"
```

## Best Practices

1. **Always handle rate limits** - Check headers and respect retry-after
2. **Use connection pooling** - Reuse client instances
3. **Implement timeouts** - Never wait indefinitely
4. **Log failures** - Track patterns in failures
5. **Cache when appropriate** - Reduce unnecessary API calls
6. **Test with mocks** - Don't hit real APIs in unit tests
7. **Monitor usage** - Track your API consumption
8. **Handle pagination** - Don't assume single-page responses
