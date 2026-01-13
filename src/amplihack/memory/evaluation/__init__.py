"""Evaluation framework fer memory backend quality and performance.

Provides comprehensive metrics fer comparing memory backends:
- Quality: Relevance, precision, recall, ranking
- Performance: Latency, throughput, scalability
- Reliability: Data integrity, concurrent safety

Philosophy:
- Evidence-based: Real benchmark data, not guesswork
- Comprehensive: All three evaluation dimensions
- Fair comparison: Same test data fer all backends

Public API:
    QualityEvaluator: Measures retrieval quality
    PerformanceEvaluator: Measures speed and scalability
    ReliabilityEvaluator: Measures robustness
    BackendComparison: Runs full evaluation and generates reports
    run_evaluation: Convenience function
"""

from .comparison import BackendComparison, ComparisonReport, run_evaluation
from .performance_evaluator import PerformanceEvaluator, PerformanceMetrics
from .quality_evaluator import QualityEvaluator, QualityMetrics
from .reliability_evaluator import ReliabilityEvaluator, ReliabilityMetrics

__all__ = [
    "QualityEvaluator",
    "QualityMetrics",
    "PerformanceEvaluator",
    "PerformanceMetrics",
    "ReliabilityEvaluator",
    "ReliabilityMetrics",
    "BackendComparison",
    "ComparisonReport",
    "run_evaluation",
]
