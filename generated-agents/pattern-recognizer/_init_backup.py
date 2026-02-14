"""Code Pattern Recognizer Agent.

Learning agent that recognizes design patterns in Python code.
"""

try:
    from .agent import CodePatternRecognizer, PatternAnalysis, PatternMatch
    from .metrics import PatternRecognitionMetrics

    __all__ = [
        "CodePatternRecognizer",
        "PatternAnalysis",
        "PatternMatch",
        "PatternRecognitionMetrics",
    ]
except ImportError:
    # Allow testing without package installation
    pass
