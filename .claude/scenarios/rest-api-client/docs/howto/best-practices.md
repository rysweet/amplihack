# Best Practices for REST API Client

Guidelines and patterns for effective API client usage in production.

## Client Initialization

### Use Environment Variables

```python
import os
from rest_api_client import APIClient

# Good: Configuration from environment
api_client = APIClient(
    base_url=os.environ.get("API_BASE_URL"),
    headers={
        "Authorization": f"Bearer {os.environ.get('API_TOKEN')}"
    }
)

# Bad: Hardcoded values
api_client = APIClient(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer sk-1234567890"}
)
```

### Create Reusable Client Factory

```python
from rest_api_client import APIClient, RetryConfig, RateLimitConfig

class ClientFactory:
    @staticmethod
    def create_production_client():
        """Production client with all safety features."""
        return APIClient(
            base_url=os.environ.get("API_BASE_URL"),
            retry_config=RetryConfig(
                max_attempts=3,
                backoff_factor=2.0
            ),
            rate_limit_config=RateLimitConfig(
                requests_per_second=50
            ),
            timeout=30,
            verify_ssl=True
        )

    @staticmethod
    def create_test_client():
        """Test client with minimal retries."""
        return APIClient(
            base_url="https://test-api.example.com",
            retry_config=RetryConfig(max_attempts=1),
            timeout=5
        )

# Usage
client = ClientFactory.create_production_client()
```

## Error Handling

### Always Handle Specific Exceptions

```python
from rest_api_client import (
    APIClient,
    ConnectionException,
    RateLimitException,
    ValidationException
)

# Good: Specific exception handling
def fetch_user(user_id):
    try:
        response = client.get(f"/users/{user_id}")
        return response.data
    except ConnectionException:
        # Handle network issues
        return get_cached_user(user_id)
    except RateLimitException as e:
        # Handle rate limiting
        logger.warning(f"Rate limited, retry after {e.retry_after}s")
        raise
    except ValidationException as e:
        # Handle validation errors
        logger.error(f"Invalid request: {e.message}")
        return None

# Bad: Generic exception handling
def fetch_user_bad(user_id):
    try:
        response = client.get(f"/users/{user_id}")
        return response.data
    except Exception:
        return None  # Loses error context
```

### Implement Circuit Breaker for Critical Services

```python
from datetime import datetime, timedelta

class APIClientWithCircuitBreaker:
    def __init__(self, client, failure_threshold=5, recovery_timeout=60):
        self.client = client
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure = None
        self.is_open = False

    def get(self, *args, **kwargs):
        if self._is_circuit_open():
            raise Exception("Service temporarily unavailable")

        try:
            response = self.client.get(*args, **kwargs)
            self._on_success()
            return response
        except Exception as e:
            self._on_failure()
            raise

    def _is_circuit_open(self):
        if not self.is_open:
            return False

        # Check if recovery period has passed
        if datetime.now() > self.last_failure + timedelta(seconds=self.recovery_timeout):
            self.is_open = False
            self.failure_count = 0

        return self.is_open

    def _on_success(self):
        self.failure_count = 0
        self.is_open = False

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
```

## Performance Optimization

### Batch Requests When Possible

```python
# Good: Single request for multiple items
def get_users_batch(user_ids):
    response = client.get("/users", params={"ids": ",".join(map(str, user_ids))})
    return response.data

# Bad: Multiple individual requests
def get_users_individual(user_ids):
    users = []
    for user_id in user_ids:
        response = client.get(f"/users/{user_id}")
        users.append(response.data)
    return users
```

### Use Pagination for Large Data Sets

```python
def fetch_all_users():
    """Fetch all users using pagination."""
    all_users = []
    page = 1
    per_page = 100

    while True:
        response = client.get("/users", params={
            "page": page,
            "per_page": per_page
        })

        users = response.data
        if not users:
            break

        all_users.extend(users)
        page += 1

        # Respect rate limits between pages
        time.sleep(0.1)

    return all_users
```

### Implement Caching for Expensive Operations

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedAPIClient:
    def __init__(self, client, cache_ttl_seconds=300):
        self.client = client
        self.cache_ttl = cache_ttl_seconds
        self.cache = {}

    def get_with_cache(self, path, **kwargs):
        cache_key = f"{path}:{kwargs}"

        # Check cache
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if datetime.now() < entry["expires"]:
                return entry["data"]

        # Fetch from API
        response = self.client.get(path, **kwargs)

        # Update cache
        self.cache[cache_key] = {
            "data": response,
            "expires": datetime.now() + timedelta(seconds=self.cache_ttl)
        }

        return response
```

## Security Best Practices

### Never Log Sensitive Data

```python
import logging

# Good: Sanitize sensitive information
def log_request(method, url, headers):
    safe_headers = {
        k: "[REDACTED]" if k.lower() in ["authorization", "x-api-key"] else v
        for k, v in headers.items()
    }
    logging.info(f"{method} {url} Headers: {safe_headers}")

# Bad: Logging raw headers
def log_request_bad(method, url, headers):
    logging.info(f"{method} {url} Headers: {headers}")  # Leaks secrets
```

### Validate Input Before Sending

```python
def create_user(name, email):
    # Good: Validate before API call
    if not name or len(name) > 100:
        raise ValueError("Invalid name")

    if not email or "@" not in email:
        raise ValueError("Invalid email")

    response = client.post("/users", json={
        "name": name,
        "email": email
    })
    return response.data
```

### Use HTTPS and Verify SSL

```python
# Good: Always verify SSL in production
production_client = APIClient(
    base_url="https://api.example.com",
    verify_ssl=True
)

# Bad: Disabled SSL verification
insecure_client = APIClient(
    base_url="https://api.example.com",
    verify_ssl=False  # Never do this in production!
)
```

## Testing Strategies

### Mock External APIs in Tests

```python
import unittest
from unittest.mock import Mock, patch

class TestUserService(unittest.TestCase):
    @patch("rest_api_client.APIClient")
    def test_get_user(self, mock_client_class):
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = {"id": 123, "name": "Test User"}
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Test
        service = UserService()
        user = service.get_user(123)

        # Verify
        self.assertEqual(user["name"], "Test User")
        mock_client.get.assert_called_once_with("/users/123")
```

### Test Error Scenarios

```python
def test_handles_rate_limit():
    """Test that rate limiting is handled correctly."""
    mock_client = Mock()
    mock_client.get.side_effect = RateLimitException(
        "Rate limited",
        retry_after=60
    )

    service = ServiceWithRetry(mock_client)
    with self.assertRaises(RateLimitException) as context:
        service.fetch_data()

    self.assertEqual(context.exception.retry_after, 60)
```

## Monitoring and Observability

### Add Request Metrics

```python
import time
from dataclasses import dataclass

@dataclass
class RequestMetrics:
    total_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0

    @property
    def average_duration(self):
        if self.total_requests == 0:
            return 0
        return self.total_duration / self.total_requests

    @property
    def success_rate(self):
        if self.total_requests == 0:
            return 1.0
        return 1 - (self.failed_requests / self.total_requests)

class MetricsClient:
    def __init__(self, client):
        self.client = client
        self.metrics = RequestMetrics()

    def get(self, *args, **kwargs):
        start_time = time.time()

        try:
            response = self.client.get(*args, **kwargs)
            self.metrics.total_requests += 1
            return response
        except Exception as e:
            self.metrics.failed_requests += 1
            raise
        finally:
            duration = time.time() - start_time
            self.metrics.total_duration += duration
```

### Log Slow Requests

```python
def log_slow_requests(threshold_seconds=2.0):
    """Decorator to log slow API calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if duration > threshold_seconds:
                    logging.warning(
                        f"Slow API call: {func.__name__} took {duration:.2f}s"
                    )
        return wrapper
    return decorator

# Usage
@log_slow_requests(threshold_seconds=1.0)
def fetch_large_dataset():
    return client.get("/large-dataset")
```

## Resource Management

### Use Context Managers

```python
class APISession:
    """Context manager for API sessions."""

    def __init__(self, base_url, **kwargs):
        self.base_url = base_url
        self.kwargs = kwargs
        self.client = None

    def __enter__(self):
        self.client = APIClient(self.base_url, **self.kwargs)
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup if needed
        if self.client:
            # Log session stats, close connections, etc.
            pass

# Usage
with APISession("https://api.example.com") as client:
    response = client.get("/users")
    # Client is automatically cleaned up
```

### Handle Connection Pooling

```python
class PooledAPIClient:
    """Client with connection pooling."""

    def __init__(self, max_connections=10):
        self.pool = []
        self.max_connections = max_connections

    def get_connection(self):
        if self.pool:
            return self.pool.pop()
        return self._create_connection()

    def return_connection(self, conn):
        if len(self.pool) < self.max_connections:
            self.pool.append(conn)
        else:
            conn.close()
```

## Common Pitfalls to Avoid

### Don't Ignore Rate Limits

```python
# Bad: Ignoring rate limits
for i in range(1000):
    client.get(f"/item/{i}")  # Will get rate limited

# Good: Respect rate limits
for i in range(1000):
    response = client.get(f"/item/{i}")
    # Check rate limit headers
    if int(response.headers.get("X-RateLimit-Remaining", 100)) < 10:
        time.sleep(1)
```

### Don't Retry Indefinitely

```python
# Bad: Infinite retry
while True:
    try:
        response = client.get("/endpoint")
        break
    except:
        continue  # Infinite loop!

# Good: Limited retries with backoff
for attempt in range(3):
    try:
        response = client.get("/endpoint")
        break
    except APIException:
        if attempt < 2:
            time.sleep(2 ** attempt)
        else:
            raise
```

### Don't Trust User Input

```python
# Bad: Direct user input in API calls
def search_users(user_query):
    return client.get(f"/search?q={user_query}")  # Injection risk

# Good: Sanitize and validate
def search_users_safe(user_query):
    # Validate and sanitize
    if not user_query or len(user_query) > 100:
        raise ValueError("Invalid search query")

    # Remove special characters
    safe_query = "".join(c for c in user_query if c.isalnum() or c.isspace())

    return client.get("/search", params={"q": safe_query})
```

## Summary

Following these best practices ensures:

1. **Reliability** through proper error handling and retries
2. **Performance** through caching and batching
3. **Security** through validation and sanitization
4. **Maintainability** through clear patterns and testing
5. **Observability** through metrics and logging

Remember: Good API client usage is about being a respectful consumer of the API while building robust applications.
