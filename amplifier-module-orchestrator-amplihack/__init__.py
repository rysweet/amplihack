"""
Amplifier Module Orchestrator - AmplifierHack

Self-contained module for multi-agent orchestration and synthesis workflows.
See README.md for full contract specification.

Basic Usage:
    >>> from amplifier_module_orchestrator_amplihack import (
    ...     initialize_orchestrator,
    ...     execute_workflow,
    ...     OrchestratorConfig,
    ...     WorkflowRequest
    ... )
    >>> config = OrchestratorConfig(max_agents=5, timeout=30)
    >>> orchestrator = initialize_orchestrator(config)
    >>> request = WorkflowRequest(
    ...     task="Synthesize documents",
    ...     documents=["doc1", "doc2"],
    ...     config={}
    ... )
    >>> result = execute_workflow(orchestrator, request)
    >>> assert result.status == "success"
"""

from .core import initialize_orchestrator, execute_workflow, Orchestrator, Agent
from .models import OrchestratorConfig, WorkflowRequest, WorkflowResult, AgentResult, AgentType

__all__ = [
    "initialize_orchestrator",
    "execute_workflow",
    "Orchestrator",
    "Agent",
    "OrchestratorConfig",
    "WorkflowRequest",
    "WorkflowResult",
    "AgentResult",
    "AgentType",
]

__version__ = "1.0.0"
