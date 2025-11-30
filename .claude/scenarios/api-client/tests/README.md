# REST API Client Tests - TDD Approach

## Overview

This test suite follows Test-Driven Development (TDD) methodology and the 60-30-10 testing pyramid for comprehensive coverage of the REST API Client.

## Test Structure

```
tests/
├── __init__.py              # Test package marker
├── conftest.py              # Pytest fixtures and configuration
├── mock_server.py           # Mock HTTP server for integration tests
├── run_tests.py             # Test runner with TDD verification
├── test_client.py           # Unit tests for RESTClient (60%)
├── test_rate_limiting.py    # Rate limiting unit tests
├── test_retry.py            # Retry logic unit tests
└── test_integration.py      # Integration & E2E tests (30% + 10%)
```

## Testing Pyramid Distribution

Following the 60-30-10 testing pyramid principle:

### 60% Unit Tests

- **test_client.py**: Core RESTClient functionality
  - Initialization and configuration
  - Response dataclass and json() method
  - HTTP methods (GET, POST, PUT, DELETE, PATCH)
  - URL handling and query parameters
  - Header management
  - Basic error handling

- **test_rate_limiting.py**: Time-based rate limiting
  - Basic rate limiting enforcement
  - Requests per second timing
  - Thread safety
  - Different HTTP methods
  - Edge cases (fractional rates, disabled)

- **test_retry.py**: Exponential backoff retry
  - Retry on connection errors
  - Retry on 5xx errors
  - No retry on 4xx errors
  - Exponential backoff calculation (2^attempt)
  - Max retries enforcement

### 30% Integration Tests

- **test_integration.py**: Client with mock server
  - Real HTTP server interaction
  - Request/response verification
  - Concurrent requests
  - Rate limiting with server
  - Retry with flakey server

### 10% End-to-End Tests

- **test_integration.py**: Complete workflows
  - CRUD operations workflow
  - Pagination workflow
  - Authentication workflow
  - Batch processing workflow

## TDD Workflow

1. **Write Tests First** ✅ (Completed)
   - All tests written before implementation
   - Tests currently fail as expected (no api_client module)

2. **Implement Minimal Code** (Next Step)
   - Create api_client.py with RESTClient and Response
   - Implement just enough to make tests pass

3. **Refactor** (Final Step)
   - Improve code while keeping tests green
   - Optimize performance and readability

## Running Tests

### Verify TDD (Tests Should Fail)

```bash
python run_tests.py
```

Expected output: Import errors for api_client module (this is correct for TDD)

### Run with pytest (After Implementation)

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run with coverage
pytest --cov=api_client

# Run specific test file
pytest tests/test_client.py
```

### Run with unittest (After Implementation)

```bash
# Run all tests
python -m unittest discover tests

# Run specific test
python -m unittest tests.test_client.TestRESTClientInitialization
```

## Mock Server

The test suite includes a custom mock HTTP server (`mock_server.py`) with:

- **MockHTTPServer**: Basic HTTP server for testing
- **RateLimitingMockServer**: Simulates 429 rate limiting
- **FlakeyMockServer**: Simulates intermittent failures

Features:

- Request recording and verification
- Response queuing
- Custom status codes
- Configurable delays
- Thread-safe operation

## Key Test Scenarios

### Unit Test Coverage

- Client initialization with all parameters
- Response parsing (JSON, text)
- HTTP method implementations
- URL construction and parameters
- Header merging
- Rate limit calculations
- Retry delay calculations
- Error handling

### Integration Test Coverage

- Real HTTP communication
- Server request validation
- Concurrent request handling
- Rate limiting prevention of 429 errors
- Retry recovery from failures

### End-to-End Coverage

- Complete CRUD workflow
- Multi-page pagination
- Authentication and tokens
- Batch processing with rate limits

## Test Fixtures (pytest)

Available fixtures in `conftest.py`:

- `mock_server`: Session-scoped mock HTTP server
- `clean_mock_server`: Function-scoped reset server
- `rate_limiting_server`: Server with rate limiting
- `flakey_server`: Server with intermittent failures
- `sample_json_data`: Test JSON data
- `sample_headers`: Test HTTP headers
- `sample_query_params`: Test query parameters

## Expected Implementation

Based on the tests, the implementation should provide:

```python
# api_client.py

@dataclass
class Response:
    status_code: int
    headers: Dict[str, str]
    body: bytes
    url: str

    def json(self) -> Dict[str, Any]:
        """Parse body as JSON"""
        pass

    @property
    def text(self) -> str:
        """Get body as text"""
        pass


class RESTClient:
    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = 30,
        requests_per_second: Optional[float] = None,
        max_retries: int = 3
    ):
        """Initialize REST client with configuration"""
        pass

    def get(self, path: str, **kwargs) -> Response:
        """GET request"""
        pass

    def post(self, path: str, **kwargs) -> Response:
        """POST request"""
        pass

    def put(self, path: str, **kwargs) -> Response:
        """PUT request"""
        pass

    def delete(self, path: str, **kwargs) -> Response:
        """DELETE request"""
        pass

    def patch(self, path: str, **kwargs) -> Response:
        """PATCH request"""
        pass
```

## Success Criteria

All tests should pass when the implementation:

1. Uses only standard library (urllib)
2. Implements time-based rate limiting
3. Implements exponential backoff retry (2^attempt seconds)
4. Handles all HTTP methods
5. Properly manages headers and parameters
6. Returns Response dataclass with json() method
7. Retries on connection errors and 5xx status codes
8. Does not retry on 4xx client errors
