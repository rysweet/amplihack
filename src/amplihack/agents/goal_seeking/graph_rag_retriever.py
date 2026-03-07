"""Graph RAG retriever wrapping Kuzu queries for knowledge graph traversal.

Philosophy:
- Single responsibility: Graph-based retrieval from Kuzu
- Keyword search, similarity expansion, provenance tracking
- Returns structured subgraphs for LLM context
- Synchronous API matching HierarchicalMemory

Public API:
    GraphRAGRetriever: Main retriever class
"""

from __future__ import annotations

import json
import logging
from typing import Any

import kuzu

from .hierarchical_memory import (
    KnowledgeEdge,
    KnowledgeNode,
    KnowledgeSubgraph,
    MemoryCategory,
)

logger = logging.getLogger(__name__)


class GraphRAGRetriever:
    """Graph RAG retriever wrapping Kuzu queries.

    Provides structured methods for knowledge graph traversal:
    - keyword_search: Find seed nodes via CONTAINS queries
    - similar_to_expand: Traverse SIMILAR_TO edges
    - get_provenance: Follow DERIVES_FROM to EpisodicMemory
    - retrieve_subgraph: Full algorithm combining all methods

    Args:
        connection: Kuzu Connection instance
        agent_name: Agent name for scoping queries

    Example:
        >>> import kuzu
        >>> db = kuzu.Database("/tmp/test_db")
        >>> conn = kuzu.Connection(db)
        >>> retriever = GraphRAGRetriever(conn, "test_agent")
        >>> nodes = retriever.keyword_search("photosynthesis", limit=10)
    """

    def __init__(self, connection: kuzu.Connection, agent_name: str):
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name cannot be empty")

        self.connection = connection
        self.agent_name = agent_name.strip()

    def keyword_search(self, keyword: str, limit: int = 20) -> list[KnowledgeNode]:
        """Search SemanticMemory nodes using CONTAINS on content and concept.

        Args:
            keyword: Search keyword
            limit: Maximum nodes to return

        Returns:
            List of matching KnowledgeNode instances with metadata
        """
        if not keyword or not keyword.strip():
            return []

        keyword = keyword.strip().lower()
        nodes: list[KnowledgeNode] = []

        try:
            result = self.connection.execute(
                """
                MATCH (m:SemanticMemory)
                WHERE m.agent_id = $agent_id
                  AND (LOWER(m.content) CONTAINS $keyword
                       OR LOWER(m.concept) CONTAINS $keyword)
                RETURN m.memory_id, m.concept, m.content, m.confidence,
                       m.source_id, m.tags, m.metadata, m.created_at
                ORDER BY m.confidence DESC
                LIMIT $limit
                """,
                {
                    "agent_id": self.agent_name,
                    "keyword": keyword,
                    "limit": limit,
                },
            )

            while result.has_next():
                row = result.get_next()
                tags = json.loads(row[5]) if row[5] else []
                metadata = json.loads(row[6]) if row[6] else {}
                nodes.append(
                    KnowledgeNode(
                        node_id=row[0],
                        category=MemoryCategory.SEMANTIC,
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
            logger.debug("keyword_search failed for '%s': %s", keyword, e)

        return nodes

    def similar_to_expand(
        self, node_id: str, min_similarity: float = 0.3
    ) -> list[tuple[KnowledgeNode, float]]:
        """Traverse SIMILAR_TO edges from a given node.

        Args:
            node_id: Source node ID to expand from
            min_similarity: Minimum edge weight to include

        Returns:
            List of (KnowledgeNode, similarity_weight) tuples
        """
        results: list[tuple[KnowledgeNode, float]] = []

        try:
            result = self.connection.execute(
                """
                MATCH (a:SemanticMemory {memory_id: $nid})-[r:SIMILAR_TO]->(b:SemanticMemory)
                WHERE r.weight >= $min_sim AND b.agent_id = $agent_id
                RETURN b.memory_id, b.concept, b.content, b.confidence,
                       b.source_id, b.tags, b.created_at, r.weight, b.metadata
                ORDER BY r.weight DESC
                """,
                {
                    "nid": node_id,
                    "min_sim": min_similarity,
                    "agent_id": self.agent_name,
                },
            )

            while result.has_next():
                row = result.get_next()
                tags = json.loads(row[5]) if row[5] else []
                metadata = json.loads(row[8]) if len(row) > 8 and row[8] else {}
                node = KnowledgeNode(
                    node_id=row[0],
                    category=MemoryCategory.SEMANTIC,
                    content=row[2],
                    concept=row[1],
                    confidence=row[3],
                    source_id=row[4] or "",
                    created_at=row[6] or "",
                    tags=tags,
                    metadata=metadata,
                )
                results.append((node, row[7]))

        except Exception as e:
            logger.debug("similar_to_expand failed for '%s': %s", node_id, e)

        return results

    def get_provenance(self, node_id: str) -> list[dict[str, Any]]:
        """Follow DERIVES_FROM edges to find source EpisodicMemory nodes.

        Args:
            node_id: SemanticMemory node ID

        Returns:
            List of episode dicts with content, source_label, created_at
        """
        episodes: list[dict[str, Any]] = []

        try:
            result = self.connection.execute(
                """
                MATCH (s:SemanticMemory {memory_id: $nid})-[r:DERIVES_FROM]->(e:EpisodicMemory)
                RETURN e.memory_id, e.content, e.source_label, e.created_at, r.confidence
                """,
                {"nid": node_id},
            )

            while result.has_next():
                row = result.get_next()
                episodes.append(
                    {
                        "episode_id": row[0],
                        "content": row[1],
                        "source_label": row[2],
                        "created_at": row[3],
                        "extraction_confidence": row[4],
                    }
                )

        except Exception as e:
            logger.debug("get_provenance failed for '%s': %s", node_id, e)

        return episodes

    def retrieve_subgraph(
        self,
        query: str,
        max_depth: int = 2,
        max_nodes: int = 20,
        min_similarity: float = 0.3,
    ) -> KnowledgeSubgraph:
        """Full subgraph assembly algorithm.

        1. Split query into keywords
        2. keyword_search for each keyword -> seed nodes
        3. similar_to_expand for each seed (up to max_depth hops)
        4. Collect edges
        5. Deduplicate and rank by confidence
        6. Return KnowledgeSubgraph

        Args:
            query: Search query
            max_depth: Maximum hops via SIMILAR_TO
            max_nodes: Maximum nodes to return
            min_similarity: Minimum similarity for edge expansion

        Returns:
            KnowledgeSubgraph with nodes and edges
        """
        if not query or not query.strip():
            return KnowledgeSubgraph(query=query)

        subgraph = KnowledgeSubgraph(query=query)
        seen_ids: set[str] = set()
        all_nodes: list[KnowledgeNode] = []
        all_edges: list[KnowledgeEdge] = []

        # Step 1-2: Keyword search for seeds
        keywords = [w.strip().lower() for w in query.split() if len(w.strip()) > 2]

        for keyword in keywords:
            seed_nodes = self.keyword_search(keyword, limit=max_nodes)
            for node in seed_nodes:
                if node.node_id not in seen_ids:
                    seen_ids.add(node.node_id)
                    all_nodes.append(node)

        # Step 3: Expand seeds via SIMILAR_TO
        seeds_to_expand = list(all_nodes)  # Copy current seeds
        for depth in range(max_depth):
            if len(seen_ids) >= max_nodes:
                break

            next_seeds: list[KnowledgeNode] = []
            for seed in seeds_to_expand:
                if len(seen_ids) >= max_nodes:
                    break

                neighbors = self.similar_to_expand(seed.node_id, min_similarity)
                for neighbor_node, weight in neighbors:
                    all_edges.append(
                        KnowledgeEdge(
                            source_id=seed.node_id,
                            target_id=neighbor_node.node_id,
                            relationship="SIMILAR_TO",
                            weight=weight,
                        )
                    )

                    if neighbor_node.node_id not in seen_ids and len(seen_ids) < max_nodes:
                        seen_ids.add(neighbor_node.node_id)
                        all_nodes.append(neighbor_node)
                        next_seeds.append(neighbor_node)

            seeds_to_expand = next_seeds

        # Step 5: Rank by confidence
        all_nodes.sort(key=lambda n: n.confidence, reverse=True)
        all_nodes = all_nodes[:max_nodes]

        subgraph.nodes = all_nodes
        subgraph.edges = all_edges

        return subgraph


__all__ = ["GraphRAGRetriever"]
