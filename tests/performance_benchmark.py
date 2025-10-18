#!/usr/bin/env python3
"""
Performance benchmark tool for LiteLLM proxy optimization.
Measures baseline performance metrics and identifies optimization opportunities.
"""

import json
import os
import sys
import time
import traceback
from typing import Dict

import psutil  # type: ignore[import-untyped]
import requests  # type: ignore[import-untyped]


class ProxyBenchmark:
    """Benchmarks LiteLLM proxy performance and identifies optimization opportunities."""

    def __init__(self, proxy_url: str = "http://127.0.0.1:9001"):
        self.proxy_url = proxy_url
        self.results: Dict = {}

    def benchmark_startup_performance(self) -> Dict:
        """Benchmark proxy startup time and initialization."""
        print("🚀 Benchmarking startup performance...")

        startup_metrics = {}

        # Test if proxy is already running
        if self._is_proxy_running():
            print("  ⚠️  Proxy already running - measuring warm restart")
            startup_metrics["initial_state"] = "running"
        else:
            print("  📊 Proxy not running - measuring cold start")
            startup_metrics["initial_state"] = "stopped"

        # Measure basic connectivity
        start_time = time.time()
        try:
            response = requests.get(f"{self.proxy_url}/health", timeout=5)
            health_check_time = time.time() - start_time
            startup_metrics["health_check_latency"] = health_check_time * 1000  # ms
            startup_metrics["health_check_status"] = response.status_code
        except requests.RequestException as e:
            startup_metrics["health_check_latency"] = None
            startup_metrics["health_check_error"] = str(e)

        return startup_metrics

    def benchmark_memory_usage(self) -> Dict:
        """Benchmark memory usage patterns."""
        print("🧠 Benchmarking memory usage...")

        memory_metrics = {}

        # System memory
        system_memory = psutil.virtual_memory()
        memory_metrics["system_total_mb"] = system_memory.total / 1024 / 1024
        memory_metrics["system_used_mb"] = system_memory.used / 1024 / 1024
        memory_metrics["system_available_mb"] = system_memory.available / 1024 / 1024

        # Try to find proxy process
        proxy_processes = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if any(
                    "litellm" in str(cmd).lower() or "proxy" in str(cmd).lower()
                    for cmd in proc.info["cmdline"] or []
                ):
                    proxy_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if proxy_processes:
            total_memory = 0
            memory_metrics["proxy_processes"] = []

            for proc in proxy_processes:
                try:
                    proc_info = proc.as_dict(attrs=["pid", "memory_info", "cpu_percent"])
                    proc_memory_mb = proc_info["memory_info"].rss / 1024 / 1024
                    total_memory += proc_memory_mb

                    memory_metrics["proxy_processes"].append(
                        {
                            "pid": proc_info["pid"],
                            "memory_mb": proc_memory_mb,
                            "cpu_percent": proc_info["cpu_percent"],
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            memory_metrics["total_proxy_memory_mb"] = total_memory
        else:
            memory_metrics["proxy_processes"] = []
            memory_metrics["total_proxy_memory_mb"] = 0

        return memory_metrics

    def benchmark_response_times(self, num_requests: int = 10) -> Dict:
        """Benchmark request/response latency."""
        print(f"⚡ Benchmarking response times ({num_requests} requests)...")

        response_metrics = {
            "num_requests": num_requests,
            "latencies_ms": [],
            "successful_requests": 0,
            "failed_requests": 0,
            "errors": [],
        }

        test_request = {
            "model": "gpt-5",
            "messages": [{"role": "user", "content": "Performance test request"}],
            "max_tokens": 50,
            "temperature": 1.0,
        }

        headers = {"Authorization": "Bearer test-key", "Content-Type": "application/json"}

        for i in range(num_requests):
            start_time = time.time()
            try:
                response = requests.post(
                    f"{self.proxy_url}/v1/chat/completions",
                    json=test_request,
                    headers=headers,
                    timeout=30,
                )

                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                response_metrics["latencies_ms"].append(latency_ms)

                if response.status_code == 200:
                    response_metrics["successful_requests"] += 1
                else:
                    response_metrics["failed_requests"] += 1
                    response_metrics["errors"].append(
                        {
                            "request_id": i,
                            "status_code": response.status_code,
                            "error": response.text[:200],  # Truncate long errors
                        }
                    )

            except requests.RequestException as e:
                end_time = time.time()
                latency_ms = (end_time - start_time) * 1000
                response_metrics["latencies_ms"].append(latency_ms)
                response_metrics["failed_requests"] += 1
                response_metrics["errors"].append({"request_id": i, "error": str(e)[:200]})

            # Small delay between requests
            time.sleep(0.1)

        # Calculate statistics
        if response_metrics["latencies_ms"]:
            latencies = response_metrics["latencies_ms"]
            response_metrics["avg_latency_ms"] = sum(latencies) / len(latencies)
            response_metrics["min_latency_ms"] = min(latencies)
            response_metrics["max_latency_ms"] = max(latencies)

            # Calculate percentiles
            sorted_latencies = sorted(latencies)
            response_metrics["p50_latency_ms"] = sorted_latencies[len(sorted_latencies) // 2]
            response_metrics["p95_latency_ms"] = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            response_metrics["p99_latency_ms"] = sorted_latencies[int(len(sorted_latencies) * 0.99)]

        return response_metrics

    def benchmark_concurrent_performance(self, num_concurrent: int = 10) -> Dict:
        """Benchmark concurrent request handling."""
        print(f"🔄 Benchmarking concurrent performance ({num_concurrent} concurrent requests)...")

        import concurrent.futures

        concurrent_metrics = {
            "num_concurrent": num_concurrent,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time_seconds": 0,
            "requests_per_second": 0,
            "errors": [],
        }

        def make_request(request_id: int) -> Dict:
            test_request = {
                "model": "gpt-5",
                "messages": [{"role": "user", "content": f"Concurrent test {request_id}"}],
                "max_tokens": 50,
                "temperature": 1.0,
            }

            headers = {"Authorization": "Bearer test-key", "Content-Type": "application/json"}

            start_time = time.time()
            try:
                response = requests.post(
                    f"{self.proxy_url}/v1/chat/completions",
                    json=test_request,
                    headers=headers,
                    timeout=30,
                )

                end_time = time.time()
                return {
                    "request_id": request_id,
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "latency_ms": (end_time - start_time) * 1000,
                    "error": None if response.status_code == 200 else response.text[:100],
                }

            except requests.RequestException as e:
                end_time = time.time()
                return {
                    "request_id": request_id,
                    "success": False,
                    "status_code": None,
                    "latency_ms": (end_time - start_time) * 1000,
                    "error": str(e)[:100],
                }

        # Execute concurrent requests
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_concurrent)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        end_time = time.time()

        # Process results
        concurrent_metrics["total_time_seconds"] = end_time - start_time
        concurrent_metrics["requests_per_second"] = (
            num_concurrent / concurrent_metrics["total_time_seconds"]
        )

        for result in results:
            if result["success"]:
                concurrent_metrics["successful_requests"] += 1
            else:
                concurrent_metrics["failed_requests"] += 1
                concurrent_metrics["errors"].append(result)

        # Calculate latency statistics for successful requests
        successful_latencies = [r["latency_ms"] for r in results if r["success"]]
        if successful_latencies:
            concurrent_metrics["avg_latency_ms"] = sum(successful_latencies) / len(
                successful_latencies
            )
            concurrent_metrics["max_latency_ms"] = max(successful_latencies)

        return concurrent_metrics

    def analyze_configuration_opportunities(self) -> Dict:
        """Analyze current configuration for optimization opportunities."""
        print("🔍 Analyzing configuration opportunities...")

        opportunities = {"recommendations": [], "current_config": {}, "optimization_potential": {}}

        # Check if we can access configuration
        try:
            # Look for common config files
            config_files = [".azure.env", ".env", "config.yaml", "litellm_config.yaml"]

            for config_file in config_files:
                if os.path.exists(config_file):
                    opportunities["current_config"][config_file] = "found"

                    # Read .env files for optimization analysis
                    if config_file.endswith(".env"):
                        try:
                            with open(config_file) as f:
                                content = f.read()

                            # Look for timeout settings
                            if "timeout" in content.lower():
                                opportunities["recommendations"].append(
                                    {
                                        "category": "timeout_optimization",
                                        "description": "Found timeout configurations - consider optimizing for Azure Responses API",
                                        "priority": "medium",
                                    }
                                )

                            # Look for max_tokens settings
                            if "max_tokens" in content.lower() and "512000" in content:
                                opportunities["recommendations"].append(
                                    {
                                        "category": "token_optimization",
                                        "description": "Large max_tokens (512k) detected - consider dynamic adjustment based on request",
                                        "priority": "high",
                                    }
                                )

                        except Exception:
                            pass
                else:
                    opportunities["current_config"][config_file] = "not_found"

        except Exception as e:
            opportunities["config_analysis_error"] = str(e)

        # General recommendations based on benchmark results
        if hasattr(self, "results") and self.results:
            memory_results = self.results.get("memory_usage", {})
            response_results = self.results.get("response_times", {})

            # Memory optimization recommendations
            total_memory = memory_results.get("total_proxy_memory_mb", 0)
            if total_memory > 200:
                opportunities["recommendations"].append(
                    {
                        "category": "memory_optimization",
                        "description": f"High memory usage detected ({total_memory:.1f}MB) - consider memory optimization",
                        "priority": "high",
                    }
                )

            # Response time optimization recommendations
            avg_latency = response_results.get("avg_latency_ms", 0)
            if avg_latency > 1000:
                opportunities["recommendations"].append(
                    {
                        "category": "latency_optimization",
                        "description": f"High average latency detected ({avg_latency:.1f}ms) - consider connection pooling and caching",
                        "priority": "high",
                    }
                )

        # Default recommendations for LiteLLM proxy optimization
        default_recommendations = [
            {
                "category": "startup_optimization",
                "description": "Implement lazy loading for non-critical dependencies",
                "priority": "medium",
            },
            {
                "category": "connection_optimization",
                "description": "Configure connection pooling for Azure API calls",
                "priority": "high",
            },
            {
                "category": "caching_optimization",
                "description": "Implement response caching for repeated requests",
                "priority": "medium",
            },
            {
                "category": "async_optimization",
                "description": "Ensure all I/O operations are properly async",
                "priority": "high",
            },
        ]

        opportunities["recommendations"].extend(default_recommendations)

        return opportunities

    def _is_proxy_running(self) -> bool:
        """Check if proxy is currently running."""
        try:
            response = requests.get(f"{self.proxy_url}/health", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def run_full_benchmark(self) -> Dict:
        """Run complete performance benchmark suite."""
        print("🎯 Starting comprehensive performance benchmark...")

        self.results = {
            "timestamp": time.time(),
            "proxy_url": self.proxy_url,
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "total_memory_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
                "python_version": sys.version,
                "platform": sys.platform,
            },
        }

        # Run individual benchmarks
        benchmarks = [
            ("startup_performance", self.benchmark_startup_performance),
            ("memory_usage", self.benchmark_memory_usage),
            ("response_times", self.benchmark_response_times),
            ("concurrent_performance", self.benchmark_concurrent_performance),
            ("configuration_analysis", self.analyze_configuration_opportunities),
        ]

        for benchmark_name, benchmark_func in benchmarks:
            try:
                print(f"\n📊 Running {benchmark_name}...")
                self.results[benchmark_name] = benchmark_func()
                print(f"✅ Completed {benchmark_name}")
            except Exception as e:
                print(f"❌ Error in {benchmark_name}: {e}")
                self.results[benchmark_name] = {
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }

        return self.results

    def generate_report(self) -> str:
        """Generate human-readable performance report."""
        if not self.results:
            return "No benchmark results available. Run benchmark first."

        report = []
        report.append("🎯 LiteLLM Proxy Performance Benchmark Report")
        report.append("=" * 50)
        report.append(f"Timestamp: {time.ctime(self.results['timestamp'])}")
        report.append(f"Proxy URL: {self.results['proxy_url']}")
        report.append("")

        # System info
        sys_info = self.results["system_info"]
        report.append("🖥️ System Information:")
        report.append(f"  • CPU Cores: {sys_info['cpu_count']}")
        report.append(f"  • Total Memory: {sys_info['total_memory_gb']:.1f} GB")
        report.append(f"  • Python: {sys_info['python_version'].split()[0]}")
        report.append(f"  • Platform: {sys_info['platform']}")
        report.append("")

        # Startup performance
        startup = self.results.get("startup_performance", {})
        if startup and not startup.get("error"):
            report.append("🚀 Startup Performance:")
            report.append(f"  • Initial State: {startup.get('initial_state', 'unknown')}")

            health_latency = startup.get("health_check_latency")
            if health_latency:
                report.append(f"  • Health Check: {health_latency:.1f}ms")
                if health_latency > 1000:
                    report.append("    ⚠️ High health check latency detected")
            report.append("")

        # Memory usage
        memory = self.results.get("memory_usage", {})
        if memory and not memory.get("error"):
            report.append("🧠 Memory Usage:")
            report.append(f"  • System Available: {memory.get('system_available_mb', 0):.1f} MB")
            report.append(f"  • Proxy Memory: {memory.get('total_proxy_memory_mb', 0):.1f} MB")

            if memory.get("total_proxy_memory_mb", 0) > 200:
                report.append("    ⚠️ High proxy memory usage detected")
            elif memory.get("total_proxy_memory_mb", 0) < 50:
                report.append("    ✅ Efficient memory usage")
            report.append("")

        # Response times
        response = self.results.get("response_times", {})
        if response and not response.get("error"):
            report.append("⚡ Response Times:")
            report.append(
                f"  • Successful Requests: {response.get('successful_requests', 0)}/{response.get('num_requests', 0)}"
            )

            avg_latency = response.get("avg_latency_ms")
            if avg_latency:
                report.append(f"  • Average Latency: {avg_latency:.1f}ms")
                report.append(f"  • P95 Latency: {response.get('p95_latency_ms', 0):.1f}ms")
                report.append(f"  • P99 Latency: {response.get('p99_latency_ms', 0):.1f}ms")

                if avg_latency > 2000:
                    report.append("    ❌ Very high latency - immediate optimization needed")
                elif avg_latency > 1000:
                    report.append("    ⚠️ High latency - optimization recommended")
                elif avg_latency < 500:
                    report.append("    ✅ Good response times")
            report.append("")

        # Concurrent performance
        concurrent = self.results.get("concurrent_performance", {})
        if concurrent and not concurrent.get("error"):
            report.append("🔄 Concurrent Performance:")
            report.append(f"  • Concurrent Requests: {concurrent.get('num_concurrent', 0)}")
            report.append(
                f"  • Success Rate: {concurrent.get('successful_requests', 0)}/{concurrent.get('num_concurrent', 0)}"
            )

            rps = concurrent.get("requests_per_second")
            if rps:
                report.append(f"  • Requests/Second: {rps:.1f}")

                if rps > 50:
                    report.append("    ✅ Excellent concurrent performance")
                elif rps > 20:
                    report.append("    ✅ Good concurrent performance")
                elif rps > 5:
                    report.append("    ⚠️ Moderate concurrent performance")
                else:
                    report.append("    ❌ Poor concurrent performance")
            report.append("")

        # Configuration analysis
        config_analysis = self.results.get("configuration_analysis", {})
        if config_analysis and not config_analysis.get("error"):
            recommendations = config_analysis.get("recommendations", [])
            if recommendations:
                report.append("🔍 Optimization Recommendations:")

                high_priority = [r for r in recommendations if r.get("priority") == "high"]
                medium_priority = [r for r in recommendations if r.get("priority") == "medium"]

                if high_priority:
                    report.append("  High Priority:")
                    for rec in high_priority:
                        report.append(f"    • {rec.get('description', 'No description')}")

                if medium_priority:
                    report.append("  Medium Priority:")
                    for rec in medium_priority:
                        report.append(f"    • {rec.get('description', 'No description')}")

                report.append("")

        # Summary
        report.append("📋 Summary:")
        if response.get("successful_requests", 0) == 0:
            report.append("  ❌ Proxy appears to be non-functional - check configuration")
        elif response.get("avg_latency_ms", 0) > 2000:
            report.append("  🔴 Critical: Very high latency requires immediate attention")
        elif memory.get("total_proxy_memory_mb", 0) > 300:
            report.append("  🟡 Warning: High memory usage should be investigated")
        else:
            report.append("  ✅ Proxy is functional - optimization opportunities identified")

        return "\n".join(report)

    def save_results(self, filename: str = "proxy_benchmark_results.json"):
        """Save benchmark results to file."""
        if not self.results:
            raise ValueError("No benchmark results to save")

        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"📄 Results saved to {filename}")


def main():
    """Main benchmark execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark LiteLLM proxy performance")
    parser.add_argument("--url", default="http://127.0.0.1:9001", help="Proxy URL")
    parser.add_argument("--requests", type=int, default=10, help="Number of test requests")
    parser.add_argument("--concurrent", type=int, default=10, help="Number of concurrent requests")
    parser.add_argument("--output", help="Output file for results")

    args = parser.parse_args()

    benchmark = ProxyBenchmark(proxy_url=args.url)

    # Override request counts if specified
    original_response_func = benchmark.benchmark_response_times
    original_concurrent_func = benchmark.benchmark_concurrent_performance

    benchmark.benchmark_response_times = lambda num_requests=args.requests: original_response_func(
        num_requests
    )
    benchmark.benchmark_concurrent_performance = (
        lambda num_concurrent=args.concurrent: original_concurrent_func(num_concurrent)
    )

    # Run benchmark
    benchmark.run_full_benchmark()

    # Generate and display report
    report = benchmark.generate_report()
    print("\n" + report)

    # Save results if requested
    if args.output:
        benchmark.save_results(args.output)


if __name__ == "__main__":
    main()
