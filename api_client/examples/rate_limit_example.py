"""Rate limiting examples for API client.

This example demonstrates:
- Configuring rate limiter
- Request throttling behavior
- Handling rate limits
- Thread-safe rate limiting
"""

import threading
import time

from api_client import APIClient, RateLimiter, Request


def example_basic_rate_limiting():
    """Example: Basic rate limiting."""
    print("=== Basic Rate Limiting ===")

    # Allow 5 requests per second
    limiter = RateLimiter(max_requests=5, time_window=1.0)

    client = APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        rate_limiter=limiter,
    )

    # Make 10 requests
    print("Making 10 requests (limit: 5/sec)...")
    start = time.monotonic()

    for i in range(10):
        request = Request(method="GET", endpoint=f"/posts/{i + 1}")
        response = client.send(request)
        print(f"Request {i + 1}: {response.status_code} ({time.monotonic() - start:.3f}s)")

    elapsed = time.monotonic() - start
    print(f"\nTotal time: {elapsed:.3f}s")
    print("Notice: First 5 requests are fast, then throttling kicks in")
    print()

    client.close()


def example_conservative_rate_limiting():
    """Example: Conservative rate limiting for strict APIs."""
    print("=== Conservative Rate Limiting ===")

    # Very conservative: 1 request per 2 seconds
    limiter = RateLimiter(max_requests=1, time_window=2.0)

    with APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        rate_limiter=limiter,
    ) as client:
        print("Making 3 requests (limit: 1 per 2 seconds)...")
        start = time.monotonic()

        for i in range(3):
            request = Request(method="GET", endpoint=f"/posts/{i + 1}")
            response = client.send(request)
            elapsed = time.monotonic() - start
            print(f"Request {i + 1}: {response.status_code} at {elapsed:.3f}s")

        print(f"\nTotal time: {time.monotonic() - start:.3f}s")

    print()


def example_burst_then_steady():
    """Example: Burst of requests then steady rate."""
    print("=== Burst Then Steady Rate ===")

    # Allow burst of 10, then 10/minute steady rate
    limiter = RateLimiter(max_requests=10, time_window=60.0)

    with APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        rate_limiter=limiter,
    ) as client:
        print("Burst phase: 10 quick requests...")
        start = time.monotonic()

        # Burst of 10 requests (should be fast)
        for i in range(10):
            request = Request(method="GET", endpoint=f"/posts/{i + 1}")
            _ = client.send(request)

        burst_time = time.monotonic() - start
        print(f"Burst completed in {burst_time:.3f}s")

        print("\nSteady phase: Next request must wait...")
        request = Request(method="GET", endpoint="/posts/11")
        _ = client.send(request)

        total_time = time.monotonic() - start
        print(f"11th request completed at {total_time:.3f}s")

    print()


def example_check_available_tokens():
    """Example: Checking available tokens."""
    print("=== Checking Available Tokens ===")

    limiter = RateLimiter(max_requests=5, time_window=1.0)

    print(f"Initial tokens: {limiter.available_tokens:.1f}")

    # Consume some tokens
    for i in range(3):
        limiter.acquire()
        print(f"After request {i + 1}: {limiter.available_tokens:.1f} tokens")

    # Wait for refill
    print("\nWaiting 0.5 seconds for refill...")
    time.sleep(0.5)
    print(f"After refill: {limiter.available_tokens:.1f} tokens")

    print()


def example_reset_rate_limiter():
    """Example: Resetting rate limiter."""
    print("=== Reset Rate Limiter ===")

    limiter = RateLimiter(max_requests=5, time_window=1.0)

    # Consume all tokens
    for _ in range(5):
        limiter.acquire()

    print(f"After consuming all: {limiter.available_tokens:.1f} tokens")

    # Reset
    limiter.reset()
    print(f"After reset: {limiter.available_tokens:.1f} tokens")

    print()


def example_concurrent_requests():
    """Example: Thread-safe concurrent requests."""
    print("=== Concurrent Requests (Thread-Safe) ===")

    limiter = RateLimiter(max_requests=10, time_window=1.0)

    with APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        rate_limiter=limiter,
    ) as client:
        results = []

        def make_request(post_id):
            """Make request in thread."""
            request = Request(method="GET", endpoint=f"/posts/{post_id}")
            response = client.send(request)
            results.append(response.status_code)

        print("Launching 20 concurrent threads (limit: 10/sec)...")
        start = time.monotonic()

        threads = [threading.Thread(target=make_request, args=(i,)) for i in range(1, 21)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        elapsed = time.monotonic() - start
        print(f"All 20 requests completed in {elapsed:.3f}s")
        print(f"Success rate: {sum(1 for s in results if s == 200)}/{len(results)}")

    print()


def example_rate_limit_timeout():
    """Example: Rate limit acquisition timeout."""
    print("=== Rate Limit Timeout ===")

    from api_client.exceptions import RateLimitError

    # Very restrictive limit
    limiter = RateLimiter(max_requests=1, time_window=10.0)

    with APIClient(
        base_url="https://jsonplaceholder.typicode.com",
        rate_limiter=limiter,
    ) as client:
        # First request succeeds
        request = Request(method="GET", endpoint="/posts/1")
        response = client.send(request)
        print(f"First request: {response.status_code}")

        print("\nSecond request will timeout...")
        try:
            # Note: APIClient uses 30s timeout internally
            # This example shows the concept, but won't actually timeout
            # in practice because we'd wait for token refill
            request = Request(method="GET", endpoint="/posts/2")
            response = client.send(request)
            print(f"Second request: {response.status_code}")
        except RateLimitError as e:
            print(f"Rate limit error: {e}")

    print()


if __name__ == "__main__":
    # Run all examples
    example_basic_rate_limiting()
    example_conservative_rate_limiting()
    example_burst_then_steady()
    example_check_available_tokens()
    example_reset_rate_limiter()
    example_concurrent_requests()
    example_rate_limit_timeout()

    print("All rate limiting examples completed!")
