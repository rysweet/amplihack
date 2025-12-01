#!/usr/bin/env python
"""Example usage of the API Client."""

from amplihack.utils import APIClient, APIError, APIRequest, RateLimitError


def main():
    """Run API Client examples."""
    # Example 1: Basic usage
    client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # Get request
    request = APIRequest(method="GET", endpoint="/posts/1")
    try:
        response = client.execute(request)
        print(f"Status: {response.status_code}")
        if response.data and isinstance(response.data, dict):
            print(f"Title: {response.data.get('title', 'Unknown')}")
    except APIError as e:
        print(f"Error: {e}")

    # Example 2: POST with data
    request = APIRequest(
        method="POST",
        endpoint="/posts",
        data={"title": "Test Post", "body": "This is a test post", "userId": 1},
        headers={"Content-Type": "application/json"},
    )

    try:
        response = client.execute(request)
        if response.data and isinstance(response.data, dict):
            print(f"Created post ID: {response.data.get('id', 'Unknown')}")
    except APIError as e:
        print(f"Error creating post: {e}")

    # Example 3: With retry and rate limiting
    client_with_retry = APIClient(
        base_url="https://api.example.com", max_retries=5, backoff_factor=2.0, timeout=10.0
    )

    # This will automatically retry on 5xx errors and handle rate limits
    request = APIRequest(
        method="GET",
        endpoint="/rate-limited-endpoint",
        headers={"Authorization": "Bearer your-token"},
    )

    try:
        response = client_with_retry.execute(request)
        print(f"Success: {response.data}")
    except RateLimitError as e:
        print(f"Rate limited! Retry after {e.retry_after} seconds")
    except APIError as e:
        print(f"API error: {e}")

    # Example 4: Using convenience methods (optional)
    response = client.get("/posts/1")
    if response.data and isinstance(response.data, dict):
        print(f"Got post: {response.data.get('title', 'Unknown')}")

    response = client.post("/posts", data={"title": "Another post", "body": "Content", "userId": 1})
    if response.data and isinstance(response.data, dict):
        print(f"Created post: {response.data.get('id', 'Unknown')}")


if __name__ == "__main__":
    main()
