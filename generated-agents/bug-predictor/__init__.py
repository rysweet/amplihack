"""
Bug Predictor Learning Agent

A learning agent that predicts bugs in Python code and improves through experience.
"""

from .agent import BugPattern, BugPrediction, BugPredictor
from .bug_patterns import (
    PATTERN_DATABASE,
    get_all_patterns,
    get_critical_patterns,
    get_pattern,
    get_patterns_by_severity,
)
from .metrics import BugPredictorMetrics

__version__ = "0.1.0"

__all__ = [
    "BugPredictor",
    "BugPattern",
    "BugPrediction",
    "BugPredictorMetrics",
    "PATTERN_DATABASE",
    "get_pattern",
    "get_all_patterns",
    "get_patterns_by_severity",
    "get_critical_patterns",
]
