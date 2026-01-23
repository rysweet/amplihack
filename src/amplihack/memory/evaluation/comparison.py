"""Backend comparison and reporting.

Runs full evaluation across all backends and generates reports.

Philosophy:
- Comprehensive: All three evaluation dimensions
- Fair: Same test data for all backends
- Actionable: Clear recommendations fer use cases

Public API:
    BackendComparison: Main comparison class
    ComparisonReport: Results dataclass
    run_evaluation: Convenience function
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..backends import create_backend
from ..coordinator import MemoryCoordinator
from .performance_evaluator import PerformanceEvaluator, PerformanceMetrics
from .quality_evaluator import QualityEvaluator, QualityMetrics
from .reliability_evaluator import ReliabilityEvaluator, ReliabilityMetrics

logger = logging.getLogger(__name__)


@dataclass
class ComparisonReport:
    """Backend comparison results.

    Args:
        backend_name: Name of evaluated backend
        quality_metrics: Quality evaluation results
        performance_metrics: Performance evaluation results
        reliability_metrics: Reliability evaluation results
        overall_score: Weighted overall score (0-1)
        recommendations: Use case recommendations
        timestamp: When evaluation was run
    """

    backend_name: str
    quality_metrics: QualityMetrics
    performance_metrics: PerformanceMetrics
    reliability_metrics: ReliabilityMetrics
    overall_score: float
    recommendations: list[str]
    timestamp: datetime


class BackendComparison:
    """Compares memory backends across all evaluation dimensions.

    Runs:
    - Quality evaluation (relevance, precision, recall)
    - Performance evaluation (latency, throughput, scalability)
    - Reliability evaluation (integrity, concurrency, recovery)

    Generates comprehensive comparison report.
    """

    def __init__(self):
        """Initialize comparison."""
        self.results: dict[str, ComparisonReport] = {}

    async def evaluate_backend(self, backend_type: str, **backend_config: Any) -> ComparisonReport:
        """Evaluate a single backend.

        Args:
            backend_type: Backend type ('sqlite', 'kuzu')
            **backend_config: Backend-specific configuration

        Returns:
            Comparison report for this backend
        """
        logger.info(f"Evaluating {backend_type} backend...")

        # Create backend and coordinator
        backend = create_backend(backend_type=backend_type, **backend_config)
        coordinator = MemoryCoordinator(backend=backend)

        # Run evaluations
        quality_eval = QualityEvaluator(coordinator)
        performance_eval = PerformanceEvaluator(coordinator)
        reliability_eval = ReliabilityEvaluator(coordinator)

        # Create test set
        test_queries = await quality_eval.create_test_set(num_memories=50)

        # Run quality evaluation
        quality_metrics = await quality_eval.evaluate(test_queries)
        logger.info(
            f"{backend_type} quality: "
            f"Precision={quality_metrics.precision:.2f}, "
            f"Recall={quality_metrics.recall:.2f}"
        )

        # Run performance evaluation
        performance_metrics = await performance_eval.evaluate(num_operations=100)
        logger.info(
            f"{backend_type} performance: "
            f"Storage={performance_metrics.storage_latency_ms:.2f}ms, "
            f"Retrieval={performance_metrics.retrieval_latency_ms:.2f}ms"
        )

        # Run reliability evaluation
        reliability_metrics = await reliability_eval.evaluate()
        logger.info(
            f"{backend_type} reliability: "
            f"Integrity={reliability_metrics.data_integrity_score:.2f}, "
            f"Concurrency={reliability_metrics.concurrent_safety_score:.2f}"
        )

        # Calculate overall score (weighted average)
        overall_score = self._calculate_overall_score(
            quality_metrics, performance_metrics, reliability_metrics
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            backend_type, quality_metrics, performance_metrics, reliability_metrics
        )

        report = ComparisonReport(
            backend_name=backend_type,
            quality_metrics=quality_metrics,
            performance_metrics=performance_metrics,
            reliability_metrics=reliability_metrics,
            overall_score=overall_score,
            recommendations=recommendations,
            timestamp=datetime.now(),
        )

        self.results[backend_type] = report
        return report

    async def compare_all(self) -> dict[str, ComparisonReport]:
        """Compare all available backends.

        Returns:
            Dict mapping backend name to comparison report
        """
        backends = ["sqlite", "kuzu"]

        for backend_type in backends:
            try:
                await self.evaluate_backend(backend_type)
            except Exception as e:
                logger.error(f"Failed to evaluate {backend_type}: {e}")

        return self.results

    def _calculate_overall_score(
        self,
        quality: QualityMetrics,
        performance: PerformanceMetrics,
        reliability: ReliabilityMetrics,
    ) -> float:
        """Calculate weighted overall score.

        Weights:
        - Quality: 40% (most important - are results relevant?)
        - Performance: 30% (important - is it fast enough?)
        - Reliability: 30% (important - is it robust?)

        Args:
            quality: Quality metrics
            performance: Performance metrics
            reliability: Reliability metrics

        Returns:
            Overall score (0-1)
        """
        # Normalize quality score (average of precision and recall)
        quality_score = (quality.precision + quality.recall) / 2

        # Normalize performance score (based on contracts)
        storage_ok = 1.0 if performance.storage_latency_ms < 500 else 0.5
        retrieval_ok = 1.0 if performance.retrieval_latency_ms < 50 else 0.5
        performance_score = (storage_ok + retrieval_ok) / 2

        # Normalize reliability score (average of all metrics)
        reliability_score = (
            reliability.data_integrity_score
            + reliability.concurrent_safety_score
            + reliability.error_recovery_score
        ) / 3

        # Weighted average
        overall = (quality_score * 0.4) + (performance_score * 0.3) + (reliability_score * 0.3)

        return overall

    def _generate_recommendations(
        self,
        backend_type: str,
        quality: QualityMetrics,
        performance: PerformanceMetrics,
        reliability: ReliabilityMetrics,
    ) -> list[str]:
        """Generate use case recommendations.

        Args:
            backend_type: Backend type
            quality: Quality metrics
            performance: Performance metrics
            reliability: Reliability metrics

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Quality-based recommendations
        if quality.precision > 0.8 and quality.recall > 0.8:
            recommendations.append(
                f"{backend_type} excels at retrieval quality - good for knowledge-intensive tasks"
            )
        elif quality.precision > 0.7:
            recommendations.append(f"{backend_type} has good precision - few false positives")

        # Performance-based recommendations
        if performance.storage_latency_ms < 100:
            recommendations.append(
                f"{backend_type} has fast storage - good for high-write workloads"
            )
        if performance.retrieval_latency_ms < 10:
            recommendations.append(
                f"{backend_type} has ultra-fast retrieval - excellent for real-time queries"
            )

        # Reliability-based recommendations
        if reliability.data_integrity_score > 0.95:
            recommendations.append(
                f"{backend_type} has excellent data integrity - reliable for critical data"
            )
        if reliability.concurrent_safety_score > 0.9:
            recommendations.append(
                f"{backend_type} handles concurrency well - safe for multi-threaded use"
            )

        # Backend-specific recommendations
        if backend_type == "sqlite":
            recommendations.append("SQLite: Best for single-process, simple deployments")
        elif backend_type == "kuzu":
            recommendations.append("Kùzu: Best for graph queries and relationship traversal")

        return recommendations

    def generate_markdown_report(self) -> str:
        """Generate markdown comparison report.

        Returns:
            Markdown-formatted report
        """
        if not self.results:
            return "# Memory Backend Comparison\n\nNo evaluation results available."

        # Sort backends by overall score
        sorted_backends = sorted(
            self.results.items(), key=lambda x: x[1].overall_score, reverse=True
        )

        report = ["# Memory Backend Comparison Report\n"]
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Summary table
        report.append("## Summary\n")
        report.append("| Backend | Overall | Quality | Performance | Reliability |")
        report.append("|---------|---------|---------|-------------|-------------|")

        for backend_name, result in sorted_backends:
            quality_avg = (result.quality_metrics.precision + result.quality_metrics.recall) / 2
            perf_ok = 1.0 if result.performance_metrics.storage_latency_ms < 500 else 0.5
            reliability_avg = (
                result.reliability_metrics.data_integrity_score
                + result.reliability_metrics.concurrent_safety_score
                + result.reliability_metrics.error_recovery_score
            ) / 3

            report.append(
                f"| {backend_name} | {result.overall_score:.2f} | "
                f"{quality_avg:.2f} | {perf_ok:.2f} | {reliability_avg:.2f} |"
            )

        # Detailed results
        report.append("\n## Detailed Results\n")

        for backend_name, result in sorted_backends:
            report.append(f"\n### {backend_name}\n")

            # Quality metrics
            report.append("**Quality Metrics:**\n")
            report.append(f"- Relevance: {result.quality_metrics.relevance_score:.2f}")
            report.append(f"- Precision: {result.quality_metrics.precision:.2f}")
            report.append(f"- Recall: {result.quality_metrics.recall:.2f}")
            report.append(f"- NDCG: {result.quality_metrics.ndcg_score:.2f}\n")

            # Performance metrics
            report.append("**Performance Metrics:**\n")
            report.append(
                f"- Storage Latency: {result.performance_metrics.storage_latency_ms:.2f}ms "
                f"{'✅' if result.performance_metrics.storage_latency_ms < 500 else '❌'}"
            )
            report.append(
                f"- Retrieval Latency: {result.performance_metrics.retrieval_latency_ms:.2f}ms "
                f"{'✅' if result.performance_metrics.retrieval_latency_ms < 50 else '❌'}"
            )
            report.append(
                f"- Storage Throughput: {result.performance_metrics.storage_throughput:.1f} ops/sec"
            )
            report.append(
                f"- Retrieval Throughput: {result.performance_metrics.retrieval_throughput:.1f} ops/sec\n"
            )

            # Reliability metrics
            report.append("**Reliability Metrics:**\n")
            report.append(
                f"- Data Integrity: {result.reliability_metrics.data_integrity_score:.2f}"
            )
            report.append(
                f"- Concurrent Safety: {result.reliability_metrics.concurrent_safety_score:.2f}"
            )
            report.append(
                f"- Error Recovery: {result.reliability_metrics.error_recovery_score:.2f}\n"
            )

            # Recommendations
            report.append("**Recommendations:**\n")
            for rec in result.recommendations:
                report.append(f"- {rec}")
            report.append("")

        return "\n".join(report)


async def run_evaluation(backend_type: str | None = None, **backend_config: Any) -> str:
    """Convenience function to run evaluation and generate report.

    Args:
        backend_type: Specific backend to evaluate (None for all)
        **backend_config: Backend-specific configuration

    Returns:
        Markdown report

    Example:
        >>> report = await run_evaluation("sqlite")
        >>> print(report)

        >>> report = await run_evaluation()  # Compare all backends
        >>> print(report)
    """
    comparison = BackendComparison()

    if backend_type:
        # Evaluate single backend
        await comparison.evaluate_backend(backend_type, **backend_config)
    else:
        # Evaluate all backends
        await comparison.compare_all()

    return comparison.generate_markdown_report()


__all__ = ["BackendComparison", "ComparisonReport", "run_evaluation"]
