"""Performance benchmarks for auto-ultrathink pipeline.

Tests latency, throughput, and resource usage to ensure the system meets
performance budgets (<2s end-to-end).
"""

import gc
import time

import pytest


class TestClassificationPerformance:
    """Performance benchmarks for request classifier."""

    def test_classification_latency(self):
        """Test classification latency meets budget (<100ms)."""
        from request_classifier import classify_request

        prompts = [
            "Add authentication to the API",
            "What is UltraThink?",
            "Refactor the auth module",
            "Show me the config file",
            "/analyze src/",
        ]

        times = []
        for prompt in prompts * 200:  # 1000 total classifications
            start = time.time()
            classify_request(prompt)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        # Calculate statistics
        times.sort()
        p50 = times[len(times) // 2]
        p95 = times[int(len(times) * 0.95)]
        p99 = times[int(len(times) * 0.99)]
        avg = sum(times) / len(times)

        print(f"\n{'=' * 70}")
        print("CLASSIFICATION LATENCY BENCHMARK")
        print(f"{'=' * 70}")
        print(f"Total classifications: {len(times)}")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  Avg: {avg:.2f}ms")
        print(f"  Min: {min(times):.2f}ms")
        print(f"  Max: {max(times):.2f}ms")
        print(f"{'=' * 70}\n")

        assert avg < 100, f"Average classification too slow: {avg:.2f}ms (target: <100ms)"
        assert p95 < 150, f"P95 classification too slow: {p95:.2f}ms (target: <150ms)"
        assert p99 < 300, f"P99 classification too slow: {p99:.2f}ms (target: <300ms)"

    def test_classification_throughput(self):
        """Test classification throughput (classifications per second)."""
        from request_classifier import classify_request

        prompt = "Add authentication to the API"
        iterations = 1000

        start = time.time()
        for _ in range(iterations):
            classify_request(prompt)
        elapsed = time.time() - start

        throughput = iterations / elapsed

        print(f"\nClassification throughput: {throughput:.0f} classifications/sec")

        assert throughput > 100, f"Throughput too low: {throughput:.0f} ops/sec (target: >100 ops/sec)"


class TestPreferenceManagerPerformance:
    """Performance benchmarks for preference manager."""

    def test_preference_read_latency(self, setup_test_env):
        """Test preference reading latency."""
        from preference_manager import get_auto_ultrathink_preference

        times = []
        for _ in range(100):
            start = time.time()
            get_auto_ultrathink_preference()
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        avg = sum(times) / len(times)
        p95 = sorted(times)[int(len(times) * 0.95)]

        print("\nPreference read latency:")
        print(f"  Average: {avg:.2f}ms")
        print(f"  P95: {p95:.2f}ms")

        assert avg < 20, f"Preference read too slow: {avg:.2f}ms (target: <20ms)"

    def test_exclusion_pattern_performance(self):
        """Test exclusion pattern matching performance."""
        from preference_manager import is_excluded

        patterns = ["^test.*", ".*debug.*", "^fix.*"] * 10  # 30 patterns
        prompt = "test the authentication feature"

        start = time.time()
        for _ in range(1000):
            is_excluded(prompt, patterns)
        elapsed = time.time() - start

        avg_time_ms = (elapsed / 1000) * 1000

        print(f"\nExclusion pattern matching: {avg_time_ms:.2f}ms per check")

        assert avg_time_ms < 10, f"Pattern matching too slow: {avg_time_ms:.2f}ms (target: <10ms)"


class TestDecisionEnginePerformance:
    """Performance benchmarks for decision engine."""

    def test_decision_latency(self, create_test_classification, create_test_preference):
        """Test decision making latency."""
        from decision_engine import make_decision

        classification = create_test_classification()
        preference = create_test_preference()

        times = []
        for _ in range(1000):
            start = time.time()
            make_decision(classification, preference, "test prompt")
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        avg = sum(times) / len(times)
        p95 = sorted(times)[int(len(times) * 0.95)]

        print("\nDecision latency:")
        print(f"  Average: {avg:.2f}ms")
        print(f"  P95: {p95:.2f}ms")

        assert avg < 10, f"Decision too slow: {avg:.2f}ms (target: <10ms)"


class TestActionExecutorPerformance:
    """Performance benchmarks for action executor."""

    def test_execution_latency(self, create_test_decision):
        """Test action execution latency."""
        from action_executor import execute_action

        decision = create_test_decision(action="invoke")

        times = []
        for i in range(1000):
            start = time.time()
            execute_action(f"prompt {i}", decision)
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        avg = sum(times) / len(times)
        p95 = sorted(times)[int(len(times) * 0.95)]

        print("\nAction execution latency:")
        print(f"  Average: {avg:.2f}ms")
        print(f"  P95: {p95:.2f}ms")

        assert avg < 50, f"Execution too slow: {avg:.2f}ms (target: <50ms)"


class TestLoggerPerformance:
    """Performance benchmarks for logger."""

    def test_logging_latency(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Test logging latency."""
        from logger import log_auto_ultrathink

        log_file = tmp_path / "bench.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        times = []
        for i in range(100):
            start = time.time()
            log_auto_ultrathink(
                session_id="bench",
                prompt=f"prompt {i}",
                classification=create_test_classification(),
                preference=create_test_preference(),
                decision=create_test_decision(),
                result=create_test_result(),
                execution_time_ms=100.0,
            )
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        avg = sum(times) / len(times)
        p95 = sorted(times)[int(len(times) * 0.95)]

        print("\nLogging latency:")
        print(f"  Average: {avg:.2f}ms")
        print(f"  P95: {p95:.2f}ms")

        assert avg < 50, f"Logging too slow: {avg:.2f}ms (target: <50ms)"


class TestE2EPipelinePerformance:
    """Performance benchmarks for complete pipeline."""

    def test_full_pipeline_latency(self, setup_test_env):
        """Test full pipeline latency meets budget (<200ms)."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
  confidence_threshold: 0.80
```
"""
        )

        prompts = [
            "Add authentication to the API",
            "What is UltraThink?",
            "Refactor the auth module",
            "Show me the config",
            "/analyze src/",
        ]

        times = []
        for prompt in prompts * 20:  # 100 total invocations
            start = time.time()
            auto_ultrathink_hook(prompt, context={"session_id": "bench"})
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        # Calculate statistics
        times.sort()
        p50 = times[len(times) // 2]
        p95 = times[int(len(times) * 0.95)]
        p99 = times[int(len(times) * 0.99)]
        avg = sum(times) / len(times)

        print(f"\n{'=' * 70}")
        print("END-TO-END PIPELINE LATENCY BENCHMARK")
        print(f"{'=' * 70}")
        print(f"Total invocations: {len(times)}")
        print(f"  P50: {p50:.2f}ms")
        print(f"  P95: {p95:.2f}ms")
        print(f"  P99: {p99:.2f}ms")
        print(f"  Avg: {avg:.2f}ms")
        print(f"  Min: {min(times):.2f}ms")
        print(f"  Max: {max(times):.2f}ms")
        print(f"{'=' * 70}\n")

        assert avg < 150, f"Average pipeline too slow: {avg:.2f}ms (target: <150ms)"
        assert p95 < 200, f"P95 pipeline too slow: {p95:.2f}ms (target: <200ms)"
        assert p99 < 300, f"P99 pipeline too slow: {p99:.2f}ms (target: <300ms)"

    def test_pipeline_throughput(self, setup_test_env):
        """Test pipeline throughput (invocations per second)."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        prompt = "Add authentication to the API"
        iterations = 100

        start = time.time()
        for _ in range(iterations):
            auto_ultrathink_hook(prompt, context={"session_id": "bench"})
        elapsed = time.time() - start

        throughput = iterations / elapsed

        print(f"\nPipeline throughput: {throughput:.0f} invocations/sec")

        assert throughput > 10, f"Throughput too low: {throughput:.0f} ops/sec (target: >10 ops/sec)"


class TestMemoryUsage:
    """Memory usage benchmarks."""

    def test_classification_memory_leak(self):
        """Test for memory leaks in classification."""
        import tracemalloc

        from request_classifier import classify_request

        tracemalloc.start()
        snapshot1 = tracemalloc.take_snapshot()

        # Run many classifications
        for i in range(1000):
            classify_request(f"Add feature {i}")

        # Force garbage collection
        gc.collect()

        snapshot2 = tracemalloc.take_snapshot()
        top_stats = snapshot2.compare_to(snapshot1, "lineno")

        # Calculate total memory growth
        total_growth = sum(stat.size_diff for stat in top_stats)

        print(f"\nMemory growth (classification, 1000 ops): {total_growth / 1024:.2f} KB")

        # Allow some growth but not excessive (< 1MB)
        assert total_growth < 1024 * 1024, f"Excessive memory growth: {total_growth / 1024:.2f} KB"

        tracemalloc.stop()

    def test_pipeline_memory_leak(self, setup_test_env):
        """Test for memory leaks in full pipeline."""
        import tracemalloc

        from hook_integration import auto_ultrathink_hook

        # Setup preference
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        tracemalloc.start()
        snapshot1 = tracemalloc.take_snapshot()

        # Run many invocations
        for i in range(100):
            auto_ultrathink_hook(f"Add feature {i}", context={"session_id": "bench"})

        # Force garbage collection
        gc.collect()

        snapshot2 = tracemalloc.take_snapshot()
        top_stats = snapshot2.compare_to(snapshot1, "lineno")

        # Calculate total memory growth
        total_growth = sum(stat.size_diff for stat in top_stats)

        print(f"\nMemory growth (pipeline, 100 ops): {total_growth / 1024:.2f} KB")

        # Allow more growth for full pipeline but still limited (< 5MB)
        assert total_growth < 5 * 1024 * 1024, f"Excessive memory growth: {total_growth / 1024:.2f} KB"

        tracemalloc.stop()


class TestStressTest:
    """Stress tests for sustained load."""

    @pytest.mark.slow
    def test_sustained_load(self, setup_test_env):
        """Test pipeline under sustained load (1000 invocations)."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        prompts = [
            "Add authentication",
            "What is this?",
            "Refactor code",
            "Show config",
            "/analyze",
        ]

        errors = 0
        times = []

        for i in range(1000):
            try:
                start = time.time()
                auto_ultrathink_hook(
                    prompts[i % len(prompts)], context={"session_id": "stress"}
                )
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)
            except Exception as e:
                errors += 1
                print(f"Error at iteration {i}: {e}")

        # Calculate statistics
        if times:
            times.sort()
            p95 = times[int(len(times) * 0.95)]
            avg = sum(times) / len(times)

            print("\nStress test results (1000 invocations):")
            print(f"  Errors: {errors}")
            print(f"  Success rate: {(1000 - errors) / 10:.1f}%")
            print(f"  Average latency: {avg:.2f}ms")
            print(f"  P95 latency: {p95:.2f}ms")

            assert errors < 10, f"Too many errors: {errors}/1000 (target: <1%)"
            assert p95 < 250, f"P95 degraded under load: {p95:.2f}ms"


class TestColdStartLatency:
    """Test cold start performance."""

    def test_first_invocation_latency(self, setup_test_env):
        """Test first invocation latency (cold start)."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        # First invocation (cold start)
        start = time.time()
        auto_ultrathink_hook("Add authentication", context={"session_id": "cold"})
        cold_start_ms = (time.time() - start) * 1000

        # Warm invocation
        start = time.time()
        auto_ultrathink_hook("Add feature", context={"session_id": "cold"})
        warm_ms = (time.time() - start) * 1000

        print(f"\nCold start latency: {cold_start_ms:.2f}ms")
        print(f"Warm latency: {warm_ms:.2f}ms")
        print(f"Cold start penalty: {cold_start_ms - warm_ms:.2f}ms")

        # Cold start should still be reasonable (<500ms)
        assert cold_start_ms < 500, f"Cold start too slow: {cold_start_ms:.2f}ms"
