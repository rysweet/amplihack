"""
Workflow Tracking and Transcript Management Tool for Amplifier.

Provides workflow adherence tracking and conversation transcript management:
- Workflow step logging with timing
- Session transcript preservation and restoration
- Checkpoint creation
- Workflow statistics

Features:
- <5ms overhead per log entry
- JSONL format for efficient append-only logging
- Session-based transcript organization
- Context restoration for interrupted sessions
"""

from .tool import WorkflowTool, create_tool
from .tracker import (
    StepTimer,
    WorkflowTracker,
    get_workflow_stats,
    log_agent_invocation,
    log_skip,
    log_step,
    log_workflow_end,
    log_workflow_start,
    log_workflow_violation,
)
from .transcript import (
    TranscriptManager,
    TranscriptSummary,
    get_transcript_summary,
    list_transcripts,
    restore_transcript,
    save_checkpoint,
)

__all__ = [
    # Tracker
    "WorkflowTracker",
    "log_workflow_start",
    "log_step",
    "log_skip",
    "log_workflow_end",
    "log_agent_invocation",
    "log_workflow_violation",
    "StepTimer",
    "get_workflow_stats",
    # Transcript
    "TranscriptManager",
    "TranscriptSummary",
    "list_transcripts",
    "get_transcript_summary",
    "restore_transcript",
    "save_checkpoint",
    # Tool
    "WorkflowTool",
    "create_tool",
]
