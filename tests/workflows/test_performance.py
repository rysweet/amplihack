"""
Performance tests for workflow classification and execution.

Tests NFR2: Classification must complete in <5 seconds.
Tests execution tier cascade performance.

Following TDD: These tests should FAIL until implementation is complete.
"""

import time

import pytest


@pytest.mark.performance
class TestClassificationPerformance:
    """Test workflow classification performance (NFR2)."""

    def test_simple_classification_under_1_second(self):
        """Test simple classification completes in <1 second."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        start = time.time()
        result = classifier.classify("Add authentication")
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Simple classification took {elapsed}s, expected <1s"
        assert result["workflow"] == "DEFAULT_WORKFLOW"

    def test_complex_classification_under_5_seconds(self):
        """Test complex classification completes in <5 seconds (NFR2)."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        complex_request = (
            "Investigate the current authentication system implementation, "
            "understand how JWT tokens are validated, analyze the security "
            "implications of the current approach, review the database schema "
            "for user credentials, and then implement a new role-based access "
            "control system with proper encryption and audit logging"
        )

        start = time.time()
        _result = classifier.classify(complex_request)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Complex classification took {elapsed}s, expected <5s (NFR2)"

    def test_classification_with_context_under_5_seconds(self):
        """Test classification with context completes in <5s."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        context = {
            "session_id": "perf-test",
            "user_request": "Add authentication",
            "timestamp": "2026-02-16T00:00:00Z",
            "cwd": "/test/project",
            "is_first_message": True,
            "history": [f"Previous message {i}" for i in range(100)],  # Large context
        }

        start = time.time()
        _result = classifier.classify("Add authentication", context=context)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Classification with large context took {elapsed}s, expected <5s"

    def test_batch_classification_performance(self):
        """Test batch classification of 10 requests completes reasonably."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        requests = [
            "Add authentication",
            "What is the purpose?",
            "Fix the bug",
            "Investigate the system",
            "Clean up files",
            "Implement feature X",
            "Understand how it works",
            "Update dependencies",
            "Analyze the architecture",
            "Create a new module",
        ]

        start = time.time()
        results = [classifier.classify(req) for req in requests]
        elapsed = time.time() - start

        # 10 classifications should complete in <30 seconds
        assert elapsed < 30.0, f"Batch classification took {elapsed}s, expected <30s"
        assert len(results) == 10


@pytest.mark.performance
class TestExecutionTierCascadePerformance:
    """Test execution tier cascade performance."""

    def test_tier_detection_fast(self):
        """Test tier detection is fast (<100ms)."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        start = time.time()
        tier = cascade.detect_available_tier()
        elapsed = time.time() - start

        assert elapsed < 0.1, f"Tier detection took {elapsed}s, expected <100ms"
        assert tier in [1, 2, 3]

    def test_fallback_chain_reasonable_time(self, mock_recipe_runner):
        """Test fallback chain completes in reasonable time."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        mock_recipe_runner.run_recipe_by_name.side_effect = RuntimeError("Failed")
        cascade = ExecutionTierCascade(recipe_runner=mock_recipe_runner)

        context = {"user_request": "Add auth", "is_first_message": True}

        start = time.time()
        result = cascade.execute("DEFAULT_WORKFLOW", context)
        elapsed = time.time() - start

        # Even with fallback, should complete reasonably (<10s)
        assert elapsed < 10.0, f"Fallback chain took {elapsed}s, expected <10s"
        assert result["tier"] > 1  # Should have fallen back


@pytest.mark.performance
class TestSessionStartPerformance:
    """Test session start complete flow performance."""

    def test_full_session_start_under_5_seconds(self):
        """Test full session start flow completes in <5 seconds."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        context = {
            "user_request": "Add authentication to the API",
            "is_first_message": True,
            "session_id": "perf-test",
        }

        skill = SessionStartClassifierSkill()
        start = time.time()
        result = skill.process(context)
        elapsed = time.time() - start

        assert elapsed < 5.0, f"Session start took {elapsed}s, expected <5s (NFR2)"
        assert result["workflow"] == "DEFAULT_WORKFLOW"

    def test_session_start_with_fallback_under_10_seconds(self, mock_recipe_runner):
        """Test session start with fallback completes reasonably."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        mock_recipe_runner.run_recipe_by_name.side_effect = RuntimeError("Failed")
        context = {
            "user_request": "Add authentication",
            "is_first_message": True,
        }

        skill = SessionStartClassifierSkill(recipe_runner=mock_recipe_runner)
        start = time.time()
        _result = skill.process(context)
        elapsed = time.time() - start

        # With fallback, allow up to 10 seconds
        assert elapsed < 10.0, f"Session start with fallback took {elapsed}s, expected <10s"

    def test_multiple_session_starts_consistent_performance(self):
        """Test that multiple session starts have consistent performance."""
        from amplihack.workflows.session_start_skill import SessionStartClassifierSkill

        skill = SessionStartClassifierSkill()
        timings = []

        for i in range(5):
            context = {
                "user_request": f"Add feature {i}",
                "is_first_message": True,
                "session_id": f"perf-test-{i}",
            }

            start = time.time()
            _result = skill.process(context)
            elapsed = time.time() - start
            timings.append(elapsed)

        # All should be under 5 seconds
        for i, timing in enumerate(timings):
            assert timing < 5.0, f"Session start {i} took {timing}s, expected <5s"

        # Performance should be consistent (no degradation)
        avg_time = sum(timings) / len(timings)
        for timing in timings:
            # No timing should be >2x average
            assert timing < avg_time * 2, "Performance inconsistency detected"


@pytest.mark.performance
class TestMemoryAndResourceUsage:
    """Test memory and resource usage during classification."""

    def test_classification_memory_efficient(self):
        """Test that classification doesn't leak memory."""
        import gc

        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()

        # Get baseline memory
        gc.collect()
        baseline_objects = len(gc.get_objects())

        # Run many classifications
        for i in range(100):
            result = classifier.classify(f"Add feature {i}")
            assert result["workflow"] == "DEFAULT_WORKFLOW"

        # Check memory after classifications
        gc.collect()
        final_objects = len(gc.get_objects())

        # Object count shouldn't grow significantly (allow 10% growth)
        growth = (final_objects - baseline_objects) / baseline_objects
        assert growth < 0.1, f"Memory leak detected: {growth * 100:.1f}% object growth"

    def test_cascade_no_resource_leaks(self):
        """Test that cascade doesn't leak resources."""
        import gc

        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        context = {"user_request": "test", "is_first_message": True}

        gc.collect()
        baseline_objects = len(gc.get_objects())

        # Run many executions
        for i in range(50):
            _result = cascade.execute("Q&A_WORKFLOW", context)

        gc.collect()
        final_objects = len(gc.get_objects())

        growth = (final_objects - baseline_objects) / baseline_objects
        assert growth < 0.15, f"Resource leak detected: {growth * 100:.1f}% object growth"


@pytest.mark.performance
class TestConcurrentPerformance:
    """Test performance under concurrent load."""

    @pytest.mark.slow
    def test_concurrent_classifications(self):
        """Test concurrent classifications don't interfere."""
        import concurrent.futures

        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        requests = [f"Add feature {i}" for i in range(20)]

        def classify_request(req):
            start = time.time()
            result = classifier.classify(req)
            elapsed = time.time() - start
            return elapsed, result

        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(classify_request, requests))
        total_elapsed = time.time() - start

        # All individual classifications should be fast
        for elapsed, result in results:
            assert elapsed < 5.0, f"Classification took {elapsed}s, expected <5s"
            assert result["workflow"] == "DEFAULT_WORKFLOW"

        # Concurrent execution should be faster than sequential
        # (20 * 5s = 100s sequential, should be <40s concurrent with 5 workers)
        assert total_elapsed < 40.0, f"Concurrent execution took {total_elapsed}s"


@pytest.mark.performance
class TestPerformanceRegression:
    """Test for performance regressions."""

    def test_classification_performance_baseline(self):
        """Establish performance baseline for classification."""
        from amplihack.workflows.classifier import WorkflowClassifier

        classifier = WorkflowClassifier()
        test_cases = [
            "Add authentication",
            "What is the purpose?",
            "Fix the bug",
            "Investigate the system",
        ]

        timings = {}
        for request in test_cases:
            start = time.time()
            _result = classifier.classify(request)
            elapsed = time.time() - start
            timings[request] = elapsed

        # Store baseline for comparison
        # All should be under 1 second for simple cases
        for request, timing in timings.items():
            assert timing < 1.0, f"{request} took {timing}s, expected <1s"

    def test_execution_performance_baseline(self):
        """Establish performance baseline for execution."""
        from amplihack.workflows.execution_tier_cascade import ExecutionTierCascade

        cascade = ExecutionTierCascade()
        context = {"user_request": "test", "is_first_message": True}

        workflows = ["Q&A_WORKFLOW", "OPS_WORKFLOW"]
        timings = {}

        for workflow in workflows:
            start = time.time()
            _result = cascade.execute(workflow, context)
            elapsed = time.time() - start
            timings[workflow] = elapsed

        # Store baseline
        for workflow, timing in timings.items():
            assert timing < 5.0, f"{workflow} execution took {timing}s, expected <5s"
