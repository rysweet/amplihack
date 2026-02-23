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
    ):
        self.agent_name = agent_name
        self.memory: Any = None  # CognitiveMemory or HierarchicalMemory

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

    def retrieve_temporal_chain(
        self, entity_name: str, field: str | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve temporal transition chain for an entity.

        Walks TRANSITIONED_TO edges to reconstruct the full history of changes.
        Handles both CognitiveMemory (node_id PK) and HierarchicalMemory (memory_id PK).

        Args:
            entity_name: Entity name (case-insensitive)
            field: Optional field name to filter transitions

        Returns:
            List of dicts with transition history, chronologically ordered.
        """
        if hasattr(self.memory, "retrieve_temporal_chain"):
            return self.memory.retrieve_temporal_chain(entity_name=entity_name, field=field)

        # Direct Cypher fallback for CognitiveMemory (which uses node_id, not memory_id)
        conn = self._get_connection()
        if conn is None:
            return []

        return self._raw_retrieve_temporal_chain(conn, entity_name, field)

    def _get_connection(self):
        """Get the underlying Kuzu connection from the memory backend."""
        # CognitiveMemory typically exposes .conn or .connection
        for attr in ("connection", "conn", "_conn", "_connection"):
            if hasattr(self.memory, attr):
                return getattr(self.memory, attr)
        # Try deeper access: memory.semantic_store.conn, etc.
        for store_attr in ("semantic_store", "_semantic_store"):
            store = getattr(self.memory, store_attr, None)
            if store is not None:
                for attr in ("conn", "connection", "_conn"):
                    if hasattr(store, attr):
                        return getattr(store, attr)
        return None

    def _raw_retrieve_temporal_chain(
        self, conn, entity_name: str, field: str | None = None
    ) -> list[dict[str, Any]]:
        """Raw Cypher-based temporal chain retrieval.

        Works directly against the Kuzu DB with the CognitiveMemory schema
        (uses node_id instead of memory_id).
        """
        import json as _json

        entity_lower = entity_name.strip().lower()
        if not entity_lower:
            return []

        chain: list[dict[str, Any]] = []

        try:
            field_filter = ""
            params: dict[str, Any] = {"agent_id": self.agent_name, "entity": entity_lower}
            if field:
                field_filter = " AND r.field CONTAINS $field"
                params["field"] = field.lower()

            result = conn.execute(
                f"""
                MATCH (old_node:SemanticMemory)-[r:TRANSITIONED_TO]->(new_node:SemanticMemory)
                WHERE old_node.agent_id = $agent_id
                  AND (LOWER(old_node.entity_name) CONTAINS $entity
                       OR LOWER(new_node.entity_name) CONTAINS $entity
                       OR LOWER(old_node.content) CONTAINS $entity
                       OR LOWER(new_node.content) CONTAINS $entity
                       OR LOWER(old_node.concept) CONTAINS $entity
                       OR LOWER(new_node.concept) CONTAINS $entity)
                  {field_filter}
                RETURN old_node.node_id, old_node.content, old_node.concept,
                       old_node.metadata,
                       new_node.node_id, new_node.content, new_node.concept,
                       new_node.metadata,
                       r.field, r.old_value, r.new_value, r.reason, r.turn_number
                ORDER BY r.turn_number ASC
                """,
                params,
            )

            seen_ids: set[str] = set()
            edges: list[dict[str, Any]] = []

            while result.has_next():
                row = result.get_next()
                old_meta = _json.loads(row[3]) if row[3] and isinstance(row[3], str) else {}
                new_meta = _json.loads(row[7]) if row[7] and isinstance(row[7], str) else {}

                edges.append(
                    {
                        "old_id": row[0],
                        "old_content": row[1],
                        "old_concept": row[2],
                        "old_turn": old_meta.get("temporal_index", 0),
                        "new_id": row[4],
                        "new_content": row[5],
                        "new_concept": row[6],
                        "new_turn": new_meta.get("temporal_index", 0),
                        "field": row[8] or "",
                        "old_value": row[9] or "",
                        "new_value": row[10] or "",
                        "reason": row[11] or "",
                        "turn_number": row[12] or 0,
                    }
                )

            if not edges:
                return []

            new_ids = {e["new_id"] for e in edges}
            root_ids = {e["old_id"] for e in edges} - new_ids

            for edge in edges:
                if edge["old_id"] in root_ids and edge["old_id"] not in seen_ids:
                    seen_ids.add(edge["old_id"])
                    chain.append(
                        {
                            "memory_id": edge["old_id"],
                            "content": edge["old_content"],
                            "concept": edge["old_concept"],
                            "turn_number": edge["old_turn"],
                            "field": edge["field"],
                            "old_value": "",
                            "new_value": "",
                            "reason": "original value",
                            "is_current": False,
                        }
                    )

            for edge in edges:
                if edge["new_id"] not in seen_ids:
                    seen_ids.add(edge["new_id"])
                    chain.append(
                        {
                            "memory_id": edge["new_id"],
                            "content": edge["new_content"],
                            "concept": edge["new_concept"],
                            "turn_number": edge["turn_number"],
                            "field": edge["field"],
                            "old_value": edge["old_value"],
                            "new_value": edge["new_value"],
                            "reason": edge["reason"],
                            "is_current": False,
                        }
                    )

            if chain:
                chain[-1]["is_current"] = True

        except Exception as e:
            logger.debug("_raw_retrieve_temporal_chain failed for '%s': %s", entity_name, e)

        return chain

    def create_transition_edge(
        self,
        old_node_id: str,
        new_node_id: str,
        field: str,
        old_value: str,
        new_value: str,
        reason: str = "",
        turn_number: int = 0,
    ) -> bool:
        """Create a TRANSITIONED_TO edge between two facts.

        Args:
            old_node_id: node_id of the old-value fact
            new_node_id: node_id of the new-value fact
            field: What changed
            old_value: Previous value
            new_value: New value
            reason: Why the change happened
            turn_number: Turn number of the transition

        Returns:
            True if edge created successfully
        """
        if hasattr(self.memory, "create_transition_edge"):
            return self.memory.create_transition_edge(
                old_node_id=old_node_id,
                new_node_id=new_node_id,
                field=field,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
                turn_number=turn_number,
            )

        # Direct Cypher fallback for CognitiveMemory
        conn = self._get_connection()
        if conn is None:
            return False

        try:
            conn.execute(
                """
                MATCH (old_m:SemanticMemory {node_id: $old_id})
                MATCH (new_m:SemanticMemory {node_id: $new_id})
                CREATE (old_m)-[:TRANSITIONED_TO {
                    field: $field,
                    old_value: $old_value,
                    new_value: $new_value,
                    reason: $reason,
                    turn_number: $turn_number
                }]->(new_m)
                """,
                {
                    "old_id": old_node_id,
                    "new_id": new_node_id,
                    "field": field,
                    "old_value": old_value,
                    "new_value": new_value,
                    "reason": reason,
                    "turn_number": turn_number,
                },
            )
            return True
        except Exception as e:
            logger.debug("Failed to create TRANSITIONED_TO edge: %s", e)
            return False

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
