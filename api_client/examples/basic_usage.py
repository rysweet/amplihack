"""Basic usage examples for API client.

This example demonstrates:
- Creating an APIClient
- Making simple GET/POST requests
- Handling responses
- Using context manager
"""

from api_client import APIClient, Request


def example_simple_get():
    """Example: Simple GET request."""
    print("=== Simple GET Request ===")

    client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # Create GET request
    request = Request(method="GET", endpoint="/posts/1")

    # Send request
    response = client.send(request)

    print(f"Status: {response.status_code}")
    print(f"Data: {response.data}")
    print(f"Elapsed: {response.elapsed_seconds:.3f}s")
    print()

    client.close()


def example_simple_post():
    """Example: Simple POST request with data."""
    print("=== Simple POST Request ===")

    client = APIClient(base_url="https://jsonplaceholder.typicode.com")

    # Create POST request with data
    request = Request(
        method="POST",
        endpoint="/posts",
        data={
            "title": "My Post",
            "body": "This is the post content",
            "userId": 1,
        },
    )

    # Send request
    response = client.send(request)

    print(f"Status: {response.status_code}")
    print(f"Created ID: {response.data.get('id')}")
    print()

    client.close()


def example_with_context_manager():
    """Example: Using client as context manager."""
    print("=== Using Context Manager ===")

    with APIClient(base_url="https://jsonplaceholder.typicode.com") as client:
        # Make multiple requests
        for post_id in range(1, 4):
            request = Request(method="GET", endpoint=f"/posts/{post_id}")
            response = client.send(request)
            print(f"Post {post_id}: {response.data.get('title')}")

    print("Client automatically closed")
    print()


def example_with_custom_headers():
    """Example: Request with custom headers."""
    print("=== Custom Headers ===")

    # Create client with default headers
    client = APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        default_headers={"User-Agent": "MyApp/1.0"},
    )

    # Create request with additional headers
    request = Request(
        method="GET",
        endpoint="/posts/1",
        headers={"X-Request-ID": "12345"},
    )

    response = client.send(request)
    print(f"Status: {response.status_code}")
    print(f"Title: {response.data.get('title')}")
    print()

    client.close()


def example_with_query_params():
    """Example: Request with query parameters."""
    print("=== Query Parameters ===")

    with APIClient(base_url="https://jsonplaceholder.typicode.com") as client:
        # Search with query params
        request = Request(
            method="GET",
            endpoint="/posts",
            params={"userId": "1", "_limit": "3"},
        )

        response = client.send(request)
        print(f"Found {len(response.data)} posts")
        for post in response.data:
            print(f"  - {post['title']}")

    print()


def example_error_handling():
    """Example: Handling errors."""
    print("=== Error Handling ===")

    from api_client.exceptions import RequestError, ResponseError

    with APIClient(base_url="https://jsonplaceholder.typicode.com") as client:
        try:
            # Try to get non-existent resource
            request = Request(method="GET", endpoint="/posts/999999")
            response = client.send(request)

            if response.status_code == 404:
                print("Resource not found!")
            elif response.is_success:
                print(f"Success: {response.data}")

        except RequestError as e:
            print(f"Request failed: {e}")
        except ResponseError as e:
            print(f"Response error: {e}")

    print()


if __name__ == "__main__":
    # Run all examples
    example_simple_get()
    example_simple_post()
    example_with_context_manager()
    example_with_custom_headers()
    example_with_query_params()
    example_error_handling()

    print("All examples completed!")
