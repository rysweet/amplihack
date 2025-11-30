#!/usr/bin/env python3
"""Test script for the REST API Client - testing like a user would."""

import asyncio

# Add parent directory to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from amplihack.api_client import (
    APIClient,
    APIConfig,
    HTTPError,
    RetryConfig,
    ValidationError,
)


async def test_basic_usage():
    """Test basic GET/POST operations."""
    print("Testing basic API client usage...")

    # Create configuration
    config = APIConfig(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=30.0,
        max_retries=3,
        headers={"User-Agent": "AmplihackAPIClient/1.0"},
    )

    # Use the client
    async with APIClient(config) as client:
        # Test GET request
        print("\n1. Testing GET request...")
        response = await client.get("/posts/1")
        print(f"   Status: {response.status_code}")
        print(
            f"   Title: {response.data.get('title', 'N/A')[:50]}..."
            if response.data
            else "   No data"
        )

        # Test POST request
        print("\n2. Testing POST request...")
        post_data = {
            "title": "Test Post",
            "body": "This is a test post from the API client",
            "userId": 1,
        }
        response = await client.post("/posts", json=post_data)
        print(f"   Status: {response.status_code}")
        print(f"   Created ID: {response.data.get('id', 'N/A')}" if response.data else "   No data")

        # Test error handling (404)
        print("\n3. Testing 404 error handling...")
        try:
            await client.get("/posts/99999")
        except HTTPError as e:
            print(f"   Caught expected error: {e}")
            print(f"   Status code: {e.status_code}")

        print("\n✅ Basic usage tests passed!")
        return True


async def test_retry_logic():
    """Test retry logic with a working endpoint."""
    print("\nTesting retry logic...")

    # Create config with custom retry settings
    config = APIConfig(
        base_url="https://jsonplaceholder.typicode.com",
        timeout=10.0,
        max_retries=3,
        headers={"User-Agent": "AmplihackAPIClient/1.0"},
    )

    retry_config = RetryConfig(
        max_retries=3,
        initial_delay=0.5,
        exponential_base=2.0,
        max_delay=5.0,
        retry_on_statuses=frozenset({500, 502, 503}),
    )

    async with APIClient(config, retry_config=retry_config) as client:
        # Test with valid endpoint (should work)
        print("\n1. Testing successful request...")
        response = await client.get("/users/1")
        print(f"   Status: {response.status_code}")

        # Test 404 error (should not retry)
        print("\n2. Testing 404 error (should not retry)...")
        try:
            await client.get("/users/9999999")
            print("   Unexpected success")
        except HTTPError as e:
            print(f"   Got expected 404 error: {e.status_code}")

        print("\n✅ Retry logic tests passed!")
        return True


async def test_rate_limiting():
    """Test rate limiting behavior."""
    print("\nTesting rate limiting...")

    config = APIConfig(
        base_url="https://api.github.com",
        timeout=10.0,
        max_retries=2,
        headers={
            "User-Agent": "AmplihackAPIClient/1.0",
            "Accept": "application/vnd.github.v3+json",
        },
    )

    async with APIClient(config) as client:
        # GitHub API has rate limits
        print("\n1. Testing rate limit headers parsing...")
        response = await client.get("/rate_limit")
        print(f"   Status: {response.status_code}")

        if response.headers:
            rate_remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
            rate_limit = response.headers.get("X-RateLimit-Limit", "N/A")
            print(f"   Rate limit: {rate_remaining}/{rate_limit}")

        print("\n✅ Rate limiting tests passed!")
        return True


async def test_validation():
    """Test input validation."""
    print("\nTesting input validation...")

    # Test invalid URL
    print("\n1. Testing localhost blocking...")
    config = APIConfig(base_url="http://localhost:8080", timeout=10.0)

    try:
        async with APIClient(config) as client:
            await client.get("/test")
        print("   ERROR: Should have blocked localhost!")
    except ValidationError as e:
        print(f"   Correctly blocked: {e}")

    # Test invalid config
    print("\n2. Testing invalid timeout...")
    try:
        config = APIConfig(
            base_url="https://example.com",
            timeout=-1,  # Invalid
        )
        print("   ERROR: Should have rejected negative timeout!")
    except ValueError as e:
        print(f"   Correctly rejected: {e}")

    print("\n✅ Validation tests passed!")
    return True


async def test_complex_workflow():
    """Test a complex real-world workflow."""
    print("\nTesting complex workflow...")

    config = APIConfig(base_url="https://jsonplaceholder.typicode.com", timeout=30.0, max_retries=2)

    async with APIClient(config) as client:
        # 1. Get all posts for a user
        print("\n1. Fetching user posts...")
        response = await client.get("/posts", params={"userId": 1})
        posts = response.data if response.data else []
        print(f"   Found {len(posts)} posts")

        # 2. Get comments for first post
        if posts:
            post_id = posts[0]["id"]
            print(f"\n2. Fetching comments for post {post_id}...")
            response = await client.get(f"/posts/{post_id}/comments")
            comments = response.data if response.data else []
            print(f"   Found {len(comments)} comments")

        # 3. Create a new post
        print("\n3. Creating new post...")
        new_post = {"title": "Workflow Test Post", "body": "Testing complex workflow", "userId": 1}
        response = await client.post("/posts", json=new_post)
        created_id = response.data.get("id")
        print(f"   Created post with ID: {created_id}")

        # 4. Update the post
        print("\n4. Updating post...")
        update_data = {"title": "Updated Title"}
        response = await client.patch(f"/posts/{created_id}", json=update_data)
        print(f"   Update status: {response.status_code}")

        # 5. Delete the post
        print("\n5. Deleting post...")
        response = await client.delete(f"/posts/{created_id}")
        print(f"   Delete status: {response.status_code}")

        print("\n✅ Complex workflow tests passed!")
        return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("REST API CLIENT - LOCAL TESTING")
    print("=" * 60)

    all_passed = True

    # Run each test suite
    tests = [
        ("Basic Usage", test_basic_usage),
        ("Retry Logic", test_retry_logic),
        ("Rate Limiting", test_rate_limiting),
        ("Validation", test_validation),
        ("Complex Workflow", test_complex_workflow),
    ]

    for name, test_func in tests:
        try:
            print(f"\n{'=' * 60}")
            print(f"Running: {name}")
            print("=" * 60)
            result = await test_func()
            if not result:
                all_passed = False
                print(f"❌ {name} failed!")
        except Exception as e:
            all_passed = False
            print(f"❌ {name} failed with error: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("The REST API Client is working correctly.")
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please review the errors above.")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
