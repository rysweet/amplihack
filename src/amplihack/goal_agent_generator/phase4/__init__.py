"""
Phase 4: Learning and Adaptation from Execution History.

Tracks agent execution, learns from patterns, and adapts plans for better performance.
"""

from .execution_tracker import ExecutionTracker
from .execution_database import ExecutionDatabase
from .metrics_collector import MetricsCollector
from .performance_analyzer import PerformanceAnalyzer
from .adaptation_engine import AdaptationEngine
from .plan_optimizer import PlanOptimizer
from .self_healing_manager import SelfHealingManager

__all__ = [
    "ExecutionTracker",
    "ExecutionDatabase",
    "MetricsCollector",
    "PerformanceAnalyzer",
    "AdaptationEngine",
    "PlanOptimizer",
    "SelfHealingManager",
]
