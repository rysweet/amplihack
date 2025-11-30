#!/usr/bin/env python3
"""Test script to verify security fixes are working."""

import os

from api_client import APIClient, APIError, ClientConfig


def test_ssrf_protection():
    """Test that SSRF protection works."""
    print("Testing SSRF Protection...")

    # Test 1: Block private IP ranges
    test_urls = [
        ("http://127.0.0.1:8080", "loopback"),
        ("http://localhost:8080", "localhost"),
        ("http://192.168.1.1", "private IP"),
        ("http://10.0.0.1", "private IP"),
        ("http://172.16.0.1", "private IP"),
        ("http://169.254.169.254", "metadata service"),
        ("file:///etc/passwd", "file scheme"),
        ("ftp://example.com", "ftp scheme"),
    ]

    for url, description in test_urls:
        try:
            config = ClientConfig(base_url=url)
            client = APIClient(config)
            client.get("/test")
            print(f"  ❌ FAILED: {description} ({url}) was not blocked!")
        except APIError as e:
            print(f"  ✓ PASS: {description} blocked - {str(e)[:50]}...")
        except ValueError as e:
            print(f"  ✓ PASS: {description} blocked at config - {str(e)[:50]}...")
        except Exception as e:
            print(f"  ? UNEXPECTED: {description} - {type(e).__name__}: {str(e)[:50]}")

    # Test 2: Allow valid URLs
    print("\nTesting valid URLs are allowed...")
    valid_urls = [
        "https://api.example.com",
        "http://api.public-service.com",
    ]

    for url in valid_urls:
        try:
            config = ClientConfig(base_url=url, disable_ssrf_protection=False)
            print(f"  ✓ PASS: {url} allowed")
        except Exception as e:
            print(f"  ❌ FAILED: {url} blocked - {e}")


def test_api_key_security():
    """Test API key security features."""
    print("\nTesting API Key Security...")

    # Test 1: Environment variable loading
    os.environ["MY_API_KEY"] = "sk-test-12345678"
    config = ClientConfig(
        base_url="https://api.example.com", api_key_env="MY_API_KEY", disable_ssrf_protection=True
    )

    if config.api_key == "sk-test-12345678":
        print("  ✓ PASS: API key loaded from environment")
    else:
        print(f"  ❌ FAILED: API key not loaded, got: {config.api_key}")

    # Test 2: API key masking
    masked = config.get_masked_api_key()
    if masked == "sk-...678":
        print(f"  ✓ PASS: API key masked correctly: {masked}")
    else:
        print(f"  ❌ FAILED: API key masking incorrect: {masked}")

    # Cleanup
    del os.environ["MY_API_KEY"]


def test_config_validation():
    """Test ClientConfig validation."""
    print("\nTesting Config Validation...")

    # Test invalid configurations
    invalid_configs = [
        ({"base_url": "not-a-url"}, "invalid URL scheme"),
        ({"base_url": "https://example.com", "timeout": -1}, "negative timeout"),
        ({"base_url": "https://example.com", "max_retries": -5}, "negative retries"),
        ({"base_url": "https://example.com", "timeout": 0}, "zero timeout"),
    ]

    for kwargs, description in invalid_configs:
        try:
            config = ClientConfig(**kwargs)
            print(f"  ❌ FAILED: {description} was not rejected!")
        except ValueError as e:
            print(f"  ✓ PASS: {description} rejected - {str(e)[:50]}...")
        except Exception as e:
            print(f"  ? UNEXPECTED: {description} - {type(e).__name__}: {e}")


def test_response_binary_handling():
    """Test Response.text() handles binary data gracefully."""
    print("\nTesting Binary Data Handling...")

    from api_client.response import Response

    # Test 1: Binary data
    binary_data = bytes(range(256))  # All byte values
    response = Response(200, binary_data)
    text = response.text()

    if text.startswith("<Binary data:"):
        print(f"  ✓ PASS: Binary data handled: {text}")
    else:
        print("  ❌ FAILED: Binary data not handled correctly")

    # Test 2: Valid UTF-8
    utf8_data = "Hello 世界 🌍".encode()
    response = Response(200, utf8_data)
    text = response.text()

    if text == "Hello 世界 🌍":
        print("  ✓ PASS: UTF-8 text decoded correctly")
    else:
        print(f"  ❌ FAILED: UTF-8 decoding failed: {text}")

    # Test 3: Latin-1 text
    latin1_data = "Café résumé".encode("latin-1")
    response = Response(200, latin1_data)
    text = response.text()

    if "Café" in text or "Caf" in text:
        print("  ✓ PASS: Latin-1 text handled")
    else:
        print(f"  ❌ FAILED: Latin-1 handling failed: {text}")


if __name__ == "__main__":
    print("=" * 60)
    print("Security Fixes Verification Tests")
    print("=" * 60)

    test_ssrf_protection()
    test_api_key_security()
    test_config_validation()
    test_response_binary_handling()

    print("\n" + "=" * 60)
    print("Security verification complete!")
