"""
Workflow Tool for Amplifier.

Exposes workflow tracking and transcript management as an Amplifier tool.
"""

from pathlib import Path
from typing import Any

from .tracker import WorkflowTracker
from .transcript import TranscriptManager


class WorkflowTool:
    """Amplifier tool for workflow tracking and transcript management."""

    name = "workflow"
    description = """Workflow tracking and transcript management for Amplifier.

Operations:

Workflow Tracking:
- workflow_start: Start tracking a workflow
- workflow_step: Log a workflow step
- workflow_skip: Log a skipped step
- workflow_agent: Log an agent invocation
- workflow_violation: Log a workflow violation
- workflow_end: End workflow tracking
- workflow_stats: Get workflow statistics

Transcript Management:
- list_sessions: List available transcript sessions
- session_summary: Get summary of a session
- restore_context: Restore context from a session
- save_checkpoint: Create a checkpoint marker
- list_checkpoints: List checkpoints for a session

Examples:
- {"operation": "workflow_start", "name": "DEFAULT", "task": "Add auth feature"}
- {"operation": "workflow_step", "step": 1, "name": "Clarify Requirements",
   "agent": "prompt-writer"}
- {"operation": "workflow_skip", "step": 8, "name": "Local Testing",
   "reason": "Simple config change"}
- {"operation": "workflow_end", "success": true, "total_steps": 15, "skipped_steps": 1}
- {"operation": "list_sessions"}
- {"operation": "session_summary", "session_id": "20250101_120000"}
- {"operation": "save_checkpoint", "session_id": "20250101_120000", "name": "pre-refactor"}
"""

    def __init__(
        self,
        logs_dir: Path | None = None,
    ) -> None:
        """Initialize workflow tool.

        Args:
            logs_dir: Directory for logs and transcripts
        """
        self.tracker = WorkflowTracker(log_dir=logs_dir)
        self.transcript_manager = TranscriptManager(logs_dir=logs_dir)

    def execute(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute a workflow operation."""
        operation = input_data.get("operation", "").lower()

        handlers = {
            # Workflow tracking
            "workflow_start": self._handle_workflow_start,
            "workflow_step": self._handle_workflow_step,
            "workflow_skip": self._handle_workflow_skip,
            "workflow_agent": self._handle_workflow_agent,
            "workflow_violation": self._handle_workflow_violation,
            "workflow_end": self._handle_workflow_end,
            "workflow_stats": self._handle_workflow_stats,
            # Transcript management
            "list_sessions": self._handle_list_sessions,
            "session_summary": self._handle_session_summary,
            "restore_context": self._handle_restore_context,
            "save_checkpoint": self._handle_save_checkpoint,
            "list_checkpoints": self._handle_list_checkpoints,
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

    # Workflow tracking handlers

    def _handle_workflow_start(self, data: dict[str, Any]) -> dict[str, Any]:
        """Start tracking a workflow."""
        name = data.get("name", data.get("workflow_name", "DEFAULT"))
        task = data.get("task", data.get("task_description", ""))

        if not task:
            return {"success": False, "error": "Missing required field: task"}

        self.tracker.start_workflow(name, task)
        return {
            "success": True,
            "message": f"Started workflow: {name}",
            "task": task,
        }

    def _handle_workflow_step(self, data: dict[str, Any]) -> dict[str, Any]:
        """Log a workflow step."""
        step = data.get("step", data.get("step_number"))
        name = data.get("name", data.get("step_name", ""))

        if step is None:
            return {"success": False, "error": "Missing required field: step"}
        if not name:
            return {"success": False, "error": "Missing required field: name"}

        self.tracker.log_step(
            step_number=step,
            step_name=name,
            agent_used=data.get("agent", data.get("agent_used")),
            duration_ms=data.get("duration_ms"),
            details=data.get("details"),
        )
        return {"success": True, "message": f"Logged step {step}: {name}"}

    def _handle_workflow_skip(self, data: dict[str, Any]) -> dict[str, Any]:
        """Log a skipped step."""
        step = data.get("step", data.get("step_number"))
        name = data.get("name", data.get("step_name", ""))
        reason = data.get("reason", "")

        if step is None:
            return {"success": False, "error": "Missing required field: step"}
        if not name:
            return {"success": False, "error": "Missing required field: name"}
        if not reason:
            return {"success": False, "error": "Missing required field: reason"}

        self.tracker.log_skip(step, name, reason)
        return {"success": True, "message": f"Logged skip of step {step}: {name}"}

    def _handle_workflow_agent(self, data: dict[str, Any]) -> dict[str, Any]:
        """Log an agent invocation."""
        agent = data.get("agent", data.get("agent_name", ""))
        purpose = data.get("purpose", "")

        if not agent:
            return {"success": False, "error": "Missing required field: agent"}
        if not purpose:
            return {"success": False, "error": "Missing required field: purpose"}

        self.tracker.log_agent_invocation(
            agent_name=agent,
            purpose=purpose,
            step_number=data.get("step"),
        )
        return {"success": True, "message": f"Logged agent invocation: {agent}"}

    def _handle_workflow_violation(self, data: dict[str, Any]) -> dict[str, Any]:
        """Log a workflow violation."""
        violation_type = data.get("type", data.get("violation_type", ""))
        description = data.get("description", "")

        if not violation_type:
            return {"success": False, "error": "Missing required field: type"}
        if not description:
            return {"success": False, "error": "Missing required field: description"}

        self.tracker.log_violation(
            violation_type=violation_type,
            description=description,
            step_number=data.get("step"),
        )
        return {"success": True, "message": f"Logged violation: {violation_type}"}

    def _handle_workflow_end(self, data: dict[str, Any]) -> dict[str, Any]:
        """End workflow tracking."""
        success = data.get("success", True)
        total_steps = data.get("total_steps", 0)
        skipped_steps = data.get("skipped_steps", 0)

        self.tracker.end_workflow(
            success=success,
            total_steps=total_steps,
            skipped_steps=skipped_steps,
            notes=data.get("notes"),
        )

        completion_rate = (
            round((total_steps - skipped_steps) / total_steps * 100, 1) if total_steps > 0 else 0
        )

        return {
            "success": True,
            "message": "Workflow ended",
            "workflow_success": success,
            "completion_rate": completion_rate,
        }

    def _handle_workflow_stats(self, data: dict[str, Any]) -> dict[str, Any]:
        """Get workflow statistics."""
        limit = data.get("limit", 100)
        stats = self.tracker.get_stats(limit)
        return {"success": True, **stats}

    # Transcript management handlers

    def _handle_list_sessions(self, data: dict[str, Any]) -> dict[str, Any]:
        """List available sessions."""
        sessions = self.transcript_manager.list_sessions()
        return {
            "success": True,
            "count": len(sessions),
            "sessions": sessions[:50],  # Limit for display
        }

    def _handle_session_summary(self, data: dict[str, Any]) -> dict[str, Any]:
        """Get session summary."""
        session_id = data.get("session_id")
        if not session_id:
            return {"success": False, "error": "Missing required field: session_id"}

        summary = self.transcript_manager.get_summary(session_id)
        return {"success": True, **summary.to_dict()}

    def _handle_restore_context(self, data: dict[str, Any]) -> dict[str, Any]:
        """Restore context from session."""
        session_id = data.get("session_id")
        if not session_id:
            return {"success": False, "error": "Missing required field: session_id"}

        context = self.transcript_manager.restore_context(session_id)
        return {"success": True, **context}

    def _handle_save_checkpoint(self, data: dict[str, Any]) -> dict[str, Any]:
        """Save a checkpoint."""
        session_id = data.get("session_id")
        name = data.get("name", data.get("checkpoint_name", ""))

        if not session_id:
            return {"success": False, "error": "Missing required field: session_id"}
        if not name:
            return {"success": False, "error": "Missing required field: name"}

        result = self.transcript_manager.save_checkpoint(
            session_id=session_id,
            checkpoint_name=name,
            data=data.get("data"),
        )
        return result

    def _handle_list_checkpoints(self, data: dict[str, Any]) -> dict[str, Any]:
        """List checkpoints for a session."""
        session_id = data.get("session_id")
        if not session_id:
            return {"success": False, "error": "Missing required field: session_id"}

        checkpoints = self.transcript_manager.list_checkpoints(session_id)
        return {
            "success": True,
            "count": len(checkpoints),
            "checkpoints": checkpoints,
        }


def create_tool(config: dict | None = None) -> WorkflowTool:
    """Factory function to create workflow tool."""
    config = config or {}
    return WorkflowTool(
        logs_dir=Path(config["logs_dir"]) if config.get("logs_dir") else None,
    )
