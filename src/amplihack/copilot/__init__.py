"""Copilot CLI integration for amplihack.

This module provides UX parity between Claude Code and Copilot CLI by offering:
- Unified output formatting
- Standardized error messages
- Cross-platform compatibility
- Configuration management
- Workflow orchestration and state management
"""

from .agent_wrapper import (
    AgentInfo,
    AgentInvocationResult,
    invoke_copilot_agent,
    discover_agents,
    list_agents,
    check_copilot,
)
from .errors import CopilotError, InstallationError, InvocationError
from .formatters import OutputFormatter, ProgressIndicator, format_agent_output
from .session_manager import CopilotSessionManager, SessionRegistry, SessionState
from .workflow_orchestrator import (
    WorkflowOrchestrator,
    WorkflowStep,
    WorkflowExecutionResult,
)
from .workflow_state import (
    WorkflowState,
    WorkflowStateManager,
    TodoItem,
    Decision,
    StepStatus,
)

__all__ = [
    "AgentInfo",
    "AgentInvocationResult",
    "invoke_copilot_agent",
    "discover_agents",
    "list_agents",
    "check_copilot",
    "CopilotError",
    "InstallationError",
    "InvocationError",
    "OutputFormatter",
    "ProgressIndicator",
    "format_agent_output",
    "CopilotSessionManager",
    "SessionState",
    "SessionRegistry",
    "WorkflowOrchestrator",
    "WorkflowStep",
    "WorkflowExecutionResult",
    "WorkflowState",
    "WorkflowStateManager",
    "TodoItem",
    "Decision",
    "StepStatus",
]
