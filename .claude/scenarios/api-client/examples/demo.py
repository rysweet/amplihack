#!/usr/bin/env python3
"""Demo script for the Simple API Client.

This script demonstrates the core functionality of the API client
using JSONPlaceholder (https://jsonplaceholder.typicode.com) as
a test API.

Usage:
    python demo.py

Examples shown:
    1. GET request to fetch posts
    2. GET request to fetch a single post
    3. POST request to create a new post
    4. Error handling for various failure modes
"""

import sys
from pathlib import Path

# Add parent directory to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_client import APIClient, APIError, HTTPError, RequestTimeoutError


def main():
    """Run API client demonstration."""
    print("=" * 60)
    print("Simple API Client Demo")
    print("Using JSONPlaceholder API (https://jsonplaceholder.typicode.com)")
    print("=" * 60)
    print()

    # Create client with base URL
    client = APIClient("https://jsonplaceholder.typicode.com")

    # Demo 1: GET request - fetch all posts
    print("1. GET /posts - Fetching all posts...")
    print("-" * 40)
    try:
        posts = client.get("/posts")
        print(f"   Success! Retrieved {len(posts)} posts")
        print(f"   First post title: {posts[0]['title'][:50]}...")
    except APIError as e:
        print(f"   Error: {e}")
    print()

    # Demo 2: GET request - fetch single post
    print("2. GET /posts/1 - Fetching single post...")
    print("-" * 40)
    try:
        post = client.get("/posts/1")
        print(f"   Post ID: {post['id']}")
        print(f"   Title: {post['title']}")
        print(f"   User ID: {post['userId']}")
    except APIError as e:
        print(f"   Error: {e}")
    print()

    # Demo 3: POST request - create new post
    print("3. POST /posts - Creating new post...")
    print("-" * 40)
    try:
        new_post = client.post(
            "/posts",
            {
                "title": "Hello from API Client",
                "body": "This post was created using the Simple API Client",
                "userId": 1,
            },
        )
        print(f"   Success! Created post with ID: {new_post['id']}")
        print(f"   Title: {new_post['title']}")
    except APIError as e:
        print(f"   Error: {e}")
    print()

    # Demo 4: Error handling - 404 Not Found
    print("4. GET /posts/99999 - Handling 404 error...")
    print("-" * 40)
    try:
        result = client.get("/posts/99999")
        # JSONPlaceholder returns empty object for non-existent resources
        if not result:
            print("   Resource not found (empty response)")
        else:
            print(f"   Got: {result}")
    except HTTPError as e:
        print(f"   HTTP Error {e.status_code}: {e.message}")
    except APIError as e:
        print(f"   Error: {e}")
    print()

    # Demo 5: Error handling - invalid endpoint
    print("5. GET /invalid-endpoint - Handling invalid endpoint...")
    print("-" * 40)
    try:
        result = client.get("/this-endpoint-does-not-exist")
        print(f"   Got: {result}")
    except HTTPError as e:
        print(f"   HTTP Error {e.status_code}: {e.message}")
    except APIError as e:
        print(f"   Error: {e}")
    print()

    # Demo 6: Timeout handling (using short timeout)
    print("6. Timeout handling demo...")
    print("-" * 40)
    print("   Creating client with 1 second timeout...")
    short_timeout_client = APIClient("https://jsonplaceholder.typicode.com", timeout=1)
    try:
        # This should work with a fast API
        result = short_timeout_client.get("/posts/1")
        print(f"   Fast request succeeded: {result['title'][:30]}...")
    except RequestTimeoutError as e:
        print(f"   Request timed out: {e}")
    except APIError as e:
        print(f"   Error: {e}")
    print()

    print("=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
