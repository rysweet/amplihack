# Best Practices

Recommended patterns and practices for using the REST API Client effectively.

## Client Initialization

### DO: Reuse Client Instances

Client instances are thread-safe and should be reused:

```python
# GOOD - Single client instance
class MyService:
    def __init__(self):
        self.client = APIClient(base_url="https://api.example.com")

    def get_user(self, user_id):
        return self.client.get(f"/users/{user_id}")

    def get_posts(self, user_id):
        return self.client.get(f"/users/{user_id}/posts")
```

```python
# BAD - Creating new clients repeatedly
class MyService:
    def get_user(self, user_id):
        client = APIClient(base_url="https://api.example.com")  # Wasteful
        return client.get(f"/users/{user_id}")

    def get_posts(self, user_id):
        client = APIClient(base_url="https://api.example.com")  # Wasteful
        return client.get(f"/users/{user_id}/posts")
```

### DO: Use Configuration Objects

Use configuration objects for complex setups:

```python
# GOOD - Clear, maintainable configuration
from rest_api_client.config import APIConfig, RetryConfig

api_config = APIConfig(
    base_url="https://api.example.com",
    timeout=60,
    rate_limit_calls=100,
    rate_limit_period=60
)

retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    exponential_base=2.0
)

client = APIClient(config=api_config, retry_config=retry_config)
```

```python
# BAD - Unclear, hard to maintain
client = APIClient(
    "https://api.example.com", None, None, {}, 60, 5, 100, 60, True
)
```

### DO: Use Context Managers

Ensure proper cleanup with context managers:

```python
# GOOD - Automatic cleanup
with APIClient(base_url="https://api.example.com") as client:
    users = client.get("/users")
    # Client automatically cleaned up
```

```python
# Also GOOD - Explicit lifecycle management
client = APIClient(base_url="https://api.example.com")
try:
    users = client.get("/users")
finally:
    client.close()
```

## Error Handling

### DO: Catch Specific Exceptions

Always catch the most specific exception possible:

```python
# GOOD - Specific error handling
from rest_api_client.exceptions import (
    RateLimitError,
    AuthenticationError,
    ValidationError,
    NetworkError
)

try:
    response = client.post("/users", json=user_data)
except ValidationError as e:
    # Handle validation errors specifically
    for field, error in e.errors.items():
        print(f"Field {field}: {error}")
    return None

except RateLimitError as e:
    # Handle rate limiting specifically
    print(f"Rate limited. Retry after {e.retry_after} seconds")
    time.sleep(e.retry_after)
    return retry_request()

except NetworkError as e:
    # Handle network issues
    print(f"Network error: {e}")
    return get_cached_data()
```

```python
# BAD - Too generic
try:
    response = client.post("/users", json=user_data)
except Exception as e:  # Too broad!
    print(f"Something went wrong: {e}")
```

### DO: Implement Retry Strategies

Use appropriate retry strategies for different scenarios:

```python
# GOOD - Different strategies for different endpoints
from rest_api_client.config import RetryConfig

# Critical endpoints - retry more
critical_retry = RetryConfig(
    max_attempts=10,
    initial_delay=0.5,
    retry_on_statuses=[429, 500, 502, 503, 504]
)

# Non-critical endpoints - fail fast
non_critical_retry = RetryConfig(
    max_attempts=2,
    initial_delay=0.1,
    retry_on_statuses=[503]  # Only service unavailable
)

# Use appropriate config
if is_critical_operation:
    client.retry_config = critical_retry
else:
    client.retry_config = non_critical_retry
```

### DO: Log Errors with Context

Include relevant context in error logs:

```python
# GOOD - Detailed error logging
import logging

logger = logging.getLogger(__name__)

def make_api_call(endpoint, data):
    try:
        return client.post(endpoint, json=data)
    except APIError as e:
        logger.error(
            "API call failed",
            extra={
                'endpoint': endpoint,
                'status_code': e.status_code,
                'error_message': str(e),
                'request_data': data,
                'timestamp': datetime.now().isoformat()
            }
        )
        raise
```

## Rate Limiting

### DO: Set Conservative Limits

Always set limits below the actual API limits:

```python
# GOOD - Conservative rate limiting
# If API allows 100 requests/minute
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=80,  # 20% buffer
    rate_limit_period=60
)
```

### DO: Handle Rate Limits Gracefully

Implement proper rate limit handling:

```python
# GOOD - Graceful degradation
class RateLimitAwareClient:
    def __init__(self):
        self.client = APIClient(base_url="https://api.example.com")
        self.cache = {}

    def get_with_cache(self, endpoint):
        try:
            response = self.client.get(endpoint)
            # Update cache on success
            self.cache[endpoint] = response.data
            return response.data

        except RateLimitError:
            # Fall back to cache when rate limited
            if endpoint in self.cache:
                logger.warning(f"Using cached data for {endpoint}")
                return self.cache[endpoint]
            raise
```

### DO: Monitor Rate Limit Usage

Track your rate limit consumption:

```python
# GOOD - Rate limit monitoring
class MonitoredClient(APIClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.request_count = 0
        self.rate_limit_hits = 0

    def make_request(self, method, endpoint, **kwargs):
        self.request_count += 1
        try:
            return super().make_request(method, endpoint, **kwargs)
        except RateLimitError as e:
            self.rate_limit_hits += 1
            if self.rate_limit_hits > 10:
                logger.warning(
                    f"High rate limit hits: {self.rate_limit_hits}/{self.request_count}"
                )
            raise
```

## Authentication

### DO: Implement Token Refresh

Automatically refresh authentication tokens:

```python
# GOOD - Automatic token refresh
class AuthClient:
    def __init__(self, base_url, auth_endpoint):
        self.base_url = base_url
        self.auth_endpoint = auth_endpoint
        self.client = None
        self.token_expiry = None
        self.refresh_token()

    def refresh_token(self):
        """Refresh authentication token."""
        auth_client = APIClient(base_url=self.base_url)
        response = auth_client.post(self.auth_endpoint, json={
            "client_id": os.environ["CLIENT_ID"],
            "client_secret": os.environ["CLIENT_SECRET"]
        })

        token = response.data["access_token"]
        self.token_expiry = datetime.now() + timedelta(
            seconds=response.data["expires_in"]
        )

        self.client = APIClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {token}"}
        )

    def request(self, method, endpoint, **kwargs):
        """Make request with automatic token refresh."""
        # Check if token needs refresh
        if datetime.now() >= self.token_expiry - timedelta(minutes=5):
            self.refresh_token()

        try:
            return getattr(self.client, method)(endpoint, **kwargs)
        except AuthenticationError:
            # Token might have been revoked
            self.refresh_token()
            return getattr(self.client, method)(endpoint, **kwargs)
```

### DO: Secure Credential Storage

Never hardcode credentials:

```python
# GOOD - Environment variables
import os

client = APIClient(
    base_url="https://api.example.com",
    headers={
        "Authorization": f"Bearer {os.environ['API_TOKEN']}"
    }
)
```

```python
# GOOD - Configuration file (not in version control)
import json

with open("config.json") as f:
    config = json.load(f)

client = APIClient(
    base_url=config["api_url"],
    headers={
        "Authorization": f"Bearer {config['token']}"
    }
)
```

```python
# BAD - Hardcoded credentials
client = APIClient(
    base_url="https://api.example.com",
    headers={
        "Authorization": "Bearer abc123xyz"  # NEVER DO THIS!
    }
)
```

## Performance

### DO: Use Connection Pooling

Reuse connections for better performance:

```python
# GOOD - Client reuse enables connection pooling
class APIService:
    def __init__(self):
        # Single client instance = connection pooling
        self.client = APIClient(base_url="https://api.example.com")

    def batch_requests(self, ids):
        # Reuses connections
        return [self.client.get(f"/items/{id}") for id in ids]
```

### DO: Use Async for Concurrent Requests

Use async client for parallel requests:

```python
# GOOD - Concurrent async requests
import asyncio
from rest_api_client import AsyncAPIClient

async def fetch_all_users(user_ids):
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        tasks = [
            client.get(f"/users/{user_id}")
            for user_id in user_ids
        ]
        return await asyncio.gather(*tasks)

# Fetch 100 users concurrently
users = asyncio.run(fetch_all_users(range(1, 101)))
```

### DO: Implement Caching

Cache responses when appropriate:

```python
# GOOD - LRU cache for repeated requests
from functools import lru_cache
import hashlib

class CachedClient:
    def __init__(self):
        self.client = APIClient(base_url="https://api.example.com")

    @lru_cache(maxsize=1000)
    def get_cached(self, endpoint):
        """Cache GET requests."""
        response = self.client.get(endpoint)
        return response.data

    def post(self, endpoint, data):
        """POST requests clear relevant cache."""
        response = self.client.post(endpoint, json=data)
        # Clear cache for related GET endpoints
        self.get_cached.cache_clear()
        return response
```

## Testing

### DO: Mock External APIs

Always mock API calls in tests:

```python
# GOOD - Mocked API tests
import unittest
from unittest.mock import patch, Mock

class TestUserService(unittest.TestCase):
    @patch('rest_api_client.client.requests.get')
    def test_get_user(self, mock_get):
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Alice"}
        mock_get.return_value = mock_response

        # Test
        client = APIClient(base_url="https://test.com")
        user = client.get("/users/1")

        # Verify
        self.assertEqual(user.data["name"], "Alice")
        mock_get.assert_called_once()
```

### DO: Test Error Paths

Test error handling thoroughly:

```python
# GOOD - Test error scenarios
class TestErrorHandling(unittest.TestCase):
    def test_handles_rate_limit(self):
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 429
            mock_get.return_value.headers = {'Retry-After': '60'}

            client = APIClient(base_url="https://test.com")

            with self.assertRaises(RateLimitError) as ctx:
                client.get("/test")

            self.assertEqual(ctx.exception.retry_after, 60)

    def test_handles_network_error(self):
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError("Network down")

            client = APIClient(base_url="https://test.com")

            with self.assertRaises(NetworkError):
                client.get("/test")
```

### DO: Use Test Fixtures

Create reusable test fixtures:

```python
# GOOD - Reusable fixtures
import pytest

@pytest.fixture
def api_client():
    """Provide configured API client."""
    return APIClient(
        base_url="https://test.example.com",
        timeout=5,
        max_retries=1
    )

@pytest.fixture
def mock_success_response():
    """Provide successful response mock."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"status": "success"}
    return response

def test_successful_request(api_client, mock_success_response):
    with patch('requests.get', return_value=mock_success_response):
        result = api_client.get("/test")
        assert result.data["status"] == "success"
```

## Monitoring

### DO: Add Metrics

Track key metrics:

```python
# GOOD - Comprehensive metrics
from dataclasses import dataclass
from collections import defaultdict
import time

@dataclass
class Metrics:
    request_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0
    status_codes: dict = None

    def __post_init__(self):
        if self.status_codes is None:
            self.status_codes = defaultdict(int)

class MetricsClient(APIClient):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metrics = Metrics()

    def make_request(self, method, endpoint, **kwargs):
        start = time.time()
        try:
            response = super().make_request(method, endpoint, **kwargs)
            self.metrics.status_codes[response.status_code] += 1
            return response
        except Exception as e:
            self.metrics.error_count += 1
            raise
        finally:
            self.metrics.request_count += 1
            self.metrics.total_latency += time.time() - start

    def get_metrics_summary(self):
        return {
            'total_requests': self.metrics.request_count,
            'error_rate': self.metrics.error_count / max(1, self.metrics.request_count),
            'avg_latency': self.metrics.total_latency / max(1, self.metrics.request_count),
            'status_codes': dict(self.metrics.status_codes)
        }
```

### DO: Add Health Checks

Implement health check endpoints:

```python
# GOOD - Health check implementation
class HealthCheckClient(APIClient):
    def health_check(self, deep=False):
        """Check API health."""
        try:
            # Basic connectivity check
            response = self.get("/health", timeout=5)

            if not deep:
                return response.status_code == 200

            # Deep health check
            checks = {
                'api': response.status_code == 200,
                'auth': self.check_auth(),
                'rate_limit': self.check_rate_limit()
            }

            return all(checks.values()), checks

        except Exception as e:
            return False, {'error': str(e)}

    def check_auth(self):
        """Verify authentication works."""
        try:
            self.get("/auth/verify")
            return True
        except AuthenticationError:
            return False

    def check_rate_limit(self):
        """Check if rate limited."""
        return self.rate_limiter.available_tokens > 0
```

## Security

### DO: Validate Input

Always validate input before sending:

```python
# GOOD - Input validation
from dataclasses import dataclass
from typing import Optional
import re

@dataclass
class UserInput:
    email: str
    name: str
    age: Optional[int] = None

    def validate(self):
        errors = {}

        # Validate email
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', self.email):
            errors['email'] = 'Invalid email format'

        # Validate name
        if not self.name or len(self.name) < 2:
            errors['name'] = 'Name must be at least 2 characters'

        # Validate age
        if self.age is not None and (self.age < 0 or self.age > 150):
            errors['age'] = 'Age must be between 0 and 150'

        if errors:
            raise ValidationError("Input validation failed", errors=errors)

        return True

# Usage
def create_user(email, name, age=None):
    user_input = UserInput(email=email, name=name, age=age)
    user_input.validate()  # Validate before sending

    return client.post("/users", json={
        'email': user_input.email,
        'name': user_input.name,
        'age': user_input.age
    })
```

### DO: Sanitize Logs

Never log sensitive data:

```python
# GOOD - Sanitized logging
import logging

def sanitize_headers(headers):
    """Remove sensitive headers from logs."""
    sensitive_headers = ['Authorization', 'X-API-Key', 'Cookie']
    sanitized = headers.copy()

    for header in sensitive_headers:
        if header in sanitized:
            sanitized[header] = '***REDACTED***'

    return sanitized

class SecureLoggingClient(APIClient):
    def make_request(self, method, endpoint, headers=None, **kwargs):
        # Log sanitized version
        logger.info(
            f"Request: {method} {endpoint}",
            extra={
                'headers': sanitize_headers(headers or {})
            }
        )

        return super().make_request(method, endpoint, headers=headers, **kwargs)
```

## Summary

Key best practices:

1. **Reuse clients** for connection pooling
2. **Handle errors specifically** with proper exception catching
3. **Set conservative rate limits** with monitoring
4. **Implement retry strategies** appropriate to endpoints
5. **Secure credentials** using environment variables
6. **Test thoroughly** including error paths
7. **Monitor everything** with metrics and health checks
8. **Validate input** and sanitize logs

Following these practices ensures your API integration is robust, secure, and maintainable.
