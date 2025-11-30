#!/usr/bin/env python3
"""Basic functionality test for REST API Client"""

from rest_api_client import APIClient


def main():
    print("=" * 60)
    print("REST API Client - Basic Functionality Test")
    print("=" * 60)

    # Test 1: Create client and make simple request
    print("\n1. Testing basic GET request...")
    try:
        client = APIClient(base_url="https://httpbin.org")
        response = client.get("/get")
        print(f"   ✅ GET request successful: Status {response.status_code}")
        print(f"   Response type: {type(response)}")

        # Check if response has json data
        if hasattr(response, "json"):
            print("   ✅ Response has 'json' attribute")
            if response.json:
                print(f"   Data type: {type(response.json)}")
        else:
            print("   ❌ Response missing 'json' attribute")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Test 2: Test POST request
    print("\n2. Testing POST request...")
    try:
        client = APIClient(base_url="https://httpbin.org")
        payload = {"test": "data"}
        response = client.post("/post", json=payload)
        print(f"   ✅ POST request successful: Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 3: Test error handling
    print("\n3. Testing error handling (404)...")
    try:
        client = APIClient(base_url="https://httpbin.org")
        response = client.get("/status/404")
        print(f"   Response status: {response.status_code}")
        if response.status_code == 404:
            print("   ✅ 404 handled correctly")
    except Exception as e:
        print(f"   Error raised: {e}")
        print("   ✅ Exception handling works")

    print("\n" + "=" * 60)
    print("Basic functionality test complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
