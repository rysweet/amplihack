"""Pytest configuration and fixtures for REST API client tests.

Provides shared fixtures and configuration for all test modules.
"""

import os
import sys

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.mock_server import FlakeyMockServer, MockHTTPServer, RateLimitingMockServer


@pytest.fixture(scope="session")
def mock_server():
    """Provide a basic mock HTTP server for the entire test session."""
    server = MockHTTPServer(port=0)  # Random port
    port = server.start()
    server.base_url = f"http://127.0.0.1:{port}"

    yield server

    server.stop()


@pytest.fixture(scope="function")
def clean_mock_server(mock_server):
    """Provide a clean mock server, reset before each test."""
    mock_server.reset()
    return mock_server


@pytest.fixture(scope="function")
def rate_limiting_server():
    """Provide a rate-limiting mock server."""
    server = RateLimitingMockServer(port=0, rate_limit=3)
    port = server.start()
    server.base_url = f"http://127.0.0.1:{port}"

    yield server

    server.stop()


@pytest.fixture(scope="function")
def flakey_server():
    """Provide a flakey mock server that fails intermittently."""
    server = FlakeyMockServer(
        port=0,
        failure_pattern=[True, True, False],  # Fail twice, then succeed
    )
    port = server.start()
    server.base_url = f"http://127.0.0.1:{port}"

    yield server

    server.stop()


@pytest.fixture
def sample_json_data():
    """Provide sample JSON data for testing."""
    return {
        "user": {"id": 123, "name": "Test User", "email": "test@example.com"},
        "metadata": {"created": "2024-01-01T00:00:00Z", "updated": "2024-01-01T12:00:00Z"},
    }


@pytest.fixture
def sample_headers():
    """Provide sample HTTP headers for testing."""
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer test-token-123",
        "X-API-Key": "api-key-456",
        "User-Agent": "TestClient/1.0",
    }


@pytest.fixture
def sample_query_params():
    """Provide sample query parameters for testing."""
    return {"page": "1", "limit": "10", "sort": "created_desc", "filter": "active"}


@pytest.fixture(autouse=True)
def reset_imports():
    """Reset module imports to ensure clean state.

    This is important for TDD as the module doesn't exist yet.
    """
    # Remove api_client from sys.modules if it exists
    if "api_client" in sys.modules:
        del sys.modules["api_client"]

    yield

    # Cleanup after test
    if "api_client" in sys.modules:
        del sys.modules["api_client"]


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# Test collection configuration
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file
        if (
            "test_client" in item.nodeid
            or "test_rate_limiting" in item.nodeid
            or "test_retry" in item.nodeid
        ):
            item.add_marker(pytest.mark.unit)
        elif "test_integration" in item.nodeid:
            if "EndToEnd" in item.nodeid:
                item.add_marker(pytest.mark.e2e)
            else:
                item.add_marker(pytest.mark.integration)

        # Mark slow tests
        if any(
            slow_indicator in item.nodeid.lower()
            for slow_indicator in ["slow", "timeout", "concurrent"]
        ):
            item.add_marker(pytest.mark.slow)
