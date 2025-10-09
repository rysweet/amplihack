"""Pytest configuration and fixtures for log streaming tests.

This module provides shared fixtures and utilities for testing log streaming
functionality, including SSE event handling, WebSocket connections, and log formatting.
"""

import asyncio
import json
import logging
import socket
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

import pytest


@dataclass
class LogEvent:
    """Test log event structure."""

    timestamp: str
    level: str
    logger: str
    message: str
    extra: Optional[Dict[str, Any]] = None


@pytest.fixture
def available_port() -> int:
    """Fixture that provides an available port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def log_stream_port(available_port) -> int:
    """Fixture that provides the log stream port (main_port + 1000)."""
    return available_port + 1000


@pytest.fixture
def mock_logger():
    """Fixture that provides a mock logger for testing."""
    logger = Mock(spec=logging.Logger)
    logger.name = "test.logger"
    logger.level = logging.INFO
    logger.handlers = []
    return logger


@pytest.fixture
def sample_log_record():
    """Fixture that provides a sample log record for testing."""
    record = logging.LogRecord(
        name="amplihack.proxy.server",
        level=logging.INFO,
        pathname="/path/to/file.py",
        lineno=42,
        msg="Test log message",
        args=(),
        exc_info=None,
    )
    record.created = time.time()
    record.msecs = 123.45
    return record


@pytest.fixture
def sample_log_events() -> List[LogEvent]:
    """Fixture that provides sample log events for testing."""
    timestamp = datetime.now().isoformat()
    return [
        LogEvent(timestamp, "INFO", "amplihack.proxy", "Proxy started on port 8082"),
        LogEvent(timestamp, "DEBUG", "amplihack.azure", "Processing Azure request"),
        LogEvent(
            timestamp, "ERROR", "amplihack.auth", "Authentication failed", {"error_code": "401"}
        ),
        LogEvent(timestamp, "WARNING", "amplihack.proxy", "Rate limit exceeded"),
        LogEvent(timestamp, "CRITICAL", "amplihack.security", "Security breach detected"),
    ]


@pytest.fixture
def mock_sse_client():
    """Fixture that provides a mock Server-Sent Events client."""
    client = Mock()
    client.events = []
    client.connected = False
    client.last_event_id = None

    async def connect():
        client.connected = True

    async def disconnect():
        client.connected = False

    async def receive_event():
        if not client.events:
            return None
        return client.events.pop(0)

    client.connect = connect
    client.disconnect = disconnect
    client.receive_event = receive_event

    return client


@pytest.fixture
def sse_event_formatter():
    """Fixture that provides SSE event formatting utilities."""

    def format_sse_event(
        event_type: str, data: Dict[str, Any], event_id: Optional[str] = None
    ) -> str:
        """Format data as Server-Sent Event."""
        lines = []
        if event_id:
            lines.append(f"id: {event_id}")
        if event_type:
            lines.append(f"event: {event_type}")
        lines.append(f"data: {json.dumps(data)}")
        lines.append("")  # Empty line to end event
        return "\n".join(lines)

    def parse_sse_event(sse_text: str) -> Dict[str, str]:
        """Parse SSE event text into components."""
        lines = sse_text.strip().split("\n")
        event = {}

        for line in lines:
            if line.startswith("id: "):
                event["id"] = line[4:]
            elif line.startswith("event: "):
                event["event"] = line[7:]
            elif line.startswith("data: "):
                event["data"] = line[6:]

        return event

    return {"format": format_sse_event, "parse": parse_sse_event}


@pytest.fixture
def log_formatter():
    """Fixture that provides log formatting utilities for testing."""

    def format_log_event(record: logging.LogRecord) -> Dict[str, Any]:
        """Format log record as JSON event."""
        return {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }

    def validate_log_event_format(event: Dict[str, Any]) -> bool:
        """Validate log event has required fields."""
        required_fields = ["timestamp", "level", "logger", "message"]
        return all(field in event for field in required_fields)

    return {"format": format_log_event, "validate": validate_log_event_format}


@pytest.fixture
def mock_log_streaming_server():
    """Fixture that provides a mock log streaming server."""

    class MockLogStreamingServer:
        def __init__(self, port: int):
            self.port = port
            self.clients = set()
            self.is_running = False
            self.log_events = []

        async def start(self):
            """Start the mock server."""
            self.is_running = True

        async def stop(self):
            """Stop the mock server."""
            self.is_running = False
            self.clients.clear()

        async def add_client(self, client_id: str):
            """Add a client connection."""
            self.clients.add(client_id)

        async def remove_client(self, client_id: str):
            """Remove a client connection."""
            self.clients.discard(client_id)

        async def broadcast_log_event(self, log_event: Dict[str, Any]):
            """Broadcast log event to all clients."""
            self.log_events.append(log_event)
            # In real implementation, this would send SSE events to clients

        def get_client_count(self) -> int:
            """Get number of connected clients."""
            return len(self.clients)

    def create_server(port: int) -> MockLogStreamingServer:
        return MockLogStreamingServer(port)

    return {"create": create_server}


@contextmanager
def occupy_port(port: int):
    """Context manager to temporarily occupy a specific port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(1)
        yield port
    finally:
        sock.close()


@pytest.fixture
def port_manager():
    """Fixture that provides port management utilities."""

    def is_port_available(port: int) -> bool:
        """Check if port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                return True
        except OSError:
            return False

    def is_port_occupied(port: int) -> bool:
        """Check if port is occupied."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.0)
                result = sock.connect_ex(("127.0.0.1", port))
                return result == 0
        except Exception:
            return False

    return {
        "is_available": is_port_available,
        "is_occupied": is_port_occupied,
        "occupy_port": occupy_port,
    }


@pytest.fixture
def async_event_loop():
    """Fixture that provides an event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def security_validator():
    """Fixture that provides security validation utilities."""

    def validate_localhost_binding(host: str) -> bool:
        """Validate that binding is localhost-only."""
        return host in ("127.0.0.1", "localhost", "::1")

    def validate_log_content_safety(log_data: Dict[str, Any]) -> bool:
        """Validate that log content doesn't contain sensitive information."""
        sensitive_patterns = [
            "password",
            "token",
            "secret",
            "key",
            "api_key",
            "auth",
            "credential",
            "bearer",
            "oauth",
        ]

        log_str = json.dumps(log_data).lower()
        return not any(pattern in log_str for pattern in sensitive_patterns)

    def validate_port_range(port: int, min_port: int = 1024, max_port: int = 65535) -> bool:
        """Validate port is in safe range."""
        return min_port <= port <= max_port

    return {
        "validate_localhost_binding": validate_localhost_binding,
        "validate_log_content_safety": validate_log_content_safety,
        "validate_port_range": validate_port_range,
    }


@pytest.fixture
def performance_monitor():
    """Fixture that provides performance monitoring utilities."""

    def measure_execution_time(func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        return result, execution_time

    async def measure_async_execution_time(coro):
        """Measure execution time of an async function."""
        start_time = time.perf_counter()
        result = await coro
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        return result, execution_time

    def assert_execution_time_under(max_time_ms: float):
        """Assert that execution time is under specified milliseconds."""

        def decorator(func):
            def wrapper(*args, **kwargs):
                result, execution_time = measure_execution_time(func, *args, **kwargs)
                assert execution_time * 1000 < max_time_ms, (
                    f"Execution took {execution_time * 1000:.2f}ms, expected < {max_time_ms}ms"
                )
                return result

            return wrapper

        return decorator

    return {
        "measure_time": measure_execution_time,
        "measure_async_time": measure_async_execution_time,
        "assert_under": assert_execution_time_under,
    }


@pytest.fixture
def environment_manager():
    """Fixture that provides environment variable management."""
    import os

    original_env = dict(os.environ)

    def set_env(key: str, value: str):
        os.environ[key] = value

    def unset_env(key: str):
        os.environ.pop(key, None)

    def get_env(key: str, default=None):
        return os.environ.get(key, default)

    yield {"set": set_env, "unset": unset_env, "get": get_env}

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Configure pytest markers
def pytest_configure(config):
    """Configure pytest markers for log streaming tests."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "network: mark test as requiring network access")
    config.addinivalue_line("markers", "async_test: mark test as requiring async support")


# Custom assertions for log streaming testing
class LogStreamingTestAssertions:
    """Custom assertions for log streaming tests."""

    @staticmethod
    def assert_valid_sse_format(sse_data: str):
        """Assert that data is in valid SSE format."""
        lines = sse_data.strip().split("\n")
        assert any(line.startswith("data: ") for line in lines), "SSE must have data field"
        assert sse_data.endswith("\n\n") or sse_data.endswith("\n"), "SSE must end with newline"

    @staticmethod
    def assert_log_event_format(log_event: Dict[str, Any]):
        """Assert that log event has required format."""
        required_fields = ["timestamp", "level", "logger", "message"]
        for field in required_fields:
            assert field in log_event, f"Log event missing required field: {field}"

        # Validate timestamp format
        from datetime import datetime

        try:
            datetime.fromisoformat(log_event["timestamp"])
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {log_event['timestamp']}")

    @staticmethod
    def assert_localhost_only_binding(host: str):
        """Assert that server binds to localhost only."""
        valid_hosts = ("127.0.0.1", "localhost", "::1")
        assert host in valid_hosts, f"Server must bind to localhost only, got: {host}"


@pytest.fixture
def log_streaming_assertions():
    """Fixture that provides custom log streaming assertions."""
    return LogStreamingTestAssertions()
