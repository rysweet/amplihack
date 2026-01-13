"""Retrieval pipeline fer 5-type memory system.

Re-exports RetrievalQuery from coordinator.

Philosophy:
- Module organization: Separate concerns
- Public API: RetrievalQuery dataclass
"""

from .coordinator import RetrievalQuery

__all__ = ["RetrievalQuery"]
