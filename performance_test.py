#!/usr/bin/env python3
"""Performance test for the simplified error pattern detection system."""

import cProfile
import pstats
import sys
import time
from io import StringIO
from pathlib import Path

# Add the module path
sys.path.insert(0, str(Path(__file__).parent / ".claude" / "tools" / "amplihack" / "reflection"))

from error_analysis.simple_analyzer import SimpleErrorAnalyzer  # type: ignore


def generate_test_messages(size: int) -> list:
    """Generate test messages with various error patterns."""
    base_messages = [
        {"content": "Starting session"},
        {"content": "FileNotFoundError: No such file or directory: 'missing.txt'"},
        {"content": "PermissionError: [Errno 13] Permission denied: '/restricted/file'"},
        {"content": "ModuleNotFoundError: No module named 'requests'"},
        {"content": "HTTP 500 error from API endpoint"},
        {"content": "Connection timeout after 30 seconds"},
        {"content": "SyntaxError: invalid syntax at line 42"},
        {"content": "TypeError: unsupported operand type(s)"},
        {"content": "IndexError: list index out of range"},
        {"content": "KeyError: 'missing_key'"},
        {"content": "Operation failed with unknown error"},
        {"content": "Retrying operation due to timeout"},
        {"content": "API call failed, trying again"},
        {"content": "Processing large dataset..."},
        {"content": "Running multiple tool operations"},
        {"content": "Normal processing message"},
        {"content": "Another regular message"},
        {"content": "Debug information here"},
        {"content": "Status update message"},
        {"content": "Final completion message"},
    ]

    # Repeat and extend to reach desired size
    messages = []
    while len(messages) < size:
        messages.extend(base_messages)

    return messages[:size]


def create_test_content(messages: list) -> str:
    """Create test content from messages."""
    return " ".join(
        msg["content"] for msg in messages if isinstance(msg, dict) and "content" in msg
    )


def benchmark_pattern_matching(
    analyzer: SimpleErrorAnalyzer, content: str, iterations: int = 100
) -> dict:
    """Benchmark pattern matching performance."""
    results = {}

    # Test individual pattern matching
    pattern_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        for pattern, error_type, priority, suggestion in analyzer.compiled_patterns:
            pattern.search(content)
        end = time.perf_counter()
        pattern_times.append(end - start)

    results["pattern_matching_avg"] = sum(pattern_times) / len(pattern_times)
    results["pattern_matching_total"] = sum(pattern_times)

    # Test full analysis
    analysis_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        analyzer.analyze_errors(content)
        end = time.perf_counter()
        analysis_times.append(end - start)

    results["analysis_avg"] = sum(analysis_times) / len(analysis_times)
    results["analysis_total"] = sum(analysis_times)

    return results


def profile_analysis(analyzer: SimpleErrorAnalyzer, content: str):
    """Profile the analysis function to identify bottlenecks."""
    pr = cProfile.Profile()

    # Profile the analysis
    pr.enable()
    for _ in range(100):
        analyzer.analyze_errors(content)
    pr.disable()

    # Get stats
    s = StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(20)  # Top 20 functions

    return s.getvalue()


def test_memory_usage():
    """Test memory efficiency."""
    import tracemalloc

    tracemalloc.start()

    analyzer = SimpleErrorAnalyzer()

    # Test with various content sizes
    sizes = [100, 500, 1000, 2000]
    memory_results = {}

    for size in sizes:
        messages = generate_test_messages(size)
        content = create_test_content(messages)

        # Take snapshot before
        snapshot1 = tracemalloc.take_snapshot()

        # Run analysis
        analyzer.analyze_errors(content)

        # Take snapshot after
        snapshot2 = tracemalloc.take_snapshot()

        # Calculate memory difference
        top_stats = snapshot2.compare_to(snapshot1, "lineno")
        total_size = sum(stat.size for stat in top_stats)

        memory_results[size] = total_size

    tracemalloc.stop()
    return memory_results


def main():
    """Run comprehensive performance tests."""
    print("🔬 Performance Testing - Simplified Error Pattern Detection")
    print("=" * 60)

    # Initialize analyzer
    analyzer = SimpleErrorAnalyzer()

    # Test different session sizes
    test_sizes = [10, 25, 50, 100, 200]

    print("\n📊 Performance Results by Session Size:")
    print("-" * 40)

    for size in test_sizes:
        print(f"\n📈 Testing with {size} messages...")

        # Generate test data
        messages = generate_test_messages(size)
        content = create_test_content(messages)
        content_size_kb = len(content) / 1024

        print(f"   Content size: {content_size_kb:.1f} KB")

        # Benchmark performance
        start_time = time.perf_counter()
        results = analyzer.analyze_errors(content)
        end_time = time.perf_counter()

        analysis_time = end_time - start_time

        print(f"   Analysis time: {analysis_time:.4f}s")
        print(f"   Patterns found: {len(results)}")
        print(
            f"   Performance: {'✅ PASS' if analysis_time < 5.0 else '❌ FAIL'} (< 5s requirement)"
        )

        # Memory usage test
        if size <= 100:  # Only for smaller sizes to avoid excessive memory
            memory_results = test_memory_usage()
            if size in memory_results:
                memory_kb = memory_results[size] / 1024
                print(f"   Memory usage: {memory_kb:.1f} KB")

    # Detailed profiling for medium size
    print("\n🔍 Detailed Profiling (50 messages):")
    print("-" * 40)

    messages_50 = generate_test_messages(50)
    content_50 = create_test_content(messages_50)

    # Benchmark details
    benchmark_results = benchmark_pattern_matching(analyzer, content_50, iterations=50)

    print(f"Pattern matching avg: {benchmark_results['pattern_matching_avg']:.6f}s")
    print(f"Full analysis avg: {benchmark_results['analysis_avg']:.6f}s")

    # Profile analysis
    print("\n📋 Top Function Calls:")
    profile_output = profile_analysis(analyzer, content_50)

    # Extract key lines from profile
    lines = profile_output.split("\n")
    for line in lines[3:13]:  # Skip header, show top 10
        if line.strip():
            print(f"   {line}")

    # Test edge cases
    print("\n🧪 Edge Case Testing:")
    print("-" * 40)

    edge_cases = [
        ("Empty content", ""),
        ("Very long content", "error " * 10000),
        ("No errors", "normal processing message " * 100),
        (
            "All error types",
            " ".join(
                [
                    "FileNotFoundError",
                    "PermissionError",
                    "ModuleNotFoundError",
                    "HTTP error",
                    "timeout",
                    "SyntaxError",
                    "TypeError",
                    "IndexError",
                    "KeyError",
                    "failed operation",
                ]
            ),
        ),
    ]

    for case_name, test_content in edge_cases:
        start_time = time.perf_counter()
        results = analyzer.analyze_errors(test_content)
        end_time = time.perf_counter()

        print(f"   {case_name}: {end_time - start_time:.6f}s, {len(results)} patterns")

    print("\n✅ Performance testing complete!")
    print("\n💡 Optimization Recommendations:")
    print("   1. Check regex compilation efficiency")
    print("   2. Optimize string operations")
    print("   3. Consider early exit strategies")
    print("   4. Review memory allocation patterns")


if __name__ == "__main__":
    main()
