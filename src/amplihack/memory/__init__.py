"""Agent Memory System for amplihack.

Provides persistent memory storage for AI agents with session isolation,
thread-safe operations, and efficient retrieval.
"""

from .database import MemoryDatabase
from .manager import MemoryManager
from .models import MemoryEntry, MemoryType, SessionInfo

# Beads integration exports
from .beads_provider import BeadsMemoryProvider
from .beads_adapter import BeadsAdapter
from .beads_sync import BeadsSync
from .workflow_integration import BeadsWorkflowIntegration
from .agent_context import BeadsAgentContext
from .beads_prerequisites import BeadsPrerequisites, BeadsInstaller, verify_beads_setup

__all__ = [
    "MemoryDatabase",
    "MemoryEntry",
    "MemoryManager",
    "MemoryType",
    "SessionInfo",
    # Beads integration
    "BeadsMemoryProvider",
    "BeadsAdapter",
    "BeadsSync",
    "BeadsWorkflowIntegration",
    "BeadsAgentContext",
    "BeadsPrerequisites",
    "BeadsInstaller",
    "verify_beads_setup",
]


# Convenience function for provider access
def get_provider(name: str = "beads"):
    """Get memory provider by name.

    Args:
        name: Provider name (default: "beads")

    Returns:
        Provider instance or None
    """
    if name == "beads":
        try:
            adapter = BeadsAdapter()
            if adapter.is_available():
                return BeadsMemoryProvider(adapter)
        except Exception:
            pass
    return None
