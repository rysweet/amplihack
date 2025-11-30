#!/usr/bin/env python3
"""Real-world test of the REST API Client library."""

import sys

sys.path.insert(0, ".claude/scenarios/rest-api-client")

from rest_api_client import APIClient


def test_real_api():
    """Test with JSONPlaceholder API - a real test endpoint."""
    print("Testing REST API Client with real endpoint...")

    # Initialize client
    client = APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        max_retries=3,
        rate_limit_calls=10,
        rate_limit_period=1.0,
    )

    # Test GET request
    print("\n1. Testing GET request...")
    response = client.get("/users/1")
    print(f"   Status: {response.status_code}")
    print(f"   User: {response.json()['name']}")
    assert response.status_code == 200
    assert "id" in response.json()

    # Test GET with params
    print("\n2. Testing GET with query params...")
    response = client.get("/posts", params={"userId": 1})
    print(f"   Status: {response.status_code}")
    print(f"   Posts count: {len(response.json())}")
    assert response.status_code == 200
    assert len(response.json()) > 0

    # Test POST request
    print("\n3. Testing POST request...")
    new_post = {
        "title": "Test Post",
        "body": "This is a test from the REST API Client",
        "userId": 1,
    }
    response = client.post("/posts", json=new_post)
    print(f"   Status: {response.status_code}")
    print(f"   Created ID: {response.json().get('id')}")
    assert response.status_code == 201
    assert response.json()["title"] == new_post["title"]

    # Test PUT request
    print("\n4. Testing PUT request...")
    updated_post = {
        "id": 1,
        "title": "Updated Post",
        "body": "This post has been updated",
        "userId": 1,
    }
    response = client.put("/posts/1", json=updated_post)
    print(f"   Status: {response.status_code}")
    print(f"   Updated title: {response.json()['title']}")
    assert response.status_code == 200

    # Test DELETE request
    print("\n5. Testing DELETE request...")
    response = client.delete("/posts/1")
    print(f"   Status: {response.status_code}")
    assert response.status_code == 200

    # Test error handling (404)
    print("\n6. Testing error handling (404)...")
    try:
        response = client.get("/users/999999")
        print(f"   Status: {response.status_code}")
    except Exception as e:
        print(f"   Handled error: {type(e).__name__}")

    # Test rate limiting
    print("\n7. Testing rate limiting (10 requests quickly)...")
    for i in range(10):
        response = client.get(f"/users/{i + 1}")
        print(f"   Request {i + 1}: Status {response.status_code}")

    print("\n✅ All tests passed! REST API Client is working correctly!")
    return True


if __name__ == "__main__":
    try:
        test_real_api()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
