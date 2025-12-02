## REST API Client Module

Self-contained HTTP API client with retry logic and rate limiting.

### Philosophy

- **Ruthless Simplicity**: Direct, clear implementation using `requests` library
- **Brick Design**: Self-contained module with well-defined public API
- **Zero-BS**: No stubs, placeholders, or unimplemented functions
- **Standard Library**: Minimal dependencies (Python stdlib + `requests` only)

### Features

- ✅ **Retry Logic**: Automatic retries with exponential backoff
- ✅ **Rate Limiting**: Thread-safe token bucket rate limiting
- ✅ **Error Handling**: Comprehensive exception hierarchy
- ✅ **Type Hints**: Full type annotations for mypy compliance
- ✅ **Logging**: Structured logging for debugging
- ✅ **Context Manager**: Clean resource management
- ✅ **Immutable Models**: Request/Response dataclasses

### Installation

```bash
# Install from local module
pip install -e ./api_client

# Or install dependencies directly
pip install requests
```

### Quick Start

```python
from api_client import APIClient, Request

# Create client
client = APIClient(base_url="https://api.example.com")

# Make request
request = Request(method="GET", endpoint="/users")
response = client.send(request)

print(f"Status: {response.status_code}")
print(f"Data: {response.data}")

client.close()
```

### Basic Usage

#### Simple GET Request

```python
from api_client import APIClient, Request

with APIClient(base_url="https://api.example.com") as client:
    request = Request(method="GET", endpoint="/users/123")
    response = client.send(request)

    if response.is_success:
        print(f"User: {response.data}")
```

#### POST Request with Data

```python
request = Request(
    method="POST",
    endpoint="/users",
    data={"name": "Alice", "email": "alice@example.com"}
)

response = client.send(request)
print(f"Created user ID: {response.data['id']}")
```

#### Request with Headers and Query Parameters

```python
request = Request(
    method="GET",
    endpoint="/search",
    params={"q": "python", "limit": "10"},
    headers={"Authorization": "Bearer token"}
)

response = client.send(request)
```

### Advanced Features

#### Retry Logic

```python
from api_client import APIClient, RetryHandler

# Configure retry behavior
retry_handler = RetryHandler(
    max_retries=3,      # Retry up to 3 times
    base_delay=1.0,     # Start with 1 second delay
    multiplier=2.0,     # Double delay each retry
    max_delay=10.0      # Cap delay at 10 seconds
)

client = APIClient(
    base_url="https://api.example.com",
    retry_handler=retry_handler
)

# Automatic retries on transient failures
response = client.send(request)
```

**Retry Delays**:

- Attempt 1: 1.0s delay
- Attempt 2: 2.0s delay
- Attempt 3: 4.0s delay
- Attempt 4: 8.0s delay (capped at max_delay if configured)

#### Rate Limiting

```python
from api_client import APIClient, RateLimiter

# Configure rate limiter (10 requests per minute)
limiter = RateLimiter(
    max_requests=10,
    time_window=60.0
)

client = APIClient(
    base_url="https://api.example.com",
    rate_limiter=limiter
)

# Requests automatically throttled to respect limit
for i in range(20):
    response = client.send(request)
    # First 10 are fast, next 10 are throttled
```

#### Error Handling

```python
from api_client import APIClient, Request
from api_client.exceptions import (
    RequestError,
    ResponseError,
    RateLimitError,
    RetryExhaustedError
)

with APIClient(base_url="https://api.example.com") as client:
    try:
        response = client.send(request)

    except RequestError as e:
        # Network/connection errors
        print(f"Request failed: {e}")
        print(f"Endpoint: {e.context.get('endpoint')}")

    except ResponseError as e:
        # HTTP error status codes
        print(f"Response error: {e}")
        print(f"Status: {e.context.get('status_code')}")

    except RateLimitError as e:
        # Rate limit exceeded (429)
        print(f"Rate limited: {e}")
        print(f"Retry after: {e.context.get('retry_after')}s")

    except RetryExhaustedError as e:
        # All retries failed
        print(f"Retries exhausted: {e}")
        print(f"Attempts: {e.context.get('attempts')}")
```

### Public API

#### Core Classes

- **`APIClient`**: Main HTTP client
- **`Request`**: Immutable request data model
- **`Response`**: Immutable response data model
- **`RateLimiter`**: Thread-safe rate limiter
- **`RetryHandler`**: Retry logic with exponential backoff

#### Exceptions

- **`APIError`**: Base exception for all API errors
- **`RequestError`**: Request failed (network/connection)
- **`ResponseError`**: HTTP error response (4xx/5xx)
- **`RateLimitError`**: Rate limit exceeded (429)
- **`RetryExhaustedError`**: All retry attempts failed

### Architecture

```
api_client/
├── __init__.py         # Public API exports
├── client.py           # APIClient implementation
├── models.py           # Request/Response dataclasses
├── exceptions.py       # Exception hierarchy
├── retry.py            # RetryHandler
├── rate_limiter.py     # RateLimiter
├── tests/              # Test suite
│   ├── conftest.py     # Test fixtures
│   ├── test_*.py       # Unit/integration tests
└── examples/           # Usage examples
    ├── basic_usage.py
    ├── retry_example.py
    └── rate_limit_example.py
```

### Testing

```bash
# Run all tests
pytest api_client/tests/

# Run with coverage
pytest api_client/tests/ --cov=api_client --cov-report=html

# Run specific test categories
pytest api_client/tests/test_client.py          # Unit tests
pytest api_client/tests/test_integration.py     # Integration tests
```

**Test Coverage**: >80% line coverage

**Testing Pyramid**:

- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (mock HTTP server)

### Examples

Run the provided examples:

```bash
# Basic usage examples
python api_client/examples/basic_usage.py

# Retry logic examples
python api_client/examples/retry_example.py

# Rate limiting examples
python api_client/examples/rate_limit_example.py
```

### Design Decisions

#### Why `requests` Library?

- Battle-tested, widely used HTTP library
- Simple, intuitive API
- Comprehensive feature set
- No need to reinvent HTTP handling

#### Why Dataclasses for Models?

- Immutable by design (frozen=True)
- Built-in validation via `__post_init__`
- Clear structure with type hints
- No heavy ORM overhead

#### Why Token Bucket for Rate Limiting?

- Simple to understand and implement
- Allows natural burst behavior
- Thread-safe with minimal locking
- Industry-standard algorithm

#### Why Exponential Backoff?

- Proven strategy for transient failures
- Reduces server load during incidents
- Configurable to match API requirements
- Standard retry pattern

### Limitations

- **Not async**: Uses synchronous `requests` library
- **No connection pooling config**: Uses `requests.Session` defaults
- **Basic auth only**: No OAuth, JWT, etc. (add as headers)
- **JSON only**: Optimized for JSON APIs (raw text available)

### Philosophy Compliance

✅ **Ruthless Simplicity**: No unnecessary abstractions
✅ **Modular Design**: Self-contained brick with clear API
✅ **Zero-BS**: Every function works, no placeholders
✅ **Standard Library**: Minimal external dependencies
✅ **Type Safety**: Full type hints throughout
✅ **Testability**: Comprehensive test coverage

### License

Part of amplihack framework.

### Support

See examples directory for usage patterns.
See tests directory for behavior specifications.
