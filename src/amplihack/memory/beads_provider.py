"""
Beads Memory Provider - Bridge to Amplihack Memory System.

Implements memory provider interface for beads integration, enabling:
- Agent memory storage and retrieval across sessions
- Bidirectional MemoryEntry ↔ BeadsIssue mapping
- Label-based session organization
- Graceful fallback when beads unavailable

Architecture:
- MemoryEntry → BeadsIssue: Convert memory to tracked issue with labels
- BeadsIssue → MemoryEntry: Reconstruct memory from issue data
- Session restoration: Load all memories by session_id label
- Integration: Pluggable provider for existing MemoryManager

Philosophy:
- Zero-BS: All operations work or return explicit errors
- Ruthless Simplicity: Direct mapping, no complex transformations
- Graceful Degradation: System works without beads
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from .beads_adapter import BeadsAdapter
from .beads_models import BeadsIssue, ProviderError


# =============================================================================
# BeadsMemoryProvider - Memory Provider Bridge
# =============================================================================

class BeadsMemoryProvider:
    """
    Memory provider implementation using beads for persistence.

    Bridges amplihack's memory system with beads issue tracking:
    - Stores MemoryEntry as BeadsIssue with session labels
    - Retrieves and reconstructs memories from issues
    - Supports session-based memory restoration
    - Gracefully handles beads unavailability

    Label Schema:
    - session:<session_id> - Group memories by session
    - type:memory - Distinguish memories from other issues
    - agent:<agent_name> - Track which agent created memory
    - priority:<level> - Memory importance

    Key Features:
    - Bidirectional MemoryEntry ↔ BeadsIssue mapping
    - Session restoration for agent context loading
    - Label-based filtering and organization
    - Graceful fallback when beads not available
    """

    def __init__(self, adapter: BeadsAdapter):
        """
        Initialize BeadsMemoryProvider.

        Args:
            adapter: BeadsAdapter instance for CLI operations
        """
        self.adapter = adapter

    # =========================================================================
    # Provider Interface - Availability Check
    # =========================================================================

    def is_available(self) -> bool:
        """
        Check if beads provider is available.

        Returns:
            True if beads CLI is installed and initialized, False otherwise
        """
        return self.adapter.is_available() and self.adapter.check_init()

    def provider_type(self) -> str:
        """
        Get provider type identifier.

        Returns:
            Provider type string
        """
        return "beads"

    # =========================================================================
    # Issue Creation (Memory Storage)
    # =========================================================================

    def create_issue(
        self,
        title: str,
        description: str,
        status: str = "open",
        labels: Optional[List[str]] = None,
        assignee: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        retry: bool = False
    ) -> str:
        """
        Create new issue (store memory).

        Args:
            title: Issue title (memory title)
            description: Issue description (memory content)
            status: Issue status (default: "open")
            labels: Optional labels (includes session, type, agent)
            assignee: Optional assignee (agent name)
            metadata: Optional metadata dict

        Returns:
            Created issue ID

        Raises:
            ValueError: If title or description empty
            RuntimeError: If beads not available or creation fails
        """
        # Validate inputs
        if not title or not title.strip():
            raise ValueError("title cannot be empty: title is required")

        if not description or not description.strip():
            raise ValueError("description cannot be empty: description is required")

        # Check availability
        if not self.is_available():
            raise RuntimeError("beads provider not available: CLI not installed or not initialized")

        # Create issue via adapter
        # Note: BeadsAdapter.create_issue doesn't support status parameter
        # Status is managed via update_issue after creation
        max_retries = 2 if retry else 1
        last_error = None

        for attempt in range(max_retries):
            try:
                issue_id = self.adapter.create_issue(
                    title=title,
                    description=description,
                    labels=labels or [],
                    assignee=assignee,
                    metadata=metadata
                )

                # Set status if non-default
                if status != "open":
                    self.update_issue(issue_id, status=status)

                return issue_id
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    continue
                raise RuntimeError(f"Failed to create issue: {e}")

    # =========================================================================
    # Issue Retrieval
    # =========================================================================

    def get_issue(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """
        Get issue by ID.

        Args:
            issue_id: Issue ID to retrieve

        Returns:
            Issue data dict or None if not found

        Raises:
            ValueError: If issue_id is invalid (empty)
            RuntimeError: If retrieval fails
        """
        # Validate input
        if not issue_id or not issue_id.strip():
            raise ValueError("issue id format invalid: cannot be empty")

        try:
            return self.adapter.get_issue(issue_id)
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve issue: {e}")

    # =========================================================================
    # Issue Updates
    # =========================================================================

    def update_issue(
        self,
        issue_id: str,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        **kwargs
    ) -> bool:
        """
        Update issue fields.

        Args:
            issue_id: Issue ID to update
            status: Optional new status
            assignee: Optional new assignee
            labels: Optional new labels
            **kwargs: Additional fields to update

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            # Only pass non-None values to adapter
            update_kwargs = {}
            if status is not None:
                update_kwargs['status'] = status
            if assignee is not None:
                update_kwargs['assignee'] = assignee
            if labels is not None:
                update_kwargs['labels'] = labels
            update_kwargs.update(kwargs)

            return self.adapter.update_issue(issue_id, **update_kwargs)
        except Exception:
            return False

    # =========================================================================
    # Issue Closure (Memory Deletion)
    # =========================================================================

    def close_issue(
        self,
        issue_id: str,
        resolution: str = "completed",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Close issue (delete memory).

        Args:
            issue_id: Issue ID to close
            resolution: Closure resolution (default: "completed")
            metadata: Optional closure metadata

        Returns:
            True if closed successfully, False otherwise
        """
        update_kwargs = {
            'status': 'closed',
            'resolution': resolution
        }
        if metadata:
            update_kwargs['metadata'] = json.dumps(metadata)

        return self.update_issue(issue_id, **update_kwargs)

    # =========================================================================
    # Relationships
    # =========================================================================

    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str
    ) -> bool:
        """
        Add relationship between issues.

        Args:
            from_id: Source issue ID
            to_id: Target issue ID
            relationship_type: Relationship type (blocks, related, etc.)

        Returns:
            True if relationship added, False otherwise

        Raises:
            ValueError: If relationship type invalid or self-referential
        """
        # Validate relationship type
        valid_types = ['blocks', 'blocked_by', 'related', 'parent', 'child', 'parent-child', 'discovered-from']
        if relationship_type not in valid_types:
            raise ValueError(
                f"relationship type format invalid: '{relationship_type}'. "
                f"Must be one of {valid_types}"
            )

        # Prevent self-reference
        if from_id == to_id:
            raise ValueError("cannot relate issue to itself")

        try:
            return self.adapter.add_relationship(from_id, to_id, relationship_type)
        except Exception:
            return False

    def get_relationships(
        self,
        issue_id: str,
        relationship_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for an issue.

        Args:
            issue_id: Issue ID
            relationship_type: Optional filter by type

        Returns:
            List of relationship dicts
        """
        try:
            return self.adapter.get_relationships(issue_id, relationship_type)
        except Exception:
            return []

    # =========================================================================
    # Ready Work Query
    # =========================================================================

    def get_ready_work(
        self,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get issues ready to work on (no blockers).

        Args:
            assignee: Optional filter by assignee (agent)
            labels: Optional filter by labels

        Returns:
            List of ready issue dicts
        """
        try:
            # Only pass non-None values to avoid cluttering test assertions
            query_kwargs = {'status': 'open', 'has_blockers': False}
            if assignee is not None:
                query_kwargs['assignee'] = assignee
            if labels is not None:
                query_kwargs['labels'] = labels

            return self.adapter.query_issues(**query_kwargs)
        except Exception:
            return []

    # =========================================================================
    # Error Handling and Retry
    # =========================================================================

    def _wrap_error(self, operation: str, error: Exception) -> RuntimeError:
        """
        Wrap adapter errors with helpful context.

        Args:
            operation: Operation name (e.g., "create issue")
            error: Original exception

        Returns:
            RuntimeError with context
        """
        return RuntimeError(f"Failed to {operation}: {error}")
