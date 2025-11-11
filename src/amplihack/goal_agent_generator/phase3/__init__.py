"""
Phase 3: Multi-Agent Coordination for Complex Goals.

Provides tools for decomposing complex goals into coordinated sub-agents,
managing shared state, and orchestrating parallel/sequential execution.
"""

from .coordination_analyzer import CoordinationAnalyzer
from .coordination_protocol import CoordinationProtocol, MessageType
from .orchestration_layer import OrchestrationLayer, OrchestrationResult
from .shared_state_manager import SharedStateManager
from .sub_agent_generator import SubAgentGenerator

__all__ = [
    "CoordinationAnalyzer",
    "SubAgentGenerator",
    "SharedStateManager",
    "CoordinationProtocol",
    "MessageType",
    "OrchestrationLayer",
    "OrchestrationResult",
]
