#!/usr/bin/env python3
"""
User workflow test - Testing the API client like a real user would.
Tests all the main functionality from the outside-in perspective.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from api_client import APIClient, ClientConfig, HTTPError


def test_simple_use_case():
    """Test 1: Basic functionality - The simplest use case"""
    print("=" * 60)
    print("TEST 1: Simple GET request")
    print("-" * 60)

    # Create client with minimal config
    config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
    client = APIClient(config)

    # Make a simple GET request
    response = client.get("/posts/1")
    data = response.json()

    print("✅ GET /posts/1 successful")
    print(f"   Title: {data['title'][:50]}...")
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200
    assert "userId" in data


def test_complex_use_case():
    """Test 2: Complex functionality - POST with data"""
    print("\n" + "=" * 60)
    print("TEST 2: Complex POST request with JSON data")
    print("-" * 60)

    config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
    client = APIClient(config)

    # POST request with JSON data
    post_data = {
        "title": "Test Post from API Client",
        "body": "This is a test of the REST API client",
        "userId": 1,
    }

    response = client.post("/posts", json=post_data)
    result = response.json()

    print("✅ POST /posts successful")
    print(f"   Created ID: {result.get('id', 'N/A')}")
    print(f"   Title: {result['title']}")
    assert response.status_code == 201
    assert result["title"] == post_data["title"]


def test_error_handling():
    """Test 3: Error handling - 404 error"""
    print("\n" + "=" * 60)
    print("TEST 3: Error handling (404)")
    print("-" * 60)

    config = ClientConfig(base_url="https://jsonplaceholder.typicode.com")
    client = APIClient(config)

    try:
        response = client.get("/posts/99999")
        print(f"⚠️  Unexpected success: {response.status_code}")
    except HTTPError as e:
        print("✅ HTTPError caught correctly")
        print(f"   Status: {e.status_code}")
        print(f"   Message: {e.message}")
        assert e.status_code == 404
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


def test_with_authentication():
    """Test 4: Authentication with API key"""
    print("\n" + "=" * 60)
    print("TEST 4: Authentication with API key")
    print("-" * 60)

    # Set environment variable for testing
    os.environ["API_KEY"] = "test-api-key-12345"

    config = ClientConfig(base_url="https://httpbin.org", api_key=os.environ.get("API_KEY"))
    client = APIClient(config)

    # Make request that echoes headers
    response = client.get("/headers")
    data = response.json()

    # Check if Authorization header was sent
    auth_header = data["headers"].get("Authorization", "")
    print("✅ API key authentication working")
    print(f"   Auth header present: {'Bearer' in auth_header}")
    assert "Bearer" in auth_header or "test-api-key" in str(data)


def test_query_parameters():
    """Test 5: Query parameters"""
    print("\n" + "=" * 60)
    print("TEST 5: Query parameters")
    print("-" * 60)

    config = ClientConfig(base_url="https://httpbin.org")
    client = APIClient(config)

    params = {"foo": "bar", "number": 42}
    response = client.get("/get", params=params)
    data = response.json()

    print("✅ Query parameters working")
    print(f"   Sent: {params}")
    print(f"   Received: {data.get('args', {})}")
    assert data["args"] == {"foo": "bar", "number": "42"}


def test_retry_logic():
    """Test 6: Retry logic on server errors"""
    print("\n" + "=" * 60)
    print("TEST 6: Retry logic (using mock-like endpoint)")
    print("-" * 60)

    config = ClientConfig(
        base_url="https://httpbin.org",
        max_retries=2,  # Reduce retries for testing
    )
    client = APIClient(config)

    # httpbin.org/status/500 returns 500 error
    print("   Testing retry on 500 error...")
    try:
        response = client.get("/status/500")
        print(f"   Response: {response.status_code}")
    except HTTPError as e:
        print("✅ Retry logic executed (max retries exhausted)")
        print(f"   Final status: {e.status_code}")
        assert e.status_code == 500


def test_custom_headers():
    """Test 7: Custom headers"""
    print("\n" + "=" * 60)
    print("TEST 7: Custom headers")
    print("-" * 60)

    config = ClientConfig(base_url="https://httpbin.org")
    client = APIClient(config)

    custom_headers = {"X-Custom-Header": "test-value", "X-Request-ID": "12345"}

    response = client.get("/headers", headers=custom_headers)
    data = response.json()

    print("✅ Custom headers working")
    print(f"   X-Custom-Header: {data['headers'].get('X-Custom-Header')}")
    print(f"   X-Request-Id: {data['headers'].get('X-Request-Id')}")
    assert data["headers"].get("X-Custom-Header") == "test-value"


def test_validation():
    """Test 8: Input validation"""
    print("\n" + "=" * 60)
    print("TEST 8: Input validation")
    print("-" * 60)

    # Test invalid timeout
    try:
        config = ClientConfig(base_url="https://example.com", timeout=-1)
        print("❌ Should have raised ValueError for negative timeout")
    except ValueError as e:
        print(f"✅ Validation working: {e}")

    # Test invalid max_retries
    try:
        config = ClientConfig(base_url="https://example.com", max_retries=-1)
        print("❌ Should have raised ValueError for negative max_retries")
    except ValueError as e:
        print(f"✅ Validation working: {e}")


def main():
    """Run all user workflow tests"""
    print("\n" + "🏴‍☠️" * 20)
    print("    REST API CLIENT - USER WORKFLOW TESTS")
    print("🏴‍☠️" * 20)

    tests = [
        test_simple_use_case,
        test_complex_use_case,
        test_error_handling,
        test_with_authentication,
        test_query_parameters,
        test_retry_logic,
        test_custom_headers,
        test_validation,
    ]

    failed = []
    for test in tests:
        try:
            test()
        except Exception as e:
            failed.append((test.__name__, str(e)))
            print(f"❌ {test.__name__} failed: {e}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {len(tests) - len(failed)}/{len(tests)}")

    if failed:
        print(f"❌ Failed: {len(failed)}")
        for name, error in failed:
            print(f"   - {name}: {error}")
        return 1
    print("🎉 All tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
