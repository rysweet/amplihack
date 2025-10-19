"""
Beads Agent Context - Context Restoration and Discovery Tracking.

Provides agent startup context restoration and tracks discoveries during implementation:
- Agent startup queries beads for workstream state
- Context restoration from issue history
- Dependency chain retrieval
- Discovery tracking ("discovered-from" relationships)

Philosophy:
- Zero-BS: Direct context retrieval, no complex state management
- Ruthless Simplicity: Straightforward query patterns
- Graceful Degradation: Returns empty context when unavailable
"""

from typing import Dict, List, Any, Optional

from .beads_provider import BeadsMemoryProvider
from .beads_adapter import BeadsAdapter


# =============================================================================
# Result Type for Explicit Error Handling
# =============================================================================

class ContextError(Exception):
    """Context restoration error."""
    pass


class Result:
    """Result wrapper for explicit error handling."""

    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.is_ok = error is None

    @staticmethod
    def ok(value):
        """Create successful result."""
        return Result(value=value)

    @staticmethod
    def err(error):
        """Create error result."""
        return Result(error=error)


# =============================================================================
# BeadsAgentContext - Context Management
# =============================================================================

class BeadsAgentContext:
    """
    Manages agent context restoration and discovery tracking.

    Provides agent startup queries, context restoration from issue history,
    dependency chain retrieval, and discovery tracking.

    Key Features:
    - Agent workstream state queries
    - Context restoration from issue metadata
    - Full dependency chain traversal
    - Discovery relationship tracking
    - Context caching for performance
    """

    def __init__(self, provider: Optional[BeadsMemoryProvider] = None):
        """
        Initialize agent context manager.

        Args:
            provider: BeadsMemoryProvider instance (creates default if None)
        """
        self.provider = provider or BeadsMemoryProvider(BeadsAdapter())
        self._context_cache: Dict[str, Dict[str, Any]] = {}

    # =========================================================================
    # Agent Context Restoration
    # =========================================================================

    def restore_context(
        self,
        agent_name: str,
        session_id: Optional[str] = None
    ) -> Result:
        """
        Restore agent context on startup.

        Args:
            agent_name: Agent identifier
            session_id: Optional session ID filter

        Returns:
            Result with context dict or error
        """
        # Check cache
        cache_key = f"{agent_name}:{session_id or 'all'}"
        if cache_key in self._context_cache:
            return Result.ok(self._context_cache[cache_key])

        if not self.provider.is_available():
            return Result.ok({
                "agent": agent_name,
                "available": False,
                "assigned_tasks": [],
                "ready_work": []
            })

        try:
            # Query ready work for agent
            ready_work = self.provider.get_ready_work(assignee=agent_name)

            # Get agent's assigned tasks
            labels = [f"agent:{agent_name}"]
            if session_id:
                labels.append(f"session:{session_id}")

            # Build context
            context = {
                "agent": agent_name,
                "available": True,
                "assigned_tasks": ready_work,
                "ready_work": ready_work,
                "session_id": session_id
            }

            # Cache context
            self._context_cache[cache_key] = context

            return Result.ok(context)

        except Exception as e:
            return Result.err(ContextError(f"Failed to restore context: {e}"))

    def restore_context_from_issue(self, issue_id: str) -> Result:
        """
        Restore context from specific issue.

        Args:
            issue_id: Issue ID to restore from

        Returns:
            Result with context dict extracted from issue
        """
        if not self.provider.is_available():
            return Result.ok({"available": False})

        try:
            issue = self.provider.get_issue(issue_id)
            if not issue:
                return Result.err(ContextError(f"Issue not found: {issue_id}"))

            # Extract context from issue
            metadata = issue.get("metadata", {})

            # Get related issues
            related = self.provider.get_relationships(issue_id, "related")
            related_issues = [r["target_id"] for r in related]

            context = {
                "current_task": issue.get("title", ""),
                "description": issue.get("description", ""),
                "status": issue.get("status", "unknown"),
                "decisions": metadata.get("decisions", []),
                "progress": metadata.get("progress", ""),
                "blockers": metadata.get("blockers", []),
                "related_issues": related_issues,
                "metadata": metadata
            }

            return Result.ok(context)

        except Exception as e:
            return Result.err(ContextError(f"Failed to restore from issue: {e}"))

    # =========================================================================
    # Dependency Chain Retrieval
    # =========================================================================

    def get_dependency_chain(
        self,
        issue_id: str,
        max_depth: int = 10
    ) -> Result:
        """
        Get full dependency chain for issue.

        Args:
            issue_id: Starting issue ID
            max_depth: Maximum traversal depth

        Returns:
            Result with list of issue IDs in dependency chain
        """
        if not self.provider.is_available():
            return Result.ok([])

        try:
            chain = []
            visited = set()

            def traverse(current_id: str, depth: int):
                if depth >= max_depth or current_id in visited:
                    return
                visited.add(current_id)

                # Get blocking relationships
                relationships = self.provider.get_relationships(current_id, "blocks")
                for rel in relationships:
                    target_id = rel.get("target_id")
                    if target_id and target_id not in visited:
                        chain.append(target_id)
                        traverse(target_id, depth + 1)

            traverse(issue_id, 0)
            return Result.ok(chain)

        except Exception as e:
            return Result.err(ContextError(f"Failed to get dependency chain: {e}"))

    # =========================================================================
    # Discovery Tracking
    # =========================================================================

    def track_discovery(
        self,
        discovered_from_id: str,
        discovered_id: str,
        reason: Optional[str] = None
    ) -> Result:
        """
        Track issue discovery relationship.

        Args:
            discovered_from_id: Original issue ID
            discovered_id: Newly discovered issue ID
            reason: Optional reason for discovery

        Returns:
            Result indicating success/failure
        """
        if not self.provider.is_available():
            return Result.ok(False)

        try:
            # Add discovered-from relationship
            success = self.provider.add_relationship(
                discovered_id,
                discovered_from_id,
                "discovered-from"
            )

            # Optionally add reason to metadata
            if reason and success:
                self.provider.update_issue(
                    discovered_id,
                    metadata={"discovered_reason": reason}
                )

            return Result.ok(success)

        except Exception as e:
            return Result.err(ContextError(f"Failed to track discovery: {e}"))

    # =========================================================================
    # Workstream State
    # =========================================================================

    def get_workstream_state(self, agent_name: str) -> Result:
        """
        Get agent's current workstream state.

        Args:
            agent_name: Agent identifier

        Returns:
            Result with workstream state dict
        """
        if not self.provider.is_available():
            return Result.ok({
                "agent": agent_name,
                "available": False,
                "active_issues": [],
                "blocked_issues": []
            })

        try:
            # Query all issues assigned to agent
            from .beads_adapter import BeadsAdapter
            adapter = self.provider.adapter

            # Get active issues (in_progress)
            active = adapter.query_issues(
                assignee=agent_name,
                status="in_progress"
            )

            # Get blocked issues
            blocked = adapter.query_issues(
                assignee=agent_name,
                status="blocked"
            )

            workstream = {
                "agent": agent_name,
                "available": True,
                "active_issues": active,
                "blocked_issues": blocked,
                "total_issues": len(active) + len(blocked)
            }

            return Result.ok(workstream)

        except Exception as e:
            return Result.err(ContextError(f"Failed to get workstream state: {e}"))

    def get_relevant_context(
        self,
        agent_name: str,
        current_task: str
    ) -> Result:
        """
        Get relevant context for agent's current task.

        Args:
            agent_name: Agent identifier
            current_task: Current task description

        Returns:
            Result with relevant context dict
        """
        if not self.provider.is_available():
            return Result.ok({})

        try:
            # Get agent's workstream
            workstream_result = self.get_workstream_state(agent_name)
            if not workstream_result.is_ok:
                return workstream_result

            workstream = workstream_result.value

            # Build relevant context
            context = {
                "agent": agent_name,
                "current_task": current_task,
                "active_issues": workstream.get("active_issues", []),
                "blocked_issues": workstream.get("blocked_issues", [])
            }

            return Result.ok(context)

        except Exception as e:
            return Result.err(ContextError(f"Failed to get relevant context: {e}"))

    # =========================================================================
    # Context Cache Management
    # =========================================================================

    def invalidate_cache(self, agent_name: Optional[str] = None):
        """
        Invalidate context cache.

        Args:
            agent_name: Optional agent to invalidate (all if None)
        """
        if agent_name:
            # Invalidate specific agent
            keys_to_remove = [k for k in self._context_cache if k.startswith(f"{agent_name}:")]
            for key in keys_to_remove:
                del self._context_cache[key]
        else:
            # Invalidate all
            self._context_cache.clear()
