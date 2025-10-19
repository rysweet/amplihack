"""
Beads Workflow Integration - Automatic Issue Tracking for Workflow Steps.

Integrates beads with DEFAULT_WORKFLOW.md to automatically:
- Create issues at workflow Step 2 (task breakdown)
- Track task progress through workflow steps
- Sync beads before pre-commit operations
- Restore session context on startup

Philosophy:
- Zero-BS: All operations work or return explicit errors
- Ruthless Simplicity: Direct workflow hooks, no complex state machines
- Graceful Degradation: Workflow continues even if beads unavailable
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

from .beads_provider import BeadsMemoryProvider
from .beads_sync import BeadsSync
from .beads_adapter import BeadsAdapter


# =============================================================================
# Result Type for Explicit Error Handling
# =============================================================================

class WorkflowError(Exception):
    """Workflow integration error."""
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
# BeadsWorkflowIntegration - Main Integration Class
# =============================================================================

class BeadsWorkflowIntegration:
    """
    Integrates beads with amplihack workflow execution.

    Provides automatic issue creation, progress tracking, and context
    restoration for workflow operations.

    Key Features:
    - Automatic issue creation at workflow Step 2
    - Progress tracking through workflow steps
    - Pre-commit sync coordination
    - Session context restoration

    Workflow Hooks:
    - on_workflow_step_2: Create issue for task tracking
    - on_pre_commit: Sync JSONL before git operations
    - on_session_start: Restore context from previous session
    - track_task_progress: Update issue status
    """

    def __init__(
        self,
        provider: Optional[BeadsMemoryProvider] = None,
        sync: Optional[BeadsSync] = None
    ):
        """
        Initialize workflow integration.

        Args:
            provider: BeadsMemoryProvider instance (creates default if None)
            sync: BeadsSync instance (creates default if None)
        """
        self.provider = provider or BeadsMemoryProvider(BeadsAdapter())
        self.sync = sync or BeadsSync()
        self._enabled = True
        self._beads_steps = [2]  # Default: only Step 2 creates issues
        self._issue_template = {}

    # =========================================================================
    # Workflow Step 2 Integration - Issue Creation
    # =========================================================================

    def on_workflow_step_2(
        self,
        task_description: str,
        description: str = "",
        agent: Optional[str] = None,
        session_id: Optional[str] = None,
        subtasks: Optional[List[str]] = None,
        task_type: Optional[str] = None,
        **kwargs
    ) -> Result:
        """
        Handle workflow Step 2: Create beads issue for task tracking.

        Args:
            task_description: Main task title
            description: Detailed task description
            agent: Agent responsible for task
            session_id: Current session ID
            subtasks: Optional list of subtasks
            task_type: Optional task type (bug, feature, etc.)
            **kwargs: Additional metadata

        Returns:
            Result with issue_id on success, error otherwise
        """
        # Check if beads integration enabled
        if not self._enabled:
            return Result.ok({"status": "disabled"})

        # Check if beads available
        if not self.provider.is_available():
            return Result.ok({"status": "unavailable"})

        try:
            # Build labels
            labels = ["workflow", "step-2"]
            if task_type:
                labels.append(task_type)
            if session_id:
                labels.append(f"session:{session_id}")

            # Build metadata
            metadata = {
                "workflow_step": 2,
                "created_by_workflow": True,
                "created_at": datetime.now().isoformat()
            }
            if session_id:
                metadata["session_id"] = session_id
            if agent:
                metadata["agent"] = agent

            # Apply custom template if set
            if self._issue_template:
                if "title_prefix" in self._issue_template:
                    task_description = f"{self._issue_template['title_prefix']} {task_description}"
                if "default_labels" in self._issue_template:
                    labels.extend(self._issue_template['default_labels'])
                if "metadata" in self._issue_template:
                    metadata.update(self._issue_template['metadata'])

            # Create issue with retry
            issue_id = self.provider.create_issue(
                title=task_description,
                description=description or task_description,
                labels=labels,
                assignee=agent,
                metadata=metadata,
                retry=True
            )

            # Create subtask issues if provided
            subtask_ids = []
            if subtasks:
                for subtask in subtasks:
                    subtask_id = self.provider.create_issue(
                        title=subtask,
                        description=f"Subtask of: {task_description}",
                        labels=labels + ["subtask"],
                        assignee=agent,
                        metadata={"parent_issue": issue_id}
                    )
                    subtask_ids.append(subtask_id)
                    # Link subtask to parent
                    self.provider.add_relationship(issue_id, subtask_id, "parent-child")

            return Result.ok({
                "status": "success",
                "beads_issue_id": issue_id,
                "subtask_ids": subtask_ids
            })

        except Exception as e:
            # Workflow should continue even on beads error
            return Result.ok({
                "status": "success",
                "beads_error": str(e)
            })

    # =========================================================================
    # Task Progress Tracking
    # =========================================================================

    def track_task_progress(
        self,
        task_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Result:
        """
        Update task progress in beads.

        Args:
            task_id: Issue ID to update
            status: New status (open, in_progress, blocked, completed)
            metadata: Optional progress metadata

        Returns:
            Result indicating success/failure
        """
        if not self._enabled or not self.provider.is_available():
            return Result.ok(False)

        try:
            update_kwargs = {"status": status}
            if metadata:
                update_kwargs["metadata"] = metadata

            success = self.provider.update_issue(task_id, **update_kwargs)
            return Result.ok(success)

        except Exception as e:
            return Result.err(WorkflowError(f"Failed to track progress: {e}"))

    # =========================================================================
    # Pre-Commit Hook
    # =========================================================================

    def on_pre_commit(self) -> Result:
        """
        Handle pre-commit: Sync beads JSONL before git operations.

        Returns:
            Result indicating sync success/failure
        """
        if not self._enabled or not self.provider.is_available():
            return Result.ok(True)

        try:
            # Ensure JSONL is current
            self.sync.sync_to_git()
            return Result.ok(True)

        except Exception as e:
            return Result.err(WorkflowError(f"Pre-commit sync failed: {e}"))

    # =========================================================================
    # Session Context Restoration
    # =========================================================================

    def on_session_start(
        self,
        session_id: str,
        agent: Optional[str] = None
    ) -> Result:
        """
        Restore session context on startup.

        Args:
            session_id: Session ID to restore
            agent: Optional agent filter

        Returns:
            Result with list of memory entries
        """
        if not self._enabled or not self.provider.is_available():
            return Result.ok([])

        try:
            # Query issues by session label
            labels = [f"session:{session_id}"]
            if agent:
                labels.append(f"agent:{agent}")

            issues = self.provider.get_ready_work(labels=labels)
            return Result.ok(issues)

        except Exception as e:
            return Result.err(WorkflowError(f"Session restore failed: {e}"))

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_beads_enabled(self, enabled: bool):
        """Enable/disable beads integration."""
        self._enabled = enabled

    def set_beads_steps(self, steps: List[int]):
        """Configure which workflow steps create beads issues."""
        self._beads_steps = steps

    def set_issue_template(self, template: Dict[str, Any]):
        """Set custom issue template for workflow tasks."""
        self._issue_template = template

    # =========================================================================
    # Additional Workflow Hooks
    # =========================================================================

    def link_github_issue(
        self,
        beads_issue_id: str,
        github_issue_number: int,
        github_repo: str
    ) -> Result:
        """
        Link beads issue to GitHub issue.

        Args:
            beads_issue_id: Beads issue ID
            github_issue_number: GitHub issue number
            github_repo: GitHub repository (owner/repo)

        Returns:
            Result indicating success/failure
        """
        if not self.provider.is_available():
            return Result.ok(False)

        try:
            metadata = {
                "github_issue": github_issue_number,
                "github_repo": github_repo
            }
            success = self.provider.update_issue(beads_issue_id, metadata=metadata)
            return Result.ok(success)

        except Exception as e:
            return Result.err(WorkflowError(f"Failed to link GitHub issue: {e}"))

    def setup_task_dependencies(
        self,
        parent_id: str,
        dependencies: List[tuple]
    ) -> Result:
        """
        Setup dependencies between subtasks.

        Args:
            parent_id: Parent issue ID
            dependencies: List of (from_id, to_id) tuples

        Returns:
            Result indicating success/failure
        """
        if not self.provider.is_available():
            return Result.ok(False)

        try:
            for from_id, to_id in dependencies:
                self.provider.add_relationship(from_id, to_id, "blocks")
            return Result.ok(True)

        except Exception as e:
            return Result.err(WorkflowError(f"Failed to setup dependencies: {e}"))

    def get_ready_subtasks(self, parent_id: str) -> List[Dict[str, Any]]:
        """
        Get subtasks ready to work on (no blockers).

        Args:
            parent_id: Parent issue ID

        Returns:
            List of ready subtask dicts
        """
        if not self.provider.is_available():
            return []

        try:
            # Get all subtasks
            relationships = self.provider.get_relationships(parent_id, "parent-child")
            subtask_ids = [r['target_id'] for r in relationships]

            # Filter for ready work
            ready_tasks = []
            for subtask_id in subtask_ids:
                issue = self.provider.get_issue(subtask_id)
                if issue and issue.get("status") == "open":
                    # Check if blocked
                    blockers = self.provider.get_relationships(subtask_id, "blocked_by")
                    if not blockers:
                        ready_tasks.append(issue)

            return ready_tasks

        except Exception:
            return []
