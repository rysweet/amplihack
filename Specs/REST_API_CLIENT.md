# Module: REST API Client

## Purpose

Production-ready REST API client with enterprise-grade reliability features: automatic retries with exponential backoff, rate limit handling, structured error handling, and comprehensive logging.

## Philosophy

- **Single Responsibility**: Each component handles ONE concern (client, retry, rate limit, errors)
- **Standard Library First**: Only external dependency is `requests` library
- **Zero-BS Implementation**: Every function works or doesn't exist - no stubs
- **Regeneratable**: Clear contracts allow rebuilding any component independently

## Public API (The "Studs")

```python
# Core client
from amplihack.utils.api_client import APIClient

# Configuration
from amplihack.utils.api_client import RetryConfig, RateLimitConfig

# Data models
from amplihack.utils.api_client import APIRequest, APIResponse

# Exceptions
from amplihack.utils.api_client import (
    APIClientError,
    RequestError,
    ResponseError,
    HTTPError,
    RateLimitError,
    RetryExhaustedError,
)
```

## Module Structure

```
src/amplihack/utils/api_client/
├── __init__.py         # Public API (__all__ definition)
├── README.md          # This specification
├── client.py          # APIClient class (orchestrator)
├── config.py          # RetryConfig, RateLimitConfig dataclasses
├── exceptions.py      # Exception hierarchy
├── models.py          # APIRequest, APIResponse dataclasses
├── retry.py           # RetryHandler (exponential backoff logic)
├── rate_limit.py      # RateLimitHandler (429 detection, Retry-After)
├── tests/
│   ├── __init__.py
│   ├── test_client.py
│   ├── test_retry.py
│   ├── test_rate_limit.py
│   ├── test_exceptions.py
│   └── test_integration.py
└── examples/
    └── basic_usage.py
```

## Component Specifications

### 1. APIClient (client.py)

**Responsibility**: Orchestrate HTTP requests with retry and rate limit handling

**Contract**:

```python
class APIClient:
    def __init__(
        self,
        base_url: str,
        retry_config: Optional[RetryConfig] = None,
        rate_limit_config: Optional[RateLimitConfig] = None,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize API client with base URL and optional configurations."""
        pass

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> APIResponse:
        """Execute GET request."""
        pass

    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> APIResponse:
        """Execute POST request."""
        pass

    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, json: Optional[Dict[str, Any]] = None) -> APIResponse:
        """Execute PUT request."""
        pass

    def delete(self, endpoint: str) -> APIResponse:
        """Execute DELETE request."""
        pass

    def request(self, request: APIRequest) -> APIResponse:
        """Execute generic request (used internally by get/post/put/delete)."""
        pass
```

**Dependencies**:

- `requests` library for HTTP
- `RetryHandler` for retry logic
- `RateLimitHandler` for rate limit detection
- `logging` for request/response logging

**Error Handling**:

- Wraps `requests` exceptions as `RequestError`
- Raises `RetryExhaustedError` when max retries exceeded
- Raises `RateLimitError` when rate limit hit and no Retry-After
- Raises `HTTPError` for 4xx/5xx responses (except 429)

**Logging**:

- Log request start (method, URL)
- Log response (status, duration)
- Log retry attempts
- Log rate limit delays

### 2. RetryHandler (retry.py)

**Responsibility**: Implement exponential backoff retry logic

**Contract**:

```python
@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    retry_on_status_codes: tuple = (500, 502, 503, 504)

class RetryHandler:
    def __init__(self, config: RetryConfig):
        """Initialize retry handler with configuration."""
        pass

    def should_retry(self, attempt: int, status_code: Optional[int] = None, exception: Optional[Exception] = None) -> bool:
        """Determine if request should be retried."""
        pass

    def get_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay for given attempt."""
        pass

    def execute_with_retry(self, func: Callable[[], APIResponse]) -> APIResponse:
        """Execute function with retry logic."""
        pass
```

**Algorithm**:

```
delay = min(base_delay * (exponential_base ** attempt), max_delay)
```

**Retry Conditions**:

- Network errors (connection timeout, DNS failure)
- HTTP 500, 502, 503, 504 (configurable)
- Does NOT retry on 4xx (client errors) except 429 (handled separately)

### 3. RateLimitHandler (rate_limit.py)

**Responsibility**: Detect and handle rate limiting (HTTP 429)

**Contract**:

```python
@dataclass
class RateLimitConfig:
    max_wait_time: float = 300.0  # seconds (5 minutes)
    respect_retry_after: bool = True

class RateLimitHandler:
    def __init__(self, config: RateLimitConfig):
        """Initialize rate limit handler with configuration."""
        pass

    def is_rate_limited(self, response: requests.Response) -> bool:
        """Check if response indicates rate limiting."""
        pass

    def get_retry_after(self, response: requests.Response) -> Optional[float]:
        """Extract Retry-After header value (supports both seconds and HTTP-date)."""
        pass

    def handle_rate_limit(self, response: requests.Response) -> None:
        """Handle rate limit by sleeping or raising RateLimitError."""
        pass
```

**Retry-After Parsing**:

- Integer: Delay in seconds
- HTTP-date: Parse datetime and calculate delay
- Missing: Raise `RateLimitError` (no guessing)

**Behavior**:

- If Retry-After <= max_wait_time: Sleep and return
- If Retry-After > max_wait_time: Raise `RateLimitError`
- If no Retry-After header: Raise `RateLimitError`

### 4. Exception Hierarchy (exceptions.py)

**Responsibility**: Provide structured error information

**Hierarchy**:

```python
class APIClientError(Exception):
    """Base exception for all API client errors."""
    pass

class RequestError(APIClientError):
    """Error occurred while making request (network, timeout, etc)."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        pass

class ResponseError(APIClientError):
    """Error occurred processing response."""
    pass

class HTTPError(ResponseError):
    """HTTP error response (4xx, 5xx excluding 429)."""
    def __init__(self, status_code: int, message: str, response: Optional[requests.Response] = None):
        pass

class RateLimitError(ResponseError):
    """Rate limit exceeded (HTTP 429)."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        pass

class RetryExhaustedError(APIClientError):
    """Maximum retry attempts exceeded."""
    def __init__(self, attempts: int, last_error: Optional[Exception] = None):
        pass
```

**Key Features**:

- All exceptions inherit from `APIClientError` for easy catching
- Store original errors for debugging
- Include HTTP details (status, response) where relevant

### 5. Data Models (models.py)

**Responsibility**: Structure request and response data

**Contract**:

```python
@dataclass
class APIRequest:
    method: str  # GET, POST, PUT, DELETE
    url: str
    headers: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    json: Optional[Dict[str, Any]] = None
    timeout: int = 30

@dataclass
class APIResponse:
    status_code: int
    headers: Dict[str, str]
    body: str
    json_data: Optional[Dict[str, Any]] = None
    elapsed_seconds: float = 0.0

    def is_success(self) -> bool:
        """Return True if status code is 2xx."""
        return 200 <= self.status_code < 300

    def raise_for_status(self) -> None:
        """Raise HTTPError if status is 4xx or 5xx."""
        if not self.is_success():
            raise HTTPError(self.status_code, f"HTTP {self.status_code} error")
```

**Design Notes**:

- `APIRequest`: Mirrors `requests.request()` parameters
- `APIResponse`: Normalized response regardless of method
- `json_data`: Pre-parsed JSON (None if not JSON response)

### 6. Configuration (config.py)

**Responsibility**: Centralize configuration with sensible defaults

```python
@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    retry_on_status_codes: tuple = (500, 502, 503, 504)

@dataclass
class RateLimitConfig:
    """Configuration for rate limit handling."""
    max_wait_time: float = 300.0  # seconds (5 minutes)
    respect_retry_after: bool = True
```

**Design Philosophy**:

- Dataclasses for immutability and clear defaults
- Conservative defaults (3 retries, 1s base delay)
- All timings in seconds (no milliseconds confusion)

## Interaction Flow

### Normal Request Flow

```
User → APIClient.get()
  ↓
APIClient.request() creates APIRequest
  ↓
RetryHandler.execute_with_retry()
  ↓
  Loop (max_retries + 1 times):
    ↓
    requests.request() → requests.Response
    ↓
    RateLimitHandler.is_rate_limited()?
    ├─ Yes → RateLimitHandler.handle_rate_limit()
    │         ├─ Sleep (if Retry-After acceptable)
    │         └─ Raise RateLimitError (if too long or missing)
    └─ No → Continue
    ↓
    RetryHandler.should_retry()?
    ├─ Yes → Sleep exponentially, continue loop
    └─ No → Convert to APIResponse, return
  ↓
If all retries exhausted → Raise RetryExhaustedError
```

### Error Flow

```
Network Error → RequestError
HTTP 429 (no Retry-After) → RateLimitError
HTTP 429 (with Retry-After > max_wait) → RateLimitError
HTTP 500-504 → Retry → Eventually RetryExhaustedError or Success
HTTP 4xx (not 429) → HTTPError (no retry)
HTTP 5xx (not 500-504) → HTTPError (no retry)
```

## Dependencies

### External

- `requests>=2.31.0` - HTTP library (only external dependency)

### Standard Library

- `dataclasses` - Data models and config
- `typing` - Type hints
- `logging` - Request/response logging
- `time` - Sleep for retries and rate limits
- `datetime` - Parse HTTP-date format in Retry-After
- `email.utils` - parsedate_to_datetime for HTTP-date

## Risks and Mitigations

### Risk 1: Infinite Retry Loops

**Mitigation**: Hard cap of max_retries with RetryExhaustedError

### Risk 2: Unbounded Wait Times

**Mitigation**: max_wait_time in RateLimitConfig (default 5 minutes)

### Risk 3: Thread Safety

**Mitigation**: APIClient is NOT thread-safe by design. Users must create separate instances per thread or add their own locking. Document this clearly.

### Risk 4: Memory Leaks from Large Responses

**Mitigation**: Store response body as string. Users handle streaming if needed. Document limitation.

### Risk 5: Timezone Issues in HTTP-date Parsing

**Mitigation**: Use email.utils.parsedate_to_datetime which handles RFC 2822 format correctly

## Test Requirements

### Unit Tests (60%)

- `test_retry.py`: RetryHandler logic, exponential backoff calculation
- `test_rate_limit.py`: RateLimitHandler detection, Retry-After parsing
- `test_exceptions.py`: Exception creation, inheritance
- `test_client.py`: APIClient method routing (mocked requests)

### Integration Tests (30%)

- `test_integration.py`: End-to-end flows with mock HTTP server
  - Successful request
  - Retry on 503
  - Rate limit with Retry-After
  - Max retries exhausted
  - Various HTTP errors

### Coverage Target

- 80%+ overall coverage
- 100% coverage on retry logic (critical)
- 100% coverage on rate limit parsing (critical)

## Implementation Notes

### Logging Strategy

```python
import logging

logger = logging.getLogger(__name__)

# Request start
logger.info(f"API Request: {method} {url}")

# Response
logger.info(f"API Response: {status_code} in {elapsed}s")

# Retry
logger.warning(f"Retrying request (attempt {attempt}/{max_retries}): {reason}")

# Rate limit
logger.warning(f"Rate limited. Waiting {delay}s (Retry-After header)")
```

### Type Hints

- All public methods fully typed
- Use `Optional[T]` for nullable parameters
- Use `Dict[str, Any]` for JSON data (no complex typing)

### Error Messages

- Include context: URL, method, status code
- Include original error message when wrapping exceptions
- Be actionable: "Rate limit exceeded. Retry after 300s" not "HTTP 429"

## Success Criteria

This module is complete when:

- [x] All 9 explicit requirements addressed
- [x] Public API defined via `__all__`
- [x] Each component has single clear responsibility
- [x] Request flow documented end-to-end
- [x] Error handling covers all scenarios
- [x] Test strategy defined (unit + integration)
- [x] Dependencies minimized (only requests)
- [x] Regeneratable from this spec

## Next Steps for Builder

1. Implement `exceptions.py` first (no dependencies)
2. Implement `config.py` second (uses exceptions)
3. Implement `models.py` third (uses exceptions)
4. Implement `retry.py` (uses config, exceptions, models)
5. Implement `rate_limit.py` (uses config, exceptions, models)
6. Implement `client.py` last (orchestrates everything)
7. Write tests in parallel with implementation
8. Create `examples/basic_usage.py` to demonstrate API

Each component can be built and tested independently following this order.
