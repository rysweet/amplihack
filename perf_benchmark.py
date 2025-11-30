#!/usr/bin/env python3
"""Performance benchmark with actual HTTP requests.

Measures overhead against raw httpx performance.
"""

import statistics
import sys
import time

import httpx

sys.path.insert(
    0, "/home/azureuser/src/amplihack4/worktrees/feat-issue-1731-rest-api-client/.claude/scenarios"
)


def benchmark_raw_httpx(url="https://httpbin.org/get", iterations=10):
    """Benchmark raw httpx performance as baseline."""
    times = []

    with httpx.Client() as client:
        # Warm up
        client.get(url)

        for _ in range(iterations):
            start = time.perf_counter()
            response = client.get(url)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)

    return times


def benchmark_api_client(url="https://httpbin.org/get", iterations=10):
    """Benchmark API Client performance."""
    from rest_api_client import APIClient, APIConfig

    times = []

    config = APIConfig(
        base_url="https://httpbin.org",
        timeout=30,
        max_retries=0,  # Disable retry for fair comparison
    )

    with APIClient(config=config) as client:
        # Warm up
        client.get("/get")

        for _ in range(iterations):
            start = time.perf_counter()
            response = client.get("/get")
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)

    return times


def benchmark_overhead_only():
    """Measure just the overhead without network calls."""
    from rest_api_client import APIClient, APIConfig

    config = APIConfig(base_url="https://httpbin.org", timeout=30, max_retries=0)

    # Mock the httpx request to isolate our overhead
    def mock_request(**kwargs):
        """Mock httpx request."""

        class MockElapsed:
            def total_seconds(self):
                return 0.1

        class MockResponse:
            status_code = 200
            headers = {"content-type": "application/json"}
            text = '{"test": "data"}'
            elapsed = MockElapsed()
            url = "https://httpbin.org/get"

            def json(self):
                return {"test": "data"}

        return MockResponse()

    client = APIClient(config=config)
    # Replace httpx request with mock
    client._session.request = mock_request

    times = []
    for _ in range(1000):
        start = time.perf_counter()
        response = client.get("/get")
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        times.append(elapsed)

    client.close()
    return times


def print_stats(label, times):
    """Print statistics for a benchmark."""
    avg = statistics.mean(times)
    median = statistics.median(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0
    p99 = sorted(times)[int(len(times) * 0.99)]

    print(f"\n{label}:")
    print(f"  Average: {avg:.3f}ms")
    print(f"  Median:  {median:.3f}ms")
    print(f"  Std Dev: {stdev:.3f}ms")
    print(f"  P99:     {p99:.3f}ms")
    print(f"  Min:     {min(times):.3f}ms")
    print(f"  Max:     {max(times):.3f}ms")


def main():
    """Run benchmarks and compare performance."""
    print("=" * 60)
    print("REST API Client Performance Benchmark")
    print("=" * 60)

    print("\n[1] Testing pure overhead (no network)...")
    overhead_times = benchmark_overhead_only()
    print_stats("Pure Overhead (1000 requests)", overhead_times)

    print(f"\nOverhead per request: {statistics.mean(overhead_times):.6f}ms")

    # Check against requirement
    requirement = 1.0  # < 1ms requirement
    avg_overhead = statistics.mean(overhead_times)

    if avg_overhead < requirement:
        print(f"✅ PASS: Overhead ({avg_overhead:.3f}ms) < requirement ({requirement}ms)")
    else:
        print(f"❌ FAIL: Overhead ({avg_overhead:.3f}ms) > requirement ({requirement}ms)")

    print("\n" + "-" * 60)

    print("\n[2] Testing with actual network requests...")
    print("Note: Network latency will dominate these measurements")

    try:
        # Test with real requests (will be slower due to network)
        print("\nWarming up...")

        print("\nBenchmarking raw httpx...")
        httpx_times = benchmark_raw_httpx(iterations=10)
        print_stats("Raw httpx (baseline)", httpx_times)

        print("\nBenchmarking API Client...")
        client_times = benchmark_api_client(iterations=10)
        print_stats("API Client", client_times)

        # Calculate overhead
        avg_httpx = statistics.mean(httpx_times)
        avg_client = statistics.mean(client_times)
        overhead = avg_client - avg_httpx
        overhead_pct = (overhead / avg_httpx) * 100

        print("\n" + "-" * 60)
        print("\nComparison:")
        print(f"  Raw httpx:   {avg_httpx:.3f}ms")
        print(f"  API Client:  {avg_client:.3f}ms")
        print(f"  Overhead:    {overhead:.3f}ms ({overhead_pct:.1f}%)")

    except Exception as e:
        print(f"Network tests skipped: {e}")

    print("\n" + "=" * 60)
    print("Benchmark Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
