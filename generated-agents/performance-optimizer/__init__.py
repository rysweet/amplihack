"""
Performance Optimizer Learning Agent

A learning agent that analyzes Python code for performance issues,
applies optimizations, and learns which techniques work best over time.
"""

try:
    from .agent import (
        CodeAnalysis,
        OptimizationResult,
        OptimizationTechnique,
        PerformanceOptimizer,
    )
    from .metrics import (
        LearningMetrics,
        calculate_metrics_from_stats,
        format_metrics_report,
    )
    from .optimization_patterns import (
        OPTIMIZATION_PATTERNS,
        OptimizationPattern,
        get_all_categories,
        get_pattern,
        get_patterns_by_category,
    )

    __all__ = [
        "PerformanceOptimizer",
        "OptimizationResult",
        "OptimizationTechnique",
        "CodeAnalysis",
        "LearningMetrics",
        "calculate_metrics_from_stats",
        "format_metrics_report",
        "OptimizationPattern",
        "OPTIMIZATION_PATTERNS",
        "get_pattern",
        "get_patterns_by_category",
        "get_all_categories",
    ]
except ImportError:
    # Allow module to be imported even if dependencies aren't available
    pass

__version__ = "0.1.0"
