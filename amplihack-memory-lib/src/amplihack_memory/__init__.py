"""amplihack-memory-lib: Standalone memory system for goal-seeking agents."""

__version__ = "0.1.0"

from .connector import MemoryConnector
from .exceptions import (
    ExperienceNotFoundError,
    InvalidExperienceError,
    MemoryError,
    MemoryQuotaExceededError,
)
from .experience import Experience, ExperienceType
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
    "Experience",
    "ExperienceType",
    "MemoryConnector",
    "ExperienceStore",
    "AgentCapabilities",
    "ScopeLevel",
    "CredentialScrubber",
    "QueryValidator",
    "SecureMemoryBackend",
    "MemoryError",
    "ExperienceNotFoundError",
    "InvalidExperienceError",
    "MemoryQuotaExceededError",
    "SecurityViolationError",
    "QueryCostExceededError",
]
