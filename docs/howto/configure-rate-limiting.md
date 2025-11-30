# How to Configure Rate Limiting

This guide shows you how to configure and use rate limiting in the REST API Client to respect API limits and avoid getting blocked.

## Understanding Rate Limiting

Rate limiting controls how many requests you can make to an API within a specific time period. The REST API Client uses a token bucket algorithm to automatically throttle requests.

## Basic Rate Limiting

Configure rate limits when creating your client:

```python
from rest_api_client import APIClient

# Allow 100 requests per minute
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=100,
    rate_limit_period=60  # seconds
)
```

## Configuration Options

### Using APIConfig

```python
from rest_api_client.config import APIConfig

config = APIConfig(
    base_url="https://api.example.com",
    rate_limit_calls=1000,    # Maximum calls
    rate_limit_period=3600,    # Per hour (3600 seconds)
    rate_limit_burst=10        # Allow burst of 10 requests
)

client = APIClient(config=config)
```

### Common Rate Limit Patterns

```python
# GitHub API: 60 requests per hour for unauthenticated
github_client = APIClient(
    base_url="https://api.github.com",
    rate_limit_calls=60,
    rate_limit_period=3600
)

# Twitter API: 15 requests per 15 minutes
twitter_client = APIClient(
    base_url="https://api.twitter.com",
    rate_limit_calls=15,
    rate_limit_period=900
)

# Stripe API: 100 requests per second
stripe_client = APIClient(
    base_url="https://api.stripe.com",
    rate_limit_calls=100,
    rate_limit_period=1
)
```

## Handling Rate Limit Responses

The client automatically handles 429 (Too Many Requests) responses:

```python
from rest_api_client.exceptions import RateLimitError

try:
    response = client.get("/resource")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
    print(f"Limit: {e.limit}")
    print(f"Remaining: {e.remaining}")
    print(f"Reset time: {e.reset_time}")
```

## Dynamic Rate Limiting

Adjust rate limits based on response headers:

```python
class AdaptiveClient(APIClient):
    """Client that adapts to rate limit headers."""

    def handle_response(self, response):
        """Update rate limits from response headers."""
        # Check for rate limit headers
        if 'X-RateLimit-Limit' in response.headers:
            limit = int(response.headers['X-RateLimit-Limit'])
            period = int(response.headers.get('X-RateLimit-Period', 3600))

            # Update rate limiter
            self.rate_limiter.update_limits(
                calls=limit,
                period=period
            )

        return super().handle_response(response)
```

## Per-Endpoint Rate Limiting

Different endpoints may have different limits:

```python
from rest_api_client import APIClient
from rest_api_client.rate_limiter import RateLimiter

class MultiLimitClient:
    """Client with per-endpoint rate limiting."""

    def __init__(self, base_url):
        self.base_url = base_url
        self.limiters = {
            'search': RateLimiter(calls=10, period=60),
            'users': RateLimiter(calls=100, period=60),
            'default': RateLimiter(calls=1000, period=3600)
        }

    def get(self, endpoint, **kwargs):
        """Make a GET request with appropriate rate limiting."""
        # Determine which limiter to use
        if '/search' in endpoint:
            limiter = self.limiters['search']
        elif '/users' in endpoint:
            limiter = self.limiters['users']
        else:
            limiter = self.limiters['default']

        # Wait if rate limited
        limiter.acquire()

        # Make the request
        client = APIClient(base_url=self.base_url)
        return client.get(endpoint, **kwargs)
```

## Monitoring Rate Limit Usage

Track your rate limit consumption:

```python
from rest_api_client import APIClient
import time

class MonitoredClient(APIClient):
    """Client that tracks rate limit usage."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.request_count = 0
        self.start_time = time.time()

    def _make_request(self, method, endpoint, **kwargs):
        """Track requests and provide statistics."""
        response = super()._make_request(method, endpoint, **kwargs)
        self.request_count += 1

        # Calculate statistics
        elapsed = time.time() - self.start_time
        rate = self.request_count / elapsed if elapsed > 0 else 0

        print(f"Requests: {self.request_count}")
        print(f"Rate: {rate:.2f} req/s")
        print(f"Remaining capacity: {self.rate_limiter.tokens}")

        return response
```

## Batch Processing with Rate Limiting

Process large batches while respecting rate limits:

```python
import asyncio
from rest_api_client import AsyncAPIClient

async def process_batch_with_rate_limit(items, rate_limit=10, period=1):
    """Process items in batches with rate limiting."""
    client = AsyncAPIClient(
        base_url="https://api.example.com",
        rate_limit_calls=rate_limit,
        rate_limit_period=period
    )

    results = []
    for item in items:
        # The client automatically handles rate limiting
        result = await client.post("/process", json=item)
        results.append(result.data)
        print(f"Processed item {item['id']}")

    return results

# Process 100 items at 10 requests per second
items = [{"id": i, "data": f"item_{i}"} for i in range(100)]
results = asyncio.run(process_batch_with_rate_limit(items))
```

## Best Practices

### 1. Set Conservative Limits

Always set limits slightly below the API's actual limits:

```python
# If API allows 100/minute, use 90 to be safe
client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=90,  # 10% buffer
    rate_limit_period=60
)
```

### 2. Use Exponential Backoff

Combine rate limiting with retry logic:

```python
from rest_api_client.config import RetryConfig

retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    exponential_base=2.0,  # Double delay each retry
    retry_on_statuses=[429]  # Retry on rate limit
)

client = APIClient(
    base_url="https://api.example.com",
    rate_limit_calls=100,
    rate_limit_period=60,
    retry_config=retry_config
)
```

### 3. Log Rate Limit Events

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggingClient(APIClient):
    """Client that logs rate limit events."""

    def handle_rate_limit(self, wait_time):
        """Log when rate limited."""
        logger.warning(f"Rate limited. Waiting {wait_time:.2f} seconds")
        super().handle_rate_limit(wait_time)
```

### 4. Implement Circuit Breakers

Temporarily disable requests when consistently rate limited:

```python
from datetime import datetime, timedelta

class CircuitBreakerClient(APIClient):
    """Client with circuit breaker for rate limits."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.circuit_open = False
        self.circuit_open_until = None
        self.consecutive_rate_limits = 0

    def make_request(self, method, endpoint, **kwargs):
        """Check circuit breaker before making request."""
        # Check if circuit is open
        if self.circuit_open:
            if datetime.now() < self.circuit_open_until:
                raise Exception("Circuit breaker is open")
            else:
                self.circuit_open = False
                self.consecutive_rate_limits = 0

        try:
            return super().make_request(method, endpoint, **kwargs)
        except RateLimitError as e:
            self.consecutive_rate_limits += 1

            # Open circuit after 3 consecutive rate limits
            if self.consecutive_rate_limits >= 3:
                self.circuit_open = True
                self.circuit_open_until = datetime.now() + timedelta(minutes=5)
                logger.error("Circuit breaker opened for 5 minutes")

            raise
```

## Testing Rate Limiting

Test your rate limiting configuration:

```python
import time
import unittest
from unittest.mock import Mock, patch
from rest_api_client import APIClient

class TestRateLimiting(unittest.TestCase):
    def test_rate_limit_enforcement(self):
        """Test that rate limiting is enforced."""
        client = APIClient(
            base_url="https://test.com",
            rate_limit_calls=5,
            rate_limit_period=1  # 5 calls per second
        )

        start = time.time()

        # Make 10 requests
        with patch.object(client, '_send_request') as mock_send:
            mock_send.return_value = Mock(status_code=200, json=lambda: {})

            for i in range(10):
                client.get(f"/test/{i}")

        elapsed = time.time() - start

        # Should take at least 1 second (second batch waits)
        self.assertGreaterEqual(elapsed, 1.0)
```

## Summary

Rate limiting is essential for:

- Respecting API provider limits
- Avoiding account suspension
- Ensuring fair resource usage
- Maintaining application stability

The REST API Client makes rate limiting simple with automatic throttling, configurable limits, and proper error handling.
