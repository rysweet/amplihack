# Exception Types Reference

Complete reference for all exception types in the REST API Client library.

## Exception Hierarchy

```
APIError (base exception)
├── NetworkError         # Network connectivity issues
├── TimeoutError         # Request timeout
├── RateLimitError       # Rate limiting (429)
├── AuthenticationError  # Authentication failure (401)
├── AuthorizationError   # Authorization failure (403)
├── ValidationError      # Validation failure (400)
└── ServerError          # Server errors (5xx)
```

## Base Exception

### APIError

Base exception for all API-related errors.

```python
class APIError(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        message: str,
        status_code: int = None,
        response: Response = None,
        request: Request = None
    ):
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code
            response: Response object
            request: Original request
        """
        self.message = message
        self.status_code = status_code
        self.response = response
        self.request = request
        super().__init__(message)
```

#### Attributes

- **message** (`str`): Human-readable error message
- **status_code** (`Optional[int]`): HTTP status code if applicable
- **response** (`Optional[Response]`): Full response object
- **request** (`Optional[Request]`): Original request that caused the error

#### Usage Example

```python
try:
    client.get("/resource")
except APIError as e:
    print(f"Error: {e.message}")
    print(f"Status: {e.status_code}")
    if e.response:
        print(f"Response body: {e.response.text}")
```

## Network Errors

### NetworkError

Raised when network connectivity issues occur.

```python
class NetworkError(APIError):
    """Network connectivity error."""

    def __init__(self, message: str, original_error: Exception = None):
        """
        Initialize network error.

        Args:
            message: Error message
            original_error: Original exception that caused this error
        """
        self.original_error = original_error
        super().__init__(message)
```

#### Common Causes

- No internet connection
- DNS resolution failures
- Connection refused
- Network unreachable
- Socket errors

#### Usage Example

```python
try:
    client.get("/users")
except NetworkError as e:
    print(f"Network issue: {e.message}")
    if e.original_error:
        print(f"Caused by: {e.original_error}")
    # Implement offline mode or retry logic
```

### TimeoutError

Raised when a request exceeds the timeout limit.

```python
class TimeoutError(NetworkError):
    """Request timeout error."""

    def __init__(
        self,
        message: str,
        timeout: int,
        endpoint: str = None
    ):
        """
        Initialize timeout error.

        Args:
            message: Error message
            timeout: Timeout value that was exceeded
            endpoint: Endpoint that timed out
        """
        self.timeout = timeout
        self.endpoint = endpoint
        super().__init__(message)
```

#### Attributes

- **timeout** (`int`): Timeout value in seconds
- **endpoint** (`Optional[str]`): Endpoint that timed out

#### Usage Example

```python
try:
    client.get("/slow-endpoint", timeout=5)
except TimeoutError as e:
    print(f"Request timed out after {e.timeout} seconds")
    print(f"Endpoint: {e.endpoint}")
    # Consider increasing timeout or optimizing endpoint
```

## Authentication Errors

### AuthenticationError

Raised for 401 Unauthorized responses.

```python
class AuthenticationError(APIError):
    """Authentication failure (401)."""

    def __init__(
        self,
        message: str = "Authentication required",
        realm: str = None,
        www_authenticate: str = None
    ):
        """
        Initialize authentication error.

        Args:
            message: Error message
            realm: Authentication realm
            www_authenticate: WWW-Authenticate header value
        """
        self.realm = realm
        self.www_authenticate = www_authenticate
        super().__init__(message, status_code=401)
```

#### Attributes

- **realm** (`Optional[str]`): Authentication realm
- **www_authenticate** (`Optional[str]`): Authentication scheme

#### Usage Example

```python
try:
    client.get("/protected")
except AuthenticationError as e:
    print(f"Authentication failed: {e.message}")
    if e.realm:
        print(f"Realm: {e.realm}")
    # Refresh token or re-authenticate
    new_token = refresh_auth_token()
    client.headers["Authorization"] = f"Bearer {new_token}"
```

### AuthorizationError

Raised for 403 Forbidden responses.

```python
class AuthorizationError(APIError):
    """Authorization failure (403)."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permission: str = None,
        user_permissions: List[str] = None
    ):
        """
        Initialize authorization error.

        Args:
            message: Error message
            required_permission: Permission needed
            user_permissions: Current user permissions
        """
        self.required_permission = required_permission
        self.user_permissions = user_permissions or []
        super().__init__(message, status_code=403)
```

#### Attributes

- **required_permission** (`Optional[str]`): Permission required
- **user_permissions** (`List[str]`): Current permissions

#### Usage Example

```python
try:
    client.delete("/admin/users/123")
except AuthorizationError as e:
    print(f"Authorization failed: {e.message}")
    if e.required_permission:
        print(f"Required: {e.required_permission}")
        print(f"You have: {', '.join(e.user_permissions)}")
    # Request elevated permissions or use different endpoint
```

## Validation Errors

### ValidationError

Raised for 400 Bad Request responses with validation errors.

```python
class ValidationError(APIError):
    """Request validation error (400)."""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: dict = None,
        invalid_fields: List[str] = None
    ):
        """
        Initialize validation error.

        Args:
            message: Error message
            errors: Detailed validation errors by field
            invalid_fields: List of invalid field names
        """
        self.errors = errors or {}
        self.invalid_fields = invalid_fields or list(errors.keys()) if errors else []
        super().__init__(message, status_code=400)
```

#### Attributes

- **errors** (`dict`): Field-specific error messages
- **invalid_fields** (`List[str]`): Names of invalid fields

#### Usage Example

```python
try:
    client.post("/users", json={
        "email": "invalid-email",
        "age": -5
    })
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    for field, error in e.errors.items():
        print(f"  {field}: {error}")
    # Fix validation errors and retry
    if "email" in e.invalid_fields:
        user_data["email"] = get_valid_email()
```

## Rate Limiting Errors

### RateLimitError

Raised for 429 Too Many Requests responses.

```python
class RateLimitError(APIError):
    """Rate limit exceeded (429)."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = None,
        limit: int = None,
        remaining: int = None,
        reset_time: datetime = None
    ):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retry
            limit: Rate limit maximum
            remaining: Remaining requests
            reset_time: When limit resets
        """
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        super().__init__(message, status_code=429)
```

#### Attributes

- **retry_after** (`Optional[int]`): Seconds to wait
- **limit** (`Optional[int]`): Maximum allowed requests
- **remaining** (`Optional[int]`): Remaining requests in window
- **reset_time** (`Optional[datetime]`): When limit resets

#### Usage Example

```python
import time

try:
    client.get("/popular-endpoint")
except RateLimitError as e:
    print(f"Rate limited: {e.message}")
    if e.retry_after:
        print(f"Waiting {e.retry_after} seconds...")
        time.sleep(e.retry_after)
    if e.reset_time:
        print(f"Limit resets at: {e.reset_time}")
    # Implement backoff strategy
```

## Server Errors

### ServerError

Raised for 5xx server error responses.

```python
class ServerError(APIError):
    """Server error (5xx)."""

    def __init__(
        self,
        message: str = "Server error",
        status_code: int = 500,
        error_id: str = None,
        retry_possible: bool = True
    ):
        """
        Initialize server error.

        Args:
            message: Error message
            status_code: Specific 5xx status code
            error_id: Server error ID for support
            retry_possible: Whether retry might succeed
        """
        self.error_id = error_id
        self.retry_possible = retry_possible
        super().__init__(message, status_code=status_code)
```

#### Attributes

- **error_id** (`Optional[str]`): Error ID for support tickets
- **retry_possible** (`bool`): Whether retry might work

#### Common Status Codes

- **500**: Internal Server Error
- **502**: Bad Gateway
- **503**: Service Unavailable
- **504**: Gateway Timeout

#### Usage Example

```python
try:
    client.post("/process", json=data)
except ServerError as e:
    print(f"Server error {e.status_code}: {e.message}")
    if e.error_id:
        print(f"Error ID: {e.error_id}")
    if e.retry_possible:
        # Implement retry with backoff
        time.sleep(5)
        retry_request()
    else:
        # Contact support with error ID
        report_to_support(e.error_id)
```

## Custom Exception Handling

### Creating Custom Exceptions

```python
from rest_api_client.exceptions import APIError

class BusinessLogicError(APIError):
    """Custom business logic error."""
    pass

class InsufficientFundsError(BusinessLogicError):
    """Insufficient funds for transaction."""

    def __init__(self, required: float, available: float):
        self.required = required
        self.available = available
        super().__init__(
            f"Insufficient funds: need {required}, have {available}"
        )

class ResourceNotFoundError(APIError):
    """Resource not found."""

    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            f"{resource_type} with ID {resource_id} not found",
            status_code=404
        )
```

### Handling Multiple Exception Types

```python
def safe_api_call(client, endpoint):
    """Make API call with comprehensive error handling."""
    try:
        return client.get(endpoint)

    except ValidationError as e:
        # Handle validation errors
        log_validation_error(e.errors)
        return None

    except AuthenticationError:
        # Refresh authentication
        refresh_token()
        return safe_api_call(client, endpoint)  # Retry

    except RateLimitError as e:
        # Wait and retry
        time.sleep(e.retry_after or 60)
        return safe_api_call(client, endpoint)

    except ServerError as e:
        if e.retry_possible:
            # Retry with exponential backoff
            time.sleep(5)
            return safe_api_call(client, endpoint)
        else:
            # Fatal server error
            raise

    except NetworkError:
        # Check connectivity
        if not is_online():
            return get_cached_data(endpoint)
        raise

    except APIError as e:
        # Catch any other API errors
        logger.error(f"API error: {e}")
        raise
```

## Exception Utilities

### Extracting Error Details

```python
def extract_error_details(error: APIError) -> dict:
    """Extract all available error details."""
    details = {
        "type": error.__class__.__name__,
        "message": str(error),
        "status_code": error.status_code
    }

    if hasattr(error, "errors"):
        details["validation_errors"] = error.errors

    if hasattr(error, "retry_after"):
        details["retry_after"] = error.retry_after

    if hasattr(error, "error_id"):
        details["error_id"] = error.error_id

    if error.response:
        details["response_body"] = error.response.text
        details["response_headers"] = dict(error.response.headers)

    return details
```

### Error Recovery Strategies

```python
class ErrorRecovery:
    """Strategies for recovering from errors."""

    @staticmethod
    def with_retry(func, max_attempts=3, delay=1.0):
        """Retry function on failure."""
        for attempt in range(max_attempts):
            try:
                return func()
            except (NetworkError, ServerError) as e:
                if attempt < max_attempts - 1:
                    time.sleep(delay * (2 ** attempt))
                else:
                    raise

    @staticmethod
    def with_fallback(func, fallback_func):
        """Use fallback on failure."""
        try:
            return func()
        except APIError:
            return fallback_func()

    @staticmethod
    def with_circuit_breaker(func, failure_threshold=5):
        """Circuit breaker pattern."""
        # Implementation shown in error handling guide
        pass
```

## Testing Exception Handling

```python
import unittest
from unittest.mock import Mock
from rest_api_client.exceptions import *

class TestExceptionHandling(unittest.TestCase):
    def test_validation_error_details(self):
        """Test ValidationError with field errors."""
        error = ValidationError(
            message="Invalid input",
            errors={
                "email": "Invalid format",
                "age": "Must be positive"
            }
        )

        self.assertEqual(error.status_code, 400)
        self.assertIn("email", error.invalid_fields)
        self.assertEqual(error.errors["email"], "Invalid format")

    def test_rate_limit_error_retry_after(self):
        """Test RateLimitError retry information."""
        error = RateLimitError(
            retry_after=60,
            limit=100,
            remaining=0
        )

        self.assertEqual(error.status_code, 429)
        self.assertEqual(error.retry_after, 60)
        self.assertEqual(error.remaining, 0)

    def test_custom_exception(self):
        """Test custom exception creation."""
        class CustomError(APIError):
            pass

        error = CustomError("Custom error", status_code=418)
        self.assertIsInstance(error, APIError)
        self.assertEqual(error.status_code, 418)
```
