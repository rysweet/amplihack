"""High-level memory management interface for agents."""

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .database import MemoryDatabase
from .models import MemoryEntry, MemoryQuery, MemoryType


class MemoryManager:
    """High-level interface for agent memory operations.

    Provides simple store/retrieve operations with automatic session management,
    batch operations for efficiency, and memory lifecycle management.
    """

    def __init__(
        self, db_path: Optional[Union[str, Path]] = None, session_id: Optional[str] = None
    ):
        """Initialize memory manager.

        Args:
            db_path: Path to SQLite database file
            session_id: Session identifier. If None, generates a new session.
        """
        self.db = MemoryDatabase(db_path)
        self.session_id = session_id or self._generate_session_id()

    def store(
        self,
        agent_id: str,
        title: str,
        content: str,
        memory_type: Union[MemoryType, str] = MemoryType.CONTEXT,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[int] = None,
        expires_in: Optional[timedelta] = None,
        parent_id: Optional[str] = None,
    ) -> str:
        """Store a memory entry.

        Args:
            agent_id: Identifier of the agent storing the memory
            title: Brief title for the memory
            content: Main content of the memory
            memory_type: Type of memory (MemoryType enum or string)
            metadata: Additional structured data
            tags: List of tags for categorization
            importance: Importance score (1-10)
            expires_in: Time until memory expires
            parent_id: ID of parent memory for hierarchical organization

        Returns:
            Unique memory ID

        Raises:
            ValueError: If memory_type is invalid
        """
        # Convert string to enum if needed
        if isinstance(memory_type, str):
            try:
                memory_type = MemoryType(memory_type.lower())
            except ValueError:
                raise ValueError(f"Invalid memory type: {memory_type}")

        # Generate unique ID
        memory_id = str(uuid.uuid4())

        # Calculate expiration
        expires_at = None
        if expires_in:
            expires_at = datetime.now() + expires_in

        # Create memory entry
        memory = MemoryEntry(
            id=memory_id,
            session_id=self.session_id,
            agent_id=agent_id,
            memory_type=memory_type,
            title=title,
            content=content,
            metadata=metadata or {},
            tags=tags,
            importance=importance,
            created_at=datetime.now(),
            accessed_at=datetime.now(),
            expires_at=expires_at,
            parent_id=parent_id,
        )

        # Store in database
        if self.db.store_memory(memory):
            return memory_id
        raise RuntimeError(f"Failed to store memory: {title}")

    def retrieve(
        self,
        agent_id: Optional[str] = None,
        memory_type: Optional[Union[MemoryType, str]] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        min_importance: Optional[int] = None,
        limit: Optional[int] = None,
        include_other_agents: bool = False,
        include_expired: bool = False,
    ) -> List[MemoryEntry]:
        """Retrieve memories matching criteria.

        Args:
            agent_id: Filter by specific agent. If None, defaults to session scope.
            memory_type: Filter by memory type
            tags: Filter by tags (any match)
            search: Search in title and content
            min_importance: Minimum importance score
            limit: Maximum number of results
            include_other_agents: Include memories from other agents in session
            include_expired: Include expired memories

        Returns:
            List of matching memory entries
        """
        # Convert string to enum if needed
        if isinstance(memory_type, str):
            try:
                memory_type = MemoryType(memory_type.lower())
            except ValueError:
                raise ValueError(f"Invalid memory type: {memory_type}")

        # Build query
        query = MemoryQuery(
            session_id=self.session_id,
            agent_id=agent_id if not include_other_agents else None,
            memory_type=memory_type,
            tags=tags,
            content_search=search,
            min_importance=min_importance,
            limit=limit,
            include_expired=include_expired,
        )

        return self.db.retrieve_memories(query)

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory by ID.

        Args:
            memory_id: Unique memory identifier

        Returns:
            Memory entry if found and accessible
        """
        memory = self.db.get_memory_by_id(memory_id)

        # Check if memory belongs to current session
        if memory and memory.session_id != self.session_id:
            return None

        return memory

    def update(
        self,
        memory_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[int] = None,
    ) -> bool:
        """Update an existing memory.

        Args:
            memory_id: Memory to update
            title: New title
            content: New content
            metadata: New metadata (replaces existing)
            tags: New tags (replaces existing)
            importance: New importance score

        Returns:
            True if updated successfully
        """
        memory = self.get(memory_id)
        if not memory:
            return False

        # Update fields
        if title is not None:
            memory.title = title
        if content is not None:
            memory.content = content
        if metadata is not None:
            memory.metadata = metadata
        if tags is not None:
            memory.tags = tags
        if importance is not None:
            memory.importance = importance

        # Update access time
        memory.accessed_at = datetime.now()

        return self.db.store_memory(memory)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: Memory to delete

        Returns:
            True if deleted successfully
        """
        # Verify ownership before deletion
        memory = self.get(memory_id)
        if not memory:
            return False

        return self.db.delete_memory(memory_id)

    def store_batch(self, memories: List[Dict[str, Any]]) -> List[str]:
        """Store multiple memories efficiently.

        Args:
            memories: List of memory dictionaries with keys matching store() parameters

        Returns:
            List of memory IDs in same order as input

        Example:
            memories = [
                {
                    "agent_id": "architect",
                    "title": "System Design",
                    "content": "API architecture decisions...",
                    "memory_type": "decision",
                    "importance": 8
                },
                {
                    "agent_id": "architect",
                    "title": "Pattern Recognition",
                    "content": "Identified singleton pattern...",
                    "memory_type": "pattern",
                    "tags": ["design-patterns"]
                }
            ]
            ids = manager.store_batch(memories)
        """
        memory_ids = []

        for memory_data in memories:
            try:
                memory_id = self.store(**memory_data)
                memory_ids.append(memory_id)
            except Exception as e:
                print(f"Failed to store memory '{memory_data.get('title', 'Unknown')}': {e}")
                memory_ids.append(None)

        return memory_ids

    def search(
        self, query: str, agent_id: Optional[str] = None, limit: int = 10
    ) -> List[MemoryEntry]:
        """Simple full-text search across memories.

        Args:
            query: Search terms
            agent_id: Limit to specific agent
            limit: Maximum results

        Returns:
            List of matching memories
        """
        return self.retrieve(
            agent_id=agent_id,
            search=query,
            limit=limit,
        )

    def get_recent(self, agent_id: Optional[str] = None, limit: int = 10) -> List[MemoryEntry]:
        """Get most recently accessed memories.

        Args:
            agent_id: Limit to specific agent
            limit: Maximum results

        Returns:
            List of recent memories
        """
        return self.retrieve(agent_id=agent_id, limit=limit)

    def get_important(self, min_importance: int = 7, limit: int = 10) -> List[MemoryEntry]:
        """Get high-importance memories.

        Args:
            min_importance: Minimum importance score
            limit: Maximum results

        Returns:
            List of important memories
        """
        return self.retrieve(min_importance=min_importance, limit=limit)

    def cleanup_expired(self) -> int:
        """Remove expired memories.

        Returns:
            Number of memories removed
        """
        return self.db.cleanup_expired()

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session.

        Returns:
            Dictionary with session statistics
        """
        session_info = self.db.get_session_info(self.session_id)
        if not session_info:
            return {
                "session_id": self.session_id,
                "memory_count": 0,
                "agent_ids": [],
                "created_at": None,
                "last_accessed": None,
            }

        return {
            "session_id": session_info.session_id,
            "memory_count": session_info.memory_count,
            "agent_ids": session_info.agent_ids,
            "created_at": session_info.created_at,
            "last_accessed": session_info.last_accessed,
            "metadata": session_info.metadata,
        }

    def list_memory_types(self) -> List[str]:
        """Get list of available memory types.

        Returns:
            List of memory type names
        """
        return [t.value for t in MemoryType]

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with database statistics
        """
        return self.db.get_stats()

    @staticmethod
    def _generate_session_id() -> str:
        """Generate a unique session identifier."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"

    def __enter__(self) -> None:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with automatic cleanup."""
        # Optionally cleanup expired memories on exit
        self.cleanup_expired()
