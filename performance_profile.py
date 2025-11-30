#!/usr/bin/env python3
"""Performance profiling script for REST API Client.

Measures actual bottlenecks using cProfile and memory_profiler.
Following "measure twice, optimize once" principle.
"""

import cProfile
import io
import pstats
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rest_api_client import APIClient
from rest_api_client.config import RateLimitConfig, RetryConfig


def profile_token_bucket():
    """Profile token bucket rate limiting algorithm."""
    from rest_api_client.rate_limiter import TokenBucket

    # High throughput config
    config = RateLimitConfig(
        max_tokens=100,
        refill_rate=50.0,  # 50 tokens per second
        initial_tokens=100,
    )

    bucket = TokenBucket(config)

    # Simulate 1000 token consumptions
    start = time.perf_counter()
    consumed = 0
    for _ in range(1000):
        if bucket.consume(1):
            consumed += 1
        # Simulate work
        time.sleep(0.0001)  # 0.1ms

    elapsed = time.perf_counter() - start
    throughput = consumed / elapsed

    return {
        "tokens_consumed": consumed,
        "elapsed_time": elapsed,
        "throughput": throughput,
        "overhead_per_token": (elapsed / consumed - 0.0001) * 1000,  # ms
    }


def profile_exponential_backoff():
    """Profile exponential backoff calculation."""
    from rest_api_client.retry import RetryHandler

    config = RetryConfig(
        max_retries=5, base_delay=1.0, max_delay=60.0, exponential_base=2, jitter=0.1
    )

    handler = RetryHandler(config)

    # Time 1000 delay calculations
    start = time.perf_counter()
    delays = []
    for attempt in range(1000):
        delay = handler.calculate_delay(attempt % 5 + 1)
        delays.append(delay)

    elapsed = time.perf_counter() - start

    return {
        "calculations": 1000,
        "elapsed_time": elapsed,
        "time_per_calc_us": (elapsed / 1000) * 1_000_000,  # microseconds
        "avg_delay": sum(delays) / len(delays),
    }


def profile_connection_pooling():
    """Profile connection pooling efficiency."""
    import httpx

    from rest_api_client.config import ClientConfig
    from rest_api_client.session import SessionManager

    config = ClientConfig(base_url="http://localhost:8888", timeout=30.0)

    manager = SessionManager(config)

    # Profile reusing connection
    start = time.perf_counter()
    client = manager.get_sync_client()
    for _ in range(100):
        # Simulate getting client (should be instant after first)
        _ = manager.get_sync_client()

    reuse_time = time.perf_counter() - start

    # Profile creating new connections
    start = time.perf_counter()
    clients = []
    for _ in range(10):
        new_client = httpx.Client(base_url="http://localhost:8888", timeout=30.0)
        clients.append(new_client)

    create_time = time.perf_counter() - start

    # Cleanup
    manager.close()
    for c in clients:
        c.close()

    return {
        "reuse_100_calls_ms": reuse_time * 1000,
        "create_10_clients_ms": create_time * 1000,
        "reuse_per_call_us": (reuse_time / 100) * 1_000_000,
        "create_per_client_ms": (create_time / 10) * 1000,
    }


def profile_memory_usage():
    """Profile memory usage of key components."""
    import sys

    from rest_api_client.models import APIRequest, APIResponse

    # Create sample objects
    request = APIRequest(
        method="GET",
        url="http://api.example.com/endpoint",
        headers={"Authorization": "Bearer token", "Content-Type": "application/json"},
        params={"page": 1, "limit": 100},
        timeout=30.0,
    )

    response = APIResponse(
        status_code=200,
        headers={"Content-Type": "application/json", "X-Rate-Limit": "100"},
        body='{"data": "x" * 1000}',  # ~1KB response
        request=request,
        elapsed_time=0.123,
    )

    # Large response
    large_response = APIResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body='{"data": "' + "x" * 1_000_000 + '"}',  # ~1MB response
        request=request,
        elapsed_time=0.456,
    )

    return {
        "request_size": sys.getsizeof(request),
        "small_response_size": sys.getsizeof(response),
        "large_response_size": sys.getsizeof(large_response),
        "json_parse_overhead": sys.getsizeof(response.json_data) if response.json_data else 0,
    }


def run_full_profile():
    """Run full cProfile analysis."""
    profiler = cProfile.Profile()

    # Create client
    client = APIClient(
        base_url="http://httpbin.org",
        max_retries=3,
        retry_delay=1.0,
        rate_limit_config=RateLimitConfig(max_tokens=10, refill_rate=2.0),
    )

    profiler.enable()

    # Simulate 50 requests
    for i in range(50):
        try:
            # This will fail but we want to profile the client logic
            client.get("/status/200", timeout=0.1, skip_retry=True)
        except:
            pass

    profiler.disable()

    # Get statistics
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
    ps.print_stats(20)  # Top 20 functions

    return s.getvalue()


def main():
    """Run all performance profiles."""
    print("🏴‍☠️ REST API Client Performance Analysis")
    print("=" * 60)
    print("Measurin' actual bottlenecks, not hypothetical ones!")
    print()

    # 1. Token Bucket Performance
    print("1. Token Bucket Rate Limiting")
    print("-" * 30)
    results = profile_token_bucket()
    print(f"Tokens consumed: {results['tokens_consumed']}")
    print(f"Throughput: {results['throughput']:.1f} tokens/sec")
    print(f"Overhead per token: {results['overhead_per_token']:.3f}ms")
    print()

    # 2. Exponential Backoff
    print("2. Exponential Backoff Calculation")
    print("-" * 30)
    results = profile_exponential_backoff()
    print(f"Calculations: {results['calculations']}")
    print(f"Time per calculation: {results['time_per_calc_us']:.2f}μs")
    print(f"Average delay: {results['avg_delay']:.2f}s")
    print()

    # 3. Connection Pooling
    print("3. Connection Pooling Efficiency")
    print("-" * 30)
    results = profile_connection_pooling()
    print(f"Reuse 100 calls: {results['reuse_100_calls_ms']:.2f}ms")
    print(f"Create 10 clients: {results['create_10_clients_ms']:.2f}ms")
    print(f"Reuse overhead: {results['reuse_per_call_us']:.2f}μs per call")
    print(f"Create overhead: {results['create_per_client_ms']:.2f}ms per client")
    print()

    # 4. Memory Usage
    print("4. Memory Usage Analysis")
    print("-" * 30)
    results = profile_memory_usage()
    print(f"Request object: {results['request_size']} bytes")
    print(f"Small response (1KB): {results['small_response_size']} bytes")
    print(f"Large response (1MB): {results['large_response_size'] / 1024:.1f} KB")
    print()

    # 5. Full cProfile
    print("5. Full cProfile Analysis (Top Functions)")
    print("-" * 30)
    profile_output = run_full_profile()
    # Print first 10 lines of profile
    lines = profile_output.split("\n")
    for line in lines[:15]:
        if line.strip():
            print(line)

    print("\n" + "=" * 60)
    print("Analysis complete!")


if __name__ == "__main__":
    main()
