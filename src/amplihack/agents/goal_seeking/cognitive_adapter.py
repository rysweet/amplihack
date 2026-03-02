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
    from amplihack_memory.cognitive_memory import CognitiveMemory  # type: ignore[import-not-found]

    HAS_COGNITIVE_MEMORY = True
except ImportError:
    HAS_COGNITIVE_MEMORY = False

try:
    import amplihack_memory.graph  # type: ignore[import-not-found]  # noqa: F401

    HAS_FEDERATED = True
except ImportError:
    HAS_FEDERATED = False


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

    def __init__(
        self,
        agent_name: str,
        db_path: str | Path | None = None,
        require_cognitive: bool = False,
        hive_store: Any | None = None,
    ):
        self.agent_name = agent_name
        self.memory: Any = None  # CognitiveMemory or HierarchicalMemory
        self._hive_store = hive_store  # Optional shared hive for distributed memory

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
            if require_cognitive:
                raise ImportError(
                    "CognitiveMemory required but amplihack_memory.cognitive_memory "
                    "not available. Install amplihack-memory-lib."
                )
            # Fallback to HierarchicalMemory
            from .hierarchical_memory import HierarchicalMemory

            logger.error(
                "CognitiveMemory not available, falling back to HierarchicalMemory. "
                "Install amplihack-memory-lib for full 6-type cognitive capabilities."
            )
            self.memory = HierarchicalMemory(agent_name=agent_name, db_path=db_path)
            self._cognitive = False

    @property
    def backend_type(self) -> str:
        """Return which memory backend is active."""
        return "cognitive" if self._cognitive else "hierarchical"

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
        """Search memory and return flat list of result dicts.

        When a hive_store is connected, searches both local memory and
        the shared hive, deduplicates by content, and returns merged results.
        """
        if not query or not query.strip():
            return []

        if self._cognitive:
            results = self.memory.search_facts(
                query=query.strip(), limit=limit, min_confidence=min_confidence
            )
            local_results = [self._semantic_fact_to_dict(r) for r in results]
        else:
            subgraph = self.memory.retrieve_subgraph(query=query.strip(), max_nodes=limit)
            local_results = [
                self._node_to_dict(n) for n in subgraph.nodes if n.confidence >= min_confidence
            ]

        if self._hive_store is None:
            return local_results

        # Query hive and merge
        hive_results = self._search_hive(query.strip(), limit=limit)
        return self._merge_results(local_results, hive_results, limit)

    def get_all_facts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve all facts without keyword filtering.

        When a hive_store is connected, returns facts from both local
        memory and the shared hive, deduplicated by content.
        """
        if self._cognitive:
            results = self.memory.get_all_facts(limit=limit)
            local_results = [self._semantic_fact_to_dict(r) for r in results]
        else:
            nodes = self.memory.get_all_knowledge(limit=limit)
            local_results = [self._node_to_dict(n) for n in nodes]

        if self._hive_store is None:
            return local_results

        hive_results = self._get_all_hive_facts(limit=limit)
        return self._merge_results(local_results, hive_results, limit)

    def _search_hive(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search the shared hive store."""
        if self._hive_store is None:
            return []
        try:
            # FederatedGraphStore.federated_query returns FederatedQueryResult
            if hasattr(self._hive_store, "federated_query"):
                fqr = self._hive_store.federated_query(query, limit=limit)
                return [
                    {
                        "context": r.get("concept", ""),
                        "fact": r.get("content", ""),
                        "confidence": r.get("confidence", 0.5),
                        "tags": r.get("tags", []),
                        "source": f"hive:{r.get('source', 'unknown')}",
                    }
                    for r in (fqr.results if hasattr(fqr, "results") else fqr)
                ]
            # HiveGraphStore or InMemoryHiveGraph with query_facts
            if hasattr(self._hive_store, "query_facts"):
                facts = self._hive_store.query_facts(query, limit=limit)
                return [
                    {
                        "context": f.concept,
                        "fact": f.content,
                        "confidence": f.confidence,
                        "tags": getattr(f, "tags", []),
                        "source": f"hive:{getattr(f, 'source_agent', 'unknown')}",
                    }
                    for f in facts
                ]
            # InMemoryHiveGraph with query_federated
            if hasattr(self._hive_store, "query_federated"):
                facts = self._hive_store.query_federated(query, limit=limit)
                return [
                    {
                        "context": f.concept,
                        "fact": f.content,
                        "confidence": f.confidence,
                        "tags": getattr(f, "tags", []),
                        "source": f"hive:{getattr(f, 'source_agent', 'unknown')}",
                    }
                    for f in facts
                ]
        except Exception:
            logger.exception("Error searching hive store")
        return []

    def _get_all_hive_facts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get all facts from the shared hive store."""
        if self._hive_store is None:
            return []
        try:
            if hasattr(self._hive_store, "get_all_facts"):
                facts = self._hive_store.get_all_facts(limit=limit)
                if facts and isinstance(facts[0], dict):
                    return facts[:limit]
                return [
                    {
                        "context": getattr(f, "concept", ""),
                        "fact": getattr(f, "content", ""),
                        "confidence": getattr(f, "confidence", 0.5),
                        "tags": getattr(f, "tags", []),
                        "source": f"hive:{getattr(f, 'source_agent', 'unknown')}",
                    }
                    for f in facts[:limit]
                ]
            if hasattr(self._hive_store, "query_facts"):
                facts = self._hive_store.query_facts("", limit=limit)
                return [
                    {
                        "context": f.concept,
                        "fact": f.content,
                        "confidence": f.confidence,
                        "tags": getattr(f, "tags", []),
                        "source": f"hive:{getattr(f, 'source_agent', 'unknown')}",
                    }
                    for f in facts
                ]
        except Exception:
            logger.exception("Error getting all hive facts")
        return []

    @staticmethod
    def _merge_results(
        local: list[dict[str, Any]],
        hive: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Merge local and hive results, deduplicating by fact content."""
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []

        # Local facts first (higher trust)
        for r in local:
            content = r.get("fact", "")
            if content and content not in seen:
                seen.add(content)
                merged.append(r)

        # Then hive facts
        for r in hive:
            content = r.get("fact", "")
            if content and content not in seen:
                seen.add(content)
                merged.append(r)

        return merged[:limit]

    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics."""
        stats = self.memory.get_statistics()
        if self._cognitive:
            stats["total_experiences"] = stats.get("total", 0)
        return stats

    def retrieve_by_entity(self, entity_name: str, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve all facts about a specific entity.

        Args:
            entity_name: Entity name (case-insensitive)
            limit: Maximum results

        Returns:
            List of fact dicts matching the entity
        """
        if self._cognitive and hasattr(self.memory, "retrieve_by_entity"):
            results = self.memory.retrieve_by_entity(entity_name=entity_name, limit=limit)
            return [self._semantic_fact_to_dict(r) for r in results]
        if hasattr(self.memory, "retrieve_by_entity"):
            nodes = self.memory.retrieve_by_entity(entity_name=entity_name, limit=limit)
            return [self._node_to_dict(n) for n in nodes]
        return []

    def search_by_concept(self, keywords: list[str], limit: int = 30) -> list[dict[str, Any]]:
        """Search for facts by concept/content keyword matching.

        Args:
            keywords: List of keyword strings to search for
            limit: Maximum nodes to return per keyword

        Returns:
            List of fact dicts matching any of the keywords
        """
        if self._cognitive and hasattr(self.memory, "search_by_concept"):
            results = self.memory.search_by_concept(keywords=keywords, limit=limit)
            return [self._semantic_fact_to_dict(r) for r in results]
        if hasattr(self.memory, "search_by_concept"):
            nodes = self.memory.search_by_concept(keywords=keywords, limit=limit)
            return [self._node_to_dict(n) for n in nodes]
        return []

    def execute_aggregation(self, query_type: str, entity_filter: str = "") -> dict[str, Any]:
        """Execute Cypher aggregation query for meta-memory questions.

        Args:
            query_type: Type of aggregation
            entity_filter: Optional filter string

        Returns:
            Dict with aggregation results
        """
        if hasattr(self.memory, "execute_aggregation"):
            return self.memory.execute_aggregation(
                query_type=query_type, entity_filter=entity_filter
            )
        return {"count": 0, "query_type": query_type, "error": "Not supported"}

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

    def flush_memory(self) -> None:
        """Flush underlying memory cache without losing data."""
        if hasattr(self.memory, "flush_memory"):
            self.memory.flush_memory()

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
