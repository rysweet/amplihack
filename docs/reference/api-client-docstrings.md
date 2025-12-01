# API Client Module Docstrings

These docstrings should be added to the implementation files when creating the actual code.

## Module: amplihack/utils/api_client.py

```python
"""REST API client with automatic retry, rate limiting, and comprehensive error handling.

This module provides a production-ready HTTP client that handles common API
interaction patterns including exponential backoff retry, rate limiting,
connection pooling, and detailed error reporting.

The client is designed to be a drop-in replacement for direct requests usage
but with enterprise-grade reliability features built in.

Example:
    Basic usage with automatic retry and error handling:

        from amplihack.utils.api_client import APIClient

        client = APIClient(base_url="https://api.example.com")
        response = client.get("/users")
        users = response.json()

    Advanced configuration with custom retry logic:

        from amplihack.utils.api_client import APIClient, RetryConfig

        retry_config = RetryConfig(
            max_retries=5,
            backoff_factor=2.0,
            retry_statuses={429, 500, 502, 503, 504}
        )

        client = APIClient(
            base_url="https://api.example.com",
            retry_config=retry_config,
            rate_limit_per_second=10
        )

Classes:
    APIClient: Main client for making HTTP requests
    RetryConfig: Configuration for retry behavior
    APIRequest: Type-safe request structure
    APIResponse: Type-safe response structure
    APIError: Base exception for API errors
    RateLimitError: Raised when rate limited
    ValidationError: Raised for invalid requests
    AuthenticationError: Raised for auth failures
    TimeoutError: Raised when requests timeout
    ConnectionError: Raised for connection failures

Philosophy:
    - Ruthless simplicity: Clean API that just works
    - Zero-BS implementation: No stubs, fully functional
    - Production ready: Comprehensive error handling
    - Type safe: Full type hints throughout
"""
```

## Class: APIClient

```python
class APIClient:
    """REST API client with exponential backoff retry and rate limiting.

    Provides a robust HTTP client with automatic retries, rate limiting,
    comprehensive error handling, and type-safe request/response handling.

    The client maintains a session for connection pooling and efficiently
    handles transient failures, rate limits, and server errors automatically.

    Attributes:
        base_url (str): Base URL for all API requests.
        headers (Dict[str, str]): Default headers applied to all requests.
        timeout (int): Request timeout in seconds.
        session (requests.Session): Underlying session for connection pooling.
        retry_config (RetryConfig): Configuration for retry behavior.
        logger (logging.Logger): Logger instance for debugging.

    Example:
        Create and use a client:

            client = APIClient(base_url="https://api.github.com")

            # Make requests with automatic retry
            response = client.get("/repos/amplihack/amplihack")
            repo_data = response.json()

            # Handle errors gracefully
            try:
                response = client.post("/repos", json=new_repo_data)
            except RateLimitError as e:
                print(f"Rate limited. Retry after {e.retry_after} seconds")
            except ValidationError as e:
                print(f"Invalid data: {e.validation_errors}")

    Note:
        The client is thread-safe and can be shared across multiple threads.
        Use a single client instance for connection pooling benefits.
    """
```

## Method: **init**

```python
def __init__(
    self,
    base_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    max_retries: int = 3,
    backoff_factor: float = 1.0,
    retry_config: Optional[RetryConfig] = None,
    rate_limit_per_second: Optional[float] = None,
    verify_ssl: bool = True,
    proxies: Optional[Dict[str, str]] = None,
    debug: bool = False
):
    """Initialize the API client with configuration.

    Creates a new API client with the specified configuration. The client
    maintains a session for connection pooling and configures retry logic,
    rate limiting, and error handling based on the provided parameters.

    Args:
        base_url: Base URL for API requests. All endpoint paths will be
            appended to this URL. Must include protocol (https://).
        headers: Default headers to include in all requests. Common headers
            include Authorization, User-Agent, and Accept.
        timeout: Request timeout in seconds. Applies to both connection and
            read timeout. Default is 30 seconds.
        max_retries: Maximum number of retry attempts for failed requests.
            Only used if retry_config is not provided. Default is 3.
        backoff_factor: Multiplier for exponential backoff between retries.
            Only used if retry_config is not provided. Default is 1.0.
        retry_config: Advanced retry configuration. If provided, overrides
            max_retries and backoff_factor parameters.
        rate_limit_per_second: Client-side rate limit in requests per second.
            Enforces local throttling to prevent hitting server limits.
        verify_ssl: Whether to verify SSL certificates. Set to False only
            for development with self-signed certificates.
        proxies: Proxy configuration dictionary. Keys are protocols (http,
            https) and values are proxy URLs.
        debug: Enable debug logging for requests and responses. Useful for
            development but should be disabled in production.

    Example:
        Basic initialization:

            client = APIClient(base_url="https://api.example.com")

        With authentication and custom timeout:

            client = APIClient(
                base_url="https://api.example.com",
                headers={"Authorization": "Bearer token123"},
                timeout=60
            )

        With advanced retry configuration:

            retry_config = RetryConfig(
                max_retries=5,
                backoff_factor=2.0,
                retry_statuses={429, 500, 502, 503, 504}
            )
            client = APIClient(
                base_url="https://api.example.com",
                retry_config=retry_config
            )

    Raises:
        ValueError: If base_url is invalid or missing protocol.
    """
```

## Method: request

```python
def request(
    self,
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Any] = None,
    headers: Optional[Dict[str, str]] = None,
    **kwargs
) -> requests.Response:
    """Make an HTTP request with automatic retry and error handling.

    Sends an HTTP request to the specified endpoint with automatic retry
    for transient failures, rate limit handling, and comprehensive error
    reporting. The method handles exponential backoff, respects rate limit
    headers, and provides detailed exception information for failures.

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS).
            Case-insensitive.
        endpoint: API endpoint path relative to base_url. Should start with
            a forward slash (e.g., "/users/123").
        params: Query parameters to append to the URL. Will be properly
            encoded automatically.
        json: JSON data to send in the request body. Automatically sets
            Content-Type header to application/json.
        data: Raw data for request body. Use for non-JSON payloads.
            Cannot be used together with json parameter.
        headers: Additional headers for this specific request. These are
            merged with the default headers set on the client.
        **kwargs: Additional arguments passed through to the underlying
            requests library (e.g., stream, files, auth).

    Returns:
        Response object with status_code, headers, json() method, text,
        and other standard requests.Response attributes.

    Raises:
        APIError: Base exception for API errors. Check status_code attribute.
        RateLimitError: When rate limited (429 status). Includes retry_after,
            rate_limit, and rate_limit_remaining attributes.
        ValidationError: For request validation errors (400 status).
            Includes validation_errors dict with field-level errors.
        AuthenticationError: When authentication fails (401 status).
        ForbiddenError: When access is forbidden (403 status).
        NotFoundError: When resource is not found (404 status).
        TimeoutError: When request exceeds timeout duration.
        ConnectionError: For network connection failures.
        ServerError: For 5xx server errors.

    Example:
        Simple GET request:

            response = client.request("GET", "/users")
            users = response.json()

        POST request with JSON data:

            user_data = {"name": "Alice", "email": "alice@example.com"}
            response = client.request("POST", "/users", json=user_data)
            created_user = response.json()

        Request with query parameters and custom headers:

            response = client.request(
                "GET",
                "/search",
                params={"q": "python", "page": 2},
                headers={"Accept": "application/vnd.api+json"}
            )

        Handling specific errors:

            try:
                response = client.request("DELETE", "/users/123")
            except NotFoundError:
                print("User already deleted")
            except ForbiddenError:
                print("No permission to delete user")

    Note:
        This method automatically retries failed requests based on the retry
        configuration. Safe methods (GET, PUT, DELETE) are retried by default,
        while non-idempotent methods (POST, PATCH) are not retried to avoid
        creating duplicate resources.
    """
```

## Class: RetryConfig

```python
@dataclass
class RetryConfig:
    """Configuration for API client retry behavior.

    Controls how the API client handles failed requests, including which
    status codes trigger retries, which methods are safe to retry, and
    the backoff strategy between attempts.

    Attributes:
        max_retries: Maximum number of retry attempts. Set to 0 to disable
            retries entirely. Default is 3.
        backoff_factor: Multiplier for exponential backoff delay. The delay
            between retries is calculated as backoff_factor * (2 ** attempt).
            Default is 1.0.
        retry_statuses: Set of HTTP status codes that should trigger a retry.
            Default includes 429 (rate limit) and 5xx server errors.
        retry_methods: Set of HTTP methods that are safe to retry. Default
            includes only idempotent methods (GET, PUT, DELETE, HEAD, OPTIONS).
        max_backoff: Maximum delay between retries in seconds. Prevents
            excessive delays even with high retry counts. Default is 60.0.

    Example:
        Conservative retry for critical operations:

            config = RetryConfig(
                max_retries=10,
                backoff_factor=2.0,
                max_backoff=300.0
            )

        Aggressive retry for resilient systems:

            config = RetryConfig(
                max_retries=5,
                backoff_factor=0.5,
                retry_statuses={429, 500, 502, 503, 504, 520, 521, 522},
                retry_methods={"GET", "POST", "PUT", "DELETE"}
            )

        Disable retries entirely:

            config = RetryConfig(max_retries=0)

    Note:
        The exponential backoff formula is:
        delay = min(backoff_factor * (2 ** attempt), max_backoff)

        With default settings, delays are: 1s, 2s, 4s, 8s, etc.
    """
```

## Exception Classes

```python
class APIError(Exception):
    """Base exception for all API-related errors.

    Provides detailed error information including the HTTP status code,
    request details, and response body for debugging.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code if applicable (None for connection errors).
        response: Raw response object from requests library.
        request_url: URL that caused the error.
        request_headers: Headers sent with the failed request.
        response_body: Raw response body text for debugging.

    Example:
        Catching and inspecting API errors:

            try:
                response = client.get("/protected-resource")
            except APIError as e:
                print(f"Error: {e.message}")
                print(f"Status: {e.status_code}")
                print(f"URL: {e.request_url}")
                print(f"Response: {e.response_body}")
    """


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded (HTTP 429).

    Includes rate limit information from response headers to help with
    retry timing and quota management.

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header).
        rate_limit: Total rate limit quota (from X-RateLimit-Limit header).
        rate_limit_remaining: Remaining requests in current window
            (from X-RateLimit-Remaining header).
        rate_limit_reset: Unix timestamp when the rate limit resets
            (from X-RateLimit-Reset header).

    Example:
        Handling rate limits with backoff:

            try:
                response = client.get("/api/endpoint")
            except RateLimitError as e:
                print(f"Rate limited. Quota: {e.rate_limit}")
                print(f"Remaining: {e.rate_limit_remaining}")
                print(f"Retry after: {e.retry_after} seconds")
                time.sleep(e.retry_after)
                response = client.get("/api/endpoint")  # Retry
    """


class ValidationError(APIError):
    """Raised for request validation errors (HTTP 400).

    Includes field-level validation errors when available from the API
    response to help identify and fix invalid input data.

    Attributes:
        validation_errors: Dictionary mapping field names to lists of
            validation error messages. Structure depends on API format.

    Example:
        Handling validation errors:

            try:
                response = client.post("/users", json=user_data)
            except ValidationError as e:
                for field, errors in e.validation_errors.items():
                    print(f"{field}: {', '.join(errors)}")
                # Output:
                # email: Invalid format, Already exists
                # password: Too short, Must contain special character
    """
```

## Utility Functions

```python
def exponential_backoff(attempt: int, backoff_factor: float,
                       max_backoff: float = 60.0) -> float:
    """Calculate exponential backoff delay for retry attempt.

    Implements exponential backoff with configurable factor and maximum
    delay to prevent excessive waiting times.

    Args:
        attempt: Retry attempt number (0-indexed).
        backoff_factor: Multiplier for exponential calculation.
        max_backoff: Maximum delay in seconds.

    Returns:
        Delay in seconds before the next retry attempt.

    Example:
        Calculate delays for multiple attempts:

            for i in range(5):
                delay = exponential_backoff(i, backoff_factor=2.0)
                print(f"Attempt {i + 1}: Wait {delay} seconds")
            # Output:
            # Attempt 1: Wait 2.0 seconds
            # Attempt 2: Wait 4.0 seconds
            # Attempt 3: Wait 8.0 seconds
            # Attempt 4: Wait 16.0 seconds
            # Attempt 5: Wait 32.0 seconds
    """


def parse_rate_limit_headers(headers: Dict[str, str]) -> Dict[str, Any]:
    """Parse rate limit information from response headers.

    Extracts rate limit information from standard and vendor-specific
    headers used by various APIs (GitHub, Stripe, etc.).

    Args:
        headers: Response headers dictionary.

    Returns:
        Dictionary with rate limit information:
        - retry_after: Seconds to wait
        - rate_limit: Total limit
        - rate_limit_remaining: Remaining requests
        - rate_limit_reset: Reset timestamp

    Example:
        Parse GitHub API headers:

            headers = {
                "X-RateLimit-Limit": "5000",
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": "1642000000"
            }
            info = parse_rate_limit_headers(headers)
            print(f"Limit: {info['rate_limit']}")
            print(f"Remaining: {info['rate_limit_remaining']}")
    """
```
