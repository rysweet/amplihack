"""Pytest configuration for api_client tests."""

import pytest  # type: ignore[import-not-found]


def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
