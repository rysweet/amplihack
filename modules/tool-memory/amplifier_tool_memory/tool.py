"""
Memory Tool for Amplifier - Exposes memory operations as an Amplifier tool.
"""

import json
from pathlib import Path
from typing import Any

from .interface import AgentMemory, MemoryType


class MemoryTool:
    """Amplifier tool for agent memory operations.

    Provides a tool interface for storing, retrieving, and searching
    agent memories during sessions.
    """

    # Tool metadata
    name = "memory"
    description = """Store and retrieve persistent agent memories.

Operations:
- store: Store a memory with key, value, type, importance, and tags
- retrieve: Get a specific memory by key
- search: Search memories by type, importance, or tags
- list: List all memories for the current session
- delete: Remove a memory by key

Memory Types: conversation, decision, pattern, context, learning, artifact

Examples:
- {"operation": "store", "key": "design-choice", "value": "Using REST API",
   "type": "decision", "importance": 8}
- {"operation": "retrieve", "key": "design-choice"}
- {"operation": "search", "type": "decision", "min_importance": 7}
- {"operation": "list", "limit": 50}
- {"operation": "delete", "key": "old-memory"}
"""

    def __init__(
        self,
        agent_name: str = "amplifier",
        session_id: str | None = None,
        db_path: Path | None = None,
        enabled: bool = True,
    ) -> None:
        """Initialize memory tool.

        Args:
            agent_name: Name of the agent using memory
            session_id: Optional session ID
            db_path: Optional database path
            enabled: Whether memory is enabled
        """
        self.memory = AgentMemory(
            agent_name=agent_name,
            session_id=session_id,
            db_path=db_path,
            enabled=enabled,
        )

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute a memory operation.

        Args:
            input_data: Operation parameters with "operation" key

        Returns:
            Result dictionary with success status and data
        """
        operation = input_data.get("operation", "").lower()

        handlers = {
            "store": self._handle_store,
            "retrieve": self._handle_retrieve,
            "search": self._handle_search,
            "list": self._handle_list,
            "delete": self._handle_delete,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}. Valid: {list(handlers.keys())}",
            }

        try:
            return handler(input_data)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_store(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle store operation."""
        key = data.get("key")
        value = data.get("value")

        if not key:
            return {"success": False, "error": "Missing required field: key"}
        if value is None:
            return {"success": False, "error": "Missing required field: value"}

        # Convert value to string if needed
        if isinstance(value, dict):
            value = json.dumps(value)
        else:
            value = str(value)

        memory_type = MemoryType.CONTEXT
        type_str = data.get("type", data.get("memory_type", "context"))
        try:
            memory_type = MemoryType(type_str)
        except ValueError:
            pass  # Use default

        importance = data.get("importance", 5)
        tags = data.get("tags", [])

        success = self.memory.store(
            key=key,
            value=value,
            memory_type=memory_type,
            importance=importance,
            tags=tags if isinstance(tags, list) else [],
        )

        return {
            "success": success,
            "message": f"Memory stored: {key}" if success else "Failed to store memory",
        }

    def _handle_retrieve(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle retrieve operation."""
        key = data.get("key")
        if not key:
            return {"success": False, "error": "Missing required field: key"}

        entry = self.memory.retrieve(key)
        if entry:
            return {"success": True, "memory": entry.to_dict()}
        return {"success": False, "error": f"Memory not found: {key}"}

    def _handle_search(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle search operation."""
        memory_type = None
        type_str = data.get("type", data.get("memory_type"))
        if type_str:
            try:
                memory_type = MemoryType(type_str)
            except ValueError:
                pass

        min_importance = data.get("min_importance")
        tags = data.get("tags")
        limit = data.get("limit", 100)

        entries = self.memory.search(
            memory_type=memory_type,
            min_importance=min_importance,
            tags=tags if isinstance(tags, list) else None,
            limit=limit,
        )

        return {
            "success": True,
            "count": len(entries),
            "memories": [e.to_dict() for e in entries],
        }

    def _handle_list(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle list operation."""
        limit = data.get("limit", 100)
        entries = self.memory.list_all(limit=limit)

        return {
            "success": True,
            "count": len(entries),
            "memories": [e.to_dict() for e in entries],
        }

    def _handle_delete(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle delete operation."""
        key = data.get("key")
        if not key:
            return {"success": False, "error": "Missing required field: key"}

        success = self.memory.delete(key)
        return {
            "success": success,
            "message": f"Memory deleted: {key}" if success else "Failed to delete memory",
        }

    def close(self) -> None:
        """Close memory backend."""
        self.memory.close()


def create_tool(config: dict | None = None) -> MemoryTool:
    """Factory function to create a memory tool from config.

    Args:
        config: Optional configuration dict

    Returns:
        Configured MemoryTool instance
    """
    config = config or {}
    return MemoryTool(
        agent_name=config.get("agent_name", "amplifier"),
        session_id=config.get("session_id"),
        db_path=Path(config["db_path"]) if config.get("db_path") else None,
        enabled=config.get("enabled", True),
    )
