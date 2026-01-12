"""Storage pipeline fer 5-type memory system.

Re-exports StorageRequest from coordinator.

Philosophy:
- Module organization: Separate concerns
- Public API: StorageRequest dataclass
"""

from .coordinator import StorageRequest

__all__ = ["StorageRequest"]
