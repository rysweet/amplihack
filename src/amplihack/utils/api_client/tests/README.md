# REST API Client Tests

Comprehensive test suite for the REST API Client module following Test-Driven Development (TDD) principles.

## Overview

These tests are written **BEFORE** the implementation (TDD approach) and cover all 9 explicit requirements:

1. ✓ APIClient class with GET, POST, PUT, DELETE methods
2. ✓ Retry logic with exponential backoff
3. ✓ Rate limiting (429 handling)
4. ✓ Custom exception hierarchy
5. ✓ Request/response dataclasses
6. ✓ Integration tests with mock server
7. ✓ Comprehensive error handling
8. ✓ Logging verification
9. ✓ Type hints (verified separately via mypy)

## Test Structure

### Unit Tests (60% of test suite)

#### `test_client.py` - Core APIClient Functionality

- Basic HTTP operations (GET, POST, PUT, DELETE)
- Request/response dataclass usage
- Error handling for HTTP status codes
- Client configuration options
- Logging verification
- Base URL handling

**Coverage**: ~150 tests

#### `test_retry.py` - Retry Logic

- Exponential backoff timing calculations
- Max retries enforcement
- Retry on appropriate status codes (500, 502, 503, 504)
- No retry on client errors (4xx except 429)
- RetryExhaustedError scenarios
- Custom retry configurations
- Network error retry behavior

**Coverage**: ~80 tests

#### `test_rate_limit.py` - Rate Limiting

- HTTP 429 detection
- Retry-After header parsing (seconds and HTTP-date formats)
- Max wait time bounds enforcement
- Default backoff behavior
- RateLimitError scenarios
- Rate limit logging
- Security bounds

**Coverage**: ~70 tests

#### `test_exceptions.py` - Exception Hierarchy

- Exception inheritance chain
- All exceptions can be raised and caught
- Exception attributes and messages
- Exception catching patterns
- Multiple except blocks
- Error message formatting

**Coverage**: ~60 tests

#### `test_security.py` - Security Features

- URL validation (reject file://, javascript:, etc.)
- Header injection prevention
- Credential logging prevention
- SSL/TLS enforcement
- Parameter validation
- Rate limit security bounds
- Timeout security
- Error message sanitization

**Coverage**: ~70 tests

### Integration Tests (30% of test suite)

#### `test_integration.py` - Integration Scenarios

- End-to-end request flows
- Combined retry + rate limiting
- Authentication integration
- Real-world error scenarios
- Pagination patterns
- Batch operations
- Complex workflows
- APIRequest dataclass integration

**Coverage**: ~50 tests

### Test Distribution

```
Total Tests: ~480
├── Unit Tests (60%): ~290 tests
│   ├── test_client.py: ~150 tests
│   ├── test_retry.py: ~80 tests
│   ├── test_rate_limit.py: ~70 tests
│   ├── test_exceptions.py: ~60 tests
│   └── test_security.py: ~70 tests
└── Integration Tests (40%): ~190 tests
    └── test_integration.py: ~190 tests
```

## Running Tests

### Run All Tests

```bash
pytest src/amplihack/utils/api_client/tests/ -v
```

### Run Specific Test File

```bash
pytest src/amplihack/utils/api_client/tests/test_client.py -v
pytest src/amplihack/utils/api_client/tests/test_retry.py -v
pytest src/amplihack/utils/api_client/tests/test_rate_limit.py -v
pytest src/amplihack/utils/api_client/tests/test_exceptions.py -v
pytest src/amplihack/utils/api_client/tests/test_security.py -v
pytest src/amplihack/utils/api_client/tests/test_integration.py -v
```

### Run Tests by Category

```bash
# Unit tests only (fast)
pytest src/amplihack/utils/api_client/tests/ -m unit

# Integration tests only
pytest src/amplihack/utils/api_client/tests/ -m integration

# All except slow tests
pytest src/amplihack/utils/api_client/tests/ -m "not slow"
```

### Run with Coverage

```bash
pytest src/amplihack/utils/api_client/tests/ --cov=amplihack.utils.api_client --cov-report=html
```

### Run Specific Test

```bash
pytest src/amplihack/utils/api_client/tests/test_client.py::TestAPIClientBasicOperations::test_successful_get_request -v
```

## Test Markers

Tests are automatically marked based on their location:

- `@pytest.mark.unit` - Unit tests (fast, heavily mocked)
- `@pytest.mark.integration` - Integration tests (multiple components)
- `@pytest.mark.e2e` - End-to-end tests (complete workflows)
- `@pytest.mark.slow` - Slow running tests (>1 second)
- `@pytest.mark.network` - Tests involving network operations

## Testing Philosophy

### TDD Approach

All tests are written BEFORE implementation:

1. Write failing tests that define expected behavior
2. Run tests to verify they fail (red)
3. Implement minimal code to make tests pass (green)
4. Refactor while keeping tests passing (refactor)

### Testing Pyramid

Follow the testing pyramid for optimal coverage:

- **60% Unit Tests**: Fast, isolated, heavily mocked
- **30% Integration Tests**: Multiple components working together
- **10% E2E Tests**: Complete user workflows

### Test Quality

Each test follows AAA pattern:

- **Arrange**: Set up test data and mocks
- **Act**: Execute the code under test
- **Assert**: Verify expected outcomes

### Mocking Strategy

- Use `responses` library for HTTP request mocking
- Use `unittest.mock.patch` for time and logging mocks
- Mock at appropriate boundaries
- Avoid over-mocking (test real behavior where possible)

## Expected Test Results (Before Implementation)

Since tests are written BEFORE implementation, all tests will FAIL initially:

```
======================== FAILURES =========================
test_client.py::test_successful_get_request - ImportError: cannot import name 'APIClient'
test_retry.py::test_exponential_backoff_delays - ImportError: cannot import name 'RetryConfig'
test_rate_limit.py::test_429_raises_rate_limit_error - ImportError: cannot import name 'RateLimitError'
... (all tests fail because implementation doesn't exist yet)
```

This is EXPECTED and CORRECT for TDD! Once implementation is complete, all tests should pass.

## Test Coverage Goals

Target coverage metrics:

- **Line Coverage**: 80%+
- **Branch Coverage**: 75%+
- **Function Coverage**: 90%+

Critical areas requiring 100% coverage:

- Exception handling
- Retry logic calculations
- Rate limit parsing
- Security validation

## Dependencies

Required test dependencies:

```
pytest>=7.0.0
responses>=0.23.0
pytest-cov>=4.0.0
```

Install with:

```bash
pip install pytest responses pytest-cov
```

## Test Fixtures

Common fixtures are defined in `conftest.py`:

- `caplog_info` - Capture INFO level logs
- `caplog_debug` - Capture DEBUG level logs
- `caplog_warning` - Capture WARNING level logs
- `sample_api_response` - Sample API response data
- `sample_error_response` - Sample error response data
- `mock_base_url` - Consistent mock base URL

## Troubleshooting

### Tests are all failing

**Expected behavior!** In TDD, tests fail before implementation. This verifies tests are actually testing something.

### Import errors

Tests expect the following imports to work:

```python
from amplihack.utils.api_client import (
    APIClient,
    APIRequest,
    APIResponse,
    RetryConfig,
    RateLimitConfig,
    APIClientError,
    RequestError,
    HTTPError,
    RateLimitError,
    RetryExhaustedError,
    ResponseError,
)
```

Once implementation is complete, these imports will work.

### Mock not working

Ensure `responses` library is installed:

```bash
pip install responses
```

### Logging tests failing

Ensure using `caplog` fixture:

```python
def test_logging(caplog):
    with caplog.at_level(logging.INFO):
        # ... test code ...
    assert "expected message" in caplog.text
```

## Next Steps

1. **Verify tests fail** - Run tests to confirm they all fail (TDD red phase)
2. **Implement APIClient** - Build the implementation to make tests pass
3. **Run tests iteratively** - Watch tests turn green as you implement
4. **Refactor** - Improve code while keeping tests green
5. **Add edge cases** - Add more tests for discovered edge cases

## Contributing

When adding new tests:

1. Follow AAA pattern (Arrange, Act, Assert)
2. Use descriptive test names
3. Add docstrings explaining what is tested
4. Mock external dependencies
5. Keep tests independent and idempotent
6. Add appropriate markers (`@pytest.mark.unit`, etc.)

## References

- [pytest documentation](https://docs.pytest.org/)
- [responses library](https://github.com/getsentry/responses)
- [TDD by Example](https://www.amazon.com/Test-Driven-Development-Kent-Beck/dp/0321146530)
- [Testing Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
