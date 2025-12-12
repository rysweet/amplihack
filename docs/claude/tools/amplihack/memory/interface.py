"""
Agent Memory Interface - Clean API for agent memory operations.
Follows the API designer agent specification for minimal, clear contracts.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .core import MemoryBackend


class AgentMemory:
    """
    Simple agent memory interface following bricks & studs philosophy.

    Provides persistent memory storage for agents with session management,
    optional activation, and performance guarantees.
    """

    def __init__(
        self,
        agent_name: str,
        session_id: Optional[str] = None,
        db_path: Optional[Path] = None,
        enabled: bool = True,
    ):
        """
        Initialize agent memory with session management.

        Args:
            agent_name: Name of the agent using memory
            session_id: Optional session ID (auto-generated if None)
            db_path: Optional database path (default: .claude/runtime/memory.db)
            enabled: Whether memory is enabled (default: True)

        Example:
            >>> memory = AgentMemory("my-agent")
            >>> memory.store("key", "value")
            True
            >>> memory.retrieve("key")
            'value'
        """
        self.agent_name = agent_name
        self.session_id = session_id or self._generate_session_id()
        self.enabled = enabled

        # Set default database path if not provided
        if db_path is None:
            db_path = Path(".claude/runtime/memory.db")

        # Initialize backend only if enabled
        if self.enabled:
            try:
                self.backend = MemoryBackend(db_path)
                # Ensure session exists
                self.backend.ensure_session(self.session_id, self.agent_name)
            except Exception as e:
                print(f"Warning: Memory backend failed to initialize: {e}")
                self.backend = None
        else:
            self.backend = None

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{self.agent_name}_{timestamp}_{unique_id}"

    def store(self, key: str, value: Union[str, dict], memory_type: str = "markdown") -> bool:
        """
        Store memory with key-value pair.

        Args:
            key: Memory key (cannot be empty)
            value: Memory value (string or dict)
            memory_type: Storage type ('markdown' or 'json')

        Returns:
            True if stored successfully, False otherwise

        Raises:
            ValueError: If key is empty or value is None

        Example:
            >>> memory.store("user-pref", "dark-mode")
            True
            >>> memory.store("config", {"theme": "dark"}, "json")
            True
        """
        if not key:
            raise ValueError("Key cannot be empty")
        if value is None:
            raise ValueError("Value cannot be None")

        # Always return True for consistency, even when disabled
        if not self.enabled or not self.backend:
            return True

        return self.backend.store(self.session_id, key, value, memory_type)

    def retrieve(self, key: str) -> Optional[Union[str, dict]]:
        """
        Retrieve memory by key.

        Args:
            key: Memory key to retrieve

        Returns:
            Memory value or None if not found/disabled

        Example:
            >>> memory.retrieve("user-pref")
            'dark-mode'
            >>> memory.retrieve("nonexistent")
            None
        """
        if not self.enabled or not self.backend:
            return None

        return self.backend.retrieve(self.session_id, key)

    def list_keys(self, pattern: Optional[str] = None) -> List[str]:
        """
        List available memory keys.

        Args:
            pattern: Optional pattern for filtering (uses SQL LIKE with * as wildcard)

        Returns:
            List of memory keys (empty if disabled)

        Example:
            >>> memory.list_keys()
            ['user-pref', 'config']
            >>> memory.list_keys("user-*")
            ['user-pref']
        """
        if not self.enabled or not self.backend:
            return []

        return self.backend.list_keys(self.session_id, pattern)

    def delete(self, key: str) -> bool:
        """
        Delete memory by key.

        Args:
            key: Memory key to delete

        Returns:
            True if deleted successfully, False otherwise

        Example:
            >>> memory.delete("old-key")
            True
        """
        if not self.enabled or not self.backend:
            return False

        return self.backend.delete(self.session_id, key)

    def clear_session(self) -> bool:
        """
        Clear all memories for current session.

        Returns:
            True if cleared successfully, False otherwise

        Example:
            >>> memory.clear_session()
            True
        """
        if not self.enabled or not self.backend:
            return False

        return self.backend.clear_session(self.session_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics for monitoring.

        Returns:
            Dictionary with memory statistics

        Example:
            >>> stats = memory.get_stats()
            >>> print(f"Keys: {stats['key_count']}")
        """
        if not self.enabled or not self.backend:
            return {
                "enabled": False,
                "session_id": self.session_id,
                "agent_name": self.agent_name,
                "key_count": 0,
            }

        keys = self.list_keys()
        return {
            "enabled": True,
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "key_count": len(keys),
            "keys": keys[:10],  # First 10 keys for preview
        }

    def close(self) -> None:
        """
        Close memory backend connection.

        Example:
            >>> memory.close()
        """
        if self.backend:
            self.backend.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.close()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"AgentMemory(agent='{self.agent_name}', session='{self.session_id}', enabled={self.enabled})"
