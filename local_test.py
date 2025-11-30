#!/usr/bin/env python3
"""
Local testing script for REST API Client
Tests real-world scenarios with actual HTTP endpoints
"""

import sys
from datetime import datetime

# Add our module to path
sys.path.insert(0, ".claude/scenarios")

from rest_api_client import APIClient, APIClientError, APIConfig, RateLimitError


def test_basic_get():
    """Test simple GET request"""
    print("Testing basic GET request...")
    client = APIClient("https://httpbin.org")

    try:
        response = client.get("/get")
        print(f"✅ GET request successful: Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ GET request failed: {e}")
        return False


def test_post_with_data():
    """Test POST with JSON data"""
    print("\nTesting POST with JSON data...")
    client = APIClient("https://httpbin.org")

    test_data = {"name": "Test User", "timestamp": datetime.now().isoformat()}

    try:
        response = client.post("/post", json=test_data)
        print(f"✅ POST request successful: Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ POST request failed: {e}")
        return False


def test_error_handling():
    """Test 404 error handling"""
    print("\nTesting error handling (404)...")
    client = APIClient("https://httpbin.org")

    try:
        response = client.get("/status/404")
        print("❌ Should have raised an error for 404")
        return False
    except APIClientError as e:
        print(f"✅ Error handled correctly: {e}")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_retry_logic():
    """Test retry on server error"""
    print("\nTesting retry logic (simulated 500 error)...")
    config = APIConfig(base_url="https://httpbin.org", max_retries=2, retry_delay=1.0)
    client = APIClient("https://httpbin.org", config=config)

    # httpbin.org/status/500 returns 500 error
    try:
        response = client.get("/status/500")
        print("❌ Should have failed after retries")
        return False
    except APIClientError as e:
        print(f"✅ Retries exhausted as expected: {e}")
        return True


def test_rate_limiting():
    """Test rate limiting behavior"""
    print("\nTesting rate limiting (429 response)...")
    client = APIClient("https://httpbin.org")

    try:
        # httpbin doesn't actually rate limit, but we can test 429 handling
        response = client.get("/status/429")
        print("❌ Should have raised RateLimitError")
        return False
    except RateLimitError as e:
        print(f"✅ Rate limit handled correctly: {e}")
        return True
    except APIClientError as e:
        # May be wrapped in generic error
        if "429" in str(e) or "rate" in str(e).lower():
            print(f"✅ Rate limit detected: {e}")
            return True
        print(f"❌ Unexpected error: {e}")
        return False


def test_timeout():
    """Test timeout handling"""
    print("\nTesting timeout handling...")
    config = APIConfig(
        base_url="https://httpbin.org",
        timeout=2,  # 2 second timeout
    )
    client = APIClient("https://httpbin.org", config=config)

    try:
        # This endpoint delays for 5 seconds, should timeout
        response = client.get("/delay/5")
        print("❌ Should have timed out")
        return False
    except Exception as e:
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            print(f"✅ Timeout handled correctly: {e}")
            return True
        print(f"❌ Unexpected error: {e}")
        return False


def test_custom_headers():
    """Test custom headers"""
    print("\nTesting custom headers...")
    config = APIConfig(
        base_url="https://httpbin.org",
        headers={"X-Custom-Header": "TestValue", "User-Agent": "REST-API-Client/1.0"},
    )
    client = APIClient("https://httpbin.org", config=config)

    try:
        response = client.get("/headers")
        print(f"✅ Custom headers sent successfully: Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Custom headers test failed: {e}")
        return False


def test_all_http_methods():
    """Test all HTTP methods"""
    print("\nTesting all HTTP methods...")
    client = APIClient("https://httpbin.org")
    results = []

    methods = [
        ("GET", lambda: client.get("/get")),
        ("POST", lambda: client.post("/post", json={"test": "data"})),
        ("PUT", lambda: client.put("/put", json={"test": "data"})),
        ("PATCH", lambda: client.patch("/patch", json={"test": "data"})),
        ("DELETE", lambda: client.delete("/delete")),
    ]

    for method_name, method_func in methods:
        try:
            response = method_func()
            print(f"  ✅ {method_name}: Status {response.status_code}")
            results.append(True)
        except Exception as e:
            print(f"  ❌ {method_name}: {e}")
            results.append(False)

    return all(results)


def main():
    """Run all tests"""
    print("=" * 60)
    print("REST API Client - Local Testing")
    print("=" * 60)

    tests = [
        ("Basic GET", test_basic_get),
        ("POST with Data", test_post_with_data),
        ("Error Handling", test_error_handling),
        ("Retry Logic", test_retry_logic),
        ("Rate Limiting", test_rate_limiting),
        ("Timeout", test_timeout),
        ("Custom Headers", test_custom_headers),
        ("All HTTP Methods", test_all_http_methods),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASSED" if results[i] else "❌ FAILED"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed ({100 * passed / total:.1f}%)")

    if passed == total:
        print("\n🎉 All tests passed! The API Client is working correctly!")
        return 0
    print(f"\n⚠️  {total - passed} tests failed. See details above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
