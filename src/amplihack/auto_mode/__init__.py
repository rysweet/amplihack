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

from .orchestrator import AutoModeOrchestrator
from .session import SessionManager, SessionState
from .analysis import AnalysisEngine, ConversationAnalysis
from .quality_gates import QualityGateEvaluator, QualityGateResult

__all__ = [
    'AutoModeOrchestrator',
    'SessionManager',
    'SessionState',
    'AnalysisEngine',
    'ConversationAnalysis',
    'QualityGateEvaluator',
    'QualityGateResult'
]