# Log Streaming Test Suite

This directory contains comprehensive TDD tests for the log streaming feature, following the 60/30/10 testing pyramid principle.

## Overview

The log streaming feature provides real-time Server-Sent Events (SSE) endpoint for streaming log events from the proxy server to connected clients. The feature includes:

- **localhost-only binding** on separate port (main_port + 1000)
- **JSON-formatted log events** with timestamp, level, logger, message
- **Multiple concurrent client support**
- **Integration with existing Python logging infrastructure**

## Test Structure (60/30/10 Testing Pyramid)

### Unit Tests (60% - 18 tests)

**Core Functionality Tests:**

- `test_unit_log_formatting.py` - Log record to JSON conversion
- `test_unit_port_management.py` - Dynamic port selection logic
- `test_unit_sse_events.py` - Server-Sent Event formatting
- `test_unit_connection_management.py` - Client connection handling
- `test_unit_security.py` - Localhost-only binding enforcement

**Coverage:**

- Log Event Formatting (JSON conversion, validation, sanitization)
- Port Management (dynamic selection, conflict resolution, security)
- SSE Event Generation (formatting, validation, streaming)
- Connection Management (client lifecycle, heartbeats, cleanup)
- Security Features (localhost binding, access control, data filtering)

### Integration Tests (30% - 9 tests)

**System Integration Tests:**

- `test_integration_proxy_log_stream.py` - Proxy + log stream integration
- `test_integration_log_handler.py` - Python logging integration
- `test_integration_error_scenarios.py` - Error handling and edge cases

**Coverage:**

- Proxy and log stream simultaneous operation
- Log handler integration with Python logging
- Multiple concurrent client handling
- Network error scenarios and recovery
- Resource exhaustion handling

### E2E Tests (10% - 3 tests)

**End-to-End Workflow Tests:**

- `test_e2e_complete_workflow.py` - Complete system workflow

**Coverage:**

- Full proxy startup → log streaming → client delivery
- Azure integration with real log streaming
- Production-like scenarios with performance validation
- System stability under sustained load
- Graceful shutdown with active clients

## Test Configuration

### Fixtures (`conftest.py`)

Common fixtures for all log streaming tests:

- `available_port` - Dynamic port allocation
- `mock_logger` - Mock logging components
- `sse_event_formatter` - SSE formatting utilities
- `security_validator` - Security validation helpers
- `performance_monitor` - Performance measurement tools

### Test Markers

Tests are categorized with pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (moderate speed)
- `@pytest.mark.e2e` - End-to-end tests (slow, comprehensive)
- `@pytest.mark.async_test` - Async/await test support
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.network` - Tests requiring network access

## Running Tests

### Prerequisites

```bash
pip install pytest pytest-asyncio aiohttp
```

### Run All Tests

```bash
# Run all log streaming tests
pytest tests/log_streaming/ -v

# Run by test level
pytest tests/log_streaming/ -m "unit" -v           # Unit tests only
pytest tests/log_streaming/ -m "integration" -v    # Integration tests only
pytest tests/log_streaming/ -m "e2e" -v           # E2E tests only
```

### Run Specific Test Categories

```bash
# Core functionality
pytest tests/log_streaming/test_unit_log_formatting.py -v

# Performance tests
pytest tests/log_streaming/ -m "slow" -v

# Security tests
pytest tests/log_streaming/test_unit_security.py -v
```

## TDD Approach

### Expected Test Failures

**All tests are designed to FAIL initially** (no implementation exists yet). This follows TDD principles:

1. **RED** - Tests fail because implementation doesn't exist
2. **GREEN** - Implement minimum code to make tests pass
3. **REFACTOR** - Improve implementation while keeping tests passing

### Implementation Guidance

Tests indicate what needs to be implemented:

```python
# This import will fail initially
from amplihack.proxy.log_streaming import LogStreamServer

# Tests guide the API design
server = LogStreamServer(host="127.0.0.1", port=9082)
await server.start()
```

### Error Messages Guide Implementation

Test failures provide clear guidance:

- Missing modules/classes to create
- Required method signatures
- Expected behavior and return values
- Performance requirements
- Security constraints

## Key Requirements Validated

### Functional Requirements

- [x] Server-Sent Events endpoint implementation
- [x] Dynamic port selection (main_port + 1000)
- [x] JSON log event formatting
- [x] Multiple concurrent client support
- [x] Python logging integration

### Security Requirements

- [x] Localhost-only binding enforcement
- [x] Origin validation for connections
- [x] Sensitive data filtering from logs
- [x] Connection limits and rate limiting
- [x] Secure port range validation

### Performance Requirements

- [x] Log formatting < 5ms per event
- [x] Bulk operations < 50ms for 100 events
- [x] High-throughput logging support
- [x] Memory usage constraints
- [x] Minimal impact on proxy performance (< 20% overhead)

### Reliability Requirements

- [x] Graceful handling of client disconnections
- [x] Error recovery and resilience
- [x] Resource exhaustion handling
- [x] Concurrent operation stability
- [x] Clean shutdown with active clients

## Implementation Architecture

Tests imply the following architecture:

```
amplihack/proxy/log_streaming/
├── __init__.py
├── server.py              # LogStreamServer
├── handlers.py            # LogStreamHandler
├── formatters.py          # LogEventFormatter
├── connections.py         # ConnectionManager
├── events.py              # SSEEventFormatter
├── security.py           # Security validators
└── config.py              # Configuration management
```

## Test Coverage Goals

- **Line Coverage**: 95%+ for core functionality
- **Branch Coverage**: 90%+ for error handling
- **Integration Coverage**: All major component interactions
- **Performance Coverage**: All critical performance paths
- **Security Coverage**: All security boundaries and validations

## Contributing

When adding new tests:

1. Follow the 60/30/10 testing pyramid
2. Use appropriate pytest markers
3. Include both positive and negative test cases
4. Add performance benchmarks for critical paths
5. Ensure security test coverage for new features
6. Update this README with new test categories

## Notes

- Tests use mock Azure endpoints to avoid external dependencies
- All network tests use localhost binding for security
- Performance tests include reasonable timeouts and limits
- Error scenarios test both graceful degradation and recovery
- Async tests properly handle task cleanup and resource management
