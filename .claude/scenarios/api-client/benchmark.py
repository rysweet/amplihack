#!/usr/bin/env python3
"""Performance benchmark for REST API Client.

Measures actual performance to identify real bottlenecks.
Following 'measure twice, optimize once' principle.
"""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add parent directory to path to import api_client
sys.path.insert(0, str(Path(__file__).parent))
from api_client import RESTClient


class MockServerHandler(BaseHTTPRequestHandler):
    """Simple mock server for benchmarking."""

    def log_message(self, format, *args):
        """Suppress server log messages during benchmarking."""

    def do_GET(self):
        """Handle GET requests with minimal processing."""
        time.sleep(0.01)  # Simulate 10ms network latency
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = json.dumps({"status": "ok", "data": "x" * 100})
        self.wfile.write(response.encode())

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        _ = self.rfile.read(content_length)
        time.sleep(0.01)  # Simulate processing
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"id": 123}')


def start_mock_server(port=8888):
    """Start mock server in background thread."""
    server = HTTPServer(("localhost", port), MockServerHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server


def benchmark_sequential_requests(client, num_requests=100):
    """Benchmark sequential requests."""
    start = time.time()

    for i in range(num_requests):
        response = client.get(f"/test/{i}")
        if response.status_code != 200:
            print(f"Request {i} failed: {response.status_code}")

    elapsed = time.time() - start
    rps = num_requests / elapsed

    return {
        "total_time": elapsed,
        "requests_per_second": rps,
        "avg_latency_ms": (elapsed / num_requests) * 1000,
    }


def benchmark_rate_limited(client, num_requests=50, rate_limit=10):
    """Benchmark with rate limiting."""
    client.requests_per_second = rate_limit
    start = time.time()

    for i in range(num_requests):
        response = client.get(f"/test/{i}")
        if response.status_code != 200:
            print(f"Request {i} failed: {response.status_code}")

    elapsed = time.time() - start
    expected_time = num_requests / rate_limit
    overhead = elapsed - expected_time

    return {
        "total_time": elapsed,
        "expected_time": expected_time,
        "overhead_seconds": overhead,
        "overhead_percent": (overhead / expected_time) * 100,
    }


def benchmark_parallel_requests(client, num_requests=100, num_threads=4):
    """Benchmark parallel requests from multiple threads."""
    errors = []

    def worker(thread_id, requests_per_thread):
        for i in range(requests_per_thread):
            try:
                response = client.get(f"/test/{thread_id}_{i}")
                if response.status_code != 200:
                    errors.append(f"Thread {thread_id}, Request {i}: {response.status_code}")
            except Exception as e:
                errors.append(f"Thread {thread_id}, Request {i}: {e}")

    threads = []
    requests_per_thread = num_requests // num_threads

    start = time.time()

    for tid in range(num_threads):
        t = threading.Thread(target=worker, args=(tid, requests_per_thread))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    elapsed = time.time() - start

    return {
        "total_time": elapsed,
        "requests_per_second": num_requests / elapsed,
        "errors": len(errors),
        "error_rate": len(errors) / num_requests * 100,
    }


def benchmark_memory_usage():
    """Check memory usage of Response objects."""
    import sys

    # Small response
    small_response = {"data": "x" * 100}
    small_json = json.dumps(small_response).encode()

    # Large response (1MB)
    large_response = {"data": "x" * 1000000}
    large_json = json.dumps(large_response).encode()

    from api_client.models import Response

    small_resp = Response(200, {}, small_json, "http://test")
    large_resp = Response(200, {}, large_json, "http://test")

    return {
        "small_response_size": sys.getsizeof(small_resp.body),
        "large_response_size": sys.getsizeof(large_resp.body),
        "response_object_overhead": sys.getsizeof(small_resp) - sys.getsizeof(small_resp.body),
    }


def main():
    """Run all benchmarks."""
    print("REST API Client Performance Benchmark")
    print("=" * 50)

    # Start mock server
    print("\nStarting mock server on port 8888...")
    server = start_mock_server(8888)
    time.sleep(1)  # Give server time to start

    # Create client
    client = RESTClient("http://localhost:8888")

    # Warm up
    print("Warming up...")
    for _ in range(10):
        client.get("/warmup")

    # Benchmark 1: Sequential requests
    print("\n1. Sequential Requests (100 requests)")
    print("-" * 30)
    results = benchmark_sequential_requests(client, 100)
    print(f"Total time: {results['total_time']:.2f}s")
    print(f"Requests/second: {results['requests_per_second']:.1f}")
    print(f"Avg latency: {results['avg_latency_ms']:.1f}ms")

    # Benchmark 2: Rate limiting overhead
    print("\n2. Rate Limiting Overhead (50 requests @ 10/s)")
    print("-" * 30)
    results = benchmark_rate_limited(client, 50, 10)
    print(f"Total time: {results['total_time']:.2f}s")
    print(f"Expected time: {results['expected_time']:.2f}s")
    print(f"Overhead: {results['overhead_seconds']:.2f}s ({results['overhead_percent']:.1f}%)")

    # Benchmark 3: Thread safety
    print("\n3. Parallel Requests (100 requests, 4 threads)")
    print("-" * 30)
    results = benchmark_parallel_requests(client, 100, 4)
    print(f"Total time: {results['total_time']:.2f}s")
    print(f"Requests/second: {results['requests_per_second']:.1f}")
    print(f"Errors: {results['errors']} ({results['error_rate']:.1f}%)")

    # Benchmark 4: Memory usage
    print("\n4. Memory Usage")
    print("-" * 30)
    results = benchmark_memory_usage()
    print(f"Small response (100 bytes): {results['small_response_size']} bytes")
    print(f"Large response (1MB): {results['large_response_size'] / 1024 / 1024:.2f} MB")
    print(f"Response object overhead: {results['response_object_overhead']} bytes")

    # Shutdown server
    server.shutdown()

    print("\n" + "=" * 50)
    print("Benchmark complete!")


if __name__ == "__main__":
    main()
