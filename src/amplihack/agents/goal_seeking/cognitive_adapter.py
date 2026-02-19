"""Adapter wrapping CognitiveMemory (6-type) for backward compatibility.

Provides the same interface as FlatRetrieverAdapter (store_fact, search,
get_all_facts) while leveraging CognitiveMemory's 6 memory types:
- Sensory: raw input buffering with TTL
- Working: bounded task state tracking (20 slots)
- Episodic: events with consolidation
- Semantic: facts with confidence and similarity edges
- Procedural: step sequences with usage tracking
- Prospective: future intentions with trigger conditions

Philosophy:
- Drop-in replacement for FlatRetrieverAdapter
- Exposes additional cognitive capabilities via dedicated methods
- Falls back gracefully if CognitiveMemory unavailable
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Try importing CognitiveMemory, fall back to HierarchicalMemory
try:
    from amplihack_memory.cognitive_memory import CognitiveMemory

    HAS_COGNITIVE_MEMORY = True
except ImportError:
    HAS_COGNITIVE_MEMORY = False


class CognitiveAdapter:
    """Adapter providing FlatRetrieverAdapter-compatible interface over CognitiveMemory.

    Uses the 6-type CognitiveMemory system from amplihack-memory-lib.
    Falls back to FlatRetrieverAdapter if the library is not installed.

    Args:
        agent_name: Name of the owning agent
        db_path: Path to Kuzu database directory

    Example:
        >>> adapter = CognitiveAdapter("test_agent", "/tmp/test_db")
        >>> adapter.store_fact("Biology", "Cells are the basic unit of life")
        >>> results = adapter.search("cells")
        >>> print(results[0]["context"])  # "Biology"
    """

    def __init__(self, agent_name: str, db_path: str | Path | None = None):
        self.agent_name = agent_name

        if db_path is None:
            db_path = Path.home() / ".amplihack" / "cognitive_memory" / agent_name
        elif isinstance(db_path, str):
            db_path = Path(db_path)

        self._db_path = db_path

        if HAS_COGNITIVE_MEMORY:
            # Clean path for Kuzu (needs non-existent directory)
            kuzu_path = db_path / "kuzu_db"
            if not kuzu_path.exists():
                kuzu_path.parent.mkdir(parents=True, exist_ok=True)
            self.memory = CognitiveMemory(agent_name=agent_name, db_path=str(kuzu_path))
            self._cognitive = True
        else:
            # Fallback to HierarchicalMemory
            from .hierarchical_memory import HierarchicalMemory

            logger.warning("CognitiveMemory not available, falling back to HierarchicalMemory")
            self.memory = HierarchicalMemory(agent_name=agent_name, db_path=db_path)
            self._cognitive = False

    # ------------------------------------------------------------------
    # FlatRetrieverAdapter-compatible interface
    # ------------------------------------------------------------------

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
            context: Topic/concept
            fact: The fact content
            confidence: Confidence score 0.0-1.0
            tags: Optional tags
            source_id: Optional source episode ID
            temporal_metadata: Optional temporal context

        Returns:
            node_id of stored knowledge
        """
        if not context or not context.strip():
            raise ValueError("context cannot be empty")
        if not fact or not fact.strip():
            raise ValueError("fact cannot be empty")

        if self._cognitive:
            return self.memory.store_fact(
                concept=context.strip(),
                content=fact.strip(),
                confidence=confidence,
                source_id=source_id,
                tags=tags,
                temporal_metadata=temporal_metadata,
            )
        return self.memory.store_knowledge(
            content=fact.strip(),
            concept=context.strip(),
            confidence=confidence,
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

        if self._cognitive:
            results = self.memory.search_facts(
                query=query.strip(), limit=limit, min_confidence=min_confidence
            )
            return [self._semantic_fact_to_dict(r) for r in results]
        subgraph = self.memory.retrieve_subgraph(query=query.strip(), max_nodes=limit)
        return [self._node_to_dict(n) for n in subgraph.nodes if n.confidence >= min_confidence]

    def get_all_facts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve all facts without keyword filtering."""
        if self._cognitive:
            results = self.memory.get_all_facts(limit=limit)
            return [self._semantic_fact_to_dict(r) for r in results]
        nodes = self.memory.get_all_knowledge(limit=limit)
        return [self._node_to_dict(n) for n in nodes]

    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics."""
        stats = self.memory.get_statistics()
        if self._cognitive:
            stats["total_experiences"] = stats.get("total", 0)
        return stats

    def store_episode(self, content: str, source_label: str = "") -> str:
        """Store an episode (raw source content)."""
        if self._cognitive:
            return self.memory.store_episode(content=content, source_label=source_label)
        return self.memory.store_episode(content=content, source_label=source_label)

    # ------------------------------------------------------------------
    # CognitiveMemory-specific capabilities
    # ------------------------------------------------------------------

    def push_working(
        self, slot_type: str, content: str, task_id: str, relevance: float = 1.0
    ) -> str | None:
        """Add to working memory (bounded, 20 slots per task)."""
        if self._cognitive:
            return self.memory.push_working(slot_type, content, task_id, relevance)
        return None

    def get_working(self, task_id: str) -> list[Any]:
        """Get working memory slots for a task."""
        if self._cognitive:
            return self.memory.get_working(task_id)
        return []

    def clear_working(self, task_id: str) -> int:
        """Clear working memory for a task."""
        if self._cognitive:
            return self.memory.clear_working(task_id)
        return 0

    def store_procedure(self, name: str, steps: list[str], **kwargs: Any) -> str | None:
        """Store a procedural memory (step sequence)."""
        if self._cognitive:
            return self.memory.store_procedure(name=name, steps=steps, **kwargs)
        return None

    def recall_procedure(self, query: str, limit: int = 5) -> list[Any]:
        """Recall a procedure by query."""
        if self._cognitive:
            return self.memory.recall_procedure(query=query, limit=limit)
        return []

    def store_prospective(
        self, description: str, trigger_condition: str, action: str, **kwargs: Any
    ) -> str | None:
        """Store a prospective memory (future intention)."""
        if self._cognitive:
            return self.memory.store_prospective(
                description=description,
                trigger_condition=trigger_condition,
                action_on_trigger=action,
                **kwargs,
            )
        return None

    def check_triggers(self, content: str) -> list[Any]:
        """Check if any prospective memories are triggered by content."""
        if self._cognitive:
            return self.memory.check_triggers(content)
        return []

    def record_sensory(self, modality: str, raw_data: str, ttl_seconds: int = 300) -> str | None:
        """Record sensory memory (short-lived observation)."""
        if self._cognitive:
            return self.memory.record_sensory(modality, raw_data, ttl_seconds)
        return None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close underlying memory."""
        self.memory.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def _semantic_fact_to_dict(fact: Any) -> dict[str, Any]:
        """Convert CognitiveMemory SemanticFact to flat dict."""
        return {
            "experience_id": fact.node_id,
            "context": fact.concept,
            "outcome": fact.content,
            "confidence": fact.confidence,
            "timestamp": str(fact.created_at) if hasattr(fact, "created_at") else "",
            "tags": fact.tags if hasattr(fact, "tags") else [],
            "metadata": fact.metadata if hasattr(fact, "metadata") else {},
        }

    @staticmethod
    def _node_to_dict(node: Any) -> dict[str, Any]:
        """Convert HierarchicalMemory KnowledgeNode to flat dict."""
        return {
            "experience_id": node.node_id,
            "context": node.concept,
            "outcome": node.content,
            "confidence": node.confidence,
            "timestamp": node.created_at,
            "tags": node.tags,
            "metadata": node.metadata if hasattr(node, "metadata") else {},
        }


__all__ = ["CognitiveAdapter", "HAS_COGNITIVE_MEMORY"]
