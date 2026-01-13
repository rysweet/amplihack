"""Example: Evaluating memory backends.

This example shows how to use the evaluation framework to compare
different memory backends on quality, performance, and reliability.

Usage:
    python examples/evaluate_backends.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.backends import create_backend
from amplihack.memory.coordinator import MemoryCoordinator
from amplihack.memory.evaluation import (
    BackendComparison,
    PerformanceEvaluator,
    QualityEvaluator,
    ReliabilityEvaluator,
    run_evaluation,
)


async def example_quality_evaluation():
    """Example: Evaluate retrieval quality."""
    print("=== Quality Evaluation ===\n")

    # Create coordinator with SQLite backend
    backend = create_backend(backend_type="sqlite", db_path=":memory:")
    coordinator = MemoryCoordinator(backend=backend)

    # Create evaluator
    evaluator = QualityEvaluator(coordinator)

    # Create test set
    print("Creating test set...")
    test_queries = await evaluator.create_test_set(num_memories=50)
    print(f"Created {len(test_queries)} test queries\n")

    # Run evaluation
    print("Evaluating quality...")
    metrics = await evaluator.evaluate(test_queries)

    # Display results
    print(f"Backend: {metrics.backend_name}")
    print(f"Relevance: {metrics.relevance_score:.2f}")
    print(f"Precision: {metrics.precision:.2f}")
    print(f"Recall: {metrics.recall:.2f}")
    print(f"NDCG: {metrics.ndcg_score:.2f}")
    print(f"Queries: {metrics.num_queries}\n")


async def example_performance_evaluation():
    """Example: Evaluate performance."""
    print("=== Performance Evaluation ===\n")

    # Create coordinator
    backend = create_backend(backend_type="sqlite", db_path=":memory:")
    coordinator = MemoryCoordinator(backend=backend)

    # Create evaluator
    evaluator = PerformanceEvaluator(coordinator)

    # Run evaluation
    print("Evaluating performance...")
    metrics = await evaluator.evaluate(num_operations=100)

    # Display results
    print(f"Backend: {metrics.backend_name}")
    print(f"Storage Latency: {metrics.storage_latency_ms:.2f}ms")
    print(f"Retrieval Latency: {metrics.retrieval_latency_ms:.2f}ms")
    print(f"Storage Throughput: {metrics.storage_throughput:.1f} ops/sec")
    print(f"Retrieval Throughput: {metrics.retrieval_throughput:.1f} ops/sec")
    print(f"Memories: {metrics.num_memories}\n")

    # Check performance contracts
    contracts = evaluator.check_performance_contracts(metrics)
    print("Performance Contracts:")
    for contract, passed in contracts.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {contract}")
    print()


async def example_reliability_evaluation():
    """Example: Evaluate reliability."""
    print("=== Reliability Evaluation ===\n")

    # Create coordinator
    backend = create_backend(backend_type="sqlite", db_path=":memory:")
    coordinator = MemoryCoordinator(backend=backend)

    # Create evaluator
    evaluator = ReliabilityEvaluator(coordinator)

    # Run evaluation
    print("Evaluating reliability...")
    metrics = await evaluator.evaluate()

    # Display results
    print(f"Backend: {metrics.backend_name}")
    print(f"Data Integrity: {metrics.data_integrity_score:.2f}")
    print(f"Concurrent Safety: {metrics.concurrent_safety_score:.2f}")
    print(f"Error Recovery: {metrics.error_recovery_score:.2f}")
    print(f"Tests: {metrics.num_tests}\n")


async def example_backend_comparison():
    """Example: Compare multiple backends."""
    print("=== Backend Comparison ===\n")

    # Create comparison
    comparison = BackendComparison()

    # Evaluate SQLite
    print("Evaluating SQLite...")
    sqlite_report = await comparison.evaluate_backend("sqlite", db_path=":memory:")
    print(f"SQLite Overall Score: {sqlite_report.overall_score:.2f}\n")

    # Evaluate Kùzu
    print("Evaluating Kùzu...")
    kuzu_report = await comparison.evaluate_backend("kuzu", db_path=":memory:")
    print(f"Kùzu Overall Score: {kuzu_report.overall_score:.2f}\n")

    # Generate markdown report
    print("Generating comparison report...")
    report = comparison.generate_markdown_report()
    print("\n" + report)


async def example_convenience_function():
    """Example: Using the convenience function."""
    print("=== Using Convenience Function ===\n")

    # Evaluate all backends and generate report
    print("Running full evaluation...")
    report = await run_evaluation()

    print(report)


async def main():
    """Run all examples."""
    print("Memory Backend Evaluation Examples\n")
    print("=" * 50)
    print()

    # Run individual evaluations
    await example_quality_evaluation()
    await example_performance_evaluation()
    await example_reliability_evaluation()

    # Run comparison
    await example_backend_comparison()

    # Run convenience function
    # await example_convenience_function()


if __name__ == "__main__":
    asyncio.run(main())
