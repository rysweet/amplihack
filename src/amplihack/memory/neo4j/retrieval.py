"""Memory retrieval strategies with isolation enforcement.

Provides multiple retrieval strategies for finding relevant memories:
- TemporalRetrieval: Time-based memory access (recent, historical)
- SimilarityRetrieval: Content similarity via labels/tags
- GraphTraversal: Navigate memory relationships
- HybridRetrieval: Combine multiple strategies

All retrievals enforce isolation boundaries:
- Project-level: Agent can't see other project memories
- Agent-type: Architect can't see builder memories
- Instance: Ephemeral session state
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .connector import Neo4jConnector
from .exceptions import Neo4jConnectionError

logger = logging.getLogger(__name__)


class IsolationLevel(Enum):
    """Memory isolation levels."""

    PROJECT = "project"  # Isolated by project
    AGENT_TYPE = "agent_type"  # Isolated by agent type within project
    INSTANCE = "instance"  # Isolated by agent instance (ephemeral)


@dataclass
class RetrievalContext:
    """Context for memory retrieval with isolation boundaries.

    Defines what memories can be accessed based on current context.
    """

    # Identity context
    project_id: str
    agent_type: str
    agent_instance_id: Optional[str] = None

    # Retrieval parameters
    isolation_level: IsolationLevel = IsolationLevel.AGENT_TYPE
    include_global: bool = True  # Include global (non-project) memories

    # Time boundaries
    time_window_hours: Optional[int] = None  # Only recent memories
    since: Optional[datetime] = None  # Created after this time

    # Quality filters
    min_importance: Optional[int] = None  # 1-10 scale
    memory_types: Optional[List[str]] = None  # Filter by type

    def validate(self) -> bool:
        """Validate retrieval context.

        Returns:
            True if valid, False otherwise
        """
        if not self.project_id or not self.agent_type:
            logger.error("Missing required context: project_id and agent_type")
            return False

        if self.isolation_level == IsolationLevel.INSTANCE and not self.agent_instance_id:
            logger.error("Instance isolation requires agent_instance_id")
            return False

        if self.min_importance is not None and not (1 <= self.min_importance <= 10):
            logger.error("min_importance must be between 1 and 10")
            return False

        return True


@dataclass
class MemoryResult:
    """Single memory retrieval result."""

    memory_id: str
    content: str
    memory_type: str
    created_at: datetime
    importance: Optional[int]
    tags: List[str]
    metadata: Dict[str, Any]
    score: float  # Relevance score (0.0-1.0)

    @classmethod
    def from_neo4j_record(cls, record: Dict[str, Any], score: float = 1.0) -> "MemoryResult":
        """Create from Neo4j query result.

        Args:
            record: Neo4j record dictionary
            score: Relevance score (default 1.0)

        Returns:
            MemoryResult instance
        """
        # Handle both node properties and direct properties
        memory = record.get("m", record)

        return cls(
            memory_id=memory.get("id", ""),
            content=memory.get("content", ""),
            memory_type=memory.get("memory_type", ""),
            created_at=datetime.fromtimestamp(memory.get("created_at", 0) / 1000),
            importance=memory.get("importance"),
            tags=memory.get("tags", []),
            metadata=memory.get("metadata", {}),
            score=score,
        )


class RetrievalStrategy(ABC):
    """Abstract base for retrieval strategies."""

    def __init__(self, connector: Neo4jConnector):
        """Initialize strategy.

        Args:
            connector: Connected Neo4jConnector instance
        """
        self.conn = connector

    @abstractmethod
    def retrieve(
        self, context: RetrievalContext, limit: int = 10
    ) -> List[MemoryResult]:
        """Retrieve memories using this strategy.

        Args:
            context: Retrieval context with isolation boundaries
            limit: Maximum number of results

        Returns:
            List of MemoryResult instances, sorted by relevance

        Raises:
            Neo4jConnectionError: If query fails
        """

    def _build_isolation_clause(self, context: RetrievalContext) -> tuple[str, Dict[str, Any]]:
        """Build Cypher WHERE clause for isolation.

        Args:
            context: Retrieval context

        Returns:
            Tuple of (where_clause, parameters)
        """
        conditions = []
        params = {}

        # Project isolation
        if context.isolation_level in [IsolationLevel.PROJECT, IsolationLevel.AGENT_TYPE, IsolationLevel.INSTANCE]:
            if context.include_global:
                conditions.append("(p.id = $project_id OR p.id = 'global')")
            else:
                conditions.append("p.id = $project_id")
            params["project_id"] = context.project_id

        # Agent type isolation
        if context.isolation_level in [IsolationLevel.AGENT_TYPE, IsolationLevel.INSTANCE]:
            conditions.append("at.id = $agent_type")
            params["agent_type"] = context.agent_type

        # Instance isolation
        if context.isolation_level == IsolationLevel.INSTANCE:
            conditions.append("m.agent_instance_id = $agent_instance_id")
            params["agent_instance_id"] = context.agent_instance_id

        # Time window
        if context.time_window_hours:
            cutoff = datetime.now() - timedelta(hours=context.time_window_hours)
            conditions.append("m.created_at >= $time_cutoff")
            params["time_cutoff"] = int(cutoff.timestamp() * 1000)

        # Since timestamp
        if context.since:
            conditions.append("m.created_at >= $since")
            params["since"] = int(context.since.timestamp() * 1000)

        # Quality filters
        if context.min_importance:
            conditions.append("m.importance >= $min_importance")
            params["min_importance"] = context.min_importance

        # Memory types
        if context.memory_types:
            conditions.append("m.memory_type IN $memory_types")
            params["memory_types"] = context.memory_types

        where_clause = " AND ".join(conditions) if conditions else "true"
        return where_clause, params


class TemporalRetrieval(RetrievalStrategy):
    """Time-based memory retrieval.

    Finds memories based on temporal patterns:
    - Recent memories (last N hours/days)
    - Historical memories (time ranges)
    - Frequently accessed memories
    """

    def retrieve(
        self, context: RetrievalContext, limit: int = 10
    ) -> List[MemoryResult]:
        """Retrieve recent memories.

        Args:
            context: Retrieval context
            limit: Maximum results

        Returns:
            List of memories, most recent first
        """
        if not context.validate():
            raise ValueError("Invalid retrieval context")

        where_clause, params = self._build_isolation_clause(context)
        params["limit"] = limit

        query = f"""
        MATCH (m:Memory)-[:CREATED_BY]->(at:AgentType)
        MATCH (m)-[:BELONGS_TO]->(p:Project)
        WHERE {where_clause}
        RETURN m
        ORDER BY m.created_at DESC
        LIMIT $limit
        """

        try:
            results = self.conn.execute_query(query, params)
            return [
                MemoryResult.from_neo4j_record(r, score=1.0 - (i / len(results)))
                for i, r in enumerate(results)
            ]
        except Exception as e:
            logger.error("Temporal retrieval failed: %s", e)
            raise Neo4jConnectionError(f"Query failed: {e}")


class SimilarityRetrieval(RetrievalStrategy):
    """Content similarity retrieval via labels and tags.

    Note: This is a simplified version using tags/labels.
    Full vector similarity will be added in a future phase.
    """

    def retrieve(
        self, context: RetrievalContext, limit: int = 10, query_tags: Optional[List[str]] = None
    ) -> List[MemoryResult]:
        """Retrieve similar memories based on tags.

        Args:
            context: Retrieval context
            limit: Maximum results
            query_tags: Tags to match against

        Returns:
            List of memories, most similar first
        """
        if not context.validate():
            raise ValueError("Invalid retrieval context")

        if not query_tags:
            logger.warning("No query tags provided, returning empty results")
            return []

        where_clause, params = self._build_isolation_clause(context)
        params["query_tags"] = query_tags
        params["limit"] = limit

        # Match memories with overlapping tags
        query = f"""
        MATCH (m:Memory)-[:CREATED_BY]->(at:AgentType)
        MATCH (m)-[:BELONGS_TO]->(p:Project)
        WHERE {where_clause} AND m.tags IS NOT NULL
        WITH m,
             [tag IN m.tags WHERE tag IN $query_tags] as matching_tags
        WHERE size(matching_tags) > 0
        RETURN m, size(matching_tags) as match_count
        ORDER BY match_count DESC, m.importance DESC
        LIMIT $limit
        """

        try:
            results = self.conn.execute_query(query, params)
            max_matches = results[0]["match_count"] if results else 1

            return [
                MemoryResult.from_neo4j_record(
                    r, score=r["match_count"] / max_matches if max_matches > 0 else 0.0
                )
                for r in results
            ]
        except Exception as e:
            logger.error("Similarity retrieval failed: %s", e)
            raise Neo4jConnectionError(f"Query failed: {e}")


class GraphTraversal(RetrievalStrategy):
    """Graph-based memory traversal.

    Navigates memory relationships:
    - Parent-child hierarchies
    - Related memories
    - Context chains
    """

    def retrieve(
        self, context: RetrievalContext, limit: int = 10, start_memory_id: Optional[str] = None
    ) -> List[MemoryResult]:
        """Retrieve related memories via graph traversal.

        Args:
            context: Retrieval context
            limit: Maximum results
            start_memory_id: Memory to start traversal from

        Returns:
            List of related memories
        """
        if not context.validate():
            raise ValueError("Invalid retrieval context")

        if not start_memory_id:
            logger.warning("No start memory provided, returning empty results")
            return []

        where_clause, params = self._build_isolation_clause(context)
        params["start_id"] = start_memory_id
        params["limit"] = limit

        # Traverse RELATED_TO relationships (depth 1-2)
        query = f"""
        MATCH (start:Memory {{id: $start_id}})
        MATCH path = (start)-[:RELATED_TO*1..2]-(m:Memory)
        MATCH (m)-[:CREATED_BY]->(at:AgentType)
        MATCH (m)-[:BELONGS_TO]->(p:Project)
        WHERE {where_clause} AND m.id <> $start_id
        WITH m, length(path) as distance
        RETURN m, distance
        ORDER BY distance ASC, m.importance DESC
        LIMIT $limit
        """

        try:
            results = self.conn.execute_query(query, params)
            max_distance = max((r["distance"] for r in results), default=1)

            return [
                MemoryResult.from_neo4j_record(
                    r, score=1.0 - (r["distance"] / max_distance) if max_distance > 0 else 1.0
                )
                for r in results
            ]
        except Exception as e:
            logger.error("Graph traversal failed: %s", e)
            raise Neo4jConnectionError(f"Query failed: {e}")


class HybridRetrieval(RetrievalStrategy):
    """Hybrid retrieval combining multiple strategies.

    Combines temporal, similarity, and graph-based retrieval
    with weighted scoring.
    """

    def __init__(
        self,
        connector: Neo4jConnector,
        temporal_weight: float = 0.4,
        similarity_weight: float = 0.4,
        graph_weight: float = 0.2,
    ):
        """Initialize hybrid retrieval.

        Args:
            connector: Neo4jConnector instance
            temporal_weight: Weight for temporal score
            similarity_weight: Weight for similarity score
            graph_weight: Weight for graph score
        """
        super().__init__(connector)

        # Validate weights
        total = temporal_weight + similarity_weight + graph_weight
        if not abs(total - 1.0) < 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")

        self.temporal_weight = temporal_weight
        self.similarity_weight = similarity_weight
        self.graph_weight = graph_weight

        # Initialize strategies
        self.temporal = TemporalRetrieval(connector)
        self.similarity = SimilarityRetrieval(connector)
        self.graph = GraphTraversal(connector)

    def retrieve(
        self,
        context: RetrievalContext,
        limit: int = 10,
        query_tags: Optional[List[str]] = None,
        start_memory_id: Optional[str] = None,
    ) -> List[MemoryResult]:
        """Retrieve memories using hybrid strategy.

        Args:
            context: Retrieval context
            limit: Maximum results
            query_tags: Tags for similarity search
            start_memory_id: Starting point for graph traversal

        Returns:
            List of memories ranked by combined score
        """
        if not context.validate():
            raise ValueError("Invalid retrieval context")

        # Collect results from all strategies
        all_results: Dict[str, MemoryResult] = {}

        # Temporal retrieval
        try:
            temporal_results = self.temporal.retrieve(context, limit * 2)
            for result in temporal_results:
                result.score *= self.temporal_weight
                all_results[result.memory_id] = result
        except Exception as e:
            logger.warning("Temporal retrieval failed: %s", e)

        # Similarity retrieval
        if query_tags:
            try:
                similarity_results = self.similarity.retrieve(context, limit * 2, query_tags)
                for result in similarity_results:
                    if result.memory_id in all_results:
                        all_results[result.memory_id].score += result.score * self.similarity_weight
                    else:
                        result.score *= self.similarity_weight
                        all_results[result.memory_id] = result
            except Exception as e:
                logger.warning("Similarity retrieval failed: %s", e)

        # Graph traversal
        if start_memory_id:
            try:
                graph_results = self.graph.retrieve(context, limit * 2, start_memory_id)
                for result in graph_results:
                    if result.memory_id in all_results:
                        all_results[result.memory_id].score += result.score * self.graph_weight
                    else:
                        result.score *= self.graph_weight
                        all_results[result.memory_id] = result
            except Exception as e:
                logger.warning("Graph traversal failed: %s", e)

        # Sort by combined score and limit
        sorted_results = sorted(
            all_results.values(), key=lambda r: r.score, reverse=True
        )
        return sorted_results[:limit]


# Convenience functions

def retrieve_recent_memories(
    connector: Neo4jConnector,
    project_id: str,
    agent_type: str,
    hours: int = 24,
    limit: int = 10,
) -> List[MemoryResult]:
    """Retrieve recent memories for a project and agent type.

    Args:
        connector: Neo4jConnector instance
        project_id: Project identifier
        agent_type: Agent type identifier
        hours: Time window in hours
        limit: Maximum results

    Returns:
        List of recent memories
    """
    context = RetrievalContext(
        project_id=project_id,
        agent_type=agent_type,
        time_window_hours=hours,
    )

    strategy = TemporalRetrieval(connector)
    return strategy.retrieve(context, limit)


def retrieve_similar_memories(
    connector: Neo4jConnector,
    project_id: str,
    agent_type: str,
    tags: List[str],
    limit: int = 10,
) -> List[MemoryResult]:
    """Retrieve memories similar to given tags.

    Args:
        connector: Neo4jConnector instance
        project_id: Project identifier
        agent_type: Agent type identifier
        tags: Tags to match
        limit: Maximum results

    Returns:
        List of similar memories
    """
    context = RetrievalContext(
        project_id=project_id,
        agent_type=agent_type,
    )

    strategy = SimilarityRetrieval(connector)
    return strategy.retrieve(context, limit, query_tags=tags)
