# API Client Test Suite

Ahoy! This here be the comprehensive test suite fer the REST API Client library, written followin' TDD (Test-Driven Development) methodology.

## Test-Driven Development Approach

**CRITICAL**: These tests were written BEFORE the implementation code. They define the EXPECTED BEHAVIOR and act as the executable specification.

**TDD Workflow**:

1. **Write tests first** - Define behavior through tests (DONE ✓)
2. **Run tests** - All should FAIL (no implementation yet)
3. **Implement code** - Write minimal code to make tests pass
4. **Verify tests pass** - All tests should turn green
5. **Refactor** - Improve code while keeping tests green

## Test Organization

The test suite follows the **Testing Pyramid** principle:

- **60% Unit tests** - Fast, isolated, heavily mocked
- **30% Integration tests** - Multiple components working together
- **10% End-to-End tests** - Complete workflows

```
          /\
         /  \  E2E Tests (10%)
        /____\
       /      \
      / Integration \ (30%)
     /    Tests      \
    /__________________\
   /                    \
  /     Unit Tests       \ (60%)
 /________________________\
```

## Test Files

### 1. `conftest.py` - Test Fixtures

**Purpose**: Shared fixtures and test utilities

**Provides**:

- Valid/invalid URLs for testing
- Mock headers (valid and malicious)
- Mock JSON bodies
- Authentication tokens
- Rate limit headers
- SSRF test data (private IPs, localhost)

**Usage**:

```python
def test_example(valid_url, valid_headers):
    # Fixtures are automatically injected by pytest
    request = Request(url=valid_url, headers=valid_headers)
```

### 2. `test_models.py` - Request/Response Dataclasses

**Distribution**: 100% Unit tests (40 tests)

**Coverage**:

- Request creation (minimal, full, all HTTP methods)
- Response creation (all status codes, body types)
- Immutability (frozen dataclasses)
- Equality/inequality
- Edge cases (empty values, None, bytes)

**Key Tests**:

- `test_request_is_frozen` - Validates immutability
- `test_request_with_bytes_body` - Binary data support
- `test_response_preserves_original_request` - Request reference

### 3. `test_exceptions.py` - Exception Hierarchy

**Distribution**: 100% Unit tests (36 tests)

**Coverage**:

- APIError base exception with helper methods
- ClientError (4xx) inheritance and behavior
- ServerError (5xx) inheritance and behavior
- `is_timeout()` method (status 408)
- `is_rate_limited()` method (status 429)
- Exception hierarchy and catch order

**Key Tests**:

- `test_api_error_is_timeout_true` - Timeout detection
- `test_api_error_is_rate_limited_true` - Rate limit detection
- `test_exception_inheritance_chain` - Proper inheritance
- `test_catch_all_api_errors` - Exception polymorphism

### 4. `test_rate_limiter.py` - Token Bucket Rate Limiting

**Distribution**: 80% Unit / 20% Integration (35 tests)

**Coverage**:

- RateLimiter creation (defaults, custom rates, validation)
- Token acquisition (burst, throttling, enforcement)
- Thread safety (CRITICAL - concurrent access)
- Edge cases (idle refill, very low/high rates, fractional rates)
- Integration with realistic request patterns

**Key Tests**:

- `test_acquire_exceeding_burst_blocks` - Throttling works
- `test_thread_safe_concurrent_acquire` - Thread safety
- `test_acquire_after_long_idle` - Token refill
- `test_simulate_api_client_requests` - Realistic usage

**Performance Requirements**:

- All tests complete in <10 seconds
- Thread safety tests use real threads (not mocked)
- Timing tests allow tolerance for CI environments

### 5. `test_retry.py` - Exponential Backoff Retry

**Distribution**: 90% Unit / 10% Integration (30 tests)

**Coverage**:

- RetryPolicy creation (defaults, custom max_retries, validation)
- Retry decision logic (which status codes retry)
- Max retries enforcement
- Exponential backoff calculation (2^n with jitter)
- Edge cases (zero retries, high attempts, all 5xx codes)
- Integration with realistic retry sequences

**Key Tests**:

- `test_should_retry_on_500_error` - Retry on 5xx
- `test_should_not_retry_on_404_error` - No retry on 4xx
- `test_get_backoff_exponential_growth` - Exponential growth
- `test_retry_sequence_timing` - Complete retry workflow

**Backoff Requirements**:

- First retry: ~1s (with ±25% jitter)
- Second retry: ~2s
- Third retry: ~4s
- Jitter prevents thundering herd

### 6. `test_client.py` - HTTP Client with Security

**Distribution**: 70% Unit / 30% Integration (60+ tests)

**Coverage**:

- HTTPClient creation and configuration
- Input validation (URL, method, headers)
- **SSRF protection** (private IPs, localhost, allowed_hosts)
- **Header injection prevention** (CRLF attacks)
- Timeout enforcement (default, custom, per-request)
- Logging (with secret scrubbing for Authorization headers)
- Error handling (4xx ClientError, 5xx ServerError)
- Response parsing (JSON, text, bytes, empty)

**Security Tests** (MANDATORY - MUST PASS):

- `test_ssrf_blocks_private_ip` - Block 192.168.x.x
- `test_ssrf_blocks_localhost` - Block localhost/127.0.0.1
- `test_ssrf_blocks_10_network` - Block 10.0.0.0/8
- `test_ssrf_blocks_172_network` - Block 172.16.0.0/12
- `test_rejects_crlf_in_header_value` - Prevent header injection
- `test_logs_scrub_authorization_header` - No secrets in logs

**Key Tests**:

- `test_validate_url_rejects_empty_string` - Input validation
- `test_ssrf_allowed_hosts_blocks_mismatch` - Allowlist enforcement
- `test_raises_client_error_on_404` - Exception mapping
- `test_parses_json_response` - Response parsing

### 7. `test_integration.py` - Complete System Integration

**Distribution**: 100% Integration/E2E (20+ tests)

**Coverage**:

- Client + RateLimiter integration
- Client + RetryPolicy integration
- Client + RateLimiter + RetryPolicy together
- SSRF protection in real workflows
- End-to-end API workflows (CRUD operations)
- Realistic patterns (pagination, authentication, error recovery)

**E2E Tests** (Real-world scenarios):

- `test_realistic_api_workflow` - GET, POST, PUT, DELETE sequence
- `test_api_pagination_workflow` - Multi-page data fetching
- `test_complex_error_recovery` - Multiple retries with different errors
- `test_complete_configuration` - All options together

**Key Tests**:

- `test_rate_limiting_and_retry_work_together` - Components integrate
- `test_exhausts_retries_and_fails` - Retry limit enforcement
- `test_handle_rate_limit_response_429` - API rate limiting
- `test_multiple_requests_with_rate_limit_and_retry` - Real usage

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_models.py -v
pytest tests/test_client.py -v
pytest tests/test_integration.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_client.py::TestHTTPClientSSRFProtection -v
```

### Run Specific Test

```bash
pytest tests/test_client.py::TestHTTPClientSSRFProtection::test_ssrf_blocks_private_ip -v
```

### Run with Coverage Report

```bash
pytest tests/ --cov=api_client --cov-report=html
```

Open `htmlcov/index.html` to view detailed coverage report.

### Run Only Fast Tests (Skip Integration)

```bash
pytest tests/ -v -m "not integration"
```

### Run Only Integration Tests

```bash
pytest tests/test_integration.py -v
```

## Test Markers

Tests are marked by category:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, multiple components)
- `@pytest.mark.security` - Security-critical tests (MUST PASS)

## Expected Test Results (Before Implementation)

**ALL TESTS SHOULD FAIL** with `ModuleNotFoundError` or `ImportError` because the implementation doesn't exist yet!

Example expected failures:

```
FAILED test_models.py::TestRequestDataclass::test_create_minimal_request - ModuleNotFoundError: No module named 'api_client.models'
FAILED test_exceptions.py::TestAPIError::test_create_api_error_minimal - ModuleNotFoundError: No module named 'api_client.exceptions'
FAILED test_rate_limiter.py::TestRateLimiterCreation::test_create_rate_limiter_with_default - ModuleNotFoundError: No module named 'api_client.rate_limiter'
```

**This is GOOD!** It means tests are correctly written and waiting for implementation.

## Coverage Requirements

Target coverage goals:

- **Overall**: 100% line coverage, 100% branch coverage
- **models.py**: 100% (pure dataclasses, no conditionals)
- **exceptions.py**: 100% (simple classes, helper methods)
- **rate_limiter.py**: 95%+ (thread safety edge cases)
- **retry.py**: 95%+ (backoff randomization)
- **client.py**: 90%+ (main complexity, many branches)

## Dependencies

Test dependencies (install before running tests):

```bash
pip install pytest pytest-cov responses
```

- **pytest**: Test framework
- **pytest-cov**: Coverage reporting
- **responses**: HTTP response mocking library

## Test Execution Speed

Expected test execution times:

- **Unit tests**: <5 seconds total
- **Integration tests**: <15 seconds total (includes timing tests)
- **Complete suite**: <20 seconds total

If tests are slower, check:

- Are you using mocked HTTP responses? (Use `@responses.activate`)
- Are timing tests too strict? (Allow tolerance for CI)
- Are thread safety tests running correctly?

## Security Test Validation

**CRITICAL**: All security tests MUST pass before shipping:

1. **SSRF Protection**:
   - Blocks private IPs (10.x.x.x, 172.16.x.x, 192.168.x.x)
   - Blocks localhost/127.0.0.1
   - Enforces allowed_hosts when configured

2. **Header Injection**:
   - Rejects CRLF characters in header values
   - Prevents header injection attacks

3. **Secret Scrubbing**:
   - Authorization headers are redacted in logs
   - No secrets appear in error messages or logs

4. **Timeout Enforcement**:
   - Requests timeout as configured
   - No hanging requests

## Test Maintenance

When adding new features:

1. **Write tests first** (TDD!)
2. **Follow testing pyramid** (60/30/10 split)
3. **Add fixtures** to `conftest.py` for reusable test data
4. **Update this README** with new test descriptions
5. **Ensure coverage** doesn't drop below targets

When fixing bugs:

1. **Write failing test** that reproduces bug
2. **Fix implementation** to make test pass
3. **Verify** all other tests still pass

## Troubleshooting

### Tests Import Errors

If you see `ModuleNotFoundError: No module named 'api_client'`:

- **Before implementation**: This is EXPECTED! Tests are written first.
- **After implementation**: Check `PYTHONPATH` and ensure you're running from project root.

### Tests Hanging or Slow

- Check for missing `@responses.activate` decorator on HTTP tests
- Verify timeout values in timing tests aren't too long
- Look for actual network calls (should all be mocked)

### Thread Safety Tests Failing

- These tests use real threading and timing
- CI environments may be slower - allow tolerance in assertions
- Check for race conditions in test setup

### Coverage Not 100%

- Run with `--cov-report=html` to see uncovered lines
- Check for defensive code (error handling) that's hard to trigger
- Verify all branches (if/else) are tested

## Questions?

Read the tests! They're the executable specification. If behavior is unclear, the tests define the truth.

---

**Remember**: These tests define WHAT the code should do. The implementation defines HOW it does it. Tests come first!

Arr, may yer tests always be green! ⚓
