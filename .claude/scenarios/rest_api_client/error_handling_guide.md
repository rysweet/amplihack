# REST API Client - Error Handling Guide

Comprehensive guide to handling errors and exceptions when using the REST API Client.

## Exception Hierarchy

```
APIError (base exception)
├── NetworkError (connection/network issues)
│   ├── ConnectionError (cannot connect)
│   ├── TimeoutError (request timeout)
│   └── SSLError (SSL/TLS issues)
├── HTTPError (HTTP status errors)
│   ├── ClientError (4xx status codes)
│   │   ├── BadRequestError (400)
│   │   ├── AuthenticationError (401, 403)
│   │   ├── NotFoundError (404)
│   │   ├── ConflictError (409)
│   │   ├── ValidationError (422)
│   │   └── RateLimitError (429)
│   └── ServerError (5xx status codes)
│       ├── InternalServerError (500)
│       ├── BadGatewayError (502)
│       ├── ServiceUnavailableError (503)
│       └── GatewayTimeoutError (504)
└── ValidationError (client-side validation failures)
```

## Basic Error Handling

### Simple Try-Catch

```python
from rest_api_client import APIClient, APIError

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/users/123")
    print(f"User: {response.data}")
except APIError as e:
    print(f"API request failed: {e}")
```

### Specific Exception Handling

```python
from rest_api_client import (
    APIClient,
    NetworkError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServerError
)

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/users/123")
except AuthenticationError as e:
    # Handle authentication failures (401, 403)
    print(f"Authentication failed: {e.message}")
    print(f"Status code: {e.status_code}")
    # Refresh token or re-authenticate
    refresh_authentication()
except NotFoundError as e:
    # Handle 404 responses
    print(f"User not found: {e.message}")
    return None
except RateLimitError as e:
    # Handle rate limiting (429)
    print(f"Rate limited. Retry after {e.retry_after} seconds")
    time.sleep(e.retry_after)
    # Retry the request
except NetworkError as e:
    # Handle network issues
    print(f"Network error: {e.message}")
    # Check connectivity or retry later
except ServerError as e:
    # Handle server errors (5xx)
    print(f"Server error ({e.status_code}): {e.message}")
    # Log error and notify monitoring
```

## Network Errors

### Connection Errors

```python
from rest_api_client import ConnectionError
import time

def make_request_with_retry(client, path, max_attempts=3):
    """Make request with connection retry logic."""
    for attempt in range(max_attempts):
        try:
            return client.get(path)
        except ConnectionError as e:
            if attempt == max_attempts - 1:
                # Last attempt failed
                raise
            print(f"Connection failed, retrying in {2 ** attempt} seconds...")
            time.sleep(2 ** attempt)
```

### Timeout Errors

```python
from rest_api_client import TimeoutError

def make_request_with_timeout_handling(client, path):
    """Handle timeout errors gracefully."""
    try:
        # Try with default timeout
        return client.get(path)
    except TimeoutError as e:
        print(f"Request timed out after {e.timeout} seconds")

        # Retry with longer timeout
        print("Retrying with extended timeout...")
        return client.get(path, timeout=60)
```

### SSL Errors

```python
from rest_api_client import SSLError

def handle_ssl_error(client, path):
    """Handle SSL certificate errors."""
    try:
        return client.get(path)
    except SSLError as e:
        print(f"SSL Error: {e.message}")

        # In development only - never in production!
        if is_development_environment():
            print("WARNING: Disabling SSL verification (dev only)")
            insecure_client = APIClient(
                base_url=client.base_url,
                verify_ssl=False
            )
            return insecure_client.get(path)
        else:
            raise
```

## HTTP Status Errors

### Authentication Errors (401, 403)

```python
from rest_api_client import AuthenticationError
import os

class AuthenticatedClient:
    """Client with automatic token refresh."""

    def __init__(self, base_url):
        self.base_url = base_url
        self.client = APIClient(base_url=base_url)
        self.token = None
        self.refresh_token = None

    def authenticate(self):
        """Authenticate and get tokens."""
        response = self.client.post("/auth/login", json={
            "username": os.environ["API_USERNAME"],
            "password": os.environ["API_PASSWORD"]
        })
        self.token = response.data["access_token"]
        self.refresh_token = response.data["refresh_token"]
        self.client.headers["Authorization"] = f"Bearer {self.token}"

    def refresh_authentication(self):
        """Refresh access token."""
        response = self.client.post("/auth/refresh", json={
            "refresh_token": self.refresh_token
        })
        self.token = response.data["access_token"]
        self.client.headers["Authorization"] = f"Bearer {self.token}"

    def request(self, method, path, **kwargs):
        """Make authenticated request with auto-refresh."""
        try:
            return getattr(self.client, method)(path, **kwargs)
        except AuthenticationError as e:
            if e.status_code == 401:
                # Token expired, try refresh
                print("Token expired, refreshing...")
                self.refresh_authentication()
                return getattr(self.client, method)(path, **kwargs)
            else:
                # 403 or other auth error
                raise
```

### Rate Limit Errors (429)

```python
from rest_api_client import RateLimitError
import time
from typing import Optional

class RateLimitHandler:
    """Handle rate limiting with intelligent backoff."""

    def __init__(self, client: APIClient):
        self.client = client
        self.rate_limit_info = None

    def request_with_rate_limit_handling(
        self,
        method: str,
        path: str,
        max_wait: Optional[int] = 300,
        **kwargs
    ):
        """Make request with rate limit handling."""
        while True:
            try:
                response = getattr(self.client, method)(path, **kwargs)

                # Store rate limit info from headers
                self.rate_limit_info = response.rate_limit_info
                if self.rate_limit_info:
                    print(f"Rate limit: {self.rate_limit_info.remaining}/{self.rate_limit_info.limit}")

                return response

            except RateLimitError as e:
                wait_time = e.retry_after or 60  # Default to 60s if not specified

                if max_wait and wait_time > max_wait:
                    print(f"Rate limit wait time ({wait_time}s) exceeds max ({max_wait}s)")
                    raise

                print(f"Rate limited. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
```

### Server Errors (5xx)

```python
from rest_api_client import ServerError, ServiceUnavailableError
import random
import time

class RobustClient:
    """Client with robust server error handling."""

    def __init__(self, base_url):
        self.client = APIClient(base_url=base_url)
        self.circuit_breaker = CircuitBreaker()

    def request_with_circuit_breaker(self, method, path, **kwargs):
        """Make request with circuit breaker pattern."""
        if self.circuit_breaker.is_open():
            raise Exception("Circuit breaker is open - service unavailable")

        try:
            response = getattr(self.client, method)(path, **kwargs)
            self.circuit_breaker.record_success()
            return response

        except ServerError as e:
            self.circuit_breaker.record_failure()

            if isinstance(e, ServiceUnavailableError):
                # Service temporarily unavailable
                retry_after = getattr(e, 'retry_after', None)
                if retry_after:
                    print(f"Service unavailable. Retry after {retry_after}s")
                    time.sleep(retry_after)
                    return self.request_with_circuit_breaker(method, path, **kwargs)

            # Log server error for monitoring
            log_server_error(e)
            raise

class CircuitBreaker:
    """Simple circuit breaker implementation."""

    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def is_open(self):
        """Check if circuit breaker is open."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                return False
            return True
        return False

    def record_success(self):
        """Record successful request."""
        if self.state == "half-open":
            self.state = "closed"
        self.failure_count = 0

    def record_failure(self):
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            print(f"Circuit breaker opened after {self.failure_count} failures")
```

## Validation Errors

### Request Validation

```python
from rest_api_client import ValidationError

def create_user(client, user_data):
    """Create user with validation."""
    # Client-side validation
    required_fields = ["name", "email", "username"]
    missing_fields = [f for f in required_fields if f not in user_data]

    if missing_fields:
        raise ValidationError(f"Missing required fields: {missing_fields}")

    if not is_valid_email(user_data["email"]):
        raise ValidationError(f"Invalid email: {user_data['email']}")

    try:
        return client.post("/users", json=user_data)
    except BadRequestError as e:
        # Server-side validation failed
        if e.response and e.response.data:
            errors = e.response.data.get("errors", {})
            raise ValidationError(f"Validation failed: {errors}")
        raise
```

## Error Recovery Patterns

### Pattern: Exponential Backoff with Jitter

```python
import random
import time

def exponential_backoff_with_jitter(
    client,
    method,
    path,
    max_retries=5,
    base_delay=1,
    max_delay=60,
    **kwargs
):
    """Retry with exponential backoff and jitter."""
    for attempt in range(max_retries):
        try:
            return getattr(client, method)(path, **kwargs)
        except (NetworkError, ServerError) as e:
            if attempt == max_retries - 1:
                raise

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2 ** attempt), max_delay)

            # Add jitter to prevent thundering herd
            jitter = random.uniform(0, delay * 0.1)
            actual_delay = delay + jitter

            print(f"Attempt {attempt + 1} failed. Retrying in {actual_delay:.2f}s...")
            time.sleep(actual_delay)
```

### Pattern: Fallback Strategy

```python
class FallbackClient:
    """Client with fallback to alternative endpoints."""

    def __init__(self, primary_url, fallback_urls):
        self.primary_client = APIClient(base_url=primary_url)
        self.fallback_clients = [
            APIClient(base_url=url) for url in fallback_urls
        ]

    def get_with_fallback(self, path):
        """Try primary, then fallbacks."""
        # Try primary endpoint
        try:
            return self.primary_client.get(path)
        except (NetworkError, ServerError) as e:
            print(f"Primary endpoint failed: {e}")

        # Try fallback endpoints
        for i, client in enumerate(self.fallback_clients):
            try:
                print(f"Trying fallback endpoint {i + 1}...")
                return client.get(path)
            except (NetworkError, ServerError) as e:
                print(f"Fallback {i + 1} failed: {e}")
                continue

        raise Exception("All endpoints failed")
```

### Pattern: Graceful Degradation

```python
class GracefulClient:
    """Client with graceful degradation."""

    def __init__(self, base_url):
        self.client = APIClient(base_url=base_url)
        self.cache = {}

    def get_with_cache_fallback(self, path):
        """Get data with cache fallback on error."""
        try:
            # Try to get fresh data
            response = self.client.get(path)
            # Update cache
            self.cache[path] = {
                "data": response.data,
                "timestamp": time.time()
            }
            return response.data

        except APIError as e:
            # Check if we have cached data
            if path in self.cache:
                cached = self.cache[path]
                age = time.time() - cached["timestamp"]
                print(f"Using cached data (age: {age:.0f}s) due to error: {e}")
                return cached["data"]

            # No cache available, re-raise error
            raise
```

## Error Logging and Monitoring

### Structured Error Logging

```python
import logging
import json
from datetime import datetime

class ErrorLogger:
    """Log errors with structured format."""

    def __init__(self):
        self.logger = logging.getLogger("api_errors")

    def log_error(self, error: APIError, context: dict = None):
        """Log error with context."""
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": type(error).__name__,
            "message": str(error),
            "request_method": getattr(error.request, "method", None),
            "request_url": getattr(error.request, "url", None),
            "status_code": getattr(error, "status_code", None),
            "correlation_id": getattr(error.request, "correlation_id", None),
            "context": context or {}
        }

        if isinstance(error, RateLimitError):
            error_data["retry_after"] = error.retry_after
            error_data["rate_limit_info"] = error.limit_info

        self.logger.error(json.dumps(error_data))
```

### Error Metrics

```python
from collections import defaultdict
from datetime import datetime, timedelta

class ErrorMetrics:
    """Track error metrics for monitoring."""

    def __init__(self):
        self.errors = defaultdict(list)
        self.window = timedelta(hours=1)

    def record_error(self, error: APIError):
        """Record error occurrence."""
        error_type = type(error).__name__
        self.errors[error_type].append(datetime.now())
        self._cleanup_old_errors()

    def get_error_rate(self, error_type: str = None) -> float:
        """Get error rate in last hour."""
        self._cleanup_old_errors()

        if error_type:
            return len(self.errors.get(error_type, []))
        else:
            return sum(len(errors) for errors in self.errors.values())

    def _cleanup_old_errors(self):
        """Remove errors outside time window."""
        cutoff = datetime.now() - self.window
        for error_type in list(self.errors.keys()):
            self.errors[error_type] = [
                ts for ts in self.errors[error_type] if ts > cutoff
            ]
```

## Best Practices

1. **Always handle specific exceptions** - Don't catch generic Exception
2. **Log errors with context** - Include request details and correlation IDs
3. **Implement retry logic** - But set reasonable limits
4. **Use circuit breakers** - Prevent cascading failures
5. **Cache for fallback** - Provide degraded service over no service
6. **Monitor error rates** - Set up alerts for unusual patterns
7. **Test error paths** - Error handling code needs testing too
8. **Document error behavior** - Make error handling predictable for users
