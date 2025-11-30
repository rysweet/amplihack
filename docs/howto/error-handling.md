# How to Handle Errors Gracefully

This guide shows you how to implement robust error handling with the REST API Client's comprehensive exception hierarchy.

## Exception Hierarchy

The REST API Client provides a structured exception hierarchy:

```
APIError (base exception)
├── NetworkError       # Connection issues
├── TimeoutError       # Request timeouts
├── RateLimitError     # 429 responses
├── AuthenticationError # 401 responses
├── AuthorizationError  # 403 responses
├── ValidationError     # 400 responses
└── ServerError        # 5xx responses
```

## Basic Error Handling

Catch specific exceptions for targeted error handling:

```python
from rest_api_client import APIClient
from rest_api_client.exceptions import (
    APIError,
    NetworkError,
    RateLimitError,
    AuthenticationError,
    ValidationError,
    ServerError
)

client = APIClient(base_url="https://api.example.com")

try:
    response = client.get("/protected-resource")
    print(f"Success: {response.data}")

except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
    print("Please check your API credentials")

except RateLimitError as e:
    print(f"Rate limited. Wait {e.retry_after} seconds")

except NetworkError as e:
    print(f"Network issue: {e.message}")
    print("Check your internet connection")

except ValidationError as e:
    print(f"Bad request: {e.message}")
    print(f"Errors: {e.errors}")  # Detailed validation errors

except ServerError as e:
    print(f"Server error ({e.status_code}): {e.message}")
    print("The API is experiencing issues")

except APIError as e:
    # Catch any other API errors
    print(f"API error: {e}")
```

## Handling Network Errors

Network errors require special handling as they're often transient:

```python
import time
from rest_api_client.exceptions import NetworkError

def fetch_with_network_retry(client, endpoint, max_retries=3):
    """Fetch data with network error recovery."""
    for attempt in range(max_retries):
        try:
            return client.get(endpoint)
        except NetworkError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Network error, retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts: {e}")
                raise

# Usage
response = fetch_with_network_retry(client, "/users")
```

## Handling Authentication Errors

Implement token refresh on authentication failures:

```python
from rest_api_client.exceptions import AuthenticationError

class AuthenticatedClient:
    """Client with automatic token refresh."""

    def __init__(self, base_url, get_token_func):
        self.base_url = base_url
        self.get_token_func = get_token_func
        self.token = None
        self._refresh_client()

    def _refresh_client(self):
        """Create a new client with fresh token."""
        self.token = self.get_token_func()
        self.client = APIClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.token}"}
        )

    def request(self, method, endpoint, retry_auth=True, **kwargs):
        """Make a request with automatic token refresh."""
        try:
            return getattr(self.client, method)(endpoint, **kwargs)
        except AuthenticationError:
            if retry_auth:
                print("Token expired, refreshing...")
                self._refresh_client()
                return self.request(method, endpoint, retry_auth=False, **kwargs)
            raise

# Usage
def get_new_token():
    # Your token generation logic here
    return "new_token_123"

auth_client = AuthenticatedClient(
    base_url="https://api.example.com",
    get_token_func=get_new_token
)

response = auth_client.request("get", "/protected")
```

## Handling Validation Errors

Extract and display validation errors clearly:

```python
from rest_api_client.exceptions import ValidationError

def create_user(client, user_data):
    """Create a user with validation error handling."""
    try:
        response = client.post("/users", json=user_data)
        print(f"User created: {response.data['id']}")
        return response.data

    except ValidationError as e:
        print("Validation failed:")

        # Handle structured errors
        if hasattr(e, 'errors') and e.errors:
            for field, messages in e.errors.items():
                if isinstance(messages, list):
                    for message in messages:
                        print(f"  - {field}: {message}")
                else:
                    print(f"  - {field}: {messages}")
        else:
            print(f"  - {e.message}")

        return None

# Test with invalid data
invalid_user = {
    "email": "not-an-email",  # Invalid format
    "age": -5                  # Invalid value
}

create_user(client, invalid_user)
# Output:
# Validation failed:
#   - email: Must be a valid email address
#   - age: Must be a positive number
```

## Handling Rate Limit Errors

Implement smart rate limit handling with backoff:

```python
from rest_api_client.exceptions import RateLimitError
import time

class RateLimitHandler:
    """Handle rate limits with exponential backoff."""

    def __init__(self, client):
        self.client = client
        self.consecutive_rate_limits = 0

    def request_with_backoff(self, method, endpoint, **kwargs):
        """Make request with rate limit handling."""
        max_retries = 5

        for attempt in range(max_retries):
            try:
                response = getattr(self.client, method)(endpoint, **kwargs)
                self.consecutive_rate_limits = 0  # Reset on success
                return response

            except RateLimitError as e:
                self.consecutive_rate_limits += 1

                if attempt < max_retries - 1:
                    # Use retry-after header if available
                    if e.retry_after:
                        wait_time = e.retry_after
                    else:
                        # Exponential backoff
                        wait_time = min(300, 2 ** self.consecutive_rate_limits)

                    print(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Still rate limited after {max_retries} attempts")
                    raise

# Usage
handler = RateLimitHandler(client)
response = handler.request_with_backoff("get", "/popular-endpoint")
```

## Creating Custom Exceptions

Extend the exception hierarchy for domain-specific errors:

```python
from rest_api_client.exceptions import APIError

class BusinessLogicError(APIError):
    """Custom exception for business logic errors."""
    pass

class InsufficientCreditsError(BusinessLogicError):
    """User doesn't have enough credits."""
    def __init__(self, required, available):
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient credits: need {required}, have {available}"
        )

class DataIntegrityError(BusinessLogicError):
    """Data integrity violation."""
    pass

# Custom client with business logic errors
class BusinessClient(APIClient):
    def handle_error(self, response):
        """Handle custom error responses."""
        if response.status_code == 402:
            data = response.json()
            raise InsufficientCreditsError(
                required=data.get('required_credits'),
                available=data.get('available_credits')
            )
        elif response.status_code == 409:
            raise DataIntegrityError(response.json().get('message'))
        else:
            super().handle_error(response)

# Usage
try:
    client = BusinessClient(base_url="https://api.example.com")
    client.post("/expensive-operation")
except InsufficientCreditsError as e:
    print(f"Need {e.required - e.available} more credits")
```

## Error Recovery Patterns

### Circuit Breaker Pattern

```python
from datetime import datetime, timedelta
from rest_api_client.exceptions import APIError, ServerError

class CircuitBreaker:
    """Circuit breaker for failing endpoints."""

    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker."""
        if self.state == "OPEN":
            if datetime.now() - self.last_failure > timedelta(seconds=self.recovery_timeout):
                self.state = "HALF_OPEN"
                print("Circuit breaker: Trying half-open")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                print("Circuit breaker: Recovered, now CLOSED")
            return result

        except (ServerError, APIError) as e:
            self.failure_count += 1
            self.last_failure = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                print(f"Circuit breaker: OPEN after {self.failure_count} failures")

            raise

# Usage
breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

def make_request():
    return breaker.call(client.get, "/unreliable-endpoint")
```

### Fallback Pattern

```python
def get_user_with_fallback(user_id):
    """Get user with fallback to cache."""
    try:
        # Try primary source
        response = client.get(f"/users/{user_id}")
        # Cache the result
        cache[user_id] = response.data
        return response.data

    except (NetworkError, ServerError) as e:
        # Fall back to cache
        if user_id in cache:
            print(f"Using cached data due to: {e}")
            return cache[user_id]
        else:
            print(f"No cached data available for user {user_id}")
            raise

cache = {}
user = get_user_with_fallback(123)
```

## Error Logging

Implement comprehensive error logging:

```python
import logging
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggingClient(APIClient):
    """Client with detailed error logging."""

    def make_request(self, method, endpoint, **kwargs):
        """Make request with error logging."""
        try:
            return super().make_request(method, endpoint, **kwargs)

        except APIError as e:
            # Log API errors with context
            logger.error(
                f"API Error: {e.__class__.__name__}",
                extra={
                    'method': method,
                    'endpoint': endpoint,
                    'status_code': getattr(e, 'status_code', None),
                    'message': str(e),
                    'traceback': traceback.format_exc()
                }
            )
            raise

        except Exception as e:
            # Log unexpected errors
            logger.critical(
                f"Unexpected error: {e}",
                extra={
                    'method': method,
                    'endpoint': endpoint,
                    'traceback': traceback.format_exc()
                }
            )
            raise
```

## Testing Error Handling

```python
import unittest
from unittest.mock import Mock, patch
from rest_api_client import APIClient
from rest_api_client.exceptions import *

class TestErrorHandling(unittest.TestCase):
    def setUp(self):
        self.client = APIClient(base_url="https://test.com")

    @patch('requests.get')
    def test_handles_network_error(self, mock_get):
        """Test network error handling."""
        mock_get.side_effect = ConnectionError("Network unreachable")

        with self.assertRaises(NetworkError) as context:
            self.client.get("/test")

        self.assertIn("Network unreachable", str(context.exception))

    @patch('requests.get')
    def test_handles_rate_limit(self, mock_get):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_get.return_value = mock_response

        with self.assertRaises(RateLimitError) as context:
            self.client.get("/test")

        self.assertEqual(context.exception.retry_after, 60)

    @patch('requests.get')
    def test_handles_validation_error(self, mock_get):
        """Test validation error handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'errors': {
                'email': ['Invalid format'],
                'age': ['Must be positive']
            }
        }
        mock_get.return_value = mock_response

        with self.assertRaises(ValidationError) as context:
            self.client.get("/test")

        self.assertIn('email', context.exception.errors)
        self.assertIn('age', context.exception.errors)
```

## Best Practices

1. **Always catch specific exceptions** - Don't use bare except clauses
2. **Log errors with context** - Include request details in logs
3. **Implement retry logic** - For transient failures
4. **Use circuit breakers** - For failing services
5. **Provide fallbacks** - Cache or default values
6. **Test error paths** - Ensure error handling works
7. **Monitor error rates** - Track failure patterns
8. **Document error responses** - Help users handle errors

## Summary

Proper error handling is crucial for building resilient applications. The REST API Client's exception hierarchy provides:

- Clear error categorization
- Detailed error information
- Easy error recovery patterns
- Testable error paths
