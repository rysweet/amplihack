"""Orchestrator brick for coordinating context management operations.

This module coordinates the token monitor, context extractor, and
context rehydrator components to handle skill actions.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from .context_extractor import ContextExtractor
from .context_rehydrator import ContextRehydrator
from .token_monitor import TokenMonitor


class ContextManagementOrchestrator:
    """Coordinates token monitoring, extraction, and rehydration.

    This brick serves as the main coordinator, delegating to specialized
    components based on the requested action.

    Attributes:
        monitor: TokenMonitor instance for usage tracking
        extractor: ContextExtractor instance for snapshot creation
        rehydrator: ContextRehydrator instance for context restoration
    """

    def __init__(self, snapshot_dir: Optional[Path] = None, max_tokens: int = 1_000_000):
        """Initialize orchestrator with component bricks.

        Args:
            snapshot_dir: Directory for snapshots (default: .claude/runtime/context-snapshots)
            max_tokens: Maximum context window size (default: 1,000,000)
        """
        self.monitor = TokenMonitor(max_tokens=max_tokens)
        self.extractor = ContextExtractor(snapshot_dir=snapshot_dir)
        self.rehydrator = ContextRehydrator(snapshot_dir=snapshot_dir)

    def handle_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """Handle skill action by coordinating components.

        Args:
            action: One of 'status', 'snapshot', 'rehydrate', 'list'
            **kwargs: Action-specific parameters

        Returns:
            Dict with action results

        Raises:
            ValueError: If action is invalid

        Example:
            >>> orch = ContextManagementOrchestrator()
            >>> result = orch.handle_action('status', current_tokens=500000)
            >>> result['status']
            'ok'
        """
        if action == "status":
            return self._handle_status(**kwargs)
        if action == "snapshot":
            return self._handle_snapshot(**kwargs)
        if action == "rehydrate":
            return self._handle_rehydrate(**kwargs)
        if action == "list":
            return self._handle_list(**kwargs)
        raise ValueError(
            f"Invalid action '{action}'. Must be one of: status, snapshot, rehydrate, list"
        )

    def _handle_status(self, current_tokens: int = 0, **kwargs) -> Dict[str, Any]:
        """Handle 'status' action - check token usage.

        Args:
            current_tokens: Current token count

        Returns:
            Dict with status and usage statistics
        """
        usage_stats = self.monitor.check_usage(current_tokens)

        return {"status": usage_stats.threshold_status, "usage": usage_stats.to_dict()}

    def _handle_snapshot(
        self, conversation_data: Any = None, name: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Handle 'snapshot' action - create context snapshot.

        Args:
            conversation_data: Conversation history (list of messages)
            name: Optional snapshot name

        Returns:
            Dict with snapshot creation results
        """
        if conversation_data is None:
            return {"status": "error", "error": "conversation_data is required for snapshot action"}

        # Extract context
        context = self.extractor.extract_from_conversation(conversation_data)

        # Create snapshot file
        snapshot_path = self.extractor.create_snapshot(context, name=name)

        # Load snapshot metadata for response
        import json

        with open(snapshot_path, encoding="utf-8") as f:
            snapshot_data = json.load(f)

        return {
            "status": "success",
            "snapshot": {
                "snapshot_id": snapshot_data["snapshot_id"],
                "name": snapshot_data.get("name"),
                "file_path": str(snapshot_path),
                "token_count": snapshot_data.get("token_count", 0),
                "components": ["requirements", "decisions", "state", "open_items", "tools_used"],
            },
            "recommendation": (
                "Snapshot created successfully. You can now continue working and "
                "use /transcripts or let Claude compact naturally. Use the rehydrate "
                "action to restore this context later."
            ),
        }

    def _handle_rehydrate(
        self, snapshot_id: str = None, level: str = "standard", **kwargs
    ) -> Dict[str, Any]:
        """Handle 'rehydrate' action - restore context from snapshot.

        Args:
            snapshot_id: Snapshot ID to restore
            level: Detail level ('essential', 'standard', 'comprehensive')

        Returns:
            Dict with rehydrated context
        """
        if not snapshot_id:
            return {"status": "error", "error": "snapshot_id is required for rehydrate action"}

        # Get snapshot path
        snapshot_path = self.rehydrator.get_snapshot_path(snapshot_id)
        if not snapshot_path:
            return {"status": "error", "error": f"Snapshot not found: {snapshot_id}"}

        try:
            # Rehydrate context
            context_text = self.rehydrator.rehydrate(snapshot_path, level=level)

            return {
                "status": "success",
                "context": context_text,
                "snapshot_id": snapshot_id,
                "level": level,
            }
        except Exception as e:
            return {"status": "error", "error": f"Failed to rehydrate snapshot: {e!s}"}

    def _handle_list(self, **kwargs) -> Dict[str, Any]:
        """Handle 'list' action - list all snapshots.

        Returns:
            Dict with list of available snapshots
        """
        snapshots = self.rehydrator.list_snapshots()

        total_size = sum(self._parse_size(s["size"]) for s in snapshots)

        return {
            "status": "success",
            "snapshots": snapshots,
            "count": len(snapshots),
            "total_size": self._format_size_bytes(total_size),
        }

    def _parse_size(self, size_str: str) -> int:
        """Parse size string back to bytes."""
        if size_str.endswith("B") and not size_str.endswith("KB") and not size_str.endswith("MB"):
            return int(size_str[:-1])
        if size_str.endswith("KB"):
            return int(float(size_str[:-2]) * 1024)
        if size_str.endswith("MB"):
            return int(float(size_str[:-2]) * 1024 * 1024)
        return 0

    def _format_size_bytes(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes}B"
        if size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f}KB"
        return f"{size_bytes / (1024 * 1024):.1f}MB"
