"""Neo4j memory store with agent type support.

Provides CRUD operations for agent memories with automatic
agent type linking and relationship management.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from .config import get_config
from .connector import Neo4jConnector

logger = logging.getLogger(__name__)


class MemoryStore:
    """Neo4j-based memory store with agent type awareness.

    Handles:
    - Memory CRUD operations
    - Agent type linking
    - Project scoping
    - Quality tracking
    """

    def __init__(self, connector: Neo4jConnector):
        """Initialize memory store.

        Args:
            connector: Connected Neo4jConnector instance
        """
        self.conn = connector
        self.config = get_config()

    def create_memory(
        self,
        content: str,
        agent_type: str,
        category: str = "general",
        memory_type: str = "procedural",
        project_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        quality_score: float = 0.5,
        confidence: float = 0.7,
    ) -> str:
        """Create a new memory linked to an agent type.

        Args:
            content: Memory content
            agent_type: Type of agent (architect, builder, etc.)
            category: Memory category (design_pattern, error_handling, etc.)
            memory_type: Type (procedural, declarative, meta, anti_pattern)
            project_id: Optional project scope
            metadata: Additional structured data
            tags: Searchable tags
            quality_score: Overall quality (0-1)
            confidence: Agent's confidence (0-1)

        Returns:
            Memory ID

        Raises:
            ValueError: If agent_type doesn't exist
        """
        memory_id = str(uuid4())
        now = datetime.now().isoformat()

        query = """
        // Find or create agent type
        MATCH (at:AgentType {id: $agent_type})

        // Create memory node
        CREATE (m:Memory {
            id: $memory_id,
            content: $content,
            agent_type: $agent_type,
            category: $category,
            memory_type: $memory_type,
            quality_score: $quality_score,
            confidence: $confidence,
            created_at: $created_at,
            last_validated: $created_at,
            validation_count: 0,
            application_count: 0,
            success_rate: 0.0,
            tags: $tags,
            metadata: $metadata
        })

        // Link to agent type
        CREATE (at)-[:HAS_MEMORY {
            created_at: $created_at,
            shared: true
        }]->(m)

        // Link to project if provided
        WITH m, at
        OPTIONAL MATCH (p:Project {id: $project_id})
        FOREACH (proj IN CASE WHEN p IS NOT NULL THEN [p] ELSE [] END |
            CREATE (m)-[:SCOPED_TO {
                scope_type: "project_specific",
                created_at: $created_at
            }]->(proj)
        )

        // Universal scope if no project
        FOREACH (_ IN CASE WHEN $project_id IS NULL THEN [1] ELSE [] END |
            CREATE (m)-[:SCOPED_TO {
                scope_type: "universal",
                created_at: $created_at
            }]->(at)
        )

        RETURN m.id as memory_id
        """

        # Serialize metadata to JSON string (Neo4j doesn't support nested dicts)
        metadata_json = json.dumps(metadata) if metadata else "{}"

        params = {
            "memory_id": memory_id,
            "agent_type": agent_type,
            "content": content,
            "category": category,
            "memory_type": memory_type,
            "project_id": project_id,
            "quality_score": quality_score,
            "confidence": confidence,
            "created_at": now,
            "tags": tags or [],
            "metadata": metadata_json,
        }

        try:
            result = self.conn.execute_write(query, params)
            if result:
                logger.info("Created memory %s for agent type %s", memory_id, agent_type)
                return memory_id
            raise RuntimeError("Failed to create memory")
        except Exception as e:
            logger.error("Failed to create memory: %s", e)
            raise

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Retrieve a memory by ID.

        Args:
            memory_id: Memory identifier

        Returns:
            Memory data or None if not found
        """
        query = """
        MATCH (m:Memory {id: $memory_id})
        OPTIONAL MATCH (at:AgentType)-[:HAS_MEMORY]->(m)
        OPTIONAL MATCH (m)-[:SCOPED_TO]->(scope)

        RETURN m {
            .*,
            agent_type: at.id,
            scope_label: labels(scope)[0],
            scope_id: scope.id
        } as memory
        """

        result = self.conn.execute_query(query, {"memory_id": memory_id})

        if result:
            return result[0].get("memory")
        return None

    def update_memory(
        self,
        memory_id: str,
        content: str | None = None,
        quality_score: float | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """Update memory properties.

        Args:
            memory_id: Memory to update
            content: New content
            quality_score: New quality score
            metadata: New metadata (merges with existing)
            tags: New tags (replaces existing)

        Returns:
            True if updated successfully
        """
        # Build dynamic SET clause
        updates = []
        params = {"memory_id": memory_id, "updated_at": datetime.now().isoformat()}

        if content is not None:
            updates.append("m.content = $content")
            params["content"] = content

        if quality_score is not None:
            updates.append("m.quality_score = $quality_score")
            params["quality_score"] = quality_score

        if metadata is not None:
            updates.append("m.metadata = $metadata")
            params["metadata"] = json.dumps(metadata)

        if tags is not None:
            updates.append("m.tags = $tags")
            params["tags"] = tags

        if not updates:
            return True  # Nothing to update

        updates.append("m.last_validated = $updated_at")

        query = f"""
        MATCH (m:Memory {{id: $memory_id}})
        SET {", ".join(updates)}
        RETURN m.id as memory_id
        """

        try:
            result = self.conn.execute_write(query, params)
            return bool(result)
        except Exception as e:
            logger.error("Failed to update memory: %s", e)
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory and its relationships.

        Args:
            memory_id: Memory to delete

        Returns:
            True if deleted successfully
        """
        query = """
        MATCH (m:Memory {id: $memory_id})
        DETACH DELETE m
        RETURN count(m) as deleted
        """

        try:
            result = self.conn.execute_write(query, {"memory_id": memory_id})
            deleted = result[0].get("deleted", 0) if result else 0
            return deleted > 0
        except Exception as e:
            logger.error("Failed to delete memory: %s", e)
            return False

    def get_memories_by_agent_type(
        self,
        agent_type: str,
        project_id: str | None = None,
        category: str | None = None,
        min_quality: float = 0.0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve memories for a specific agent type.

        Args:
            agent_type: Agent type to filter by
            project_id: Optional project scope filter
            category: Optional category filter
            min_quality: Minimum quality score
            limit: Maximum results

        Returns:
            List of memory dictionaries
        """
        query = """
        MATCH (at:AgentType {id: $agent_type})-[:HAS_MEMORY]->(m:Memory)
        WHERE m.quality_score >= $min_quality
        """

        params = {
            "agent_type": agent_type,
            "min_quality": min_quality,
            "limit": limit,
        }

        # Add project filter if specified
        if project_id:
            query += """
            AND (
                (m)-[:SCOPED_TO]->(:Project {id: $project_id})
                OR (m)-[:SCOPED_TO {scope_type: "universal"}]->()
            )
            """
            params["project_id"] = project_id

        # Add category filter if specified
        if category:
            query += " AND m.category = $category"
            params["category"] = category

        query += """
        RETURN m {
            .*,
            agent_type: at.id
        } as memory
        ORDER BY m.quality_score DESC, m.created_at DESC
        LIMIT $limit
        """

        result = self.conn.execute_query(query, params)
        return [r.get("memory") for r in result if r.get("memory")]

    def record_usage(
        self,
        memory_id: str,
        agent_instance_id: str,
        outcome: str = "successful",
        feedback_score: float | None = None,
    ) -> bool:
        """Record that an agent used a memory.

        Args:
            memory_id: Memory that was used
            agent_instance_id: Agent instance that used it
            outcome: Usage outcome (successful, failed, partial)
            feedback_score: Optional feedback score (0-1)

        Returns:
            True if recorded successfully
        """
        query = """
        MATCH (m:Memory {id: $memory_id})

        // Create or find agent instance
        MERGE (ai:AgentInstance {id: $agent_instance_id})

        // Create usage relationship
        CREATE (ai)-[:USED {
            used_at: $used_at,
            outcome: $outcome,
            feedback_score: $feedback_score
        }]->(m)

        // Update memory statistics
        SET m.application_count = m.application_count + 1,
            m.last_used = $used_at

        // Update success rate if outcome provided
        WITH m
        MATCH (m)<-[u:USED]-()
        WITH m,
             count(u) as total_uses,
             size([x IN collect(u) WHERE x.outcome = 'successful']) as successes
        SET m.success_rate = toFloat(successes) / toFloat(total_uses)

        // Update quality score based on feedback
        WITH m
        WHERE $feedback_score IS NOT NULL
        SET m.quality_score = (m.quality_score * 0.9 + $feedback_score * 0.1)

        RETURN m.id as memory_id
        """

        params = {
            "memory_id": memory_id,
            "agent_instance_id": agent_instance_id,
            "used_at": datetime.now().isoformat(),
            "outcome": outcome,
            "feedback_score": feedback_score,
        }

        try:
            result = self.conn.execute_write(query, params)
            return bool(result)
        except Exception as e:
            logger.error("Failed to record usage: %s", e)
            return False

    def validate_memory(
        self,
        memory_id: str,
        agent_instance_id: str,
        feedback_score: float,
        outcome: str = "successful",
        notes: str | None = None,
    ) -> bool:
        """Record validation of a memory by an agent.

        Args:
            memory_id: Memory being validated
            agent_instance_id: Agent providing validation
            feedback_score: Validation score (0-1)
            outcome: Validation outcome
            notes: Optional validation notes

        Returns:
            True if recorded successfully
        """
        query = """
        MATCH (m:Memory {id: $memory_id})

        // Create or find agent instance
        MERGE (ai:AgentInstance {id: $agent_instance_id})

        // Create validation relationship
        CREATE (ai)-[:VALIDATED {
            validated_at: $validated_at,
            outcome: $outcome,
            feedback_score: $feedback_score,
            notes: $notes
        }]->(m)

        // Update memory validation statistics
        SET m.validation_count = m.validation_count + 1,
            m.last_validated = $validated_at

        // Recalculate quality score with validation feedback
        WITH m
        MATCH (m)<-[v:VALIDATED]-()
        WITH m, avg(v.feedback_score) as avg_validation_score
        SET m.quality_score = (m.confidence * 0.3 + avg_validation_score * 0.7)

        RETURN m.id as memory_id
        """

        params = {
            "memory_id": memory_id,
            "agent_instance_id": agent_instance_id,
            "validated_at": datetime.now().isoformat(),
            "outcome": outcome,
            "feedback_score": feedback_score,
            "notes": notes,
        }

        try:
            result = self.conn.execute_write(query, params)
            return bool(result)
        except Exception as e:
            logger.error("Failed to validate memory: %s", e)
            return False

    def search_memories(
        self,
        query: str,
        agent_type: str | None = None,
        project_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search memories by content and tags.

        Args:
            query: Search query string
            agent_type: Optional agent type filter
            project_id: Optional project filter
            limit: Maximum results

        Returns:
            List of matching memories
        """
        cypher_query = """
        MATCH (m:Memory)
        WHERE m.content CONTAINS $query OR any(tag IN m.tags WHERE tag CONTAINS $query)
        """

        params = {"query": query, "limit": limit}

        if agent_type:
            cypher_query += """
            AND exists((m)<-[:HAS_MEMORY]-(:AgentType {id: $agent_type}))
            """
            params["agent_type"] = agent_type

        if project_id:
            cypher_query += """
            AND (
                (m)-[:SCOPED_TO]->(:Project {id: $project_id})
                OR (m)-[:SCOPED_TO {scope_type: "universal"}]->()
            )
            """
            params["project_id"] = project_id

        cypher_query += """
        OPTIONAL MATCH (at:AgentType)-[:HAS_MEMORY]->(m)
        RETURN m {
            .*,
            agent_type: at.id
        } as memory
        ORDER BY m.quality_score DESC
        LIMIT $limit
        """

        result = self.conn.execute_query(cypher_query, params)
        return [r.get("memory") for r in result if r.get("memory")]

    def get_high_quality_memories(
        self,
        agent_type: str,
        min_quality: float = 0.8,
        min_validations: int = 3,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get high-quality, well-validated memories.

        Args:
            agent_type: Agent type to filter by
            min_quality: Minimum quality score
            min_validations: Minimum validation count
            limit: Maximum results

        Returns:
            List of high-quality memories
        """
        query = """
        MATCH (at:AgentType {id: $agent_type})-[:HAS_MEMORY]->(m:Memory)
        WHERE m.quality_score >= $min_quality
          AND m.validation_count >= $min_validations

        RETURN m {
            .*,
            agent_type: at.id
        } as memory
        ORDER BY m.quality_score DESC, m.validation_count DESC
        LIMIT $limit
        """

        params = {
            "agent_type": agent_type,
            "min_quality": min_quality,
            "min_validations": min_validations,
            "limit": limit,
        }

        result = self.conn.execute_query(query, params)
        return [r.get("memory") for r in result if r.get("memory")]

    def get_memory_stats(self, agent_type: str | None = None) -> dict[str, Any]:
        """Get memory statistics.

        Args:
            agent_type: Optional agent type filter

        Returns:
            Dictionary with statistics
        """
        if agent_type:
            query = """
            MATCH (at:AgentType {id: $agent_type})-[:HAS_MEMORY]->(m:Memory)
            RETURN
                count(m) as total_memories,
                avg(m.quality_score) as avg_quality,
                sum(m.application_count) as total_applications,
                avg(m.success_rate) as avg_success_rate
            """
            params = {"agent_type": agent_type}
        else:
            query = """
            MATCH (m:Memory)
            RETURN
                count(m) as total_memories,
                avg(m.quality_score) as avg_quality,
                sum(m.application_count) as total_applications,
                avg(m.success_rate) as avg_success_rate
            """
            params = {}

        result = self.conn.execute_query(query, params)

        if result:
            return result[0]
        return {
            "total_memories": 0,
            "avg_quality": 0.0,
            "total_applications": 0,
            "avg_success_rate": 0.0,
        }
