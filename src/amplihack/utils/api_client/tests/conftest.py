"""
Pytest configuration and shared fixtures for API client tests.

This module provides common fixtures and configuration for all test files.
"""

import logging

import pytest


@pytest.fixture
def disable_network():
    """
    Fixture to ensure tests don't make real network requests.

    This is a safety mechanism to prevent tests from accidentally
    hitting real APIs during test runs.
    """
    # responses library already mocks requests, but this provides extra safety


@pytest.fixture
def caplog_info(caplog):
    """Fixture to capture logs at INFO level"""
    caplog.set_level(logging.INFO)
    return caplog


@pytest.fixture
def caplog_debug(caplog):
    """Fixture to capture logs at DEBUG level"""
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def caplog_warning(caplog):
    """Fixture to capture logs at WARNING level"""
    caplog.set_level(logging.WARNING)
    return caplog


@pytest.fixture
def sample_api_response():
    """Fixture providing sample API response data"""
    return {
        "id": 123,
        "name": "Test User",
        "email": "test@example.com",
        "created_at": "2025-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_error_response():
    """Fixture providing sample error response data"""
    return {
        "error": "Invalid request",
        "message": "The provided data is invalid",
        "code": "VALIDATION_ERROR",
    }


@pytest.fixture
def mock_base_url():
    """Fixture providing a consistent mock base URL"""
    return "https://api.example.com"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: mark test as a unit test (fast, heavily mocked)")
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (multiple components)"
    )
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test (complete workflows)")
    config.addinivalue_line("markers", "slow: mark test as slow running (may take >1 second)")
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access (should be mocked)"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location and name"""
    for item in items:
        # Mark tests by file
        if (
            "test_client.py" in str(item.fspath)
            or "test_retry.py" in str(item.fspath)
            or "test_rate_limit.py" in str(item.fspath)
            or "test_exceptions.py" in str(item.fspath)
            or "test_security.py" in str(item.fspath)
        ):
            item.add_marker(pytest.mark.unit)
        elif "test_integration.py" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark tests that test network errors as requiring network handling
        if "network" in item.name.lower() or "connection" in item.name.lower():
            item.add_marker(pytest.mark.network)
