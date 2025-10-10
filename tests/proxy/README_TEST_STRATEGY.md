# Proxy Robustness Test Strategy

## Overview

This test suite implements comprehensive proxy robustness testing using Test-Driven Development (TDD) principles. All tests are intentionally **FAILING** until implementation is created, following the Red-Green-Refactor cycle.

## Test Pyramid Structure (60% Unit, 30% Integration, 10% E2E)

### Unit Tests (60%)

- **Port Selection Logic** (`test_port_selector.py`)
  - Dynamic port finding with fallback strategies
  - Range limiting and OS port assignment
  - Timeout handling and error conditions

- **Error Reporting Logic** (`test_error_reporter.py`)
  - Error categorization (critical/important/debug)
  - User-friendly message formatting
  - Actionable advice generation
  - Output channel routing

### Integration Tests (30%)

- **ProxyManager Integration** (`test_proxy_robustness_integration.py`)
  - PortSelector integration for dynamic ports
  - ErrorReporter integration for user messages
  - Environment variable updates
  - Launcher integration

### End-to-End Tests (10%)

- **Complete System Flow** (`test_proxy_robustness.py`)
  - Full proxy startup with conflicts
  - Claude integration with dynamic ports
  - Complete user error experience

## Key Requirements Being Tested

### 1. Dynamic Port Selection

- ✅ Proxy finds alternative ports when preferred port unavailable
- ✅ Graceful fallback through port ranges
- ✅ OS-assigned port as final fallback
- ✅ Timeout handling for port selection

### 2. Error Surfacing

- ✅ User-friendly error messages without technical jargon
- ✅ Actionable advice in error messages
- ✅ Appropriate verbosity levels
- ✅ Proper output channel routing (stderr vs logs)

## Test Infrastructure

### Fixtures and Utilities (`conftest.py`)

- `available_port`: Provides guaranteed available ports
- `port_occupier`: Context managers for occupying ports
- `mock_proxy_process`: Mock subprocess for testing
- `error_message_validator`: Validates message quality
- `environment_manager`: Safe env var testing
- `proxy_assertions`: Custom assertions for proxy testing

### Mock Classes and Test Utilities

- `MockSocketServer`: Occupies ports for conflict testing
- `PortManager`: Port availability utilities
- `ErrorMessageValidator`: Message quality validation
- `ProxyTestAssertions`: Custom proxy-specific assertions

## Implementation Components Needed

### 1. PortSelector Class

```python
class PortSelector:
    def __init__(self, default_port=8080, port_range=(8080, 8180), timeout=30.0):
        ...

    def select_port(self) -> int:
        """Select available port with fallback strategy."""
        ...

    def select_port_with_info(self) -> dict:
        """Select port and return detailed selection info."""
        ...
```

### 2. ErrorReporter Class

```python
class ErrorReporter:
    def __init__(self, verbosity="normal", output_channels=["stderr", "log"]):
        ...

    def categorize_error(self, error) -> str:
        """Categorize error as critical/important/debug."""
        ...

    def format_message(self, error) -> str:
        """Format user-friendly error message."""
        ...

    def report_error(self, error):
        """Report error to appropriate channels."""
        ...
```

### 3. Exception Classes

```python
class PortRangeExhaustedError(Exception):
    """Raised when all ports in range are occupied."""
    ...

class PortSelectionTimeoutError(Exception):
    """Raised when port selection times out."""
    ...

class ProxyStartupError(Exception):
    """Raised when proxy fails to start."""
    ...
```

### 4. ProxyManager Integration

- Integrate PortSelector for dynamic port selection
- Integrate ErrorReporter for user-friendly messages
- Update environment variables with selected ports
- Preserve error context through system layers

## Running the Tests

### Run All Failing Tests

```bash
cd tests/proxy
pytest -v
```

### Run by Category

```bash
# Unit tests only
pytest -v -m unit

# Integration tests only
pytest -v -m integration

# E2E tests only
pytest -v -m e2e
```

### Run Specific Test Files

```bash
# Port selector tests
pytest test_port_selector.py -v

# Error reporter tests
pytest test_error_reporter.py -v

# Integration tests
pytest test_proxy_robustness_integration.py -v

# Complete robustness suite
pytest test_proxy_robustness.py -v
```

## Test Failure Analysis

### Expected Behavior

- **All tests should FAIL initially** - this is correct TDD behavior
- Each test failure indicates missing implementation
- Failures should be clear about what needs to be implemented

### Common Failure Patterns

1. `ImportError`: Missing classes/modules
2. `AssertionError: "X not implemented yet"`: Missing functionality
3. `AttributeError`: Missing methods/properties

### Implementation Progress Tracking

As components are implemented, tests will transition from RED → GREEN:

1. **RED Phase**: All tests fail (current state)
2. **GREEN Phase**: Minimal implementation makes tests pass
3. **REFACTOR Phase**: Improve implementation while keeping tests green

## Edge Cases Covered

### Port Selection Edge Cases

- Multiple simultaneous proxy startup attempts
- Permission denied for privileged ports (< 1024)
- Network interface binding failures
- Resource exhaustion conditions
- Platform-specific networking differences

### Error Handling Edge Cases

- Complex failure scenarios with multiple issues
- Error context preservation through system layers
- Graceful degradation under resource constraints
- User experience with different verbosity levels

## Success Criteria

### Functional Requirements

- ✅ Proxy successfully starts even when preferred port is occupied
- ✅ Users receive clear, actionable error messages
- ✅ Environment variables reflect actually used ports
- ✅ System gracefully handles edge cases and failures

### Quality Requirements

- ✅ Test coverage follows 60/30/10 pyramid structure
- ✅ All error messages are user-friendly (no technical jargon)
- ✅ All error messages contain actionable advice
- ✅ System performance is not significantly impacted

### Robustness Requirements

- ✅ Works across different operating systems
- ✅ Handles concurrent proxy startup attempts
- ✅ Recovers gracefully from transient failures
- ✅ Maintains security (no credential leakage in errors)

## Next Steps

1. **Implement PortSelector**: Start with basic port selection logic
2. **Implement ErrorReporter**: Focus on message formatting first
3. **Integrate with ProxyManager**: Connect new components
4. **Add Exception Classes**: Define specific exception hierarchy
5. **Run Tests**: Verify implementation against failing tests
6. **Iterate**: Refactor and improve based on test feedback

The beauty of TDD is that these comprehensive tests serve as both specification and validation - when all tests pass, the requirements are fully implemented.
