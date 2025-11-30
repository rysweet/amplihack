#!/usr/bin/env python3
"""Local testing of REST API Client - testing like a user would."""

import sys

sys.path.insert(0, ".")

from api_client import RESTClient

# Import exceptions that actually exist


def test_simple_use_case():
    """Test basic functionality - GET request to a public API."""
    print("Test 1: Simple GET request...")
    client = RESTClient("https://jsonplaceholder.typicode.com")

    try:
        response = client.get("/posts/1")
        print(f"✓ Status: {response.status_code}")
        data = response.json()
        print(f"✓ Got post with title: {data['title'][:30]}...")
        assert response.status_code == 200
        print("✓ Simple use case PASSED")
    except Exception as e:
        print(f"✗ Simple use case FAILED: {e}")
        return False
    return True


def test_complex_use_case():
    """Test complex functionality - POST with JSON data."""
    print("\nTest 2: Complex POST request with JSON...")
    client = RESTClient("https://jsonplaceholder.typicode.com")

    try:
        post_data = {
            "title": "REST API Client Test",
            "body": "Testing our consolidated implementation",
            "userId": 1,
        }
        response = client.post("/posts", json=post_data)
        print(f"✓ Status: {response.status_code}")
        data = response.json()
        print(f"✓ Created post with ID: {data.get('id', 'N/A')}")
        assert response.status_code in [200, 201]
        print("✓ Complex use case PASSED")
    except Exception as e:
        print(f"✗ Complex use case FAILED: {e}")
        return False
    return True


def test_error_handling():
    """Test error handling - 404 response."""
    print("\nTest 3: Error handling (404)...")
    client = RESTClient("https://jsonplaceholder.typicode.com")

    try:
        response = client.get("/posts/999999")  # Doesn't exist
        print(f"✓ Status: {response.status_code}")
        if response.status_code == 404:
            print("✓ 404 handled gracefully")
            print("✓ Error handling PASSED")
            return True
        print(f"✗ Expected 404, got {response.status_code}")
        return False
    except Exception as e:
        print(f"✗ Error handling FAILED: {e}")
        return False


def test_rate_limiting():
    """Test rate limiting - rapid requests."""
    print("\nTest 4: Rate limiting (10 rapid requests)...")
    client = RESTClient(
        "https://jsonplaceholder.typicode.com",
        requests_per_second=5,  # Limit to 5 req/s
    )

    import time

    start = time.time()
    try:
        for i in range(10):
            response = client.get(f"/posts/{i + 1}")
            print(f"  Request {i + 1}: {response.status_code}", end="")
            if i < 9:
                print(" ->", end="")
        elapsed = time.time() - start
        print(f"\n✓ 10 requests took {elapsed:.1f}s (expected ~2s for 5 req/s)")
        # With 5 req/s limit, 10 requests should take ~2 seconds
        assert elapsed >= 1.8  # Allow some margin
        print("✓ Rate limiting PASSED")
        return True
    except Exception as e:
        print(f"\n✗ Rate limiting FAILED: {e}")
        return False


def test_integration_points():
    """Test integration with different APIs."""
    print("\nTest 5: Integration with multiple endpoints...")
    client = RESTClient("https://jsonplaceholder.typicode.com")

    try:
        # Test different HTTP methods
        get_resp = client.get("/users/1")
        print(f"✓ GET /users/1: {get_resp.status_code}")

        put_data = {"name": "Updated Name"}
        put_resp = client.put("/users/1", json=put_data)
        print(f"✓ PUT /users/1: {put_resp.status_code}")

        delete_resp = client.delete("/posts/1")
        print(f"✓ DELETE /posts/1: {delete_resp.status_code}")

        print("✓ Integration points PASSED")
        return True
    except Exception as e:
        print(f"✗ Integration FAILED: {e}")
        return False


def main():
    """Run all local tests."""
    print("=" * 60)
    print("REST API CLIENT - LOCAL TESTING")
    print("Testing like a user would use the feature")
    print("=" * 60)

    tests = [
        test_simple_use_case,
        test_complex_use_case,
        test_error_handling,
        test_rate_limiting,
        test_integration_points,
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test_func.__name__} crashed: {e}")
            results.append(False)

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Tests Passed: {passed}/{total}")

    if passed == total:
        print("✓ ALL LOCAL TESTS PASSED - Ready for commit!")
        return 0
    print("✗ Some tests failed - needs fixing")
    return 1


if __name__ == "__main__":
    sys.exit(main())
