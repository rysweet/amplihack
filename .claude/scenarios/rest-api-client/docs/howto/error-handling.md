# How to Handle Errors

Implement robust error handling for production applications.

## Understanding Exception Hierarchy

```
APIException (base)
├── ConnectionException     # Network connectivity issues
├── TimeoutException       # Request timeout
├── RateLimitException     # Rate limit exceeded
└── ValidationException    # Request validation failed
```

## Basic Error Handling

### Catch All API Errors

```python
from rest_api_client import APIClient, APIException

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/users/123")
    user = response.data
except APIException as e:
    print(f"API error: {e.message}")
    print(f"Status code: {e.status_code}")
    if e.response:
        print(f"Response data: {e.response.data}")
```

### Handle Specific Error Types

```python
from rest_api_client import (
    APIClient,
    ConnectionException,
    TimeoutException,
    RateLimitException,
    ValidationException
)

client = APIClient(base_url="https://api.example.com")

try:
    response = client.post("/users", json={"name": "Alice"})
except ConnectionException as e:
    # Network is down or server unreachable
    print(f"Connection failed: {e.message}")
    print("Check your network connection")
except TimeoutException as e:
    # Request took too long
    print(f"Request timed out: {e.message}")
    print("Server may be overloaded")
except RateLimitException as e:
    # Too many requests
    print(f"Rate limited: {e.message}")
    print(f"Retry after {e.retry_after} seconds")
except ValidationException as e:
    # Invalid request data
    print(f"Validation error: {e.message}")
    print("Check your request parameters")
except APIException as e:
    # Other API errors
    print(f"API error: {e.message} (status: {e.status_code})")
```

## HTTP Status Code Handling

### Check Status Codes

```python
response = client.get("/users/123")

if response.status_code == 200:
    print(f"Success: {response.data}")
elif response.status_code == 404:
    print("User not found")
elif response.status_code == 401:
    print("Authentication required")
elif response.status_code >= 500:
    print("Server error - try again later")
```

### Use raise_for_status()

```python
try:
    response = client.get("/protected-resource")
    response.raise_for_status()  # Raises exception for 4xx/5xx

    # Only runs if status is 2xx
    print(f"Got data: {response.data}")

except APIException as e:
    if e.status_code == 401:
        print("Please log in first")
    elif e.status_code == 403:
        print("You don't have permission")
    elif e.status_code == 404:
        print("Resource not found")
    else:
        print(f"Error {e.status_code}: {e.message}")
```

## Retry Strategies

### Automatic Retry with Backoff

```python
from rest_api_client import APIClient, RetryConfig

# Configure automatic retries
retry_config = RetryConfig(
    max_attempts=5,
    backoff_factor=2.0,  # Wait 1, 2, 4, 8, 16 seconds
    retry_on_status=[429, 500, 502, 503, 504]
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)

# This automatically retries on failure
response = client.get("/unstable-endpoint")
```

### Manual Retry Logic

```python
import time
from rest_api_client import APIClient, APIException

client = APIClient(base_url="https://api.example.com")

def get_with_retry(path, max_attempts=3):
    """Manually retry with custom logic."""

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.get(path)
            response.raise_for_status()
            return response

        except APIException as e:
            if attempt == max_attempts:
                print(f"Failed after {max_attempts} attempts")
                raise

            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Attempt {attempt} failed, waiting {wait_time}s...")
            time.sleep(wait_time)

# Usage
try:
    response = get_with_retry("/flaky-endpoint")
    print(f"Success: {response.data}")
except APIException as e:
    print(f"All retries failed: {e.message}")
```

## Rate Limit Handling

### Respect Rate Limits

```python
from rest_api_client import APIClient, RateLimitException
import time

client = APIClient(base_url="https://api.example.com")

def make_request_with_rate_limit_handling(path):
    """Handle rate limits gracefully."""

    while True:
        try:
            response = client.get(path)
            return response

        except RateLimitException as e:
            print(f"Rate limited. Waiting {e.retry_after} seconds...")
            time.sleep(e.retry_after)
            # Retry after waiting
```

### Track Rate Limit Headers

```python
response = client.get("/api/data")

# Check rate limit headers
remaining = response.headers.get("X-RateLimit-Remaining")
reset_time = response.headers.get("X-RateLimit-Reset")

if remaining:
    print(f"Remaining requests: {remaining}")
if reset_time:
    print(f"Reset at: {reset_time}")

# Slow down if approaching limit
if remaining and int(remaining) < 10:
    print("Approaching rate limit, slowing down...")
    time.sleep(1)
```

## Graceful Degradation

### Fallback Strategies

```python
from rest_api_client import APIClient, APIException

client = APIClient(base_url="https://api.example.com")

def get_user_data(user_id):
    """Get user data with fallback options."""

    # Try primary endpoint
    try:
        response = client.get(f"/users/{user_id}/full")
        return response.data
    except APIException:
        pass

    # Fallback to basic endpoint
    try:
        response = client.get(f"/users/{user_id}/basic")
        return response.data
    except APIException:
        pass

    # Final fallback to cached data
    return get_cached_user(user_id)

def get_cached_user(user_id):
    """Return cached user data as last resort."""
    return {
        "id": user_id,
        "name": "Cached User",
        "cached": True
    }
```

### Circuit Breaker Pattern

```python
from datetime import datetime, timedelta
from rest_api_client import APIClient, APIException

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker."""

        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self):
        return (
            self.last_failure_time and
            datetime.now() > self.last_failure_time + timedelta(seconds=self.recovery_timeout)
        )

    def _on_success(self):
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

# Usage
client = APIClient(base_url="https://api.example.com")
breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

try:
    response = breaker.call(client.get, "/unstable-endpoint")
    print(f"Success: {response.data}")
except Exception as e:
    print(f"Service unavailable: {e}")
```

## Logging Errors

### Structured Error Logging

```python
import logging
import json
from rest_api_client import APIClient, APIException

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

client = APIClient(base_url="https://api.example.com")

def log_api_error(exception, context=None):
    """Log API errors with context."""

    error_data = {
        "timestamp": datetime.now().isoformat(),
        "error_type": type(exception).__name__,
        "message": str(exception.message),
        "status_code": exception.status_code,
        "context": context or {}
    }

    if exception.response:
        error_data["response_data"] = exception.response.data
        error_data["request_url"] = exception.response.request.url

    logger.error(json.dumps(error_data, indent=2))

# Usage
try:
    response = client.get("/users/123")
except APIException as e:
    log_api_error(e, context={"user_id": 123, "operation": "fetch_user"})
    raise
```

## Error Recovery Patterns

### Batch Processing with Error Recovery

```python
from rest_api_client import APIClient, APIException

client = APIClient(base_url="https://api.example.com")

def process_batch_with_recovery(items):
    """Process batch with individual error handling."""

    results = {
        "success": [],
        "failed": []
    }

    for item in items:
        try:
            response = client.post("/process", json=item)
            results["success"].append({
                "item": item,
                "result": response.data
            })
        except APIException as e:
            results["failed"].append({
                "item": item,
                "error": e.message,
                "status": e.status_code
            })
            # Continue processing other items

    return results

# Usage
items = [{"id": 1}, {"id": 2}, {"id": 3}]
results = process_batch_with_recovery(items)

print(f"Processed: {len(results['success'])}")
print(f"Failed: {len(results['failed'])}")

for failure in results["failed"]:
    print(f"Item {failure['item']['id']} failed: {failure['error']}")
```

### Async Error Handling

```python
import asyncio
from rest_api_client import AsyncAPIClient, APIException

async def fetch_with_timeout(client, path, timeout=5):
    """Fetch with custom timeout handling."""

    try:
        response = await asyncio.wait_for(
            client.get(path),
            timeout=timeout
        )
        return response
    except asyncio.TimeoutError:
        print(f"Custom timeout reached for {path}")
        return None
    except APIException as e:
        print(f"API error for {path}: {e.message}")
        return None

async def fetch_multiple(paths):
    """Fetch multiple endpoints with error handling."""

    client = AsyncAPIClient(base_url="https://api.example.com")

    tasks = [fetch_with_timeout(client, path) for path in paths]
    results = await asyncio.gather(*tasks)

    # Filter out failed requests
    successful = [r for r in results if r is not None]
    print(f"Successfully fetched {len(successful)} out of {len(paths)}")

    return successful

# Usage
paths = ["/users/1", "/users/2", "/users/3"]
results = asyncio.run(fetch_multiple(paths))
```

## Best Practices

1. **Always catch specific exceptions first**, then general ones
2. **Log errors with context** for debugging
3. **Implement retry logic** for transient failures
4. **Use circuit breakers** for unstable services
5. **Provide meaningful error messages** to users
6. **Never expose sensitive data** in error messages
7. **Monitor error rates** and set up alerts
8. **Test error handling paths** explicitly

## Next Steps

- [Configuration Guide](./configure-client.md) - Configure retry and error behavior
- [API Reference](../reference/api.md#exceptions) - Complete exception documentation
- [Advanced Features Tutorial](../tutorials/advanced-features.md) - Learn about retry strategies
