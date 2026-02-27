"""amplihack-memory-lib: Standalone memory system for goal-seeking agents."""

__version__ = "0.2.0"

from .cognitive_memory import CognitiveMemory
from .connector import MemoryConnector
from .exceptions import (
    ExperienceNotFoundError,
    InvalidExperienceError,
    MemoryError,
    MemoryQuotaExceededError,
)
from .experience import Experience, ExperienceType
from .memory_types import (
    ConsolidatedEpisode,
    EpisodicMemory,
    MemoryCategory,
    ProceduralMemory,
    ProspectiveMemory,
    SemanticFact,
    SensoryItem,
    WorkingMemorySlot,
)
from .security import (
    AgentCapabilities,
    CredentialScrubber,
    QueryCostExceededError,
    QueryValidator,
    ScopeLevel,
    SecureMemoryBackend,
    SecurityViolationError,
)
from .store import ExperienceStore

__all__ = [
    # Cognitive memory (new)
    "CognitiveMemory",
    "MemoryCategory",
    "SensoryItem",
    "WorkingMemorySlot",
    "EpisodicMemory",
    "SemanticFact",
    "ProceduralMemory",
    "ProspectiveMemory",
    "ConsolidatedEpisode",
    # Experience store (existing)
    "Experience",
    "ExperienceType",
    "MemoryConnector",
    "ExperienceStore",
    # Security (existing)
    "AgentCapabilities",
    "ScopeLevel",
    "CredentialScrubber",
    "QueryValidator",
    "SecureMemoryBackend",
    # Exceptions (existing)
    "MemoryError",
    "ExperienceNotFoundError",
    "InvalidExperienceError",
    "MemoryQuotaExceededError",
    "SecurityViolationError",
    "QueryCostExceededError",
]
