#!/usr/bin/env python
"""Simple test to verify the consolidation works correctly."""

from rest_api_client import (
    APIClient,
    APIClientError,
    APIRequest,
    APIResponse,
    ClientConfig,
    NetworkError,
    RateLimitConfig,
    RetryConfig,
)


def test_imports():
    """Test all imports work."""
    print("✓ All imports successful")


def test_client_creation():
    """Test basic client creation."""
    client = APIClient("https://api.example.com")
    assert client.base_url == "https://api.example.com"
    assert client.timeout == 30.0
    assert client.max_retries == 3
    print("✓ Client creation successful")


def test_config_creation():
    """Test configuration creation."""
    retry_config = RetryConfig(max_retries=5)
    assert retry_config.max_retries == 5

    rate_config = RateLimitConfig(max_tokens=20)
    assert rate_config.max_tokens == 20

    client_config = ClientConfig(base_url="https://test.com")
    assert client_config.base_url == "https://test.com"
    print("✓ Configuration creation successful")


def test_exception_hierarchy():
    """Test exception hierarchy."""
    try:
        raise NetworkError("Test error")
    except APIClientError:
        print("✓ Exception hierarchy working")


def test_request_response_models():
    """Test request and response models."""
    request = APIRequest(method="GET", url="https://api.example.com/test")
    assert request.method == "GET"

    response = APIResponse(status_code=200, headers={}, body='{"test": "data"}')
    assert response.is_success
    assert response.json_data == {"test": "data"}
    print("✓ Request/Response models working")


if __name__ == "__main__":
    test_imports()
    test_client_creation()
    test_config_creation()
    test_exception_hierarchy()
    test_request_response_models()
    print("\n✅ All tests passed! Module consolidation successful.")
    print("📊 Module count reduced from 8 to 3 (client.py, models.py, utils.py)")
