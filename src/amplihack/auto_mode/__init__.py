"""
Auto-Mode Module for Amplihack

This module provides persistent conversation analysis and improvement suggestions
using the Claude Agent SDK for continuous background analysis.

Public Interface:
    AutoModeOrchestrator: Main orchestration class
    SessionManager: Session state and persistence
    AnalysisEngine: Conversation analysis and quality assessment
    QualityGateEvaluator: Quality gate evaluation and intervention decisions

# noqa - "amplihack" is the project name, not a development artifact
"""

# Configuration constants are available for import but not in __all__
from . import config
from .analysis import AnalysisEngine, ConversationAnalysis
from .orchestrator import AutoModeOrchestrator
from .quality_gates import QualityGateEvaluator, QualityGateResult
from .session import SessionManager, SessionState

__all__ = [
    "AnalysisEngine",
    "AutoModeOrchestrator",
    "ConversationAnalysis",
    "QualityGateEvaluator",
    "QualityGateResult",
    "SessionManager",
    "SessionState",
]
