from __future__ import annotations

"""Memory retrieval using Kuzu backend for goal-seeking agents.

Philosophy:
- Single responsibility: Query memory system
- Uses amplihack-memory-lib with Kuzu backend
- Simple interface for text search
- Returns structured results for LLM consumption
"""

from pathlib import Path
from typing import Any

from amplihack_memory import Experience, ExperienceStore, ExperienceType


class MemoryRetriever:
    """Memory search interface using Kuzu graph database.

    Provides simple text-based search over stored experiences.
    Used by goal-seeking agents to retrieve relevant knowledge.

    Attributes:
        agent_name: Name of the agent (for memory isolation)
        connector: MemoryConnector to Kuzu backend
    """

    def __init__(self, agent_name: str, storage_path: Path | None = None, backend: str = "kuzu"):
        """Initialize memory retriever.

        Args:
            agent_name: Agent identifier (must not be empty)
            storage_path: Storage directory (defaults to ~/.amplihack/memory/<agent>)
            backend: Backend type ('kuzu' or 'sqlite', default: 'kuzu')

        Raises:
            ValueError: If agent_name is empty
        """
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name cannot be empty")

        self.agent_name = agent_name.strip()
        store_kwargs: dict[str, Any] = {"agent_name": self.agent_name}
        if storage_path:
            store_kwargs["storage_path"] = (
                Path(storage_path) if isinstance(storage_path, str) else storage_path
            )
        self.store = ExperienceStore(**store_kwargs)
        self.connector = self.store.connector

    def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        experience_type: ExperienceType | None = None,
    ) -> list[dict[str, Any]]:
        """Search memory for relevant experiences.

        Args:
            query: Search query (text)
            limit: Maximum results to return
            min_confidence: Minimum confidence threshold
            experience_type: Filter by experience type

        Returns:
            List of matching experiences as dictionaries with:
                - context: The original context
                - outcome: The learned outcome
                - confidence: Confidence score (0.0-1.0)
                - timestamp: When experience was stored
                - tags: Associated tags

        Example:
            >>> retriever = MemoryRetriever("wikipedia_agent")
            >>> results = retriever.search("photosynthesis", limit=5)
            >>> for result in results:
            ...     print(f"Context: {result['context']}")
            ...     print(f"Outcome: {result['outcome']}")
        """
        if not query or not query.strip():
            return []

        experiences = self.store.search(
            query=query.strip(),
            limit=limit,
            min_confidence=min_confidence,
            experience_type=experience_type,
        )

        # Convert to dictionaries for easier consumption
        results = []
        for exp in experiences:
            results.append(
                {
                    "experience_id": exp.experience_id,
                    "context": exp.context,
                    "outcome": exp.outcome,
                    "confidence": exp.confidence,
                    "timestamp": exp.timestamp.isoformat(),
                    "tags": exp.tags,
                    "metadata": exp.metadata,
                }
            )

        return results

    def store_fact(
        self, context: str, fact: str, confidence: float = 0.9, tags: list[str] | None = None
    ) -> str:
        """Store a learned fact in memory.

        Args:
            context: The context where this fact applies
            fact: The actual fact/knowledge learned
            confidence: Confidence in this fact (0.0-1.0)
            tags: Optional tags for categorization

        Returns:
            experience_id: ID of stored experience

        Raises:
            ValueError: If context or fact is empty
            ValueError: If confidence is not between 0.0 and 1.0

        Example:
            >>> retriever = MemoryRetriever("wikipedia_agent")
            >>> exp_id = retriever.store_fact(
            ...     context="Photosynthesis",
            ...     fact="Plants convert light energy into chemical energy",
            ...     tags=["biology", "plants"]
            ... )
        """
        if not context or not context.strip():
            raise ValueError("context cannot be empty")
        if not fact or not fact.strip():
            raise ValueError("fact cannot be empty")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

        experience = Experience(
            experience_type=ExperienceType.SUCCESS,
            context=context.strip(),
            outcome=fact.strip(),
            confidence=confidence,
            tags=tags or [],
        )

        return self.connector.store_experience(experience)

    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics.

        Returns:
            Dictionary with storage statistics:
                - total_experiences: Total number of stored experiences
                - by_type: Count by experience type
                - storage_size_kb: Storage size in KB
        """
        return self.store.get_statistics()

    def close(self) -> None:
        """Close database connection."""
        self.connector.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.close()
