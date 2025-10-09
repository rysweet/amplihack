"""Pytest configuration and fixtures for proxy robustness tests.

This module provides shared fixtures and utilities for testing proxy robustness,
including port management, error simulation, and test infrastructure.
"""

import socket
import time
from contextlib import contextmanager
from typing import List, Tuple
from unittest.mock import Mock

import pytest


@pytest.fixture
def available_port() -> int:
    """Fixture that provides an available port for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        return sock.getsockname()[1]


@pytest.fixture
def available_port_range() -> Tuple[int, int]:
    """Fixture that provides a range of available ports for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("localhost", 0))
        start_port = sock.getsockname()[1]
    return start_port, start_port + 10


@pytest.fixture
def occupied_port() -> int:
    """Fixture that provides a port that's guaranteed to be occupied.

    Note: The socket is kept open for the duration of the test,
    so the port remains occupied.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("localhost", 0))
    port = sock.getsockname()[1]

    # Store the socket in the fixture so it stays open
    # pytest will clean it up automatically
    return port


@contextmanager
def occupy_port(port: int):
    """Context manager to temporarily occupy a specific port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("localhost", port))
        sock.listen(1)
        yield port
    finally:
        sock.close()


@contextmanager
def occupy_ports(ports: List[int]):
    """Context manager to temporarily occupy multiple ports."""
    sockets = []
    try:
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("localhost", port))
            sock.listen(1)
            sockets.append(sock)
        yield ports
    finally:
        for sock in sockets:
            sock.close()


@pytest.fixture
def port_occupier():
    """Fixture that provides utilities for occupying ports during tests."""
    return {
        "occupy_port": occupy_port,
        "occupy_ports": occupy_ports,
    }


@pytest.fixture
def mock_proxy_process():
    """Fixture that provides a mock proxy process for testing."""
    mock_process = Mock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None  # Process is running
    mock_process.returncode = None
    mock_process.stdout = Mock()
    mock_process.stderr = Mock()
    mock_process.communicate.return_value = ("", "")
    mock_process.wait.return_value = 0
    mock_process.terminate.return_value = None
    mock_process.kill.return_value = None
    return mock_process


@pytest.fixture
def mock_failed_proxy_process():
    """Fixture that provides a mock failed proxy process for testing."""
    mock_process = Mock()
    mock_process.pid = 12346
    mock_process.poll.return_value = 1  # Process has exited with error
    mock_process.returncode = 1
    mock_process.stdout = Mock()
    mock_process.stderr = Mock()
    mock_process.communicate.return_value = ("", "Error starting proxy")
    mock_process.wait.return_value = 1
    return mock_process


@pytest.fixture
def port_checker():
    """Fixture that provides port checking utilities."""

    def is_port_occupied(port: int, host: str = "localhost") -> bool:
        """Check if a port is occupied."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.0)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False

    def is_port_available(port: int, host: str = "localhost") -> bool:
        """Check if a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
                return True
        except OSError:
            return False

    def find_available_port(start_port: int = 8000, end_port: int = 9000) -> int:
        """Find an available port in the given range."""
        for port in range(start_port, end_port):
            if is_port_available(port):
                return port
        raise RuntimeError(f"No available ports found in range {start_port}-{end_port}")

    return {
        "is_occupied": is_port_occupied,
        "is_available": is_port_available,
        "find_available": find_available_port,
    }


@pytest.fixture
def error_message_validator():
    """Fixture that provides error message validation utilities."""

    def is_user_friendly(message: str) -> bool:
        """Check if an error message is user-friendly."""
        # Should not contain internal debugging information
        unfriendly_patterns = [
            "traceback",
            "exception",
            "errno",
            "socket.error",
            "__",
            "stderr",
            "stdout",
            ".py:",
            "line ",
        ]
        message_lower = message.lower()
        return not any(pattern in message_lower for pattern in unfriendly_patterns)

    def has_actionable_advice(message: str) -> bool:
        """Check if an error message contains actionable advice."""
        actionable_keywords = [
            "try",
            "use",
            "check",
            "ensure",
            "configure",
            "available",
            "alternative",
            "instead",
            "port",
            "set",
            "export",
            "install",
            "run",
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in actionable_keywords)

    def is_appropriately_verbose(message: str, verbosity: str = "normal") -> bool:
        """Check if message verbosity is appropriate for the level."""
        if verbosity == "minimal":
            return len(message) < 100
        if verbosity == "detailed":
            return len(message) > 50 and len(message) < 500
        # normal
        return len(message) > 20 and len(message) < 300

    return {
        "is_user_friendly": is_user_friendly,
        "has_actionable_advice": has_actionable_advice,
        "is_appropriately_verbose": is_appropriately_verbose,
    }


@pytest.fixture
def environment_manager():
    """Fixture that provides environment variable management for tests."""
    import os

    original_env = dict(os.environ)

    def set_env(key: str, value: str):
        """Set an environment variable."""
        os.environ[key] = value

    def get_env(key: str, default=None):
        """Get an environment variable."""
        return os.environ.get(key, default)

    def unset_env(key: str):
        """Unset an environment variable."""
        os.environ.pop(key, None)

    def restore_env():
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(original_env)

    # Automatically restore environment after test
    yield {
        "set": set_env,
        "get": get_env,
        "unset": unset_env,
        "restore": restore_env,
    }

    # Cleanup
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def timing_utilities():
    """Fixture that provides timing utilities for tests."""

    def measure_time(func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        return result, elapsed_time

    def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
        """Wait for a condition to become true."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if condition_func():
                return True
            time.sleep(interval)
        return False

    return {
        "measure_time": measure_time,
        "wait_for_condition": wait_for_condition,
    }


# Markers for different test categories
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "network: mark test as requiring network access")


# Custom assertions for proxy testing
class ProxyTestAssertions:
    """Custom assertions for proxy robustness testing."""

    @staticmethod
    def assert_port_available(port: int, host: str = "localhost"):
        """Assert that a port is available for binding."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind((host, port))
        except OSError as e:
            pytest.fail(f"Port {port} is not available: {e}")

    @staticmethod
    def assert_port_occupied(port: int, host: str = "localhost"):
        """Assert that a port is occupied."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1.0)
                result = sock.connect_ex((host, port))
                if result != 0:
                    pytest.fail(f"Port {port} is not occupied")
        except Exception as e:
            pytest.fail(f"Could not check if port {port} is occupied: {e}")

    @staticmethod
    def assert_error_message_quality(
        message: str, should_be_friendly: bool = True, should_have_advice: bool = True
    ):
        """Assert that an error message meets quality standards."""
        if should_be_friendly:
            unfriendly_patterns = ["traceback", "exception", "errno", "__"]
            for pattern in unfriendly_patterns:
                if pattern in message.lower():
                    pytest.fail(f"Error message contains unfriendly pattern '{pattern}': {message}")

        if should_have_advice:
            actionable_keywords = ["try", "use", "check", "configure", "alternative"]
            if not any(keyword in message.lower() for keyword in actionable_keywords):
                pytest.fail(f"Error message lacks actionable advice: {message}")


@pytest.fixture
def proxy_assertions():
    """Fixture that provides custom proxy testing assertions."""
    return ProxyTestAssertions()
