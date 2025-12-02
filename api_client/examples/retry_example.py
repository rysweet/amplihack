"""Retry logic examples for API client.

This example demonstrates:
- Configuring retry handler
- Automatic retries on failures
- Exponential backoff behavior
- Retry exhaustion handling
"""

from api_client import APIClient, Request, RetryHandler
from api_client.exceptions import RetryExhaustedError


def example_with_retry():
    """Example: Client with retry handler."""
    print("=== Client with Retry Handler ===")

    # Configure retry handler
    retry_handler = RetryHandler(
        max_retries=3,  # Retry up to 3 times
        base_delay=1.0,  # Start with 1 second delay
        multiplier=2.0,  # Double delay each retry
        max_delay=10.0,  # Cap delay at 10 seconds
    )

    client = APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        retry_handler=retry_handler,
    )

    # This request will succeed immediately
    request = Request(method="GET", endpoint="/posts/1")
    response = client.send(request)

    print(f"Status: {response.status_code}")
    print(f"Success: {response.is_success}")
    print()

    client.close()


def example_retry_on_server_error():
    """Example: Retry on transient server errors.

    Note: This example uses a public API that should be stable.
    In real scenarios, you'd see retries when the server returns 5xx errors.
    """
    print("=== Retry on Server Errors ===")

    retry_handler = RetryHandler(
        max_retries=2,
        base_delay=0.5,  # Shorter delay for example
    )

    with APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        retry_handler=retry_handler,
    ) as client:
        # Try to access endpoint
        request = Request(method="GET", endpoint="/posts/1")

        try:
            response = client.send(request)
            print(f"Request succeeded: {response.status_code}")
        except RetryExhaustedError as e:
            print(f"All retries failed: {e}")
            print(f"Attempts made: {e.context['attempts']}")
            print(f"Last error: {e.context.get('last_error')}")

    print()


def example_custom_retry_delays():
    """Example: Custom retry delay calculation."""
    print("=== Custom Retry Delays ===")

    # Quick retries with small delays
    fast_retry = RetryHandler(
        max_retries=5,
        base_delay=0.1,  # Start with 100ms
        multiplier=1.5,  # Slower growth
    )

    # Aggressive retries with longer delays
    slow_retry = RetryHandler(
        max_retries=3,
        base_delay=5.0,  # Start with 5 seconds
        multiplier=3.0,  # Aggressive growth
        max_delay=30.0,
    )

    print("Fast retry delays:")
    for attempt in range(5):
        delay = fast_retry._calculate_delay(attempt)
        print(f"  Attempt {attempt + 1}: {delay:.3f}s")

    print("\nSlow retry delays:")
    for attempt in range(3):
        delay = slow_retry._calculate_delay(attempt)
        print(f"  Attempt {attempt + 1}: {delay:.1f}s")

    print()


def example_no_retry():
    """Example: Client with no retries."""
    print("=== No Retry (Fail Fast) ===")

    # Configure handler with 0 retries for fail-fast behavior
    no_retry = RetryHandler(max_retries=0)

    with APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        retry_handler=no_retry,
    ) as client:
        request = Request(method="GET", endpoint="/posts/1")
        response = client.send(request)

        print(f"Status: {response.status_code}")
        print("No retries - fails immediately on error")

    print()


def example_retry_with_logging():
    """Example: Observe retry behavior with logging."""
    print("=== Retry with Logging ===")

    import logging

    # Enable logging to see retry attempts
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    retry_handler = RetryHandler(
        max_retries=2,
        base_delay=0.5,
    )

    with APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        retry_handler=retry_handler,
    ) as client:
        request = Request(method="GET", endpoint="/posts/1")
        response = client.send(request)

        print(f"\nFinal status: {response.status_code}")

    print()


if __name__ == "__main__":
    # Run all examples
    example_with_retry()
    example_retry_on_server_error()
    example_custom_retry_delays()
    example_no_retry()
    example_retry_with_logging()

    print("All retry examples completed!")
