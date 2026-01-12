"""Kùzu graph database backend implementation.

Implements memory storage using Kùzu's native graph structure.

Philosophy:
- Graph-native: Memories as nodes, relationships as edges
- Performance: <50ms retrieval, <500ms storage via Cypher queries
- Rich relationships: Session→Memory, Agent→Memory with properties
- Self-contained: All Kùzu-specific logic in this module

Public API:
    KuzuBackend: MemoryBackend implementation using Kùzu graph database

Schema:
    Nodes:
        Memory (id, session_id, agent_id, memory_type, title, content, ...)
        Session (session_id, created_at, last_accessed)
        Agent (agent_id, name)

    Edges:
        (Session)-[HAS_MEMORY]->(Memory)
        (Agent)-[CREATED]->(Memory)
        (Memory)-[CHILD_OF]->(Memory)  # For hierarchical memories
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import kuzu
except ImportError:
    kuzu = None  # type: ignore

from ..models import MemoryEntry, MemoryQuery, MemoryType, SessionInfo
from .base import BackendCapabilities

logger = logging.getLogger(__name__)


class KuzuBackend:
    """Kùzu graph database backend.

    Uses graph structure fer natural relationship modeling:
    - Sessions contain memories
    - Agents create memories
    - Memories can reference other memories
    """

    def __init__(self, db_path: Path | str | None = None):
        """Initialize Kùzu backend.

        Args:
            db_path: Path to Kùzu database directory. Defaults to ~/.amplihack/memory_kuzu/

        Raises:
            ImportError: If kuzu package not installed
        """
        if kuzu is None:
            raise ImportError(
                "Kùzu not installed. Install with: pip install kuzu\n"
                "This is required fer the graph backend."
            )

        if db_path is None:
            db_path = Path.home() / ".amplihack" / "memory_kuzu.db"
        elif isinstance(db_path, str):
            db_path = Path(db_path)

        self.db_path = db_path
        # Create parent directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create database connection (Kùzu creates the file)
        self.database = kuzu.Database(str(self.db_path))
        self.connection = kuzu.Connection(self.database)

    def get_capabilities(self) -> BackendCapabilities:
        """Get Kùzu backend capabilities."""
        return BackendCapabilities(
            supports_graph_queries=True,  # Native graph traversal
            supports_vector_search=False,  # Not yet (future: embeddings)
            supports_transactions=True,  # ACID transactions
            supports_fulltext_search=False,  # Not yet
            max_concurrent_connections=10,  # Multi-threaded support
            backend_name="kuzu",
            backend_version="0.x",
        )

    def initialize(self) -> None:
        """Initialize Kùzu schema.

        Creates node and relationship tables if needed.
        Idempotent - safe to call multiple times.
        """
        try:
            # Create Memory node table
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS Memory(
                    id STRING,
                    session_id STRING,
                    agent_id STRING,
                    memory_type STRING,
                    title STRING,
                    content STRING,
                    content_hash STRING,
                    metadata STRING,
                    tags STRING,
                    importance INT64,
                    created_at TIMESTAMP,
                    accessed_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    parent_id STRING,
                    PRIMARY KEY (id)
                )
            """)

            # Create Session node table
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS Session(
                    session_id STRING,
                    created_at TIMESTAMP,
                    last_accessed TIMESTAMP,
                    metadata STRING,
                    PRIMARY KEY (session_id)
                )
            """)

            # Create Agent node table
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS Agent(
                    agent_id STRING,
                    name STRING,
                    first_used TIMESTAMP,
                    last_used TIMESTAMP,
                    PRIMARY KEY (agent_id)
                )
            """)

            # Create relationship tables
            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS HAS_MEMORY(
                    FROM Session TO Memory
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS CREATED(
                    FROM Agent TO Memory,
                    created_at TIMESTAMP
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS CHILD_OF(
                    FROM Memory TO Memory
                )
            """)

            logger.info("Kùzu schema initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing Kùzu schema: {e}")
            raise

    def store_memory(self, memory: MemoryEntry) -> bool:
        """Store a memory entry in graph database.

        Creates Memory node and relationships to Session and Agent.

        Args:
            memory: Memory entry to store

        Returns:
            True if successful, False otherwise

        Performance: <500ms (node + edge creation)
        """
        try:
            # Compute content hash (same logic as SQLite)
            import hashlib

            content_hash = hashlib.sha256(memory.content.encode("utf-8")).hexdigest()

            # Prepare values (Kùzu doesn't support NULL in some cases, use empty string)
            tags_str = json.dumps(memory.tags) if memory.tags else ""
            # For expires_at: use NULL for None values (Kùzu requires proper NULL, not empty string fer TIMESTAMP)
            expires_clause = (
                f"timestamp('{memory.expires_at.isoformat()}')" if memory.expires_at else "NULL"
            )
            parent_id_str = memory.parent_id if memory.parent_id else ""
            importance_val = memory.importance if memory.importance is not None else 0

            # Create or update Memory node using CREATE
            self.connection.execute(
                f"""
                CREATE (m:Memory {{
                    id: '{memory.id}',
                    session_id: '{memory.session_id}',
                    agent_id: '{memory.agent_id}',
                    memory_type: '{memory.memory_type.value}',
                    title: $title,
                    content: $content,
                    content_hash: '{content_hash}',
                    metadata: $metadata,
                    tags: '{tags_str}',
                    importance: {importance_val},
                    created_at: timestamp('{memory.created_at.isoformat()}'),
                    accessed_at: timestamp('{memory.accessed_at.isoformat()}'),
                    expires_at: {expires_clause},
                    parent_id: '{parent_id_str}'
                }})
            """,
                {
                    "title": memory.title,
                    "content": memory.content,
                    "metadata": json.dumps(memory.metadata),
                },
            )

            # Create Session node if not exists (use MERGE to avoid duplicates)
            now_str = datetime.now().isoformat()
            self.connection.execute(
                f"""
                MERGE (s:Session {{session_id: '{memory.session_id}'}})
                ON CREATE SET
                    s.created_at = timestamp('{now_str}'),
                    s.last_accessed = timestamp('{now_str}'),
                    s.metadata = '{{}}'
                ON MATCH SET
                    s.last_accessed = timestamp('{now_str}')
            """
            )

            # Create Agent node if not exists (use MERGE to avoid duplicates)
            self.connection.execute(
                f"""
                MERGE (a:Agent {{agent_id: '{memory.agent_id}'}})
                ON CREATE SET
                    a.name = '{memory.agent_id}',
                    a.first_used = timestamp('{now_str}'),
                    a.last_used = timestamp('{now_str}')
                ON MATCH SET
                    a.last_used = timestamp('{now_str}')
            """
            )

            # Create HAS_MEMORY relationship
            self.connection.execute(
                f"""
                MATCH (s:Session), (m:Memory)
                WHERE s.session_id = '{memory.session_id}' AND m.id = '{memory.id}'
                CREATE (s)-[:HAS_MEMORY]->(m)
            """
            )

            # Create CREATED relationship
            self.connection.execute(
                f"""
                MATCH (a:Agent), (m:Memory)
                WHERE a.agent_id = '{memory.agent_id}' AND m.id = '{memory.id}'
                CREATE (a)-[:CREATED {{created_at: timestamp('{memory.created_at.isoformat()}')}}]->(m)
            """
            )

            # Create CHILD_OF relationship if parent_id specified
            if memory.parent_id:
                self.connection.execute(
                    f"""
                    MATCH (parent:Memory), (child:Memory)
                    WHERE parent.id = '{memory.parent_id}' AND child.id = '{memory.id}'
                    CREATE (child)-[:CHILD_OF]->(parent)
                """
                )

            return True

        except Exception as e:
            logger.error(f"Error storing memory in Kùzu: {e}", exc_info=True)
            return False

    def retrieve_memories(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Retrieve memories matching the query.

        Uses Cypher queries fer graph traversal.

        Args:
            query: Query parameters

        Returns:
            List of matching memory entries

        Performance: <50ms (indexed lookups)
        """
        try:
            # Build WHERE conditions
            where_conditions = []
            params = {}

            if query.session_id:
                where_conditions.append("m.session_id = $session_id")
                params["session_id"] = query.session_id

            if query.agent_id:
                where_conditions.append("m.agent_id = $agent_id")
                params["agent_id"] = query.agent_id

            if query.memory_type:
                where_conditions.append("m.memory_type = $memory_type")
                params["memory_type"] = query.memory_type.value

            if query.min_importance:
                where_conditions.append("m.importance >= $min_importance")
                params["min_importance"] = query.min_importance

            if query.created_after:
                where_conditions.append("m.created_at >= $created_after")
                params["created_after"] = query.created_after

            if query.created_before:
                where_conditions.append("m.created_at <= $created_before")
                params["created_before"] = query.created_before

            if not query.include_expired:
                where_conditions.append("(m.expires_at IS NULL OR m.expires_at > $now)")
                params["now"] = datetime.now()

            # Build WHERE clause
            where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"

            # Build Cypher query
            cypher = f"""
                MATCH (m:Memory)
                WHERE {where_clause}
                RETURN m
                ORDER BY m.accessed_at DESC, m.importance DESC
            """

            if query.limit:
                cypher += f" LIMIT {query.limit}"
                if query.offset:
                    cypher += f" SKIP {query.offset}"

            # Execute query
            result = self.connection.execute(cypher, params)

            # Convert to MemoryEntry objects
            memories = []
            while result.has_next():
                row = result.get_next()
                memory_node = row[0]

                # Parse node properties
                memory = MemoryEntry(
                    id=memory_node["id"],
                    session_id=memory_node["session_id"],
                    agent_id=memory_node["agent_id"],
                    memory_type=MemoryType(memory_node["memory_type"]),
                    title=memory_node["title"],
                    content=memory_node["content"],
                    metadata=json.loads(memory_node["metadata"]) if memory_node["metadata"] else {},
                    tags=json.loads(memory_node["tags"]) if memory_node.get("tags") else None,
                    importance=memory_node.get("importance"),
                    created_at=memory_node["created_at"],
                    accessed_at=memory_node["accessed_at"],
                    expires_at=memory_node.get("expires_at"),
                    parent_id=memory_node.get("parent_id"),
                )
                memories.append(memory)

            # Update access times
            if memories:
                memory_ids = [m.id for m in memories]
                for memory_id in memory_ids:
                    self.connection.execute(
                        """
                        MATCH (m:Memory {id: $id})
                        SET m.accessed_at = $now
                    """,
                        {"id": memory_id, "now": datetime.now()},
                    )

            return memories

        except Exception as e:
            logger.error(f"Error retrieving memories from Kùzu: {e}")
            return []

    def get_memory_by_id(self, memory_id: str) -> MemoryEntry | None:
        """Get a specific memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory entry if found, None otherwise

        Performance: <50ms (primary key lookup)
        """
        try:
            result = self.connection.execute(
                """
                MATCH (m:Memory {id: $id})
                RETURN m
            """,
                {"id": memory_id},
            )

            if not result.has_next():
                return None

            row = result.get_next()
            memory_node = row[0]

            # Update access time
            self.connection.execute(
                """
                MATCH (m:Memory {id: $id})
                SET m.accessed_at = $now
            """,
                {"id": memory_id, "now": datetime.now()},
            )

            # Parse to MemoryEntry
            return MemoryEntry(
                id=memory_node["id"],
                session_id=memory_node["session_id"],
                agent_id=memory_node["agent_id"],
                memory_type=MemoryType(memory_node["memory_type"]),
                title=memory_node["title"],
                content=memory_node["content"],
                metadata=json.loads(memory_node["metadata"]) if memory_node["metadata"] else {},
                tags=json.loads(memory_node["tags"]) if memory_node.get("tags") else None,
                importance=memory_node.get("importance"),
                created_at=memory_node["created_at"],
                accessed_at=memory_node["accessed_at"],
                expires_at=memory_node.get("expires_at"),
                parent_id=memory_node.get("parent_id"),
            )

        except Exception as e:
            logger.error(f"Error getting memory by ID from Kùzu: {e}")
            return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry and its relationships.

        Args:
            memory_id: Unique memory identifier

        Returns:
            True if deleted, False otherwise

        Performance: <100ms (node + edge deletion)
        """
        try:
            # Delete memory node and its relationships (DETACH DELETE removes edges first)
            result = self.connection.execute(
                """
                MATCH (m:Memory {id: $id})
                DETACH DELETE m
            """,
                {"id": memory_id},
            )

            return True

        except Exception as e:
            logger.error(f"Error deleting memory from Kùzu: {e}")
            return False

    def cleanup_expired(self) -> int:
        """Remove expired memory entries.

        Returns:
            Number of entries removed

        Performance: No strict limit (periodic maintenance)
        """
        try:
            result = self.connection.execute(
                """
                MATCH (m:Memory)
                WHERE m.expires_at IS NOT NULL AND m.expires_at < $now
                DELETE m
                RETURN COUNT(m) AS deleted_count
            """,
                {"now": datetime.now()},
            )

            if result.has_next():
                row = result.get_next()
                return row[0]

            return 0

        except Exception as e:
            logger.error(f"Error cleaning up expired memories from Kùzu: {e}")
            return 0

    def get_session_info(self, session_id: str) -> SessionInfo | None:
        """Get information about a session.

        Args:
            session_id: Session identifier

        Returns:
            Session information if found

        Performance: <50ms (graph traversal)
        """
        try:
            result = self.connection.execute(
                """
                MATCH (s:Session {session_id: $session_id})
                OPTIONAL MATCH (s)-[:HAS_MEMORY]->(m:Memory)
                OPTIONAL MATCH (a:Agent)-[:CREATED]->(m)
                RETURN s, COUNT(DISTINCT m) AS memory_count, COLLECT(DISTINCT a.agent_id) AS agent_ids
            """,
                {"session_id": session_id},
            )

            if not result.has_next():
                return None

            row = result.get_next()
            session_node = row[0]
            memory_count = row[1]
            agent_ids = row[2] if row[2] else []

            return SessionInfo(
                session_id=session_node["session_id"],
                created_at=session_node["created_at"],
                last_accessed=session_node["last_accessed"],
                agent_ids=agent_ids,
                memory_count=memory_count,
                metadata=json.loads(session_node["metadata"])
                if session_node.get("metadata")
                else {},
            )

        except Exception as e:
            logger.error(f"Error getting session info from Kùzu: {e}")
            return None

    def list_sessions(self, limit: int | None = None) -> list[SessionInfo]:
        """List all sessions ordered by last accessed.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session information

        Performance: <100ms (graph scan)
        """
        try:
            cypher = """
                MATCH (s:Session)
                OPTIONAL MATCH (s)-[:HAS_MEMORY]->(m:Memory)
                OPTIONAL MATCH (a:Agent)-[:CREATED]->(m)
                RETURN s, COUNT(DISTINCT m) AS memory_count, COLLECT(DISTINCT a.agent_id) AS agent_ids
                ORDER BY s.last_accessed DESC
            """

            if limit:
                cypher += f" LIMIT {limit}"

            result = self.connection.execute(cypher)

            sessions = []
            while result.has_next():
                row = result.get_next()
                session_node = row[0]
                memory_count = row[1]
                agent_ids = row[2] if row[2] else []

                sessions.append(
                    SessionInfo(
                        session_id=session_node["session_id"],
                        created_at=session_node["created_at"],
                        last_accessed=session_node["last_accessed"],
                        agent_ids=agent_ids,
                        memory_count=memory_count,
                        metadata=json.loads(session_node["metadata"])
                        if session_node.get("metadata")
                        else {},
                    )
                )

            return sessions

        except Exception as e:
            logger.error(f"Error listing sessions from Kùzu: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with backend statistics

        Performance: <100ms (graph aggregations)
        """
        try:
            stats = {}

            # Total memories
            result = self.connection.execute("MATCH (m:Memory) RETURN COUNT(m) AS count")
            if result.has_next():
                stats["total_memories"] = result.get_next()[0]

            # Total sessions
            result = self.connection.execute("MATCH (s:Session) RETURN COUNT(s) AS count")
            if result.has_next():
                stats["total_sessions"] = result.get_next()[0]

            # Memory types breakdown
            result = self.connection.execute(
                """
                MATCH (m:Memory)
                RETURN m.memory_type AS type, COUNT(m) AS count
            """
            )
            memory_types = {}
            while result.has_next():
                row = result.get_next()
                memory_types[row[0]] = row[1]
            stats["memory_types"] = memory_types

            # Top agents
            result = self.connection.execute(
                """
                MATCH (a:Agent)-[:CREATED]->(m:Memory)
                RETURN a.agent_id AS agent, COUNT(m) AS count
                ORDER BY count DESC
                LIMIT 10
            """
            )
            top_agents = {}
            while result.has_next():
                row = result.get_next()
                top_agents[row[0]] = row[1]
            stats["top_agents"] = top_agents

            # Approximate database size
            import os

            db_size = 0
            for root, dirs, files in os.walk(self.db_path):
                for file in files:
                    db_size += os.path.getsize(os.path.join(root, file))
            stats["db_size_bytes"] = db_size

            return stats

        except Exception as e:
            logger.error(f"Error getting stats from Kùzu: {e}")
            return {}

    def close(self) -> None:
        """Close Kùzu connection and cleanup resources.

        Idempotent - safe to call multiple times.
        """
        try:
            if hasattr(self, "connection"):
                del self.connection
            if hasattr(self, "database"):
                del self.database
        except Exception as e:
            logger.error(f"Error closing Kùzu connection: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        self.close()
        return False


__all__ = ["KuzuBackend"]
