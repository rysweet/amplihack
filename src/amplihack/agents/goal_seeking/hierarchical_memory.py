"""Hierarchical memory system using Kuzu graph database directly.

Philosophy:
- Uses Kuzu directly (not amplihack-memory-lib) for full graph control
- Five memory categories matching cognitive science model
- Auto-classification of incoming knowledge
- Similarity edges computed on store for Graph RAG traversal
- Synchronous API for simplicity

Public API:
    MemoryCategory: Enum of memory types
    KnowledgeNode: Dataclass for graph nodes
    KnowledgeEdge: Dataclass for graph edges
    KnowledgeSubgraph: Dataclass for subgraph results with to_llm_context()
    MemoryClassifier: Rule-based category classifier
    HierarchicalMemory: Main memory class with store/retrieve/subgraph
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import kuzu

from .similarity import compute_similarity

logger = logging.getLogger(__name__)


class MemoryCategory(str, Enum):
    """Categories of memory matching cognitive science model."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROSPECTIVE = "prospective"
    WORKING = "working"


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph.

    Attributes:
        node_id: Unique identifier (UUID)
        category: Memory category
        content: Main text content
        concept: Topic/concept label
        confidence: Confidence score 0.0-1.0
        source_id: ID of source episode (provenance)
        created_at: Creation timestamp
        tags: List of tags
        metadata: Additional metadata
    """

    node_id: str
    category: MemoryCategory
    content: str
    concept: str
    confidence: float = 0.8
    source_id: str = ""
    created_at: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeEdge:
    """An edge in the knowledge graph.

    Attributes:
        source_id: Source node ID
        target_id: Target node ID
        relationship: Edge type (SIMILAR_TO, DERIVES_FROM)
        weight: Edge weight/score
        metadata: Additional metadata
    """

    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeSubgraph:
    """A subgraph of knowledge nodes and edges.

    Returned by retrieve_subgraph() for Graph RAG context.

    Attributes:
        nodes: List of knowledge nodes
        edges: List of knowledge edges
        query: Original query that produced this subgraph
    """

    nodes: list[KnowledgeNode] = field(default_factory=list)
    edges: list[KnowledgeEdge] = field(default_factory=list)
    query: str = ""

    def to_llm_context(self, chronological: bool = False) -> str:
        """Format subgraph as LLM-readable context string.

        Args:
            chronological: If True, sort facts by temporal_index (creation time)
                instead of confidence. Useful for temporal reasoning questions.

        Returns:
            Formatted string with numbered facts, source provenance, and relationships.
        """
        if not self.nodes:
            return "No relevant knowledge found."

        lines = [f"Knowledge graph context for: {self.query}\n"]

        if chronological:
            def temporal_key(n: KnowledgeNode) -> tuple:
                t_idx = n.metadata.get("temporal_index", 999999) if n.metadata else 999999
                return (t_idx, n.created_at or "")

            sorted_nodes = sorted(self.nodes, key=temporal_key)
            lines.append("Facts (in chronological order):")
            for i, node in enumerate(sorted_nodes, 1):
                time_marker = ""
                source_marker = ""
                if node.metadata:
                    src_date = node.metadata.get("source_date", "")
                    t_order = node.metadata.get("temporal_order", "")
                    src_label = node.metadata.get("source_label", "")
                    if src_date:
                        time_marker = f" [Date: {src_date}]"
                    elif t_order:
                        time_marker = f" [Time: {t_order}]"
                    if src_label:
                        source_marker = f" [Source: {src_label}]"
                lines.append(
                    f"  {i}. [{node.concept}]{time_marker}{source_marker} {node.content} "
                    f"(confidence: {node.confidence:.1f})"
                )
        else:
            sorted_nodes = sorted(self.nodes, key=lambda n: n.confidence, reverse=True)
            lines.append("Facts:")
            for i, node in enumerate(sorted_nodes, 1):
                source_marker = ""
                if node.metadata:
                    src_label = node.metadata.get("source_label", "")
                    if src_label:
                        source_marker = f" [Source: {src_label}]"
                lines.append(
                    f"  {i}. [{node.concept}]{source_marker} {node.content} "
                    f"(confidence: {node.confidence:.1f})"
                )

        contradiction_edges = [
            e for e in self.edges if e.metadata and e.metadata.get("contradiction")
        ]
        if contradiction_edges:
            lines.append("\nContradictions detected:")
            for edge in contradiction_edges:
                conflict = edge.metadata.get("conflicting_values", "unknown")
                lines.append(f"  - WARNING: Conflicting information found: {conflict}")

        if self.edges:
            lines.append("\nRelationships:")
            for edge in self.edges:
                lines.append(
                    f"  - {edge.source_id[:8]}.. {edge.relationship} "
                    f"{edge.target_id[:8]}.. (weight: {edge.weight:.2f})"
                )

        return "\n".join(lines)


class MemoryClassifier:
    """Rule-based classifier for memory categories.

    Uses keyword patterns to classify content into memory categories.
    """

    _PROCEDURAL_KEYWORDS = frozenset(
        {"step", "steps", "how to", "procedure", "process", "method", "recipe", "instructions"}
    )
    _PROSPECTIVE_KEYWORDS = frozenset(
        {"plan", "goal", "future", "will", "should", "todo", "intend", "schedule"}
    )
    _EPISODIC_KEYWORDS = frozenset(
        {"happened", "event", "occurred", "experience", "observed", "saw", "noticed"}
    )

    def classify(self, content: str, concept: str = "") -> MemoryCategory:
        """Classify content into a memory category.

        Args:
            content: The text content to classify
            concept: Optional concept label for additional context

        Returns:
            MemoryCategory enum value
        """
        text = f"{content} {concept}".lower()

        if any(kw in text for kw in self._PROCEDURAL_KEYWORDS):
            return MemoryCategory.PROCEDURAL

        if any(kw in text for kw in self._PROSPECTIVE_KEYWORDS):
            return MemoryCategory.PROSPECTIVE

        if any(kw in text for kw in self._EPISODIC_KEYWORDS):
            return MemoryCategory.EPISODIC

        return MemoryCategory.SEMANTIC


def _make_id() -> str:
    """Generate a UUID string for node IDs."""
    return str(uuid.uuid4())


class HierarchicalMemory:
    """Hierarchical memory system backed by Kuzu graph database.

    Creates and manages a knowledge graph with:
    - SemanticMemory nodes for factual knowledge
    - EpisodicMemory nodes for raw episodes/sources
    - SIMILAR_TO edges computed via text similarity
    - DERIVES_FROM edges linking facts to source episodes

    Args:
        agent_name: Name of the owning agent
        db_path: Path to Kuzu database directory

    Example:
        >>> mem = HierarchicalMemory("test_agent", "/tmp/test_mem")
        >>> nid = mem.store_knowledge("Plants use photosynthesis", "biology")
        >>> sub = mem.retrieve_subgraph("photosynthesis")
        >>> print(sub.to_llm_context())
    """

    def __init__(self, agent_name: str, db_path: str | Path | None = None):
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name cannot be empty")

        cleaned = agent_name.strip()
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_\-]{0,63}$", cleaned):
            raise ValueError(
                f"agent_name must be alphanumeric with hyphens/underscores, "
                f"1-64 chars, got: {cleaned!r}"
            )
        self.agent_name = cleaned

        if db_path is None:
            db_path = Path.home() / ".amplihack" / "hierarchical_memory" / self.agent_name
        elif isinstance(db_path, str):
            db_path = Path(db_path)

        self.db_path = (
            db_path / "kuzu_db" if db_path.is_dir() and not (db_path / "lock").exists() else db_path
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.database = kuzu.Database(str(self.db_path))
        self.connection = kuzu.Connection(self.database)
        self._classifier = MemoryClassifier()
        self._init_schema()

    def _init_schema(self) -> None:
        """Create Kuzu node and relationship tables if they don't exist."""
        try:
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS SemanticMemory(
                    memory_id STRING,
                    concept STRING,
                    content STRING,
                    confidence DOUBLE,
                    source_id STRING,
                    agent_id STRING,
                    tags STRING,
                    metadata STRING,
                    created_at STRING,
                    PRIMARY KEY (memory_id)
                )
            """)

            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS EpisodicMemory(
                    memory_id STRING,
                    content STRING,
                    source_label STRING,
                    agent_id STRING,
                    tags STRING,
                    metadata STRING,
                    created_at STRING,
                    PRIMARY KEY (memory_id)
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS SIMILAR_TO(
                    FROM SemanticMemory TO SemanticMemory,
                    weight DOUBLE,
                    metadata STRING
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS DERIVES_FROM(
                    FROM SemanticMemory TO EpisodicMemory,
                    extraction_method STRING,
                    confidence DOUBLE
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS SUPERSEDES(
                    FROM SemanticMemory TO SemanticMemory,
                    reason STRING,
                    temporal_delta STRING
                )
            """)

            logger.debug("HierarchicalMemory schema initialized for agent %s", self.agent_name)

        except Exception as e:
            logger.error("Failed to initialize HierarchicalMemory schema: %s", e)
            raise

    def store_knowledge(
        self,
        content: str,
        concept: str = "",
        confidence: float = 0.8,
        category: MemoryCategory | None = None,
        source_id: str = "",
        tags: list[str] | None = None,
        temporal_metadata: dict | None = None,
    ) -> str:
        """Store a knowledge node in the graph."""
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        if category is None:
            category = self._classifier.classify(content, concept)

        node_id = _make_id()
        tags = tags or []
        now = datetime.utcnow().isoformat()

        meta = {"category": category.value}
        if temporal_metadata:
            meta.update(temporal_metadata)

        self.connection.execute(
            """
            CREATE (m:SemanticMemory {
                memory_id: $memory_id,
                concept: $concept,
                content: $content,
                confidence: $confidence,
                source_id: $source_id,
                agent_id: $agent_id,
                tags: $tags,
                metadata: $metadata,
                created_at: $created_at
            })
            """,
            {
                "memory_id": node_id,
                "concept": concept,
                "content": content.strip(),
                "confidence": confidence,
                "source_id": source_id,
                "agent_id": self.agent_name,
                "tags": json.dumps(tags),
                "metadata": json.dumps(meta),
                "created_at": now,
            },
        )

        if source_id:
            self._create_derives_from_edge(node_id, source_id)

        if temporal_metadata and temporal_metadata.get("temporal_index", 0) > 0:
            self._detect_supersedes(node_id, content, concept, temporal_metadata)

        self._create_similarity_edges(node_id, content, concept, tags)

        return node_id

    def store_episode(self, content: str, source_label: str = "") -> str:
        """Store an episodic memory node (raw source content)."""
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        episode_id = _make_id()
        now = datetime.utcnow().isoformat()

        self.connection.execute(
            """
            CREATE (e:EpisodicMemory {
                memory_id: $memory_id,
                content: $content,
                source_label: $source_label,
                agent_id: $agent_id,
                tags: $tags,
                metadata: $metadata,
                created_at: $created_at
            })
            """,
            {
                "memory_id": episode_id,
                "content": content.strip(),
                "source_label": source_label,
                "agent_id": self.agent_name,
                "tags": json.dumps([]),
                "metadata": json.dumps({}),
                "created_at": now,
            },
        )

        return episode_id

    def _create_derives_from_edge(self, semantic_id: str, episode_id: str) -> None:
        """Create a DERIVES_FROM edge from SemanticMemory to EpisodicMemory."""
        try:
            result = self.connection.execute(
                "MATCH (e:EpisodicMemory {memory_id: $eid}) RETURN COUNT(e) AS cnt",
                {"eid": episode_id},
            )
            if result.has_next() and result.get_next()[0] > 0:
                self.connection.execute(
                    """
                    MATCH (s:SemanticMemory {memory_id: $sid})
                    MATCH (e:EpisodicMemory {memory_id: $eid})
                    CREATE (s)-[:DERIVES_FROM {
                        extraction_method: $method,
                        confidence: $confidence
                    }]->(e)
                    """,
                    {
                        "sid": semantic_id,
                        "eid": episode_id,
                        "method": "llm_extraction",
                        "confidence": 1.0,
                    },
                )
        except Exception as e:
            logger.debug("Failed to create DERIVES_FROM edge: %s", e)

    def _detect_supersedes(
        self,
        new_node_id: str,
        content: str,
        concept: str,
        temporal_metadata: dict,
    ) -> None:
        """Detect if this new fact supersedes an existing fact about the same entity."""
        new_temporal_idx = temporal_metadata.get("temporal_index", 0)
        if new_temporal_idx <= 0:
            return

        try:
            result = self.connection.execute(
                """
                MATCH (m:SemanticMemory)
                WHERE m.agent_id = $agent_id
                  AND m.memory_id <> $new_id
                  AND (LOWER(m.concept) CONTAINS LOWER($concept_key)
                       OR LOWER($concept_key) CONTAINS LOWER(m.concept))
                RETURN m.memory_id, m.content, m.concept, m.metadata
                LIMIT 20
                """,
                {
                    "agent_id": self.agent_name,
                    "new_id": new_node_id,
                    "concept_key": concept.split()[0] if concept else "",
                },
            )

            while result.has_next():
                row = result.get_next()
                old_id = row[0]
                old_content = row[1]
                old_metadata_str = row[3]

                old_meta = json.loads(old_metadata_str) if old_metadata_str else {}
                old_temporal_idx = old_meta.get("temporal_index", 0)

                if old_temporal_idx <= 0 or old_temporal_idx >= new_temporal_idx:
                    continue

                contradiction = self._detect_contradiction(content, old_content, concept, row[2])
                if contradiction.get("contradiction"):
                    temporal_delta = f"index {old_temporal_idx} → {new_temporal_idx}"
                    self.connection.execute(
                        """
                        MATCH (new_m:SemanticMemory {memory_id: $new_id})
                        MATCH (old_m:SemanticMemory {memory_id: $old_id})
                        CREATE (new_m)-[:SUPERSEDES {
                            reason: $reason,
                            temporal_delta: $delta
                        }]->(old_m)
                        """,
                        {
                            "new_id": new_node_id,
                            "old_id": old_id,
                            "reason": f"Updated values: {contradiction.get('conflicting_values', '')}",
                            "delta": temporal_delta,
                        },
                    )
                    logger.debug(
                        "Created SUPERSEDES edge: %s → %s (%s)",
                        new_node_id[:8],
                        old_id[:8],
                        temporal_delta,
                    )

        except Exception as e:
            logger.debug("Failed to detect supersedes: %s", e)

    @staticmethod
    def _detect_contradiction(
        content_a: str, content_b: str, concept_a: str, concept_b: str
    ) -> dict:
        """Detect if two facts about the same concept contain contradictory numbers."""
        concept_words_a = set(concept_a.lower().split()) if concept_a else set()
        concept_words_b = set(concept_b.lower().split()) if concept_b else set()

        if not concept_words_a or not concept_words_b:
            return {}

        common = concept_words_a & concept_words_b
        common = {w for w in common if len(w) > 2}
        if not common:
            return {}

        nums_a = re.findall(r"\b\d+(?:\.\d+)?\b", content_a)
        nums_b = re.findall(r"\b\d+(?:\.\d+)?\b", content_b)

        if not nums_a or not nums_b:
            return {}

        nums_a_set = set(nums_a)
        nums_b_set = set(nums_b)

        unique_to_a = nums_a_set - nums_b_set
        unique_to_b = nums_b_set - nums_a_set

        if unique_to_a and unique_to_b:
            return {
                "contradiction": True,
                "conflicting_values": f"{', '.join(sorted(unique_to_a))} vs {', '.join(sorted(unique_to_b))}",
            }

        return {}

    def _create_similarity_edges(
        self,
        node_id: str,
        content: str,
        concept: str,
        tags: list[str],
    ) -> None:
        """Compute similarity against recent nodes and create SIMILAR_TO edges."""
        try:
            result = self.connection.execute(
                """
                MATCH (m:SemanticMemory)
                WHERE m.memory_id <> $node_id AND m.agent_id = $agent_id
                RETURN m.memory_id, m.content, m.concept, m.tags
                ORDER BY m.created_at DESC
                LIMIT 100
                """,
                {"node_id": node_id, "agent_id": self.agent_name},
            )

            new_node = {"content": content, "concept": concept, "tags": tags}

            while result.has_next():
                row = result.get_next()
                other_id = row[0]
                other_content = row[1]
                other_concept = row[2]
                other_tags_str = row[3]

                other_tags = json.loads(other_tags_str) if other_tags_str else []
                other_node = {
                    "content": other_content,
                    "concept": other_concept,
                    "tags": other_tags,
                }

                score = compute_similarity(new_node, other_node)

                if score > 0.3:
                    edge_meta = {}
                    if score > 0.5:
                        contradiction = self._detect_contradiction(
                            content, other_content, concept, other_concept
                        )
                        if contradiction:
                            edge_meta = contradiction

                    self.connection.execute(
                        """
                        MATCH (a:SemanticMemory {memory_id: $aid})
                        MATCH (b:SemanticMemory {memory_id: $bid})
                        CREATE (a)-[:SIMILAR_TO {weight: $weight, metadata: $metadata}]->(b)
                        """,
                        {
                            "aid": node_id,
                            "bid": other_id,
                            "weight": score,
                            "metadata": json.dumps(edge_meta) if edge_meta else "",
                        },
                    )

        except Exception as e:
            logger.debug("Failed to create similarity edges: %s", e)

    def retrieve_subgraph(
        self,
        query: str,
        max_depth: int = 2,
        max_nodes: int = 20,
    ) -> KnowledgeSubgraph:
        """Retrieve a knowledge subgraph relevant to a query."""
        if not query or not query.strip():
            return KnowledgeSubgraph(query=query)

        subgraph = KnowledgeSubgraph(query=query)
        seen_ids: set[str] = set()

        keywords = query.lower().split()
        seed_nodes: list[KnowledgeNode] = []

        for keyword in keywords:
            if len(keyword) <= 2:
                continue
            try:
                result = self.connection.execute(
                    """
                    MATCH (m:SemanticMemory)
                    WHERE m.agent_id = $agent_id
                      AND (LOWER(m.content) CONTAINS $keyword
                           OR LOWER(m.concept) CONTAINS $keyword)
                    RETURN m.memory_id, m.concept, m.content, m.confidence,
                           m.source_id, m.tags, m.metadata, m.created_at
                    LIMIT $limit
                    """,
                    {
                        "agent_id": self.agent_name,
                        "keyword": keyword,
                        "limit": max_nodes,
                    },
                )

                while result.has_next():
                    row = result.get_next()
                    nid = row[0]
                    if nid not in seen_ids:
                        seen_ids.add(nid)
                        tags = json.loads(row[5]) if row[5] else []
                        metadata = json.loads(row[6]) if row[6] else {}
                        node = KnowledgeNode(
                            node_id=nid,
                            category=MemoryCategory.SEMANTIC,
                            content=row[2],
                            concept=row[1],
                            confidence=row[3],
                            source_id=row[4] or "",
                            created_at=row[7] or "",
                            tags=tags,
                            metadata=metadata,
                        )
                        seed_nodes.append(node)
            except Exception as e:
                logger.debug("Keyword search failed for '%s': %s", keyword, e)

        expanded_nodes: list[KnowledgeNode] = []
        edges: list[KnowledgeEdge] = []

        for seed in seed_nodes:
            if len(seen_ids) >= max_nodes:
                break
            try:
                hop_query = """
                    MATCH (a:SemanticMemory {memory_id: $sid})-[r:SIMILAR_TO]->(b:SemanticMemory)
                    WHERE b.agent_id = $agent_id
                    RETURN b.memory_id, b.concept, b.content, b.confidence,
                           b.source_id, b.tags, b.created_at, r.weight, b.metadata,
                           r.metadata
                """
                if max_depth >= 2:
                    hop_query += """
                    UNION ALL
                    MATCH (a:SemanticMemory {memory_id: $sid})-[:SIMILAR_TO]->()-[r2:SIMILAR_TO]->(c:SemanticMemory)
                    WHERE c.agent_id = $agent_id AND c.memory_id <> $sid
                    RETURN c.memory_id, c.concept, c.content, c.confidence,
                           c.source_id, c.tags, c.created_at, r2.weight, c.metadata,
                           r2.metadata
                    """

                result = self.connection.execute(
                    hop_query,
                    {"sid": seed.node_id, "agent_id": self.agent_name},
                )

                while result.has_next():
                    row = result.get_next()
                    nid = row[0]
                    weight = row[7]

                    if nid not in seen_ids and len(seen_ids) < max_nodes:
                        seen_ids.add(nid)
                        tags = json.loads(row[5]) if row[5] else []
                        metadata = json.loads(row[8]) if len(row) > 8 and row[8] else {}
                        node = KnowledgeNode(
                            node_id=nid,
                            category=MemoryCategory.SEMANTIC,
                            content=row[2],
                            concept=row[1],
                            confidence=row[3],
                            source_id=row[4] or "",
                            created_at=row[6] or "",
                            tags=tags,
                            metadata=metadata,
                        )
                        expanded_nodes.append(node)

                    edge_meta = {}
                    if len(row) > 9 and row[9]:
                        try:
                            edge_meta = json.loads(row[9])
                        except (json.JSONDecodeError, TypeError):
                            pass

                    edges.append(
                        KnowledgeEdge(
                            source_id=seed.node_id,
                            target_id=nid,
                            relationship="SIMILAR_TO",
                            weight=weight,
                            metadata=edge_meta,
                        )
                    )

            except Exception as e:
                logger.debug("Similarity expansion failed for %s: %s", seed.node_id, e)

        all_nodes = seed_nodes + expanded_nodes

        def rank_score(node: KnowledgeNode) -> float:
            content_lower = node.content.lower()
            keyword_hits = sum(1 for kw in keywords if len(kw) > 2 and kw in content_lower)
            keyword_relevance = keyword_hits / max(len(keywords), 1)
            return node.confidence * (0.5 + 0.5 * keyword_relevance)

        all_nodes.sort(key=rank_score, reverse=True)
        all_nodes = all_nodes[:max_nodes]

        self._attach_provenance(all_nodes)
        self._mark_superseded(all_nodes)

        subgraph.nodes = all_nodes
        subgraph.edges = edges

        return subgraph

    def _attach_provenance(self, nodes: list[KnowledgeNode]) -> None:
        """Follow DERIVES_FROM edges to attach source labels to node metadata."""
        source_ids = list({n.source_id for n in nodes if n.source_id})
        if not source_ids:
            return

        try:
            label_map: dict[str, str] = {}
            for sid in source_ids:
                result = self.connection.execute(
                    "MATCH (e:EpisodicMemory {memory_id: $eid}) RETURN e.memory_id, e.source_label",
                    {"eid": sid},
                )
                if result.has_next():
                    row = result.get_next()
                    if row[1]:
                        label_map[row[0]] = row[1]

            for node in nodes:
                if node.source_id in label_map:
                    if node.metadata is None:
                        node.metadata = {}
                    node.metadata["source_label"] = label_map[node.source_id]
        except Exception as e:
            logger.debug("Failed to attach provenance: %s", e)

    def _mark_superseded(self, nodes: list[KnowledgeNode]) -> None:
        """Mark facts that have been superseded by newer facts."""
        if not nodes:
            return

        for node in nodes:
            try:
                result = self.connection.execute(
                    """
                    MATCH (newer:SemanticMemory)-[r:SUPERSEDES]->(old:SemanticMemory {memory_id: $nid})
                    RETURN newer.memory_id, r.reason, r.temporal_delta
                    LIMIT 1
                    """,
                    {"nid": node.node_id},
                )
                if result.has_next():
                    row = result.get_next()
                    if node.metadata is None:
                        node.metadata = {}
                    node.metadata["superseded"] = True
                    node.metadata["superseded_by"] = row[0]
                    node.metadata["supersede_reason"] = row[1] or ""
                    node.confidence = max(0.1, node.confidence * 0.5)
            except Exception:
                pass

    def get_all_knowledge(self, limit: int = 50) -> list[KnowledgeNode]:
        """Retrieve all semantic knowledge nodes."""
        nodes: list[KnowledgeNode] = []

        try:
            result = self.connection.execute(
                """
                MATCH (m:SemanticMemory)
                WHERE m.agent_id = $agent_id
                RETURN m.memory_id, m.concept, m.content, m.confidence,
                       m.source_id, m.tags, m.metadata, m.created_at
                ORDER BY m.created_at DESC
                LIMIT $limit
                """,
                {"agent_id": self.agent_name, "limit": limit},
            )

            while result.has_next():
                row = result.get_next()
                tags = json.loads(row[5]) if row[5] else []
                metadata = json.loads(row[6]) if row[6] else {}
                category_str = metadata.get("category", "semantic")
                try:
                    category = MemoryCategory(category_str)
                except ValueError:
                    category = MemoryCategory.SEMANTIC

                nodes.append(
                    KnowledgeNode(
                        node_id=row[0],
                        category=category,
                        content=row[2],
                        concept=row[1],
                        confidence=row[3],
                        source_id=row[4] or "",
                        created_at=row[7] or "",
                        tags=tags,
                        metadata=metadata,
                    )
                )

        except Exception as e:
            logger.error("Failed to get all knowledge: %s", e)

        return nodes

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the hierarchical memory."""
        stats: dict[str, Any] = {"agent_name": self.agent_name}

        try:
            result = self.connection.execute(
                "MATCH (m:SemanticMemory) WHERE m.agent_id = $aid RETURN COUNT(m)",
                {"aid": self.agent_name},
            )
            if result.has_next():
                stats["semantic_nodes"] = result.get_next()[0]

            result = self.connection.execute(
                "MATCH (e:EpisodicMemory) WHERE e.agent_id = $aid RETURN COUNT(e)",
                {"aid": self.agent_name},
            )
            if result.has_next():
                stats["episodic_nodes"] = result.get_next()[0]

            stats["total_experiences"] = stats.get("semantic_nodes", 0) + stats.get(
                "episodic_nodes", 0
            )

            try:
                result = self.connection.execute(
                    """
                    MATCH (a:SemanticMemory)-[r:SIMILAR_TO]->(b:SemanticMemory)
                    WHERE a.agent_id = $aid
                    RETURN COUNT(r)
                    """,
                    {"aid": self.agent_name},
                )
                if result.has_next():
                    stats["similar_to_edges"] = result.get_next()[0]
            except Exception:
                stats["similar_to_edges"] = 0

            try:
                result = self.connection.execute(
                    """
                    MATCH (s:SemanticMemory)-[r:DERIVES_FROM]->(e:EpisodicMemory)
                    WHERE s.agent_id = $aid
                    RETURN COUNT(r)
                    """,
                    {"aid": self.agent_name},
                )
                if result.has_next():
                    stats["derives_from_edges"] = result.get_next()[0]
            except Exception:
                stats["derives_from_edges"] = 0

        except Exception as e:
            logger.error("Failed to get statistics: %s", e)

        return stats

    def close(self) -> None:
        """Close database connection and release resources."""
        try:
            if hasattr(self, "connection"):
                del self.connection
            if hasattr(self, "database"):
                del self.database
        except Exception as e:
            logger.debug("Error closing HierarchicalMemory: %s", e)


__all__ = [
    "MemoryCategory",
    "KnowledgeNode",
    "KnowledgeEdge",
    "KnowledgeSubgraph",
    "MemoryClassifier",
    "HierarchicalMemory",
]
