"""Context Management Skill - Proactive context window management.

This skill provides intelligent token monitoring, context extraction,
and selective rehydration for Claude Code sessions.
"""

from .context_extractor import ContextExtractor
from .context_rehydrator import ContextRehydrator
from .core import (
    check_status,
    context_management_skill,
    create_snapshot,
    list_snapshots,
    rehydrate_context,
)
from .models import ContextSnapshot, UsageStats
from .orchestrator import ContextManagementOrchestrator
from .token_monitor import TokenMonitor

__all__ = [
    # Main skill entry point
    "context_management_skill",
    # Convenience functions
    "check_status",
    "create_snapshot",
    "rehydrate_context",
    "list_snapshots",
    # Data models
    "UsageStats",
    "ContextSnapshot",
    # Component bricks (for advanced usage)
    "TokenMonitor",
    "ContextExtractor",
    "ContextRehydrator",
    "ContextManagementOrchestrator",
]

__version__ = "1.0.0"
