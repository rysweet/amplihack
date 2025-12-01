# How to Handle API Errors

Learn effective strategies for handling errors when using the amplihack API Client.

## Understanding the Error Hierarchy

The API Client provides specific exception types for different failure scenarios:

```
APIError (base exception)
├── RateLimitError      # Too many requests (429)
├── ValidationError     # Bad request data (400)
├── AuthenticationError # Invalid credentials (401)
├── ForbiddenError     # Access denied (403)
├── NotFoundError      # Resource not found (404)
├── TimeoutError       # Request timed out
├── ConnectionError    # Network issues
└── ServerError        # Server problems (5xx)
```

## Basic Error Handling

### Catching All API Errors

Handle any API-related error with the base exception:

```python
from amplihack.utils.api_client import APIClient, APIError

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/users/123")
    user = response.json()
except APIError as e:
    print(f"API request failed: {e.message}")
    print(f"Status code: {e.status_code}")
```

### Handling Specific Error Types

Catch and handle specific error scenarios:

```python
from amplihack.utils.api_client import (
    APIClient,
    NotFoundError,
    ValidationError,
    RateLimitError,
    ServerError
)

client = APIClient(base_url="https://api.example.com")

try:
    response = client.post("/users", json={"name": "Alice"})
except NotFoundError:
    print("User not found - may have been deleted")
except ValidationError as e:
    print(f"Invalid data: {e.validation_errors}")
except RateLimitError as e:
    print(f"Rate limited - retry after {e.retry_after} seconds")
except ServerError:
    print("Server error - please try again later")
```

## Rate Limit Handling

### Automatic Retry with Backoff

The client automatically retries rate-limited requests:

```python
# Client will automatically retry with exponential backoff
client = APIClient(
    base_url="https://api.example.com",
    max_retries=5,  # Will retry up to 5 times
    backoff_factor=2.0  # Exponential backoff multiplier
)

# This will retry automatically if rate limited
response = client.get("/popular-endpoint")
```

### Manual Rate Limit Handling

For custom rate limit logic:

```python
import time
from amplihack.utils.api_client import APIClient, RateLimitError

client = APIClient(base_url="https://api.example.com", max_retries=0)

def fetch_with_custom_retry(endpoint: str, max_attempts: int = 3):
    """Fetch with custom rate limit handling."""
    for attempt in range(max_attempts):
        try:
            return client.get(endpoint)
        except RateLimitError as e:
            if attempt == max_attempts - 1:
                raise  # Re-raise on final attempt

            print(f"Rate limited. Waiting {e.retry_after} seconds...")
            print(f"Limit: {e.rate_limit}, Remaining: {e.rate_limit_remaining}")
            time.sleep(e.retry_after)

    raise Exception("Max attempts reached")
```

## Validation Error Handling

### Processing Field-Level Errors

Handle validation errors with detailed field information:

```python
from amplihack.utils.api_client import APIClient, ValidationError

client = APIClient(base_url="https://api.example.com")

def create_user(user_data: dict):
    """Create user with validation error handling."""
    try:
        response = client.post("/users", json=user_data)
        return response.json()
    except ValidationError as e:
        print("Validation failed:")
        for field, errors in e.validation_errors.items():
            print(f"  {field}: {', '.join(errors)}")

        # Example output:
        # Validation failed:
        #   email: Invalid format, Already exists
        #   password: Too short, Must contain special character

        return None
```

### Input Validation Strategy

Validate input before sending requests:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class UserInput:
    name: str
    email: str
    age: Optional[int] = None

    def validate(self) -> list:
        """Validate input before API call."""
        errors = []

        if not self.name or len(self.name) < 2:
            errors.append("Name must be at least 2 characters")

        if "@" not in self.email:
            errors.append("Invalid email format")

        if self.age is not None and (self.age < 0 or self.age > 150):
            errors.append("Age must be between 0 and 150")

        return errors

def create_user_safe(client: APIClient, user_input: UserInput):
    """Create user with client-side validation."""
    # Validate locally first
    errors = user_input.validate()
    if errors:
        print(f"Validation errors: {errors}")
        return None

    # Then make API call
    try:
        response = client.post("/users", json=user_input.__dict__)
        return response.json()
    except ValidationError as e:
        # Server-side validation caught additional issues
        print(f"Server validation failed: {e.validation_errors}")
        return None
```

## Connection and Timeout Errors

### Handling Network Issues

Deal with connection problems gracefully:

```python
from amplihack.utils.api_client import (
    APIClient,
    ConnectionError,
    TimeoutError
)

client = APIClient(
    base_url="https://api.example.com",
    timeout=10  # 10 second timeout
)

def fetch_with_fallback(endpoint: str, fallback_value=None):
    """Fetch data with fallback for network issues."""
    try:
        response = client.get(endpoint)
        return response.json()
    except ConnectionError:
        print("Cannot connect to API server - using fallback")
        return fallback_value
    except TimeoutError:
        print("Request timed out - using fallback")
        return fallback_value

# Use cached or default data when API is unavailable
data = fetch_with_fallback("/config", fallback_value={"version": "1.0"})
```

### Implementing Circuit Breaker

Prevent cascading failures with circuit breaker pattern:

```python
from datetime import datetime, timedelta
from amplihack.utils.api_client import APIClient, APIError

class CircuitBreaker:
    """Circuit breaker for API calls."""

    def __init__(self, client: APIClient, failure_threshold: int = 5,
                 recovery_timeout: int = 60):
        self.client = client
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False

    def call(self, method: str, endpoint: str, **kwargs):
        """Make API call with circuit breaker protection."""
        # Check if circuit is open
        if self.is_open:
            if self._should_attempt_reset():
                self.is_open = False
            else:
                raise Exception("Circuit breaker is open - API unavailable")

        try:
            # Attempt the call
            response = getattr(self.client, method)(endpoint, **kwargs)
            self._on_success()
            return response
        except APIError as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to retry."""
        return (datetime.now() - self.last_failure_time).seconds > self.recovery_timeout

    def _on_success(self):
        """Reset failure count on success."""
        self.failure_count = 0

    def _on_failure(self):
        """Increment failure count and possibly open circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            print(f"Circuit breaker opened after {self.failure_count} failures")
```

## Authentication Error Handling

### Token Refresh Strategy

Handle expired authentication tokens:

```python
from amplihack.utils.api_client import APIClient, AuthenticationError

class TokenManager:
    """Manage authentication tokens with auto-refresh."""

    def __init__(self, auth_url: str, client_id: str, client_secret: str):
        self.auth_client = APIClient(base_url=auth_url)
        self.api_client = None
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.refresh_token = None

    def authenticate(self):
        """Get initial authentication tokens."""
        response = self.auth_client.post("/oauth/token", json={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        })

        data = response.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token")

        # Create API client with token
        self.api_client = APIClient(
            base_url="https://api.example.com",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )

    def refresh_auth(self):
        """Refresh expired access token."""
        if not self.refresh_token:
            # No refresh token - need full re-authentication
            self.authenticate()
            return

        try:
            response = self.auth_client.post("/oauth/refresh", json={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            })

            data = response.json()
            self.access_token = data["access_token"]
            self.api_client.headers["Authorization"] = f"Bearer {self.access_token}"
        except APIError:
            # Refresh failed - do full authentication
            self.authenticate()

    def request(self, method: str, endpoint: str, **kwargs):
        """Make authenticated request with automatic token refresh."""
        if not self.api_client:
            self.authenticate()

        try:
            return getattr(self.api_client, method)(endpoint, **kwargs)
        except AuthenticationError:
            # Token expired - refresh and retry
            self.refresh_auth()
            return getattr(self.api_client, method)(endpoint, **kwargs)
```

## Error Recovery Patterns

### Retry with Exponential Backoff

Implement custom retry logic:

```python
import time
import random
from amplihack.utils.api_client import APIClient, APIError

def retry_with_jitter(func, max_attempts: int = 3, base_delay: float = 1.0):
    """Retry with exponential backoff and jitter."""
    for attempt in range(max_attempts):
        try:
            return func()
        except APIError as e:
            if attempt == max_attempts - 1:
                raise  # Final attempt failed

            # Calculate delay with exponential backoff and jitter
            delay = base_delay * (2 ** attempt)
            jitter = random.uniform(0, delay * 0.1)  # Add 10% jitter
            total_delay = delay + jitter

            print(f"Attempt {attempt + 1} failed: {e.message}")
            print(f"Retrying in {total_delay:.2f} seconds...")
            time.sleep(total_delay)
```

### Fallback Chain

Implement fallback strategies:

```python
from typing import List, Callable, Optional

def fallback_chain(strategies: List[Callable], default=None):
    """Try multiple strategies in order until one succeeds."""
    errors = []

    for strategy in strategies:
        try:
            return strategy()
        except Exception as e:
            errors.append(f"{strategy.__name__}: {str(e)}")
            continue

    print(f"All strategies failed: {errors}")
    return default

# Example usage
def get_user_data(user_id: int):
    """Get user data with multiple fallback strategies."""

    def from_primary_api():
        client = APIClient(base_url="https://api.example.com")
        return client.get(f"/users/{user_id}").json()

    def from_backup_api():
        client = APIClient(base_url="https://backup.example.com")
        return client.get(f"/users/{user_id}").json()

    def from_cache():
        # Return cached data
        return {"id": user_id, "name": "Cached User", "cached": True}

    return fallback_chain(
        strategies=[from_primary_api, from_backup_api, from_cache],
        default={"id": user_id, "name": "Unknown", "error": True}
    )
```

## Logging and Monitoring

### Error Logging Strategy

Log errors for monitoring and debugging:

```python
import logging
from amplihack.utils.api_client import APIClient, APIError

# Configure structured logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def make_api_call_with_logging(client: APIClient, endpoint: str):
    """Make API call with comprehensive error logging."""
    try:
        response = client.get(endpoint)
        logger.info(f"Successfully fetched {endpoint}")
        return response.json()
    except APIError as e:
        # Log error details for monitoring
        logger.error(f"API call failed",
                    extra={
                        "endpoint": endpoint,
                        "status_code": e.status_code,
                        "error_message": e.message,
                        "request_url": getattr(e, 'request_url', None),
                        "response_body": getattr(e, 'response_body', None)
                    })
        raise
```

### Metrics Collection

Track error rates and patterns:

```python
from collections import defaultdict
from datetime import datetime

class ErrorMetrics:
    """Collect metrics on API errors."""

    def __init__(self):
        self.error_counts = defaultdict(int)
        self.error_times = defaultdict(list)

    def record_error(self, error: APIError):
        """Record an error occurrence."""
        error_type = type(error).__name__
        self.error_counts[error_type] += 1
        self.error_times[error_type].append(datetime.now())

        # Log if error rate is high
        if self.get_error_rate(error_type) > 0.1:  # More than 10% errors
            print(f"High error rate for {error_type}: {self.get_error_rate(error_type):.1%}")

    def get_error_rate(self, error_type: str, window_minutes: int = 5) -> float:
        """Calculate error rate in time window."""
        if error_type not in self.error_times:
            return 0.0

        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent_errors = [t for t in self.error_times[error_type] if t > cutoff]
        return len(recent_errors) / max(1, window_minutes * 60)  # Errors per second

# Usage
metrics = ErrorMetrics()
client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/users")
except APIError as e:
    metrics.record_error(e)
    raise
```

## Best Practices

### 1. Use Specific Exception Types

Catch specific exceptions rather than the base APIError when you need different handling logic.

### 2. Log Error Context

Always log enough context to debug issues in production.

### 3. Implement Graceful Degradation

Have fallback strategies for when the API is unavailable.

### 4. Monitor Error Patterns

Track error rates to identify systemic issues.

### 5. Test Error Paths

Write tests that simulate various error conditions.

## Next Steps

- Learn about [Advanced Configuration Options](../reference/api-client-config.md)
- See [Common API Patterns](./common-api-patterns.md)
- Read the [API Client Reference](../reference/api-client.md)
