"""
Auto-Mode Module for Amplihack

This module provides persistent conversation analysis and improvement suggestions
using the Claude Agent SDK for continuous background analysis.

Public Interface:
    AutoModeOrchestrator: Main orchestration class
    SessionManager: Session state and persistence
    AnalysisEngine: Conversation analysis and quality assessment
    QualityGateEvaluator: Quality gate evaluation and intervention decisions
"""

from .analysis import AnalysisEngine, ConversationAnalysis
from .orchestrator import AutoModeOrchestrator
from .quality_gates import QualityGateEvaluator, QualityGateResult
from .session import SessionManager, SessionState

# Configuration constants are available for import but not in __all__
from . import config

__all__ = [
    "AutoModeOrchestrator",
    "SessionManager",
    "SessionState",
    "AnalysisEngine",
    "ConversationAnalysis",
    "QualityGateEvaluator",
    "QualityGateResult",
]
