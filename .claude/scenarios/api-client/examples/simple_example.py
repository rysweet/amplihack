#!/usr/bin/env python3
"""Simple example of using the REST API Client."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_client import APIClient, APITimeoutError, HTTPError


def main():
    # Create a client with rate limiting and retry
    client = APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        requests_per_second=2,  # Max 2 requests per second
        max_retries=3,  # Retry up to 3 times on failure
        timeout=10,  # 10 second timeout
    )

    try:
        # GET request
        print("Fetching users...")
        response = client.get("/users")
        users = response.json()
        print(f"Found {len(users)} users")

        # GET with parameters
        print("\nFetching posts for user 1...")
        response = client.get("/posts", params={"userId": 1})
        posts = response.json()
        print(f"User 1 has {len(posts)} posts")

        # POST request
        print("\nCreating a new post...")
        new_post = {
            "title": "Test Post",
            "body": "This is a test post created with APIClient",
            "userId": 1,
        }
        response = client.post("/posts", json=new_post)
        created = response.json()
        print(f"Created post with ID: {created.get('id')}")

        # Error handling example
        print("\nTrying to fetch non-existent resource...")
        try:
            response = client.get("/users/999999")
        except HTTPError as e:
            print(f"Got expected error: {e}")

    except APITimeoutError as e:
        print(f"Request timed out: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    print("\nAll examples completed successfully!")


if __name__ == "__main__":
    main()
