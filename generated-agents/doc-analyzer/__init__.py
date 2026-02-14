"""
Documentation Analyzer Agent

A learning agent that analyzes documentation quality and improves over time.
"""

from .agent import DocAnalysis, DocumentationAnalyzer, SectionInfo
from .metrics import AnalysisMetrics, LearningProgress, MetricsTracker
from .mslearn_fetcher import MSLearnFetcher, get_sample_markdown

__version__ = "0.1.0"

__all__ = [
    "DocumentationAnalyzer",
    "DocAnalysis",
    "SectionInfo",
    "MetricsTracker",
    "LearningProgress",
    "AnalysisMetrics",
    "MSLearnFetcher",
    "get_sample_markdown",
]
