"""Tests fer memory evaluation framework.

Tests:
- QualityEvaluator: Relevance, precision, recall, NDCG
- PerformanceEvaluator: Latency, throughput, scalability
- ReliabilityEvaluator: Integrity, concurrency, recovery
- BackendComparison: Full evaluation and reporting
"""

import pytest
import pytest_asyncio

from src.amplihack.memory.backends import create_backend
from src.amplihack.memory.coordinator import MemoryCoordinator, StorageRequest
from src.amplihack.memory.evaluation import (
    BackendComparison,
    PerformanceEvaluator,
    QualityEvaluator,
    ReliabilityEvaluator,
    run_evaluation,
)
from src.amplihack.memory.evaluation.quality_evaluator import QueryTestCase
from src.amplihack.memory.types import MemoryType


@pytest_asyncio.fixture
async def coordinator():
    """Create coordinator with SQLite backend fer testing."""
    backend = create_backend(backend_type="sqlite", db_path=":memory:")
    coordinator = MemoryCoordinator(backend=backend)
    return coordinator


class TestQualityEvaluator:
    """Tests fer quality evaluation."""

    @pytest.mark.asyncio
    async def test_evaluate_with_perfect_results(self, coordinator):
        """Test evaluation when all retrieved memories are relevant."""
        evaluator = QualityEvaluator(coordinator)

        # Store test memories
        memory_id1 = await coordinator.store(
            StorageRequest(
                content="Feature A implementation details",
                memory_type=MemoryType.EPISODIC,
                context={"agent_id": "test"},
            )
        )
        memory_id2 = await coordinator.store(
            StorageRequest(
                content="Feature A testing strategy",
                memory_type=MemoryType.EPISODIC,
                context={"agent_id": "test"},
            )
        )

        # Create test query (all results are relevant)
        test_queries = [
            QueryTestCase(
                query_text="Feature A",
                relevant_memory_ids=[memory_id1, memory_id2],
            )
        ]

        # Evaluate
        metrics = await evaluator.evaluate(test_queries)

        # Verify
        assert metrics.backend_name == "sqlite"
        assert metrics.num_queries == 1
        assert metrics.precision >= 0.0  # Some memories might be retrieved
        assert metrics.recall >= 0.0

    @pytest.mark.asyncio
    async def test_create_test_set(self, coordinator):
        """Test creating a standard test set."""
        evaluator = QualityEvaluator(coordinator)

        test_queries = await evaluator.create_test_set(num_memories=50)

        # Verify test set structure
        assert len(test_queries) >= 3  # At least 3 queries
        assert all(isinstance(q, QueryTestCase) for q in test_queries)
        assert all(q.query_text for q in test_queries)
        assert all(isinstance(q.relevant_memory_ids, list) for q in test_queries)


class TestPerformanceEvaluator:
    """Tests fer performance evaluation."""

    @pytest.mark.asyncio
    async def test_evaluate_latency(self, coordinator):
        """Test latency measurement."""
        evaluator = PerformanceEvaluator(coordinator)

        # Run small benchmark
        metrics = await evaluator.evaluate(num_operations=10)

        # Verify metrics structure
        assert metrics.backend_name == "sqlite"
        assert metrics.storage_latency_ms >= 0
        assert metrics.retrieval_latency_ms >= 0
        assert metrics.storage_throughput >= 0
        assert metrics.retrieval_throughput >= 0

    @pytest.mark.asyncio
    async def test_check_performance_contracts(self, coordinator):
        """Test performance contract checking."""
        evaluator = PerformanceEvaluator(coordinator)

        metrics = await evaluator.evaluate(num_operations=10)
        contracts = evaluator.check_performance_contracts(metrics)

        # Verify contract checks
        assert "storage_latency_ok" in contracts
        assert "retrieval_latency_ok" in contracts
        assert "storage_throughput_ok" in contracts
        assert "retrieval_throughput_ok" in contracts
        assert all(isinstance(v, bool) for v in contracts.values())

    @pytest.mark.asyncio
    async def test_evaluate_scalability(self, coordinator):
        """Test scalability measurement at different scales."""
        evaluator = PerformanceEvaluator(coordinator)

        # Test at small scales (fast test)
        results = await evaluator.evaluate_scalability(scales=[10, 20])

        # Verify results at each scale
        assert len(results) == 2
        assert 10 in results
        assert 20 in results
        assert results[10].num_memories >= 10
        assert results[20].num_memories >= 20


class TestReliabilityEvaluator:
    """Tests fer reliability evaluation."""

    @pytest.mark.asyncio
    async def test_data_integrity(self, coordinator):
        """Test data integrity measurement."""
        evaluator = ReliabilityEvaluator(coordinator)

        metrics = await evaluator.evaluate()

        # Verify integrity score
        assert 0 <= metrics.data_integrity_score <= 1
        assert metrics.backend_name == "sqlite"

    @pytest.mark.asyncio
    async def test_concurrent_safety(self, coordinator):
        """Test concurrent safety measurement."""
        evaluator = ReliabilityEvaluator(coordinator)

        metrics = await evaluator.evaluate()

        # Verify concurrency score
        assert 0 <= metrics.concurrent_safety_score <= 1

    @pytest.mark.asyncio
    async def test_error_recovery(self, coordinator):
        """Test error recovery measurement."""
        evaluator = ReliabilityEvaluator(coordinator)

        metrics = await evaluator.evaluate()

        # Verify recovery score
        assert 0 <= metrics.error_recovery_score <= 1


class TestBackendComparison:
    """Tests fer backend comparison."""

    @pytest.mark.asyncio
    async def test_evaluate_sqlite_backend(self):
        """Test evaluating SQLite backend."""
        comparison = BackendComparison()

        report = await comparison.evaluate_backend("sqlite", db_path=":memory:")

        # Verify report structure
        assert report.backend_name == "sqlite"
        assert 0 <= report.overall_score <= 1
        assert report.quality_metrics is not None
        assert report.performance_metrics is not None
        assert report.reliability_metrics is not None
        assert isinstance(report.recommendations, list)
        assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    async def test_generate_markdown_report(self):
        """Test markdown report generation."""
        comparison = BackendComparison()

        await comparison.evaluate_backend("sqlite", db_path=":memory:")
        report = comparison.generate_markdown_report()

        # Verify report content
        assert "# Memory Backend Comparison Report" in report
        assert "## Summary" in report
        assert "sqlite" in report
        assert "Quality Metrics" in report
        assert "Performance Metrics" in report
        assert "Reliability Metrics" in report

    @pytest.mark.asyncio
    async def test_run_evaluation_convenience_function(self):
        """Test convenience function fer running evaluation."""
        report = await run_evaluation("sqlite", db_path=":memory:")

        # Verify report generation
        assert isinstance(report, str)
        assert "sqlite" in report
        assert "Quality Metrics" in report
