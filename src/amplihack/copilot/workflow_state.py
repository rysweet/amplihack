"""Workflow state management for Copilot CLI.

Manages state persistence for workflow execution, enabling resume and
progress tracking across sessions.

Philosophy:
- Ruthless simplicity - JSON files, no database
- Zero-BS - file operations work or raise clear errors
- Regeneratable - state files are human-readable JSON
- Resilient - atomic writes, corruption detection

Public API (the "studs"):
    WorkflowState: State container
    WorkflowStateManager: State persistence operations
    TodoItem: Individual todo tracking
    Decision: Decision record
"""

import json
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal


StepStatus = Literal["pending", "in_progress", "completed"]


@dataclass
class TodoItem:
    """Individual todo item for step tracking.

    Attributes:
        step: Step number
        content: Todo description
        status: Current status
        timestamp: Last update timestamp
    """
    step: int
    content: str
    status: StepStatus
    timestamp: str


@dataclass
class Decision:
    """Decision record for architectural choices.

    Attributes:
        what: What was decided
        why: Reason for decision
        alternatives: Alternative approaches considered
        timestamp: When decision was made
    """
    what: str
    why: str
    alternatives: str
    timestamp: str


@dataclass
class WorkflowState:
    """Complete workflow state container.

    Attributes:
        session_id: Unique session identifier
        workflow: Workflow name (e.g., "DEFAULT_WORKFLOW")
        current_step: Current step number
        total_steps: Total number of steps
        todos: List of todo items
        decisions: List of decisions made
        context: Additional context (task description, etc.)
        state_path: Path to state file
    """
    session_id: str
    workflow: str
    current_step: int
    total_steps: int
    todos: List[TodoItem]
    decisions: List[Decision]
    context: Dict[str, Any]
    state_path: Path

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation

        Example:
            >>> state_dict = state.to_dict()
            >>> state_dict['session_id']
            '20240115-143052'
        """
        data = asdict(self)
        # Convert Path to string
        data['state_path'] = str(self.state_path)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], state_path: Path) -> 'WorkflowState':
        """Create WorkflowState from dictionary.

        Args:
            data: Dictionary with state data
            state_path: Path to state file

        Returns:
            WorkflowState instance

        Example:
            >>> state = WorkflowState.from_dict(data, Path("state.json"))
        """
        # Convert todos
        todos = [TodoItem(**todo) for todo in data.get('todos', [])]

        # Convert decisions
        decisions = [Decision(**dec) for dec in data.get('decisions', [])]

        return cls(
            session_id=data['session_id'],
            workflow=data['workflow'],
            current_step=data.get('current_step', 0),
            total_steps=data.get('total_steps', 0),
            todos=todos,
            decisions=decisions,
            context=data.get('context', {}),
            state_path=state_path,
        )


class WorkflowStateManager:
    """Manages workflow state persistence.

    Handles state file creation, loading, saving, and cleanup.
    Uses atomic writes to prevent corruption.

    Example:
        >>> manager = WorkflowStateManager()
        >>> state = manager.create_session("20240115-143052", "DEFAULT_WORKFLOW")
        >>> manager.save_state(state)
        >>> loaded = manager.load_state("20240115-143052")
    """

    def __init__(self, state_dir: Path = Path(".claude/runtime/copilot-state")):
        """Initialize state manager.

        Args:
            state_dir: Base directory for state files
        """
        self.state_dir = state_dir

    def create_session(
        self,
        session_id: str,
        workflow: str,
        task_description: str = "",
    ) -> WorkflowState:
        """Create new workflow session.

        Args:
            session_id: Unique session identifier
            workflow: Workflow name
            task_description: User's task description

        Returns:
            WorkflowState initialized for new session

        Example:
            >>> state = manager.create_session(
            ...     "20240115-143052",
            ...     "DEFAULT_WORKFLOW",
            ...     "Add authentication"
            ... )
        """
        # Create session directory
        session_dir = self.state_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        state_path = session_dir / "state.json"

        state = WorkflowState(
            session_id=session_id,
            workflow=workflow,
            current_step=0,
            total_steps=0,
            todos=[],
            decisions=[],
            context={
                "task_description": task_description,
                "created": datetime.now().isoformat(),
            },
            state_path=state_path,
        )

        self.save_state(state)
        return state

    def save_state(self, state: WorkflowState) -> None:
        """Save workflow state to file.

        Uses atomic write (write to temp, then rename) to prevent corruption.

        Args:
            state: WorkflowState to save

        Raises:
            IOError: If write fails
            PermissionError: If cannot write to directory

        Example:
            >>> manager.save_state(state)
        """
        state_path = state.state_path
        temp_path = state_path.with_suffix('.tmp')

        try:
            # Write to temporary file
            state_dict = state.to_dict()
            temp_path.write_text(
                json.dumps(state_dict, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )

            # Atomic rename
            temp_path.replace(state_path)

        except Exception as e:
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise IOError(f"Failed to save state: {str(e)}") from e

    def load_state(self, session_id: str) -> Optional[WorkflowState]:
        """Load workflow state from file.

        Args:
            session_id: Session identifier

        Returns:
            WorkflowState if found, None if not exists

        Raises:
            ValueError: If state file is corrupted

        Example:
            >>> state = manager.load_state("20240115-143052")
            >>> state.workflow
            'DEFAULT_WORKFLOW'
        """
        session_dir = self.state_dir / session_id
        state_path = session_dir / "state.json"

        if not state_path.exists():
            return None

        try:
            data = json.loads(state_path.read_text(encoding='utf-8'))
            return WorkflowState.from_dict(data, state_path)

        except json.JSONDecodeError as e:
            raise ValueError(
                f"Corrupted state file: {state_path}\n"
                f"Error: {str(e)}\n"
                f"Fix: Delete state file or restore from backup"
            ) from e

    def delete_session(self, session_id: str) -> bool:
        """Delete workflow session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found

        Example:
            >>> manager.delete_session("20240115-143052")
            True
        """
        session_dir = self.state_dir / session_id

        if not session_dir.exists():
            return False

        try:
            shutil.rmtree(session_dir)
            return True
        except Exception:
            return False

    def list_sessions(self) -> List[str]:
        """List all session IDs.

        Returns:
            List of session IDs sorted by creation time (newest first)

        Example:
            >>> sessions = manager.list_sessions()
            >>> sessions[0]
            '20240115-143052'
        """
        if not self.state_dir.exists():
            return []

        sessions = []
        for session_dir in self.state_dir.iterdir():
            if session_dir.is_dir() and (session_dir / "state.json").exists():
                sessions.append(session_dir.name)

        return sorted(sessions, reverse=True)

    def cleanup_old_sessions(self, keep_days: int = 7) -> int:
        """Clean up sessions older than keep_days.

        Args:
            keep_days: Number of days to keep sessions

        Returns:
            Number of sessions deleted

        Example:
            >>> deleted = manager.cleanup_old_sessions(keep_days=7)
            >>> print(f"Deleted {deleted} old sessions")
        """
        if not self.state_dir.exists():
            return 0

        cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
        deleted = 0

        for session_dir in self.state_dir.iterdir():
            if not session_dir.is_dir():
                continue

            state_file = session_dir / "state.json"
            if not state_file.exists():
                continue

            # Check file modification time
            if state_file.stat().st_mtime < cutoff_time:
                try:
                    shutil.rmtree(session_dir)
                    deleted += 1
                except Exception:
                    # Skip sessions that can't be deleted
                    continue

        return deleted

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of session without loading full state.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session summary, or None if not found

        Example:
            >>> summary = manager.get_session_summary("20240115-143052")
            >>> summary['workflow']
            'DEFAULT_WORKFLOW'
        """
        state = self.load_state(session_id)
        if not state:
            return None

        steps_completed = sum(1 for t in state.todos if t.status == "completed")

        return {
            "session_id": state.session_id,
            "workflow": state.workflow,
            "current_step": state.current_step,
            "total_steps": state.total_steps,
            "steps_completed": steps_completed,
            "progress_percent": (
                round(steps_completed / state.total_steps * 100, 1)
                if state.total_steps > 0 else 0
            ),
            "task_description": state.context.get("task_description", ""),
            "created": state.context.get("created", "unknown"),
            "last_updated": max(
                (t.timestamp for t in state.todos),
                default=state.context.get("created", "unknown")
            ),
        }


__all__ = [
    "WorkflowState",
    "WorkflowStateManager",
    "TodoItem",
    "Decision",
    "StepStatus",
]
