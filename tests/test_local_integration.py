#!/usr/bin/env python3
"""
Local integration testing for REST API Client
Tests the implementation in realistic scenarios
"""

import time

from rest_api_client.config import ClientConfig, RateLimitConfig, RetryConfig
from rest_api_client.exceptions import APIClientError

from rest_api_client import APIClient


def test_simple_use_case():
    """Test basic functionality - simple GET request"""
    print("\n=== Test 1: Simple Use Case ===")
    client = APIClient(base_url="https://httpbin.org")

    try:
        response = client.get("/get")
        print(f"✅ Simple GET request successful: {response.status_code}")
        # APIResponse uses .json property, not method
        data = response.json
        print(f"   Response contains: {list(data.keys()) if data else 'No JSON data'}")
        return True
    except Exception as e:
        print(f"❌ Simple GET failed: {e}")
        return False


def test_complex_use_case():
    """Test complex functionality - POST with JSON, headers, retry"""
    print("\n=== Test 2: Complex Use Case ===")

    config = ClientConfig(
        retry_config=RetryConfig(max_retries=3),
        rate_limit_config=RateLimitConfig(requests_per_second=5),
    )
    client = APIClient(base_url="https://httpbin.org", config=config)

    try:
        # POST with JSON body
        payload = {"name": "Test User", "email": "test@example.com"}
        headers = {"X-Custom-Header": "test-value"}
        response = client.post("/post", json=payload, headers=headers)

        print(f"✅ Complex POST request successful: {response.status_code}")
        data = response.json

        # Verify payload was sent correctly
        if data.get("json") == payload:
            print("   ✅ JSON payload correctly transmitted")
        else:
            print("   ❌ JSON payload mismatch")

        # Verify headers were sent
        if "X-Custom-Header" in data.get("headers", {}):
            print("   ✅ Custom headers correctly transmitted")
        else:
            print("   ❌ Custom headers missing")

        return True
    except Exception as e:
        print(f"❌ Complex POST failed: {e}")
        return False


def test_retry_logic():
    """Test retry logic with server errors"""
    print("\n=== Test 3: Retry Logic ===")

    config = ClientConfig(
        retry_config=RetryConfig(max_retries=3, initial_delay=0.5, exponential_base=2)
    )
    client = APIClient(base_url="https://httpbin.org", config=config)

    try:
        # This endpoint returns 500 error
        start_time = time.time()
        response = client.get("/status/500")
        print(f"❌ Should have failed with server error but got: {response.status_code}")
        return False
    except APIClientError:
        elapsed = time.time() - start_time
        print("✅ Retry logic triggered on 500 error")
        print(f"   Total time with retries: {elapsed:.2f}s")

        # Check if retries happened (should take at least initial_delay * attempts)
        if elapsed >= 1.5:  # 0.5 + 1.0 = 1.5s minimum with 2 retries
            print("   ✅ Exponential backoff working correctly")
            return True
        print("   ❌ Retries may not be working properly")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_rate_limiting():
    """Test rate limiting functionality"""
    print("\n=== Test 4: Rate Limiting ===")

    config = ClientConfig(
        rate_limit_config=RateLimitConfig(
            requests_per_second=2,  # Very low rate for testing
            burst_size=2,
        )
    )
    client = APIClient(base_url="https://httpbin.org", config=config)

    try:
        start_time = time.time()

        # Make 4 rapid requests (should be rate limited)
        for i in range(4):
            response = client.get(f"/get?request={i}")
            print(f"   Request {i + 1}: {response.status_code}")

        elapsed = time.time() - start_time
        print(f"✅ Rate limiting test completed in {elapsed:.2f}s")

        # With 2 req/sec, 4 requests should take at least 1.5 seconds
        if elapsed >= 1.5:
            print("   ✅ Rate limiting working correctly")
            return True
        print("   ⚠️ Requests may be too fast, rate limiting might not be working")
        return False

    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        return False


def test_integration_points():
    """Test integration with external APIs"""
    print("\n=== Test 5: Integration Points ===")

    client = APIClient(base_url="https://httpbin.org")

    tests_passed = []

    # Test different HTTP methods
    methods = [
        ("GET", "/get", None),
        ("POST", "/post", {"test": "data"}),
        ("PUT", "/put", {"update": "data"}),
        ("DELETE", "/delete", None),
        ("PATCH", "/patch", {"patch": "data"}),
    ]

    for method, endpoint, data in methods:
        try:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=data)
            elif method == "PUT":
                response = client.put(endpoint, json=data)
            elif method == "DELETE":
                response = client.delete(endpoint)
            elif method == "PATCH":
                response = client.patch(endpoint, json=data)

            if response.status_code == 200:
                print(f"   ✅ {method} request successful")
                tests_passed.append(True)
            else:
                print(f"   ❌ {method} request failed: {response.status_code}")
                tests_passed.append(False)
        except Exception as e:
            print(f"   ❌ {method} request error: {e}")
            tests_passed.append(False)

    return all(tests_passed)


def test_no_regressions():
    """Verify existing functionality still works"""
    print("\n=== Test 6: No Regressions ===")

    # Test basic client creation
    try:
        client = APIClient("https://httpbin.org")
        print("   ✅ Basic client creation works")
    except Exception as e:
        print(f"   ❌ Basic client creation failed: {e}")
        return False

    # Test with custom config
    try:
        config = ClientConfig()
        client = APIClient("https://httpbin.org", config=config)
        print("   ✅ Client with custom config works")
    except Exception as e:
        print(f"   ❌ Client with custom config failed: {e}")
        return False

    # Test context manager
    try:
        with APIClient("https://httpbin.org") as client:
            _ = client.get("/get")
        print("   ✅ Context manager works")
    except Exception as e:
        print(f"   ❌ Context manager failed: {e}")
        return False

    return True


def main():
    """Run all local integration tests"""
    print("=" * 60)
    print("REST API Client - Local Integration Testing")
    print("Testing in realistic scenarios before committing")
    print("=" * 60)

    test_results = []

    # Run all tests
    test_results.append(("Simple Use Case", test_simple_use_case()))
    test_results.append(("Complex Use Case", test_complex_use_case()))
    test_results.append(("Retry Logic", test_retry_logic()))
    test_results.append(("Rate Limiting", test_rate_limiting()))
    test_results.append(("Integration Points", test_integration_points()))
    test_results.append(("No Regressions", test_no_regressions()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    for test_name, passed in test_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<40} {status}")

    total_passed = sum(1 for _, passed in test_results if passed)
    total_tests = len(test_results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed")

    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED - Ready to commit!")
        return 0
    print("\n⚠️ Some tests failed - Review before committing")
    return 1


if __name__ == "__main__":
    exit(main())
