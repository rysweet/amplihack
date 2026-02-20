"""Flat retriever adapter wrapping HierarchicalMemory for backward compatibility.

Philosophy:
- Adapter pattern: same interface as MemoryRetriever but backed by HierarchicalMemory
- store_fact -> store_knowledge(category=SEMANTIC)
- search -> retrieve_subgraph then flatten to list[dict]
- get_all_facts -> get_all_knowledge then flatten
- Drop-in replacement for MemoryRetriever in LearningAgent

Public API:
    FlatRetrieverAdapter: Backward-compatible interface over HierarchicalMemory
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .hierarchical_memory import HierarchicalMemory, MemoryCategory


class FlatRetrieverAdapter:
    """Adapter providing MemoryRetriever-compatible interface over HierarchicalMemory.

    This allows LearningAgent to use HierarchicalMemory without
    changing its existing code that expects store_fact/search/get_all_facts.

    Args:
        agent_name: Name of the owning agent
        db_path: Path to Kuzu database directory

    Example:
        >>> adapter = FlatRetrieverAdapter("test_agent", "/tmp/test_db")
        >>> adapter.store_fact("Biology", "Cells are the basic unit of life")
        >>> results = adapter.search("cells")
        >>> print(results[0]["context"])  # "Biology"
    """

    def __init__(self, agent_name: str, db_path: str | Path | None = None):
        self.agent_name = agent_name
        self.memory = HierarchicalMemory(agent_name=agent_name, db_path=db_path)

    def store_fact(
        self,
        context: str,
        fact: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
        source_id: str = "",
        temporal_metadata: dict | None = None,
    ) -> str:
        """Store a fact as semantic knowledge.

        Args:
            context: Topic/concept (mapped to concept field)
            fact: The fact content (mapped to content field)
            confidence: Confidence score 0.0-1.0
            tags: Optional tags
            source_id: Optional source episode ID
            temporal_metadata: Optional temporal context dict

        Returns:
            node_id of stored knowledge

        Raises:
            ValueError: If context or fact is empty
            ValueError: If confidence is not between 0.0 and 1.0
        """
        if not context or not context.strip():
            raise ValueError("context cannot be empty")
        if not fact or not fact.strip():
            raise ValueError("fact cannot be empty")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

        return self.memory.store_knowledge(
            content=fact.strip(),
            concept=context.strip(),
            confidence=confidence,
            category=MemoryCategory.SEMANTIC,
            source_id=source_id,
            tags=tags,
            temporal_metadata=temporal_metadata,
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Search memory and return flat list of result dicts."""
        if not query or not query.strip():
            return []

        subgraph = self.memory.retrieve_subgraph(
            query=query.strip(),
            max_nodes=limit,
        )

        results = []
        for node in subgraph.nodes:
            if node.confidence >= min_confidence:
                results.append(self._node_to_dict(node))

        return results[:limit]

    def get_all_facts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve all facts without keyword filtering."""
        nodes = self.memory.get_all_knowledge(limit=limit)
        return [self._node_to_dict(node) for node in nodes]

    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics."""
        return self.memory.get_statistics()

    def store_episode(self, content: str, source_label: str = "") -> str:
        """Store an episode (raw source content)."""
        return self.memory.store_episode(content=content, source_label=source_label)

    def close(self) -> None:
        """Close underlying HierarchicalMemory."""
        self.memory.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.close()

    @staticmethod
    def _node_to_dict(node) -> dict[str, Any]:
        """Convert a KnowledgeNode to MemoryRetriever-compatible dict."""
        return {
            "experience_id": node.node_id,
            "context": node.concept,
            "outcome": node.content,
            "confidence": node.confidence,
            "timestamp": node.created_at,
            "tags": node.tags,
            "metadata": node.metadata if hasattr(node, "metadata") else {},
        }


__all__ = ["FlatRetrieverAdapter"]
