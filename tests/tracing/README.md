# Native Binary Trace Logging Tests

Comprehensive failing tests for the native binary migration with optional trace logging feature.
Written following TDD (Test-Driven Development) principles.

## Test Coverage Summary

Following the testing pyramid principle (60% unit, 30% integration, 10% E2E):

### Unit Tests (60%)

1. **test_trace_logger.py** - TraceLogger module
   - JSONL formatting and writing (12 tests)
   - Token sanitization integration (6 tests)
   - Performance requirements (3 tests)
   - Context manager lifecycle (5 tests)
   - Edge cases and error handling (11 tests)
   - Configuration (3 tests)
   - **Total: 40 unit tests**

2. **test_binary_manager.py** - ClaudeBinaryManager module
   - Binary detection (rustyclawd, claude-cli) (6 tests)
   - BinaryInfo dataclass (2 tests)
   - Command building with trace flags (7 tests)
   - Version detection (4 tests)
   - Trace support detection (3 tests)
   - Error handling (2 tests)
   - Environment configuration (2 tests)
   - Fallback behavior (2 tests)
   - Platform-specific (2 tests)
   - Caching (2 tests)
   - **Total: 32 unit tests**

3. **test_litellm_callbacks.py** - LiteLLM callbacks
   - Callback registration/unregistration (6 tests)
   - TraceCallback class (2 tests)
   - Lifecycle events (4 tests)
   - Data logging (3 tests)
   - Token sanitization (3 tests)
   - Performance (3 tests)
   - Error handling (4 tests)
   - Streaming support (2 tests)
   - Integration (2 tests)
   - Configuration (2 tests)
   - **Total: 31 unit tests**

**Unit Tests Total: 103 tests (~60%)**

### Integration Tests (30%)

4. **test_integration.py** - Component integration
   - Launcher integration (5 tests)
   - LiteLLM integration (3 tests)
   - Configuration integration (2 tests)
   - Error handling integration (2 tests)
   - Performance integration (1 test)
   - Concurrent access (1 test)
   - Prerequisites integration (2 tests)
   - Cleanup integration (1 test)
   - Cross-component data flow (2 tests)
   - **Total: 19 integration tests**

5. **test_prerequisites_integration.py** - Prerequisites integration
   - Native binary detection (5 tests)
   - Prerequisite result enhancement (2 tests)
   - Installation guidance (2 tests)
   - Platform-specific detection (1 test)
   - Error handling (2 tests)
   - Check all prerequisites (2 tests)
   - Interactive installer integration (2 tests)
   - Fallback behavior (2 tests)
   - **Total: 18 integration tests**

**Integration Tests Total: 37 tests (~30%)**

### E2E Tests (10%)

6. **test_e2e.py** - End-to-end workflows
   - Full workflow tests (2 tests)
   - Multi-request session (1 test)
   - Streaming request (1 test)
   - Error handling E2E (1 test)
   - Real-world scenarios (3 tests)
   - Performance E2E (2 tests)
   - File format validation (2 tests)
   - Cleanup and resource management (2 tests)
   - CLI integration (2 tests)
   - **Total: 16 E2E tests**

**E2E Tests Total: 16 tests (~10%)**

## Grand Total: 156 Tests

- Unit: 103 (66%)
- Integration: 37 (24%)
- E2E: 16 (10%)

## Performance Requirements Tested

All tests validate these performance requirements:

1. **Disabled overhead**: < 0.1ms per log (100μs)
   - `test_disabled_overhead_under_100_microseconds()`
   - `test_performance_no_sanitization_overhead_when_disabled()`

2. **Enabled overhead**: < 10ms per log
   - `test_enabled_overhead_under_10_milliseconds()`
   - `test_high_throughput_scenario()`

3. **Callback overhead**: < 5ms per call
   - `test_callback_overhead_under_5_milliseconds()`
   - `test_callback_async_logging_performance()`

4. **End-to-end overhead**: < 20ms per complete cycle
   - `test_end_to_end_trace_overhead()`

## Security Requirements Tested

All tests validate security through TokenSanitizer:

1. **API key sanitization**
   - `test_log_sanitizes_api_keys()`
   - `test_callback_sanitizes_api_keys()`
   - `test_security_audit_scenario()`

2. **Bearer token sanitization**
   - `test_log_sanitizes_bearer_tokens()`
   - `test_callback_sanitizes_auth_headers()`

3. **GitHub token sanitization**
   - `test_log_sanitizes_github_tokens()`

4. **Nested credential sanitization**
   - `test_log_sanitizes_nested_credentials()`
   - `test_callback_sanitizes_nested_credentials()`

## Running Tests

### Run all tests

```bash
pytest tests/tracing/
```

### Run by category

```bash
# Unit tests only
pytest tests/tracing/test_trace_logger.py
pytest tests/tracing/test_binary_manager.py
pytest tests/tracing/test_litellm_callbacks.py

# Integration tests only
pytest tests/tracing/test_integration.py
pytest tests/tracing/test_prerequisites_integration.py

# E2E tests only
pytest tests/tracing/test_e2e.py
```

### Run by marker

```bash
# Performance tests
pytest tests/tracing/ -m performance

# Integration tests
pytest tests/tracing/ -m integration

# E2E tests
pytest tests/tracing/ -m e2e
```

### Run with coverage

```bash
pytest tests/tracing/ --cov=amplihack.tracing --cov=amplihack.launcher.claude_binary_manager --cov=amplihack.proxy.litellm_callbacks --cov-report=html
```

## Test Status: FAILING (Expected)

All tests are currently **FAILING** as expected for TDD approach. These tests define the requirements
and will pass once the implementation is complete.

### Expected Failures

```
ModuleNotFoundError: No module named 'amplihack.tracing'
ModuleNotFoundError: No module named 'amplihack.launcher.claude_binary_manager'
AttributeError: module 'amplihack.proxy' has no attribute 'litellm_callbacks'
```

## Implementation Order

Based on test dependencies, implement in this order:

1. **TraceLogger** (`src/amplihack/tracing/trace_logger.py`)
   - JSONL logging
   - TokenSanitizer integration
   - Context manager support
   - Environment configuration

2. **ClaudeBinaryManager** (`src/amplihack/launcher/claude_binary_manager.py`)
   - Binary detection
   - Command building
   - Trace flag injection
   - Version/support detection

3. **LiteLLM Callbacks** (`src/amplihack/proxy/litellm_callbacks.py`)
   - Callback registration
   - TraceLogger integration
   - Lifecycle event handlers
   - Error handling

4. **Launcher Integration** (`src/amplihack/launcher/core.py`)
   - Binary manager integration
   - Trace initialization
   - Callback registration
   - Configuration management

5. **Prerequisites Integration** (`src/amplihack/utils/prerequisites.py`)
   - Native binary detection
   - Trace support reporting
   - Installation guidance

## Test Quality Checklist

- [x] Tests are independent (no shared state)
- [x] Tests are deterministic (no random values)
- [x] Tests are fast (unit tests < 100ms)
- [x] Tests have clear names describing what they test
- [x] Tests follow AAA pattern (Arrange, Act, Assert)
- [x] Tests cover happy path and edge cases
- [x] Tests validate error handling
- [x] Tests validate performance requirements
- [x] Tests validate security requirements
- [x] Tests use mocking appropriately
- [x] Tests are documented with docstrings

## Key Testing Patterns Used

1. **Fixtures for Setup** - Reusable test setup (tmp_path, mock objects)
2. **Parametrized Tests** - Multiple scenarios with same logic
3. **Context Managers** - Proper resource cleanup in tests
4. **Performance Timing** - Precise measurement with perf_counter
5. **Mock Patching** - Isolate units under test
6. **Marker Categorization** - Organize tests by type
7. **Property Testing** - Validate invariants

## Coverage Goals

- **Line Coverage**: > 90%
- **Branch Coverage**: > 85%
- **Critical Paths**: 100%

## Next Steps

1. Implement `TraceLogger` module
2. Run `pytest tests/tracing/test_trace_logger.py` to see tests pass
3. Implement `ClaudeBinaryManager` module
4. Run `pytest tests/tracing/test_binary_manager.py` to see tests pass
5. Continue through implementation order
6. Verify all 156 tests pass
7. Review coverage report
8. Refactor as needed while keeping tests green
