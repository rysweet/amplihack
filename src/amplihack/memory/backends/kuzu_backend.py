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
        """Initialize Kùzu schema with 5 memory node types.

        Creates node and relationship tables for the new schema:
        - 5 memory node types (Episodic, Semantic, Procedural, Prospective, Working)
        - Session and Agent nodes
        - 11 relationship types for memory interactions

        Idempotent - safe to call multiple times.
        """
        try:
            # Create Session node table (first-class citizen)
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS Session(
                    session_id STRING,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    user_id STRING,
                    context STRING,
                    status STRING,
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

            # Create EpisodicMemory node table (session-specific events)
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS EpisodicMemory(
                    memory_id STRING,
                    timestamp TIMESTAMP,
                    content STRING,
                    event_type STRING,
                    emotional_valence DOUBLE,
                    importance_score DOUBLE,
                    title STRING,
                    metadata STRING,
                    tags STRING,
                    created_at TIMESTAMP,
                    accessed_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    agent_id STRING,
                    PRIMARY KEY (memory_id)
                )
            """)

            # Create SemanticMemory node table (cross-session knowledge)
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS SemanticMemory(
                    memory_id STRING,
                    concept STRING,
                    content STRING,
                    category STRING,
                    confidence_score DOUBLE,
                    last_updated TIMESTAMP,
                    version INT64,
                    title STRING,
                    metadata STRING,
                    tags STRING,
                    created_at TIMESTAMP,
                    accessed_at TIMESTAMP,
                    agent_id STRING,
                    PRIMARY KEY (memory_id)
                )
            """)

            # Create ProceduralMemory node table (how-to knowledge)
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS ProceduralMemory(
                    memory_id STRING,
                    procedure_name STRING,
                    description STRING,
                    steps STRING,
                    preconditions STRING,
                    postconditions STRING,
                    success_rate DOUBLE,
                    usage_count INT64,
                    last_used TIMESTAMP,
                    title STRING,
                    content STRING,
                    metadata STRING,
                    tags STRING,
                    created_at TIMESTAMP,
                    accessed_at TIMESTAMP,
                    agent_id STRING,
                    PRIMARY KEY (memory_id)
                )
            """)

            # Create ProspectiveMemory node table (future intentions)
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS ProspectiveMemory(
                    memory_id STRING,
                    intention STRING,
                    trigger_condition STRING,
                    priority STRING,
                    due_date TIMESTAMP,
                    status STRING,
                    scope STRING,
                    completion_criteria STRING,
                    title STRING,
                    content STRING,
                    metadata STRING,
                    tags STRING,
                    created_at TIMESTAMP,
                    accessed_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    agent_id STRING,
                    PRIMARY KEY (memory_id)
                )
            """)

            # Create WorkingMemory node table (active task state)
            self.connection.execute("""
                CREATE NODE TABLE IF NOT EXISTS WorkingMemory(
                    memory_id STRING,
                    content STRING,
                    memory_type STRING,
                    priority INT64,
                    created_at TIMESTAMP,
                    ttl_seconds INT64,
                    title STRING,
                    metadata STRING,
                    tags STRING,
                    accessed_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    agent_id STRING,
                    PRIMARY KEY (memory_id)
                )
            """)

            # Create Session → Memory relationship tables
            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS CONTAINS_EPISODIC(
                    FROM Session TO EpisodicMemory,
                    sequence_number INT64
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS CONTAINS_WORKING(
                    FROM Session TO WorkingMemory,
                    activation_level DOUBLE
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS CONTRIBUTES_TO_SEMANTIC(
                    FROM Session TO SemanticMemory,
                    contribution_type STRING,
                    timestamp TIMESTAMP,
                    delta STRING
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS USES_PROCEDURE(
                    FROM Session TO ProceduralMemory,
                    timestamp TIMESTAMP,
                    success BOOL,
                    notes STRING
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS CREATES_INTENTION(
                    FROM Session TO ProspectiveMemory,
                    timestamp TIMESTAMP
                )
            """)

            # Create cross-memory relationship tables
            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS DERIVES_FROM(
                    FROM SemanticMemory TO EpisodicMemory,
                    extraction_method STRING,
                    confidence DOUBLE
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS REFERENCES(
                    FROM ProceduralMemory TO SemanticMemory,
                    reference_type STRING,
                    context STRING
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS TRIGGERS(
                    FROM ProspectiveMemory TO WorkingMemory,
                    trigger_time TIMESTAMP,
                    condition_met BOOL
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS ACTIVATES(
                    FROM WorkingMemory TO SemanticMemory,
                    activation_strength DOUBLE,
                    timestamp TIMESTAMP
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS RECALLS(
                    FROM EpisodicMemory TO EpisodicMemory,
                    similarity_score DOUBLE,
                    recall_reason STRING
                )
            """)

            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS BUILDS_ON(
                    FROM ProceduralMemory TO ProceduralMemory,
                    relationship_type STRING
                )
            """)

            # Keep Agent relationships
            self.connection.execute("""
                CREATE REL TABLE IF NOT EXISTS CREATED(
                    FROM Agent TO EpisodicMemory,
                    created_at TIMESTAMP
                )
            """)

            logger.info("Kùzu schema initialized successfully with 5 memory node types")

        except Exception as e:
            logger.error(f"Error initializing Kùzu schema: {e}")
            raise

    def store_memory(self, memory: MemoryEntry) -> bool:
        """Store a memory entry in appropriate node type based on memory_type.

        Routes to one of 5 node types:
        - EPISODIC → EpisodicMemory (session-specific events)
        - SEMANTIC → SemanticMemory (cross-session knowledge)
        - PROCEDURAL → ProceduralMemory (how-to knowledge)
        - PROSPECTIVE → ProspectiveMemory (future intentions)
        - WORKING → WorkingMemory (active task state)

        Creates appropriate relationships to Session and Agent.

        Args:
            memory: Memory entry to store

        Returns:
            True if successful, False otherwise

        Performance: <500ms (node + edge creation)
        """
        try:
            # Prepare common values
            tags_str = json.dumps(memory.tags) if memory.tags else ""
            importance_val = memory.importance if memory.importance is not None else 0
            now = datetime.now()

            # Route to appropriate node type based on memory_type
            if memory.memory_type == MemoryType.EPISODIC:
                # Create EpisodicMemory node
                self.connection.execute(
                    """
                    CREATE (m:EpisodicMemory {
                        memory_id: $memory_id,
                        timestamp: $timestamp,
                        content: $content,
                        event_type: $event_type,
                        emotional_valence: $emotional_valence,
                        importance_score: $importance_score,
                        title: $title,
                        metadata: $metadata,
                        tags: $tags,
                        created_at: $created_at,
                        accessed_at: $accessed_at,
                        expires_at: $expires_at,
                        agent_id: $agent_id
                    })
                """,
                    {
                        "memory_id": memory.id,
                        "timestamp": memory.created_at,
                        "content": memory.content,
                        "event_type": memory.metadata.get("event_type", "general"),
                        "emotional_valence": memory.metadata.get("emotional_valence", 0.0),
                        "importance_score": float(importance_val),
                        "title": memory.title,
                        "metadata": json.dumps(memory.metadata),
                        "tags": tags_str,
                        "created_at": memory.created_at,
                        "accessed_at": memory.accessed_at,
                        "expires_at": memory.expires_at,
                        "agent_id": memory.agent_id,
                    },
                )

                # Create CONTAINS_EPISODIC relationship
                self._create_session_node(memory.session_id, now)
                self.connection.execute(
                    """
                    MATCH (s:Session {session_id: $session_id}), (m:EpisodicMemory {memory_id: $memory_id})
                    CREATE (s)-[:CONTAINS_EPISODIC {sequence_number: $sequence_number}]->(m)
                """,
                    {
                        "session_id": memory.session_id,
                        "memory_id": memory.id,
                        "sequence_number": 0,  # TODO: track sequence
                    },
                )

            elif memory.memory_type == MemoryType.SEMANTIC:
                # Create SemanticMemory node
                self.connection.execute(
                    """
                    CREATE (m:SemanticMemory {
                        memory_id: $memory_id,
                        concept: $concept,
                        content: $content,
                        category: $category,
                        confidence_score: $confidence_score,
                        last_updated: $last_updated,
                        version: $version,
                        title: $title,
                        metadata: $metadata,
                        tags: $tags,
                        created_at: $created_at,
                        accessed_at: $accessed_at,
                        agent_id: $agent_id
                    })
                """,
                    {
                        "memory_id": memory.id,
                        "concept": memory.title,  # Use title as concept
                        "content": memory.content,
                        "category": memory.metadata.get("category", "general"),
                        "confidence_score": memory.metadata.get("confidence_score", 1.0),
                        "last_updated": memory.created_at,
                        "version": memory.metadata.get("version", 1),
                        "title": memory.title,
                        "metadata": json.dumps(memory.metadata),
                        "tags": tags_str,
                        "created_at": memory.created_at,
                        "accessed_at": memory.accessed_at,
                        "agent_id": memory.agent_id,
                    },
                )

                # Create CONTRIBUTES_TO_SEMANTIC relationship
                self._create_session_node(memory.session_id, now)
                self.connection.execute(
                    """
                    MATCH (s:Session {session_id: $session_id}), (m:SemanticMemory {memory_id: $memory_id})
                    CREATE (s)-[:CONTRIBUTES_TO_SEMANTIC {
                        contribution_type: $contribution_type,
                        timestamp: $timestamp,
                        delta: $delta
                    }]->(m)
                """,
                    {
                        "session_id": memory.session_id,
                        "memory_id": memory.id,
                        "contribution_type": "created",
                        "timestamp": now,
                        "delta": "initial_creation",
                    },
                )

            elif memory.memory_type == MemoryType.PROCEDURAL:
                # Create ProceduralMemory node
                self.connection.execute(
                    """
                    CREATE (m:ProceduralMemory {
                        memory_id: $memory_id,
                        procedure_name: $procedure_name,
                        description: $description,
                        steps: $steps,
                        preconditions: $preconditions,
                        postconditions: $postconditions,
                        success_rate: $success_rate,
                        usage_count: $usage_count,
                        last_used: $last_used,
                        title: $title,
                        content: $content,
                        metadata: $metadata,
                        tags: $tags,
                        created_at: $created_at,
                        accessed_at: $accessed_at,
                        agent_id: $agent_id
                    })
                """,
                    {
                        "memory_id": memory.id,
                        "procedure_name": memory.title,
                        "description": memory.content,
                        "steps": json.dumps(memory.metadata.get("steps", [])),
                        "preconditions": json.dumps(memory.metadata.get("preconditions", [])),
                        "postconditions": json.dumps(memory.metadata.get("postconditions", [])),
                        "success_rate": memory.metadata.get("success_rate", 1.0),
                        "usage_count": memory.metadata.get("usage_count", 0),
                        "last_used": memory.created_at,
                        "title": memory.title,
                        "content": memory.content,
                        "metadata": json.dumps(memory.metadata),
                        "tags": tags_str,
                        "created_at": memory.created_at,
                        "accessed_at": memory.accessed_at,
                        "agent_id": memory.agent_id,
                    },
                )

                # Create USES_PROCEDURE relationship
                self._create_session_node(memory.session_id, now)
                self.connection.execute(
                    """
                    MATCH (s:Session {session_id: $session_id}), (m:ProceduralMemory {memory_id: $memory_id})
                    CREATE (s)-[:USES_PROCEDURE {
                        timestamp: $timestamp,
                        success: $success,
                        notes: $notes
                    }]->(m)
                """,
                    {
                        "session_id": memory.session_id,
                        "memory_id": memory.id,
                        "timestamp": now,
                        "success": True,
                        "notes": "",
                    },
                )

            elif memory.memory_type == MemoryType.PROSPECTIVE:
                # Create ProspectiveMemory node
                self.connection.execute(
                    """
                    CREATE (m:ProspectiveMemory {
                        memory_id: $memory_id,
                        intention: $intention,
                        trigger_condition: $trigger_condition,
                        priority: $priority,
                        due_date: $due_date,
                        status: $status,
                        scope: $scope,
                        completion_criteria: $completion_criteria,
                        title: $title,
                        content: $content,
                        metadata: $metadata,
                        tags: $tags,
                        created_at: $created_at,
                        accessed_at: $accessed_at,
                        expires_at: $expires_at,
                        agent_id: $agent_id
                    })
                """,
                    {
                        "memory_id": memory.id,
                        "intention": memory.content,
                        "trigger_condition": memory.metadata.get("trigger_condition", ""),
                        "priority": memory.metadata.get("priority", "medium"),
                        "due_date": memory.expires_at,
                        "status": memory.metadata.get("status", "pending"),
                        "scope": memory.metadata.get("scope", "session"),
                        "completion_criteria": memory.metadata.get("completion_criteria", ""),
                        "title": memory.title,
                        "content": memory.content,
                        "metadata": json.dumps(memory.metadata),
                        "tags": tags_str,
                        "created_at": memory.created_at,
                        "accessed_at": memory.accessed_at,
                        "expires_at": memory.expires_at,
                        "agent_id": memory.agent_id,
                    },
                )

                # Create CREATES_INTENTION relationship
                self._create_session_node(memory.session_id, now)
                self.connection.execute(
                    """
                    MATCH (s:Session {session_id: $session_id}), (m:ProspectiveMemory {memory_id: $memory_id})
                    CREATE (s)-[:CREATES_INTENTION {timestamp: $timestamp}]->(m)
                """,
                    {
                        "session_id": memory.session_id,
                        "memory_id": memory.id,
                        "timestamp": now,
                    },
                )

            elif memory.memory_type == MemoryType.WORKING:
                # Create WorkingMemory node
                self.connection.execute(
                    """
                    CREATE (m:WorkingMemory {
                        memory_id: $memory_id,
                        content: $content,
                        memory_type: $memory_type,
                        priority: $priority,
                        created_at: $created_at,
                        ttl_seconds: $ttl_seconds,
                        title: $title,
                        metadata: $metadata,
                        tags: $tags,
                        accessed_at: $accessed_at,
                        expires_at: $expires_at,
                        agent_id: $agent_id
                    })
                """,
                    {
                        "memory_id": memory.id,
                        "content": memory.content,
                        "memory_type": memory.metadata.get("memory_type", "goal"),
                        "priority": memory.metadata.get("priority", 0),
                        "created_at": memory.created_at,
                        "ttl_seconds": memory.metadata.get("ttl_seconds", 3600),
                        "title": memory.title,
                        "metadata": json.dumps(memory.metadata),
                        "tags": tags_str,
                        "accessed_at": memory.accessed_at,
                        "expires_at": memory.expires_at,
                        "agent_id": memory.agent_id,
                    },
                )

                # Create CONTAINS_WORKING relationship
                self._create_session_node(memory.session_id, now)
                self.connection.execute(
                    """
                    MATCH (s:Session {session_id: $session_id}), (m:WorkingMemory {memory_id: $memory_id})
                    CREATE (s)-[:CONTAINS_WORKING {activation_level: $activation_level}]->(m)
                """,
                    {
                        "session_id": memory.session_id,
                        "memory_id": memory.id,
                        "activation_level": 1.0,
                    },
                )

            # Create Agent node if not exists
            self._create_agent_node(memory.agent_id, now)

            return True

        except Exception as e:
            logger.error(f"Error storing memory in Kùzu: {e}", exc_info=True)
            return False

    def _create_session_node(self, session_id: str, timestamp: datetime) -> None:
        """Create or update Session node."""
        self.connection.execute(
            """
            MERGE (s:Session {session_id: $session_id})
            ON CREATE SET
                s.start_time = $start_time,
                s.created_at = $created_at,
                s.last_accessed = $last_accessed,
                s.status = $status,
                s.metadata = $metadata
            ON MATCH SET
                s.last_accessed = $last_accessed
        """,
            {
                "session_id": session_id,
                "start_time": timestamp,
                "created_at": timestamp,
                "last_accessed": timestamp,
                "status": "active",
                "metadata": "{}",
            },
        )

    def _create_agent_node(self, agent_id: str, timestamp: datetime) -> None:
        """Create or update Agent node."""
        self.connection.execute(
            """
            MERGE (a:Agent {agent_id: $agent_id})
            ON CREATE SET
                a.name = $name,
                a.first_used = $first_used,
                a.last_used = $last_used
            ON MATCH SET
                a.last_used = $last_used
        """,
            {
                "agent_id": agent_id,
                "name": agent_id,
                "first_used": timestamp,
                "last_used": timestamp,
            },
        )

    def retrieve_memories(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Retrieve memories matching the query.

        Uses Cypher queries fer graph traversal across all 5 memory node types.

        Args:
            query: Query parameters

        Returns:
            List of matching memory entries

        Performance: <50ms (indexed lookups)
        """
        try:
            memories = []

            # If memory_type specified, query only that node type
            if query.memory_type:
                node_label = self._get_node_label_for_type(query.memory_type)
                memories = self._query_memories_by_type(query, node_label)
            else:
                # Query all 5 node types and combine results
                for memory_type in [
                    MemoryType.EPISODIC,
                    MemoryType.SEMANTIC,
                    MemoryType.PROCEDURAL,
                    MemoryType.PROSPECTIVE,
                    MemoryType.WORKING,
                ]:
                    node_label = self._get_node_label_for_type(memory_type)
                    type_memories = self._query_memories_by_type(query, node_label)
                    memories.extend(type_memories)

                # Sort combined results
                memories.sort(key=lambda m: (m.accessed_at, m.importance or 0), reverse=True)

                # Apply limit/offset after combining
                if query.offset:
                    memories = memories[query.offset :]
                if query.limit:
                    memories = memories[: query.limit]

            return memories

        except Exception as e:
            logger.error(f"Error retrieving memories from Kùzu: {e}")
            return []

    def _get_node_label_for_type(self, memory_type: MemoryType) -> str:
        """Map MemoryType to node label."""
        type_to_label = {
            MemoryType.EPISODIC: "EpisodicMemory",
            MemoryType.SEMANTIC: "SemanticMemory",
            MemoryType.PROCEDURAL: "ProceduralMemory",
            MemoryType.PROSPECTIVE: "ProspectiveMemory",
            MemoryType.WORKING: "WorkingMemory",
        }
        return type_to_label.get(memory_type, "Memory")  # Fallback to legacy

    def _query_memories_by_type(self, query: MemoryQuery, node_label: str) -> list[MemoryEntry]:
        """Query memories from a specific node type."""
        # Build WHERE conditions
        where_conditions = []
        params = {}

        if query.agent_id:
            where_conditions.append("m.agent_id = $agent_id")
            params["agent_id"] = query.agent_id

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
            MATCH (m:{node_label})
            WHERE {where_clause}
            RETURN m
            ORDER BY m.accessed_at DESC
        """

        # Only apply limit/offset if querying single type
        if query.memory_type and query.limit:
            cypher += " LIMIT $limit"
            params["limit"] = query.limit
            if query.offset:
                cypher += " SKIP $offset"
                params["offset"] = query.offset

        # Execute query
        result = self.connection.execute(cypher, params)

        # Convert to MemoryEntry objects
        memories = []
        while result.has_next():
            row = result.get_next()
            memory_node = row[0]

            # Determine memory type from node label
            memory_type = self._get_memory_type_from_label(node_label)

            # Parse node properties
            memory = MemoryEntry(
                id=memory_node["memory_id"],
                session_id=memory_node.get("session_id", "unknown"),
                agent_id=memory_node["agent_id"],
                memory_type=memory_type,
                title=memory_node["title"],
                content=memory_node["content"],
                metadata=json.loads(memory_node["metadata"]) if memory_node.get("metadata") else {},
                tags=json.loads(memory_node["tags"]) if memory_node.get("tags") else None,
                importance=memory_node.get("importance"),
                created_at=memory_node["created_at"],
                accessed_at=memory_node["accessed_at"],
                expires_at=memory_node.get("expires_at"),
                parent_id=memory_node.get("parent_id"),
            )
            memories.append(memory)

        # Update access times for retrieved memories
        now = datetime.now()
        for memory in memories:
            try:
                self.connection.execute(
                    f"""
                    MATCH (m:{node_label} {{memory_id: $memory_id}})
                    SET m.accessed_at = $now
                """,
                    {"memory_id": memory.id, "now": now},
                )
            except Exception as e:
                logger.warning(f"Could not update access time for {memory.id}: {e}")

        return memories

    def _get_memory_type_from_label(self, node_label: str) -> MemoryType:
        """Map node label back to MemoryType."""
        label_to_type = {
            "EpisodicMemory": MemoryType.EPISODIC,
            "SemanticMemory": MemoryType.SEMANTIC,
            "ProceduralMemory": MemoryType.PROCEDURAL,
            "ProspectiveMemory": MemoryType.PROSPECTIVE,
            "WorkingMemory": MemoryType.WORKING,
        }
        return label_to_type.get(node_label, MemoryType.EPISODIC)  # Default fallback

    def get_memory_by_id(self, memory_id: str) -> MemoryEntry | None:
        """Get a specific memory by ID.

        Searches across all 5 node types to find the memory.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory entry if found, None otherwise

        Performance: <50ms (primary key lookup)
        """
        try:
            # Try each node type until we find the memory
            for memory_type in [
                MemoryType.EPISODIC,
                MemoryType.SEMANTIC,
                MemoryType.PROCEDURAL,
                MemoryType.PROSPECTIVE,
                MemoryType.WORKING,
            ]:
                node_label = self._get_node_label_for_type(memory_type)

                result = self.connection.execute(
                    f"""
                    MATCH (m:{node_label} {{memory_id: $memory_id}})
                    RETURN m
                """,
                    {"memory_id": memory_id},
                )

                if result.has_next():
                    row = result.get_next()
                    memory_node = row[0]

                    # Update access time
                    now = datetime.now()
                    self.connection.execute(
                        f"""
                        MATCH (m:{node_label} {{memory_id: $memory_id}})
                        SET m.accessed_at = $now
                    """,
                        {"memory_id": memory_id, "now": now},
                    )

                    # Parse to MemoryEntry
                    return MemoryEntry(
                        id=memory_node["memory_id"],
                        session_id=memory_node.get("session_id", "unknown"),
                        agent_id=memory_node["agent_id"],
                        memory_type=memory_type,
                        title=memory_node["title"],
                        content=memory_node["content"],
                        metadata=json.loads(memory_node["metadata"])
                        if memory_node.get("metadata")
                        else {},
                        tags=json.loads(memory_node["tags"]) if memory_node.get("tags") else None,
                        importance=memory_node.get("importance"),
                        created_at=memory_node["created_at"],
                        accessed_at=memory_node["accessed_at"],
                        expires_at=memory_node.get("expires_at"),
                        parent_id=memory_node.get("parent_id"),
                    )

            # Memory not found in any node type
            return None

        except Exception as e:
            logger.error(f"Error getting memory by ID from Kùzu: {e}")
            return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory entry and its relationships.

        Searches across all 5 node types to find and delete the memory.

        Args:
            memory_id: Unique memory identifier

        Returns:
            True if deleted, False otherwise

        Performance: <100ms (node + edge deletion)
        """
        try:
            # Try to delete from each node type
            for memory_type in [
                MemoryType.EPISODIC,
                MemoryType.SEMANTIC,
                MemoryType.PROCEDURAL,
                MemoryType.PROSPECTIVE,
                MemoryType.WORKING,
            ]:
                node_label = self._get_node_label_for_type(memory_type)

                # Check if node exists in this type
                result = self.connection.execute(
                    f"""
                    MATCH (m:{node_label} {{memory_id: $memory_id}})
                    RETURN COUNT(m) AS count
                """,
                    {"memory_id": memory_id},
                )

                if result.has_next() and result.get_next()[0] > 0:
                    # Delete memory node and its relationships (DETACH DELETE removes edges first)
                    self.connection.execute(
                        f"""
                        MATCH (m:{node_label} {{memory_id: $memory_id}})
                        DETACH DELETE m
                    """,
                        {"memory_id": memory_id},
                    )
                    return True

            # Memory not found in any node type
            return False

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

            params = {}
            if limit:
                cypher += " LIMIT $limit"
                params["limit"] = limit

            result = self.connection.execute(cypher, params)

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

        Counts across all 5 memory node types.

        Returns:
            Dictionary with backend statistics

        Performance: <100ms (graph aggregations)
        """
        try:
            stats = {}

            # Count memories by type across all 5 node types
            memory_types = {}
            total_memories = 0

            for memory_type in [
                MemoryType.EPISODIC,
                MemoryType.SEMANTIC,
                MemoryType.PROCEDURAL,
                MemoryType.PROSPECTIVE,
                MemoryType.WORKING,
            ]:
                node_label = self._get_node_label_for_type(memory_type)

                result = self.connection.execute(f"MATCH (m:{node_label}) RETURN COUNT(m) AS count")

                if result.has_next():
                    count = result.get_next()[0]
                    memory_types[memory_type.value] = count
                    total_memories += count

            stats["total_memories"] = total_memories
            stats["memory_types"] = memory_types

            # Total sessions
            result = self.connection.execute("MATCH (s:Session) RETURN COUNT(s) AS count")
            if result.has_next():
                stats["total_sessions"] = result.get_next()[0]

            # Total agents
            result = self.connection.execute("MATCH (a:Agent) RETURN COUNT(a) AS count")
            if result.has_next():
                stats["total_agents"] = result.get_next()[0]

            # Top agents by memory count (across all types)
            top_agents = {}
            for memory_type in [
                MemoryType.EPISODIC,
                MemoryType.SEMANTIC,
                MemoryType.PROCEDURAL,
                MemoryType.PROSPECTIVE,
                MemoryType.WORKING,
            ]:
                node_label = self._get_node_label_for_type(memory_type)

                result = self.connection.execute(
                    f"""
                    MATCH (m:{node_label})
                    RETURN m.agent_id AS agent, COUNT(m) AS count
                """
                )

                while result.has_next():
                    row = result.get_next()
                    agent_id = row[0]
                    count = row[1]
                    top_agents[agent_id] = top_agents.get(agent_id, 0) + count

            # Sort and limit to top 10
            sorted_agents = sorted(top_agents.items(), key=lambda x: x[1], reverse=True)[:10]
            stats["top_agents"] = dict(sorted_agents)

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

    def _has_old_schema(self) -> bool:
        """Check if old Memory table exists in database.

        Returns:
            True if old schema exists, False otherwise
        """
        try:
            # Try to query old Memory table
            result = self.connection.execute(
                """
                MATCH (m:Memory)
                RETURN COUNT(m) AS count
                LIMIT 1
            """
            )
            # If query succeeds, old schema exists
            return result.has_next()
        except Exception:
            # If query fails, old schema doesn't exist
            return False

    def migrate_to_new_schema(self) -> bool:
        """Migrate data from old Memory table to new 5-node schema.

        This is a stub for future migration implementation.

        Returns:
            True if migration successful, False otherwise
        """
        try:
            if not self._has_old_schema():
                logger.info("No old schema detected, skipping migration")
                return True

            logger.warning("Migration from old schema not yet implemented")
            # TODO: Implement migration logic
            # 1. Query all nodes from old Memory table
            # 2. Route each to appropriate new node type based on memory_type
            # 3. Create proper relationships (Session, Agent)
            # 4. Verify data integrity
            # 5. Optionally remove old Memory table

            return False

        except Exception as e:
            logger.error(f"Error during schema migration: {e}")
            return False


__all__ = ["KuzuBackend"]
