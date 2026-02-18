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

    def to_llm_context(self) -> str:
        """Format subgraph as LLM-readable context string.

        Returns:
            Formatted string with numbered facts and relationships.
        """
        if not self.nodes:
            return "No relevant knowledge found."

        lines = [f"Knowledge graph context for: {self.query}\n"]

        # Sort nodes by confidence descending
        sorted_nodes = sorted(self.nodes, key=lambda n: n.confidence, reverse=True)

        lines.append("Facts:")
        for i, node in enumerate(sorted_nodes, 1):
            lines.append(
                f"  {i}. [{node.concept}] {node.content} (confidence: {node.confidence:.1f})"
            )

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

        # Check procedural first (most specific)
        if any(kw in text for kw in self._PROCEDURAL_KEYWORDS):
            return MemoryCategory.PROCEDURAL

        # Check prospective
        if any(kw in text for kw in self._PROSPECTIVE_KEYWORDS):
            return MemoryCategory.PROSPECTIVE

        # Check episodic
        if any(kw in text for kw in self._EPISODIC_KEYWORDS):
            return MemoryCategory.EPISODIC

        # Default: semantic knowledge
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

        self.agent_name = agent_name.strip()

        if db_path is None:
            db_path = Path.home() / ".amplihack" / "hierarchical_memory" / self.agent_name
        elif isinstance(db_path, str):
            db_path = Path(db_path)

        # Kuzu needs a path to its database directory (it creates it)
        # If the path already exists as a regular directory without Kuzu files, append /kuzu_db
        self.db_path = db_path / "kuzu_db" if db_path.is_dir() and not (db_path / "lock").exists() else db_path
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
                    weight DOUBLE
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS DERIVES_FROM(
                    FROM SemanticMemory TO EpisodicMemory,
                    extraction_method STRING,
                    confidence DOUBLE
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
    ) -> str:
        """Store a knowledge node in the graph.

        Auto-classifies if category not given. Computes similarity against
        recent nodes and creates SIMILAR_TO edges for scores > 0.3.

        If source_id is provided and refers to an EpisodicMemory node,
        a DERIVES_FROM edge is created.

        Args:
            content: The knowledge content
            concept: Topic/concept label
            confidence: Confidence score 0.0-1.0
            category: Optional memory category (auto-classified if None)
            source_id: Optional source episode ID for provenance
            tags: Optional list of tags

        Returns:
            node_id of the stored knowledge node
        """
        if not content or not content.strip():
            raise ValueError("content cannot be empty")

        if category is None:
            category = self._classifier.classify(content, concept)

        node_id = _make_id()
        tags = tags or []
        now = datetime.utcnow().isoformat()

        # Store as SemanticMemory (primary knowledge store for Graph RAG)
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
                "metadata": json.dumps({"category": category.value}),
                "created_at": now,
            },
        )

        # Create DERIVES_FROM edge if source_id points to an episode
        if source_id:
            self._create_derives_from_edge(node_id, source_id)

        # Compute similarity edges against recent nodes
        self._create_similarity_edges(node_id, content, concept, tags)

        return node_id

    def store_episode(self, content: str, source_label: str = "") -> str:
        """Store an episodic memory node (raw source content).

        Args:
            content: The episode content
            source_label: Label for the source (e.g., "Wikipedia: Photosynthesis")

        Returns:
            episode_id of the stored node
        """
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
            # Verify episode exists
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

    def _create_similarity_edges(
        self,
        node_id: str,
        content: str,
        concept: str,
        tags: list[str],
    ) -> None:
        """Compute similarity against recent nodes and create SIMILAR_TO edges.

        Checks the last 100 SemanticMemory nodes. Creates edges for
        similarity scores > 0.3.
        """
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
                    self.connection.execute(
                        """
                        MATCH (a:SemanticMemory {memory_id: $aid})
                        MATCH (b:SemanticMemory {memory_id: $bid})
                        CREATE (a)-[:SIMILAR_TO {weight: $weight}]->(b)
                        """,
                        {"aid": node_id, "bid": other_id, "weight": score},
                    )

        except Exception as e:
            logger.debug("Failed to create similarity edges: %s", e)

    def retrieve_subgraph(
        self,
        query: str,
        max_depth: int = 2,
        max_nodes: int = 20,
    ) -> KnowledgeSubgraph:
        """Retrieve a knowledge subgraph relevant to a query.

        Algorithm:
        1. Keyword search for seed nodes (CONTAINS on content/concept)
        2. Expand via SIMILAR_TO edges (1-2 hops)
        3. Rank by confidence * keyword_relevance
        4. Return subgraph with nodes and edges

        Args:
            query: Search query
            max_depth: Maximum traversal depth (default 2)
            max_nodes: Maximum nodes to return (default 20)

        Returns:
            KnowledgeSubgraph with nodes, edges, and to_llm_context()
        """
        if not query or not query.strip():
            return KnowledgeSubgraph(query=query)

        subgraph = KnowledgeSubgraph(query=query)
        seen_ids: set[str] = set()

        # Step 1: Find seed nodes via keyword search
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
                        node = KnowledgeNode(
                            node_id=nid,
                            category=MemoryCategory.SEMANTIC,
                            content=row[2],
                            concept=row[1],
                            confidence=row[3],
                            source_id=row[4] or "",
                            created_at=row[7] or "",
                            tags=tags,
                        )
                        seed_nodes.append(node)
            except Exception as e:
                logger.debug("Keyword search failed for '%s': %s", keyword, e)

        # Step 2: Expand via SIMILAR_TO edges
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
                           b.source_id, b.tags, b.created_at, r.weight
                """
                if max_depth >= 2:
                    # Also get 2-hop neighbors
                    hop_query += """
                    UNION ALL
                    MATCH (a:SemanticMemory {memory_id: $sid})-[:SIMILAR_TO]->()-[r2:SIMILAR_TO]->(c:SemanticMemory)
                    WHERE c.agent_id = $agent_id AND c.memory_id <> $sid
                    RETURN c.memory_id, c.concept, c.content, c.confidence,
                           c.source_id, c.tags, c.created_at, r2.weight
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
                        node = KnowledgeNode(
                            node_id=nid,
                            category=MemoryCategory.SEMANTIC,
                            content=row[2],
                            concept=row[1],
                            confidence=row[3],
                            source_id=row[4] or "",
                            created_at=row[6] or "",
                            tags=tags,
                        )
                        expanded_nodes.append(node)

                    edges.append(
                        KnowledgeEdge(
                            source_id=seed.node_id,
                            target_id=nid,
                            relationship="SIMILAR_TO",
                            weight=weight,
                        )
                    )

            except Exception as e:
                logger.debug("Similarity expansion failed for %s: %s", seed.node_id, e)

        # Step 3: Combine and rank by confidence * keyword relevance
        all_nodes = seed_nodes + expanded_nodes

        def rank_score(node: KnowledgeNode) -> float:
            # keyword_relevance: how many query keywords appear in content
            content_lower = node.content.lower()
            keyword_hits = sum(1 for kw in keywords if len(kw) > 2 and kw in content_lower)
            keyword_relevance = keyword_hits / max(len(keywords), 1)
            return node.confidence * (0.5 + 0.5 * keyword_relevance)

        all_nodes.sort(key=rank_score, reverse=True)
        all_nodes = all_nodes[:max_nodes]

        subgraph.nodes = all_nodes
        subgraph.edges = edges

        return subgraph

    def get_all_knowledge(self, limit: int = 50) -> list[KnowledgeNode]:
        """Retrieve all semantic knowledge nodes.

        Args:
            limit: Maximum nodes to return

        Returns:
            List of KnowledgeNode sorted by creation time descending
        """
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
        """Get statistics about the hierarchical memory.

        Returns:
            Dictionary with counts of nodes and edges
        """
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

            # Count edges
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
