#!/usr/bin/env python3
"""Performance analysis for REST API Client.

Following the "measure twice, optimize once" philosophy.
"""

import cProfile
import io
import pstats
import sys
import time
from contextlib import contextmanager

# Add the REST API client to the path
sys.path.insert(
    0, "/home/azureuser/src/amplihack4/worktrees/feat-issue-1731-rest-api-client/.claude/scenarios"
)


@contextmanager
def timer(name):
    """Simple timer context manager for micro-benchmarks."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000  # Convert to milliseconds
        print(f"{name}: {elapsed:.3f}ms")


def test_initialization_overhead():
    """Measure initialization overhead."""
    print("\n=== Initialization Overhead ===")

    from rest_api_client import APIClient, APIConfig

    # Measure APIConfig creation
    with timer("APIConfig creation"):
        for _ in range(1000):
            config = APIConfig(base_url="https://api.example.com")

    # Measure APIClient creation
    config = APIConfig(base_url="https://api.example.com")
    with timer("APIClient creation (x100)"):
        for _ in range(100):
            client = APIClient(config=config)
            client.close()

    # Measure single client creation
    with timer("Single APIClient creation"):
        client = APIClient(config=config)
        client.close()


def test_rate_limiter_overhead():
    """Measure rate limiter overhead per request."""
    print("\n=== Rate Limiter Overhead ===")

    from rest_api_client.rate_limiter import RateLimiter

    # Token bucket overhead
    limiter = RateLimiter(strategy="token_bucket", capacity=100, refill_rate=10)

    with timer("TokenBucket.consume (x10000)"):
        for _ in range(10000):
            limiter.allow_request()

    # Calculate per-request overhead
    start = time.perf_counter()
    for _ in range(100000):
        limiter.allow_request()
    elapsed = (time.perf_counter() - start) * 1000
    print(f"Per-request overhead: {elapsed / 100000:.6f}ms")

    # Sliding window overhead
    limiter = RateLimiter(strategy="sliding_window", max_requests=100, window_size=60)

    with timer("SlidingWindow.allow_request (x10000)"):
        for _ in range(10000):
            limiter.allow_request()


def test_retry_calculation_overhead():
    """Measure retry delay calculation overhead."""
    print("\n=== Retry Calculation Overhead ===")

    from rest_api_client.retry import ExponentialBackoff, LinearBackoff

    # Exponential backoff
    backoff = ExponentialBackoff(initial_delay=1.0, max_delay=60.0)

    with timer("ExponentialBackoff.get_delay (x100000)"):
        for attempt in range(100000):
            delay = backoff.get_delay(attempt % 10)

    # With jitter
    backoff_jitter = ExponentialBackoff(initial_delay=1.0, max_delay=60.0, jitter=True)

    with timer("ExponentialBackoff.get_delay with jitter (x100000)"):
        for attempt in range(100000):
            delay = backoff_jitter.get_delay(attempt % 10)

    # Linear backoff
    linear = LinearBackoff(delay=5.0, increment=2.0)

    with timer("LinearBackoff.get_delay (x100000)"):
        for attempt in range(100000):
            delay = linear.get_delay(attempt % 10)


def test_logging_overhead():
    """Measure logging overhead."""
    print("\n=== Logging Overhead ===")

    import logging

    # Disable logging
    logging.disable(logging.CRITICAL)

    logger = logging.getLogger("test")

    with timer("Disabled logging.debug (x100000)"):
        for _ in range(100000):
            logger.debug("Test message with %s", "parameter")

    # Enable logging but no handlers
    logging.disable(logging.NOTSET)
    logger.setLevel(logging.ERROR)

    with timer("ERROR level logging.debug (x100000)"):
        for _ in range(100000):
            logger.debug("Test message with %s", "parameter")


def profile_request_flow():
    """Profile the entire request flow to identify bottlenecks."""
    print("\n=== Request Flow Profiling ===")

    from rest_api_client import APIClient, APIConfig

    config = APIConfig(base_url="https://httpbin.org", timeout=30, max_retries=3)

    # Create a mock request that won't actually make network calls
    def mock_execute_request(self, request):
        """Mock request execution to measure overhead without network."""
        from rest_api_client.models import Response

        return Response(
            status_code=200,
            headers={},
            json={"test": "data"},
            text='{"test": "data"}',
            elapsed=0.1,
            url="https://httpbin.org/get",
        )

    # Profile the request preparation overhead
    profiler = cProfile.Profile()

    client = APIClient(config=config)
    # Replace actual network call with mock
    original_execute = client._execute_request
    client._execute_request = mock_execute_request.__get__(client, APIClient)

    profiler.enable()

    # Make 100 requests to get meaningful profile data
    for _ in range(100):
        try:
            response = client.get("/get", params={"test": "value"})
        except Exception:
            pass  # Ignore any errors from mocking

    profiler.disable()

    # Print profiling results
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(20)  # Top 20 functions
    print(s.getvalue())

    client.close()


def test_memory_usage():
    """Test memory usage patterns."""
    print("\n=== Memory Usage Analysis ===")

    import tracemalloc

    from rest_api_client import APIClient, APIConfig

    tracemalloc.start()

    # Create multiple clients
    clients = []
    snapshot1 = tracemalloc.take_snapshot()

    for i in range(10):
        config = APIConfig(base_url=f"https://api{i}.example.com")
        client = APIClient(config=config)
        clients.append(client)

    snapshot2 = tracemalloc.take_snapshot()

    top_stats = snapshot2.compare_to(snapshot1, "lineno")

    print("[ Top 10 memory allocations ]")
    for stat in top_stats[:10]:
        print(stat)

    # Cleanup
    for client in clients:
        client.close()

    tracemalloc.stop()


def main():
    """Run all performance tests."""
    print("=" * 60)
    print("REST API Client Performance Analysis")
    print("=" * 60)

    test_initialization_overhead()
    test_rate_limiter_overhead()
    test_retry_calculation_overhead()
    test_logging_overhead()
    profile_request_flow()
    test_memory_usage()

    print("\n" + "=" * 60)
    print("Analysis Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
