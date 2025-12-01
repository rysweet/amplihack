# REST API Client Test Suite

## Overview

Comprehensive test suite fer the REST API Client module followin' TDD methodology and the testin' pyramid principle (60% unit, 30% integration, 10% E2E).

## Test Structure

```
amplihack/api_client/tests/
├── TEST_SPECIFICATION.md     # This file
├── __init__.py
├── test_exceptions.py         # Exception hierarchy tests (Unit)
├── test_models.py             # Data model tests (Unit)
├── test_retry.py              # Retry logic tests (Unit)
├── test_client.py             # API client tests (Unit)
└── test_integration.py        # Integration and E2E tests
```

## Test Coverage by Module

### 1. Exception Tests (`test_exceptions.py`)

**Coverage**: Exception hierarchy, factory functions, context attributes

**Tests** (~8 unit tests):

- Exception hierarchy verification (APIError base)
- ClientError subclasses (400, 401, 403, 404, 429)
- ServerError subclasses (500, 502, 503, 504)
- NetworkError and TimeoutError creation
- `create_exception_for_status()` factory function
- Exception context attributes (message, status_code, request, response)

**Key Scenarios**:

- Proper inheritance chain
- Correct exception type fer each status code
- Context preservation across exceptions

### 2. Model Tests (`test_models.py`)

**Coverage**: Request/Response dataclasses, validation, helper methods

**Tests** (~10 unit tests):

- APIRequest dataclass instantiation
- APIRequest validation (required fields)
- APIResponse dataclass creation
- `is_success()` method (2xx responses)
- `is_client_error()` method (4xx responses)
- `is_server_error()` method (5xx responses)
- `is_rate_limited()` method (429 detection)
- `json()` parsing with valid/invalid JSON
- `raise_for_status()` exception raising
- `get_retry_after()` header extraction
- `to_dict()` fer logging (sensitive data redaction)

**Key Scenarios**:

- Valid and invalid dataclass instantiation
- Status code range detection
- JSON parsing error handling
- Retry-After header parsing (seconds and HTTP date)

### 3. Retry Logic Tests (`test_retry.py`)

**Coverage**: Retry configuration, backoff strategies, retry decisions

**Tests** (~10 unit tests):

- RetryConfig dataclass defaults
- RetryStrategy enum values (EXPONENTIAL, LINEAR)
- `calculate_delay()` fer exponential backoff
- `calculate_delay()` fer linear backoff
- `calculate_delay()` with max_delay capping
- `calculate_delay()` with jitter application
- `should_retry()` logic (5xx → retry, 4xx → no retry)
- `should_retry()` fer 429 (rate limiting → retry)
- `should_retry()` respects max_attempts
- Retry delay calculation with attempt number

**Key Scenarios**:

- Exponential backoff: 1s → 2s → 4s → 8s
- Linear backoff: 1s → 2s → 3s → 4s
- Max delay prevents excessive waits
- Jitter adds randomness to prevent thundering herd
- 5xx errors trigger retry, 4xx don't (except 429)

### 4. API Client Tests (`test_client.py`)

**Coverage**: HTTP methods, retry integration, logging, configuration

**Tests** (~8 unit tests):

- APIClient initialization with defaults
- GET request implementation
- POST request with body
- PUT request with body
- DELETE request
- PATCH request with body
- Retry logic integration (mock 3 attempts)
- Rate limiting detection
- Exception raising on errors
- Logging sanitization (Authorization header redacted)
- Timeout configuration
- Context manager protocol (`__enter__` / `__exit__`)

**Key Scenarios**:

- All HTTP methods work correctly
- Retry happens automatically on 5xx
- Rate limiting triggers appropriate delays
- Sensitive headers never logged
- Client works as context manager

### 5. Integration Tests (`test_integration.py`)

**Coverage**: Complete request/response flows with mock HTTP server

**Integration Tests** (~18 tests - 30%):

- Successful GET request end-to-end
- Successful POST with JSON body
- Retry on 500 error (verify 3 attempts)
- Retry with exponential backoff timing
- Rate limiting with Retry-After: seconds
- Rate limiting with Retry-After: HTTP date
- Rate limiting without Retry-After (fallback backoff)
- ClientError exceptions fer 4xx responses
- ServerError exceptions fer 5xx responses
- NetworkError on connection failure
- TimeoutError on request timeout
- Request/response logging
- Multiple requests in sequence
- Concurrent requests handling

**E2E Tests** (~6 tests - 10%):

- Complete workflow: auth → request → retry → success
- Complete workflow: rate limit → wait → retry → success
- Complete workflow: multiple failures → exhaustion → error
- Complete workflow: timeout → retry → success
- Complete workflow: network error → retry → success
- Complex multi-step API interaction

**Key Scenarios**:

- httpretty mocks HTTP responses
- Timing verification fer backoff delays
- Header parsing (Retry-After)
- Exception types match status codes
- Complete workflows from start to finish

## Testing Approach

### Unit Tests (60%)

**Strategy**: Fast, isolated, heavily mocked

- Mock external dependencies (requests library)
- Test individual functions and methods
- Verify logic without network calls
- Run in milliseconds

**Tools**:

- `pytest` framework
- `unittest.mock` fer mocking
- `@pytest.mark.parametrize` fer data-driven tests

### Integration Tests (30%)

**Strategy**: Multiple components, mock HTTP server

- httpretty mocks HTTP responses
- Test component interactions
- Verify retry/rate limiting behavior
- Test timing and delays

**Tools**:

- `pytest` framework
- `httpretty` fer HTTP mocking
- `time.time()` fer timing verification

### E2E Tests (10%)

**Strategy**: Complete workflows, realistic scenarios

- End-to-end user flows
- Multiple operations in sequence
- Real-world usage patterns
- Comprehensive error paths

**Tools**:

- `pytest` framework
- `httpretty` fer HTTP mocking
- Scenario-based test cases

## Test Quality Standards

### All Tests Must:

1. **Follow AAA Pattern**:
   - Arrange: Setup test data and mocks
   - Act: Execute the code under test
   - Assert: Verify expected behavior

2. **Have Clear Docstrings**:
   - Explain what is being tested
   - Describe the expected behavior
   - Note any special conditions

3. **Be Fast**:
   - Total suite runs in < 5 seconds
   - Unit tests < 100ms each
   - Integration tests < 500ms each

4. **Be Isolated**:
   - No test dependencies
   - No shared state between tests
   - Each test can run independently

5. **Pass Type Checking**:
   - All tests pass `mypy --strict`
   - Type hints throughout
   - No `type: ignore` comments

6. **Be Deterministic**:
   - Same input → same result
   - No random failures
   - Reliable CI execution

## Running the Tests

```bash
# Run all tests
pytest amplihack/api_client/tests/

# Run specific test file
pytest amplihack/api_client/tests/test_retry.py

# Run with coverage
pytest --cov=amplihack.api_client amplihack/api_client/tests/

# Run with type checking
mypy --strict amplihack/api_client/tests/

# Run pre-commit hooks
pre-commit run --all-files
```

## Expected Behavior (TDD)

**Initial State**: All tests FAIL (no implementation exists)

**After Implementation**: All tests PASS

This verifies that:

1. Tests accurately describe requirements
2. Implementation matches specifications
3. TDD cycle is complete (Red → Green → Refactor)

## Test Metrics

**Target Coverage**:

- Line coverage: > 95%
- Branch coverage: > 90%
- Function coverage: 100%

**Performance**:

- Total test execution: < 5 seconds
- Unit tests: < 2 seconds
- Integration tests: < 2.5 seconds
- E2E tests: < 0.5 seconds

**Test Count**:

- Total: ~60 tests
- Unit: ~36 tests (60%)
- Integration: ~18 tests (30%)
- E2E: ~6 tests (10%)
