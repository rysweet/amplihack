# How to Customize Retry Logic

This guide shows you how to configure retry behavior to handle transient failures and improve reliability.

## Understanding Retry Logic

The REST API Client implements exponential backoff with configurable parameters:

- Number of retry attempts
- Initial delay between retries
- Backoff multiplier for increasing delays
- Maximum delay cap
- Which status codes to retry

## Basic Retry Configuration

Configure basic retry settings:

```python
from rest_api_client import APIClient

# Simple retry configuration
client = APIClient(
    base_url="https://api.example.com",
    max_retries=3  # Retry failed requests up to 3 times
)
```

## Advanced Retry Configuration

Use `RetryConfig` for fine-grained control:

```python
from rest_api_client import APIClient
from rest_api_client.config import RetryConfig

# Detailed retry configuration
retry_config = RetryConfig(
    max_attempts=5,                    # Total attempts (1 initial + 4 retries)
    initial_delay=1.0,                  # Start with 1 second delay
    max_delay=60.0,                     # Cap delay at 60 seconds
    exponential_base=2.0,               # Double delay each retry
    retry_on_statuses=[429, 500, 502, 503, 504],  # Status codes to retry
    retry_on_exceptions=[ConnectionError, TimeoutError]  # Exceptions to retry
)

client = APIClient(
    base_url="https://api.example.com",
    retry_config=retry_config
)
```

## Exponential Backoff

Understanding how delays increase:

```python
from rest_api_client.config import RetryConfig

# Example: Exponential backoff with base 2
retry_config = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    exponential_base=2.0,
    max_delay=30.0
)

# Delays will be:
# Attempt 1: 1 second
# Attempt 2: 2 seconds
# Attempt 3: 4 seconds
# Attempt 4: 8 seconds
# Attempt 5: 16 seconds (capped at max_delay if set lower)
```

## Custom Retry Strategies

### Fibonacci Backoff

```python
from rest_api_client.retry import RetryStrategy

class FibonacciRetryStrategy(RetryStrategy):
    """Retry with Fibonacci sequence delays."""

    def __init__(self, max_attempts=5, initial_delay=1.0):
        super().__init__(max_attempts)
        self.initial_delay = initial_delay
        self.fib_sequence = [1, 1]

    def get_delay(self, attempt):
        """Calculate Fibonacci-based delay."""
        while len(self.fib_sequence) <= attempt:
            self.fib_sequence.append(
                self.fib_sequence[-1] + self.fib_sequence[-2]
            )

        return self.initial_delay * self.fib_sequence[attempt]

# Use custom strategy
client = APIClient(
    base_url="https://api.example.com",
    retry_strategy=FibonacciRetryStrategy(max_attempts=5)
)
```

### Jittered Backoff

Add randomness to prevent thundering herd:

```python
import random
from rest_api_client.retry import RetryStrategy

class JitteredRetryStrategy(RetryStrategy):
    """Exponential backoff with jitter."""

    def __init__(self, max_attempts=3, initial_delay=1.0, jitter_range=0.3):
        super().__init__(max_attempts)
        self.initial_delay = initial_delay
        self.jitter_range = jitter_range

    def get_delay(self, attempt):
        """Calculate delay with random jitter."""
        base_delay = self.initial_delay * (2 ** attempt)
        jitter = random.uniform(-self.jitter_range, self.jitter_range)
        return base_delay * (1 + jitter)

client = APIClient(
    base_url="https://api.example.com",
    retry_strategy=JitteredRetryStrategy(jitter_range=0.3)
)
```

## Status Code Specific Retries

Retry only specific status codes:

```python
from rest_api_client.config import RetryConfig

# Retry only server errors
server_error_retry = RetryConfig(
    max_attempts=5,
    retry_on_statuses=[500, 502, 503, 504],  # Server errors only
    initial_delay=2.0
)

# Retry only rate limits
rate_limit_retry = RetryConfig(
    max_attempts=10,
    retry_on_statuses=[429],  # Only 429 Too Many Requests
    initial_delay=5.0,
    exponential_base=1.5  # Slower backoff for rate limits
)

# No retry for client errors
no_client_error_retry = RetryConfig(
    max_attempts=3,
    retry_on_statuses=[502, 503, 504],  # Exclude 400-499
    initial_delay=1.0
)
```

## Conditional Retry Logic

Implement custom retry conditions:

```python
from rest_api_client import APIClient
from rest_api_client.exceptions import APIError

class ConditionalRetryClient(APIClient):
    """Client with conditional retry logic."""

    def should_retry(self, response, attempt):
        """Determine if request should be retried."""
        # Don't retry if we've exceeded attempts
        if attempt >= self.retry_config.max_attempts:
            return False

        # Check status code
        if response.status_code in self.retry_config.retry_on_statuses:
            return True

        # Custom logic: Retry if specific error message
        try:
            data = response.json()
            if data.get('error_code') == 'TEMPORARY_FAILURE':
                return True
        except:
            pass

        # Check response headers
        if response.headers.get('X-Retry-Recommended') == 'true':
            return True

        return False

client = ConditionalRetryClient(base_url="https://api.example.com")
```

## Retry with Circuit Breaker

Combine retries with circuit breaker pattern:

```python
from datetime import datetime, timedelta

class SmartRetryClient:
    """Client with smart retry and circuit breaker."""

    def __init__(self, base_url, retry_config):
        self.client = APIClient(base_url=base_url, retry_config=retry_config)
        self.failure_counts = {}  # Track failures per endpoint
        self.circuit_states = {}  # Track circuit states

    def request_with_circuit_breaker(self, method, endpoint, **kwargs):
        """Make request with circuit breaker and retry."""
        # Check circuit state
        if self._is_circuit_open(endpoint):
            raise Exception(f"Circuit open for {endpoint}")

        try:
            # Make request with built-in retry
            response = getattr(self.client, method)(endpoint, **kwargs)
            self._reset_circuit(endpoint)
            return response

        except Exception as e:
            self._record_failure(endpoint)
            raise

    def _is_circuit_open(self, endpoint):
        """Check if circuit is open for endpoint."""
        state = self.circuit_states.get(endpoint, {})
        if state.get('open'):
            # Check if enough time has passed
            if datetime.now() > state.get('reset_time'):
                self.circuit_states[endpoint]['open'] = False
                return False
            return True
        return False

    def _record_failure(self, endpoint):
        """Record failure and possibly open circuit."""
        self.failure_counts[endpoint] = self.failure_counts.get(endpoint, 0) + 1

        # Open circuit after 5 consecutive failures
        if self.failure_counts[endpoint] >= 5:
            self.circuit_states[endpoint] = {
                'open': True,
                'reset_time': datetime.now() + timedelta(minutes=5)
            }
            print(f"Circuit opened for {endpoint}")

    def _reset_circuit(self, endpoint):
        """Reset circuit on success."""
        self.failure_counts[endpoint] = 0
        self.circuit_states[endpoint] = {'open': False}
```

## Retry Hooks and Callbacks

Add callbacks for retry events:

```python
from rest_api_client import APIClient
import logging

logger = logging.getLogger(__name__)

class RetryCallbackClient(APIClient):
    """Client with retry callbacks."""

    def on_retry(self, attempt, delay, response):
        """Called before each retry."""
        logger.warning(
            f"Retry attempt {attempt} after {delay}s. "
            f"Last status: {response.status_code if response else 'N/A'}"
        )

        # Custom logic: Send metrics
        self.send_retry_metric(attempt, response)

        # Custom logic: Update rate limiter
        if response and response.status_code == 429:
            self.adjust_rate_limit(response)

    def send_retry_metric(self, attempt, response):
        """Send retry metrics to monitoring system."""
        # Your metrics code here
        pass

    def adjust_rate_limit(self, response):
        """Adjust rate limit based on 429 response."""
        if 'X-RateLimit-Reset' in response.headers:
            reset_time = int(response.headers['X-RateLimit-Reset'])
            # Adjust internal rate limiter
            self.rate_limiter.set_reset_time(reset_time)
```

## Retry Budget

Limit total retry time or attempts:

```python
import time
from rest_api_client import APIClient
from rest_api_client.config import RetryConfig

class BudgetedRetryClient:
    """Client with retry budget."""

    def __init__(self, base_url, retry_budget_seconds=30):
        self.client = APIClient(base_url=base_url)
        self.retry_budget_seconds = retry_budget_seconds
        self.retry_time_spent = 0
        self.budget_reset_time = time.time()

    def request_with_budget(self, method, endpoint, **kwargs):
        """Make request with retry budget."""
        # Reset budget if enough time has passed
        if time.time() - self.budget_reset_time > 60:  # Reset every minute
            self.retry_time_spent = 0
            self.budget_reset_time = time.time()

        # Check if we have budget remaining
        if self.retry_time_spent >= self.retry_budget_seconds:
            raise Exception(f"Retry budget exhausted ({self.retry_budget_seconds}s)")

        start_time = time.time()
        try:
            return getattr(self.client, method)(endpoint, **kwargs)
        finally:
            # Track time spent in retries
            elapsed = time.time() - start_time
            self.retry_time_spent += elapsed

# Use budgeted client
client = BudgetedRetryClient(
    base_url="https://api.example.com",
    retry_budget_seconds=30  # Max 30 seconds of retries per minute
)
```

## Per-Endpoint Retry Configuration

Different retry strategies for different endpoints:

```python
from rest_api_client import APIClient
from rest_api_client.config import RetryConfig

class EndpointSpecificRetryClient:
    """Client with per-endpoint retry configuration."""

    def __init__(self, base_url):
        self.base_url = base_url
        self.retry_configs = {
            '/critical': RetryConfig(
                max_attempts=10,
                initial_delay=0.5,
                exponential_base=1.5
            ),
            '/search': RetryConfig(
                max_attempts=2,  # Quick fail for search
                initial_delay=0.1
            ),
            'default': RetryConfig(
                max_attempts=3,
                initial_delay=1.0
            )
        }

    def get_retry_config(self, endpoint):
        """Get retry configuration for endpoint."""
        for pattern, config in self.retry_configs.items():
            if pattern in endpoint:
                return config
        return self.retry_configs['default']

    def request(self, method, endpoint, **kwargs):
        """Make request with endpoint-specific retry."""
        retry_config = self.get_retry_config(endpoint)
        client = APIClient(
            base_url=self.base_url,
            retry_config=retry_config
        )
        return getattr(client, method)(endpoint, **kwargs)
```

## Testing Retry Logic

```python
import unittest
from unittest.mock import Mock, patch
import time

class TestRetryLogic(unittest.TestCase):
    def test_exponential_backoff(self):
        """Test exponential backoff timing."""
        retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=0.1,
            exponential_base=2.0
        )

        client = APIClient(
            base_url="https://test.com",
            retry_config=retry_config
        )

        with patch.object(client, '_send_request') as mock_send:
            # Fail twice, succeed on third attempt
            mock_send.side_effect = [
                Mock(status_code=500),
                Mock(status_code=500),
                Mock(status_code=200, json=lambda: {"success": True})
            ]

            start = time.time()
            response = client.get("/test")
            elapsed = time.time() - start

            # Should take at least 0.1 + 0.2 = 0.3 seconds
            self.assertGreaterEqual(elapsed, 0.3)
            self.assertEqual(mock_send.call_count, 3)

    def test_max_retry_attempts(self):
        """Test maximum retry attempts."""
        retry_config = RetryConfig(
            max_attempts=2,
            initial_delay=0.01
        )

        client = APIClient(
            base_url="https://test.com",
            retry_config=retry_config
        )

        with patch.object(client, '_send_request') as mock_send:
            # Always fail
            mock_send.return_value = Mock(status_code=500)

            with self.assertRaises(Exception):
                client.get("/test")

            # Should try exactly max_attempts times
            self.assertEqual(mock_send.call_count, 2)
```

## Best Practices

1. **Start with conservative settings** - 3 attempts, 1s initial delay
2. **Use exponential backoff** - Prevents overwhelming the server
3. **Add jitter** - Prevents synchronized retries
4. **Set reasonable max delay** - Cap at 60-300 seconds
5. **Don't retry client errors** - Only retry 5xx and 429
6. **Implement retry budgets** - Prevent retry storms
7. **Monitor retry metrics** - Track retry rates and success
8. **Test retry logic** - Ensure it works as expected

## Summary

Proper retry configuration is essential for:

- Handling transient failures
- Improving reliability
- Reducing manual intervention
- Maintaining good relationships with API providers

The REST API Client provides flexible retry configuration with exponential backoff, customizable strategies, and comprehensive control over retry behavior.
