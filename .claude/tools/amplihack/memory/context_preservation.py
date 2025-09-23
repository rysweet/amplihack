"""Context preservation utilities for Claude agent workflows.

This module provides specialized functions for preserving and restoring context
across agent workflows, session boundaries, and long-running operations.

The context preservation system is designed to:
- Maintain conversation context between sessions
- Preserve agent decision history
- Store workflow state and intermediate results
- Enable context-aware agent collaboration
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Clean import setup
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from paths import get_project_root

    project_root = get_project_root()
    sys.path.insert(0, str(project_root / "src"))
except ImportError:
    # Fallback for standalone execution
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root / "src"))

from amplihack.memory import MemoryManager, MemoryType


class ContextPreserver:
    """Manages context preservation for Claude agent workflows."""

    def __init__(self, session_id: Optional[str] = None):
        """Initialize context preserver.

        Args:
            session_id: Optional session identifier for context isolation
        """
        self.session_id = session_id
        try:
            self.memory = MemoryManager(session_id=session_id)
        except Exception:
            self.memory = None

    def preserve_conversation_context(
        self,
        agent_id: str,
        conversation_summary: str,
        key_decisions: List[str],
        active_tasks: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Preserve current conversation context.

        Stores a comprehensive snapshot of the current conversation state
        including decisions made, active tasks, and relevant context.

        Args:
            agent_id: Identifier of the preserving agent
            conversation_summary: Brief summary of conversation state
            key_decisions: List of important decisions made
            active_tasks: List of currently active tasks
            metadata: Additional context metadata

        Returns:
            Memory ID if successful, None if failed

        Example:
            preserver = ContextPreserver()
            memory_id = preserver.preserve_conversation_context(
                agent_id="orchestrator",
                conversation_summary="Working on API design for user authentication",
                key_decisions=["Using JWT tokens", "REST API pattern"],
                active_tasks=["Design user model", "Create auth endpoints"],
                metadata={"priority": "high", "deadline": "2025-09-30"}
            )
        """
        if not self.memory:
            return None

        context_data = {
            "conversation_summary": conversation_summary,
            "key_decisions": key_decisions,
            "active_tasks": active_tasks,
            "preserved_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        return self.memory.store(
            agent_id=agent_id,
            title=f"Conversation Context - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            content=json.dumps(context_data, indent=2),
            memory_type=MemoryType.CONTEXT,
            importance=8,
            tags=["conversation", "context", "preservation"],
            metadata={"context_type": "conversation", "agent_count": 1},
        )

    def preserve_workflow_state(
        self,
        workflow_name: str,
        current_step: str,
        completed_steps: List[str],
        pending_steps: List[str],
        step_results: Dict[str, Any],
        workflow_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Preserve workflow execution state.

        Stores the current state of a multi-step workflow including
        progress tracking and intermediate results.

        Args:
            workflow_name: Name of the workflow being preserved
            current_step: Currently executing step
            completed_steps: List of completed workflow steps
            pending_steps: List of remaining workflow steps
            step_results: Results from completed steps
            workflow_metadata: Additional workflow context

        Returns:
            Memory ID if successful, None if failed

        Example:
            memory_id = preserver.preserve_workflow_state(
                workflow_name="API_Development",
                current_step="implement_auth",
                completed_steps=["design_schema", "create_models"],
                pending_steps=["write_tests", "deploy"],
                step_results={"design_schema": {"tables": 5}, "create_models": {"files": 3}},
                workflow_metadata={"estimated_completion": "2h"}
            )
        """
        if not self.memory:
            return None

        workflow_state = {
            "workflow_name": workflow_name,
            "current_step": current_step,
            "completed_steps": completed_steps,
            "pending_steps": pending_steps,
            "step_results": step_results,
            "preserved_at": datetime.now().isoformat(),
            "progress_percentage": len(completed_steps)
            / (len(completed_steps) + len(pending_steps) + 1)
            * 100,
            "workflow_metadata": workflow_metadata or {},
        }

        return self.memory.store(
            agent_id="workflow_manager",
            title=f"Workflow State: {workflow_name}",
            content=json.dumps(workflow_state, indent=2),
            memory_type=MemoryType.CONTEXT,
            importance=9,
            tags=["workflow", "state", "preservation", workflow_name.lower()],
            metadata={"context_type": "workflow", "workflow_name": workflow_name},
        )

    def preserve_agent_decisions(
        self,
        agent_id: str,
        decision_title: str,
        decision_description: str,
        reasoning: str,
        alternatives_considered: List[str],
        impact_assessment: Optional[str] = None,
        related_decisions: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Preserve agent decision with full context.

        Stores a comprehensive record of an agent's decision including
        reasoning, alternatives, and impact assessment.

        Args:
            agent_id: Agent making the decision
            decision_title: Brief title of the decision
            decision_description: Detailed description of what was decided
            reasoning: Explanation of why this decision was made
            alternatives_considered: List of alternative approaches considered
            impact_assessment: Assessment of decision impact
            related_decisions: References to related decisions

        Returns:
            Memory ID if successful, None if failed

        Example:
            memory_id = preserver.preserve_agent_decisions(
                agent_id="architect",
                decision_title="Database Choice: PostgreSQL",
                decision_description="Selected PostgreSQL as the primary database",
                reasoning="Need ACID compliance and complex query support",
                alternatives_considered=["MongoDB", "SQLite", "MySQL"],
                impact_assessment="High impact on performance and scalability",
                related_decisions=["auth_strategy_decision"]
            )
        """
        if not self.memory:
            return None

        decision_record = {
            "decision_title": decision_title,
            "decision_description": decision_description,
            "reasoning": reasoning,
            "alternatives_considered": alternatives_considered,
            "impact_assessment": impact_assessment,
            "related_decisions": related_decisions or [],
            "decided_at": datetime.now().isoformat(),
            "agent_id": agent_id,
        }

        return self.memory.store(
            agent_id=agent_id,
            title=decision_title,
            content=json.dumps(decision_record, indent=2),
            memory_type=MemoryType.DECISION,
            importance=8,
            tags=["decision", "architecture", "reasoning"],
            metadata={"context_type": "decision", "decision_agent": agent_id},
        )

    def restore_conversation_context(
        self, agent_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Restore the most recent conversation context.

        Retrieves the latest conversation context for continued operation.

        Args:
            agent_id: Optional agent filter for context retrieval

        Returns:
            Dictionary with context data or None if not found

        Example:
            context = preserver.restore_conversation_context("orchestrator")
            if context:
                print(f"Active tasks: {context['active_tasks']}")
        """
        if not self.memory:
            return None

        contexts = self.memory.retrieve(
            agent_id=agent_id or "orchestrator",
            memory_type=MemoryType.CONTEXT,
            tags=["conversation", "context"],
            limit=1,
        )

        if contexts:
            try:
                return json.loads(contexts[0].content)
            except json.JSONDecodeError:
                return None

        return None

    def restore_workflow_state(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """Restore workflow execution state.

        Retrieves the latest state for a specific workflow.

        Args:
            workflow_name: Name of the workflow to restore

        Returns:
            Dictionary with workflow state or None if not found

        Example:
            state = preserver.restore_workflow_state("API_Development")
            if state:
                print(f"Current step: {state['current_step']}")
        """
        if not self.memory:
            return None

        workflows = self.memory.retrieve(
            agent_id="workflow_manager",
            memory_type=MemoryType.CONTEXT,
            tags=["workflow", workflow_name.lower()],
            limit=1,
        )

        if workflows:
            try:
                return json.loads(workflows[0].content)
            except json.JSONDecodeError:
                return None

        return None

    def get_decision_history(
        self, agent_id: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get agent decision history.

        Retrieves recent decisions made by agents for context awareness.

        Args:
            agent_id: Optional agent filter
            limit: Maximum number of decisions to retrieve

        Returns:
            List of decision records

        Example:
            decisions = preserver.get_decision_history("architect", limit=5)
            for decision in decisions:
                print(f"Decision: {decision['decision_title']}")
        """
        if not self.memory:
            return []

        decisions = self.memory.retrieve(
            agent_id=agent_id, memory_type=MemoryType.DECISION, limit=limit
        )

        decision_history = []
        for decision in decisions:
            try:
                decision_data = json.loads(decision.content)
                decision_history.append(decision_data)
            except json.JSONDecodeError:
                # Fallback to basic memory entry
                decision_history.append(
                    {
                        "decision_title": decision.title,
                        "decision_description": decision.content,
                        "decided_at": decision.created_at.isoformat(),
                        "agent_id": decision.agent_id,
                    }
                )

        return decision_history

    def cleanup_old_context(self, older_than_days: int = 7) -> int:
        """Clean up old context entries.

        Removes context memories older than specified days to prevent
        database growth and maintain performance.

        Args:
            older_than_days: Remove context older than this many days

        Returns:
            Number of cleaned up contexts

        Example:
            cleaned = preserver.cleanup_old_context(older_than_days=30)
            print(f"Cleaned up {cleaned} old context entries")
        """
        if not self.memory:
            return 0

        # This would require additional database methods for cleanup
        # For now, return 0 as placeholder
        return 0


# Convenience functions for common operations
def preserve_current_context(
    agent_id: str,
    summary: str,
    decisions: List[str],
    tasks: List[str],
    session_id: Optional[str] = None,
) -> Optional[str]:
    """Convenience function to preserve current context.

    Args:
        agent_id: Agent preserving context
        summary: Context summary
        decisions: Key decisions made
        tasks: Active tasks
        session_id: Optional session identifier

    Returns:
        Memory ID if successful

    Example:
        memory_id = preserve_current_context(
            agent_id="orchestrator",
            summary="API development in progress",
            decisions=["Using REST API", "PostgreSQL database"],
            tasks=["Implement auth", "Write tests"]
        )
    """
    preserver = ContextPreserver(session_id)
    return preserver.preserve_conversation_context(
        agent_id=agent_id, conversation_summary=summary, key_decisions=decisions, active_tasks=tasks
    )


def restore_latest_context(
    agent_id: Optional[str] = None, session_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Convenience function to restore latest context.

    Args:
        agent_id: Optional agent filter
        session_id: Optional session identifier

    Returns:
        Context data dictionary

    Example:
        context = restore_latest_context("orchestrator")
        if context:
            print(f"Summary: {context['conversation_summary']}")
    """
    preserver = ContextPreserver(session_id)
    return preserver.restore_conversation_context(agent_id)


# Export public interface
__all__ = ["ContextPreserver", "preserve_current_context", "restore_latest_context"]
