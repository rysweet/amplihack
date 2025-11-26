#!/usr/bin/env python3
"""
Workflow Gate - Prevents premature task completion.

This module provides a gate mechanism that checks workflow state before
allowing task completion. It ensures mandatory steps are completed and
Step 0 compliance is verified.

Philosophy:
- Standard library only (json, pathlib)
- Actionable continuation prompts
- Fail-open for non-critical errors
- < 50ms overhead per check

Public API (the "studs"):
    WorkflowGate: Class for checking workflow completion readiness
    GateResult: Result of a gate check
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Import workflow state management
try:
    from workflow_state import ValidationResult, WorkflowState, WorkflowStateMachine
except ImportError:
    # Handle import when run as module
    from .workflow_state import ValidationResult, WorkflowState, WorkflowStateMachine

__all__ = ["WorkflowGate", "GateResult"]


# Configuration constants
MAX_DISPLAYED_STEPS = 5  # Maximum steps to show in continuation prompts

# Step names for readable continuation prompts
STEP_NAMES = {
    0: "Workflow Preparation (create 22 todos)",
    1: "Rewrite and Clarify Requirements",
    2: "Create GitHub Issue",
    3: "Setup Worktree and Branch",
    4: "Research and Design with TDD",
    5: "Implement the Solution",
    6: "Refactor and Simplify",
    7: "Run Tests and Pre-commit Hooks",
    8: "Mandatory Local Testing",
    9: "Commit and Push",
    10: "Open Pull Request",
    11: "Review the PR",
    12: "Implement Review Feedback",
    13: "Final Code Review",
    14: "Request Human Review (if needed)",
    15: "Address Human Feedback",
    16: "Philosophy Compliance Check",
    17: "Ensure PR is Mergeable",
    18: "Final Testing",
    19: "Documentation Update",
    20: "Cleanup",
    21: "Task Completion",
}


@dataclass
class GateResult:
    """Result of a workflow gate check.

    Attributes:
        decision: "allow" or "block"
        reason: Human-readable reason for the decision
        missing_steps: List of steps that need to be completed
        mandatory_incomplete: List of mandatory steps that are incomplete
        continuation_prompt: Actionable prompt for Claude to continue work
    """

    decision: str  # "allow" or "block"
    reason: str = ""
    missing_steps: list[int] = field(default_factory=list)
    mandatory_incomplete: list[int] = field(default_factory=list)
    continuation_prompt: str = ""


class WorkflowGate:
    """Gate that prevents premature task completion.

    This gate checks:
    1. Step 21 (Task Completion) is reached
    2. All mandatory steps (0, 10, 16, 17, 21) are complete
    3. Step 0 compliance (22 todos initialized)

    Usage:
        gate = WorkflowGate(project_root)
        result = gate.check(session_id)
        if result.decision == "block":
            # Return continuation prompt to Claude
            return result.continuation_prompt
    """

    def __init__(self, project_root: Path | None = None):
        """Initialize the workflow gate.

        Args:
            project_root: Project root directory. If None, will be detected.
        """
        self.state_machine = WorkflowStateMachine(project_root)
        self.project_root = self.state_machine.project_root
        self.metrics_dir = self.project_root / ".claude" / "runtime" / "metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

    def check(self, session_id: str) -> GateResult:
        """Check if workflow allows task completion.

        Args:
            session_id: Session identifier

        Returns:
            GateResult with decision and details
        """
        # Load workflow state
        state = self.state_machine.load_state(session_id)

        if state is None:
            # No workflow state - fail open (allow)
            # This handles sessions that started before enforcement was enabled
            self._log_decision(session_id, "allow", "No workflow state found")
            return GateResult(
                decision="allow",
                reason="No workflow state tracked for this session",
            )

        # Validate workflow completion
        validation = self.state_machine.validate_completion(state)

        if validation.is_valid:
            self._log_decision(session_id, "allow", "Workflow complete")
            return GateResult(
                decision="allow",
                reason="All workflow requirements satisfied",
            )

        # Workflow incomplete - generate blocking result
        continuation_prompt = self.generate_continuation_prompt(state)

        self._log_decision(
            session_id,
            "block",
            f"Missing steps: {validation.missing_steps}, Mandatory incomplete: {validation.mandatory_incomplete}",
        )

        return GateResult(
            decision="block",
            reason=self._format_block_reason(validation),
            missing_steps=validation.missing_steps,
            mandatory_incomplete=validation.mandatory_incomplete,
            continuation_prompt=continuation_prompt,
        )

    def generate_continuation_prompt(self, state: WorkflowState) -> str:
        """Generate an actionable continuation prompt for Claude.

        Creates a prompt that tells Claude exactly what needs to be done
        to complete the workflow.

        Args:
            state: Current workflow state

        Returns:
            Actionable continuation prompt string
        """
        lines = []
        lines.append("WORKFLOW INCOMPLETE - Continue working on the following:\n")

        # Check Step 0 compliance first
        if not state.todos_initialized:
            lines.append("CRITICAL: Step 0 Compliance Required")
            lines.append("  You MUST create 22 todos (one for each workflow step 0-21)")
            lines.append("  Use TodoWrite to create the complete workflow todo list")
            lines.append("")

        # Get validation for detailed info
        validation = self.state_machine.validate_completion(state)

        # List mandatory incomplete steps
        if validation.mandatory_incomplete:
            lines.append("MANDATORY STEPS (Must Complete):")
            for step in sorted(validation.mandatory_incomplete):
                step_name = STEP_NAMES.get(step, f"Step {step}")
                lines.append(f"  - Step {step}: {step_name}")
            lines.append("")

        # List other missing steps (not mandatory)
        other_missing = [
            s for s in validation.missing_steps if s not in validation.mandatory_incomplete
        ]
        if other_missing:
            lines.append("Other Incomplete Steps:")
            for step in sorted(other_missing)[:MAX_DISPLAYED_STEPS]:
                step_name = STEP_NAMES.get(step, f"Step {step}")
                lines.append(f"  - Step {step}: {step_name}")
            if len(other_missing) > MAX_DISPLAYED_STEPS:
                lines.append(f"  ... and {len(other_missing) - MAX_DISPLAYED_STEPS} more")
            lines.append("")

        # Suggest next actions
        next_steps = self.state_machine.get_next_steps(state)
        if next_steps:
            lines.append("Suggested Next Actions:")
            for idx, step in enumerate(next_steps[:3], 1):
                step_name = STEP_NAMES.get(step, f"Step {step}")
                lines.append(f"  {idx}. Complete Step {step}: {step_name}")
            lines.append("")

        lines.append("Task completion requires reaching Step 21 with all mandatory steps complete.")
        lines.append("Use TodoWrite to track progress on each step.")

        return "\n".join(lines)

    def can_override(self, state: WorkflowState) -> bool:
        """Check if user can override the gate for a state.

        Currently, overrides are only allowed for non-mandatory steps.
        Mandatory steps require explicit user_overrides to be recorded.

        Args:
            state: Workflow state to check

        Returns:
            True if override is possible
        """
        validation = self.state_machine.validate_completion(state)

        # Can override if only non-mandatory steps are incomplete
        # and all mandatory steps either complete or have overrides
        for step in validation.mandatory_incomplete:
            if step not in state.user_overrides:
                return False

        return True

    def record_user_override(
        self,
        session_id: str,
        step: int,
        user_message: str,
    ) -> None:
        """Record a user override for a mandatory step.

        Args:
            session_id: Session identifier
            step: Step number being overridden
            user_message: User's message authorizing the override
        """
        state = self.state_machine.load_state(session_id)
        if state:
            self.state_machine.record_user_override(state, step, user_message)
            self._log_decision(
                session_id,
                "override",
                f"User override for step {step}: {user_message[:100]}",
            )

    def _format_block_reason(self, validation: ValidationResult) -> str:
        """Format a human-readable block reason from validation result."""
        reasons = []

        if validation.mandatory_incomplete:
            step_list = ", ".join(str(s) for s in validation.mandatory_incomplete)
            reasons.append(f"Mandatory steps incomplete: {step_list}")

        if validation.errors:
            reasons.extend(validation.errors)

        return " | ".join(reasons) if reasons else "Workflow validation failed"

    def _log_decision(self, session_id: str, decision: str, reason: str) -> None:
        """Log a gate decision to the metrics file.

        Args:
            session_id: Session identifier
            decision: "allow", "block", or "override"
            reason: Reason for the decision
        """
        metrics_file = self.metrics_dir / "workflow_enforcement_metrics.jsonl"

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "decision": decision,
            "reason": reason,
        }

        try:
            with open(metrics_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass  # Fail silently - metrics are not critical


# Convenience function for quick gate check
def check_workflow_gate(
    session_id: str,
    project_root: Path | None = None,
) -> GateResult:
    """Convenience function to check workflow gate.

    Args:
        session_id: Session identifier
        project_root: Optional project root path

    Returns:
        GateResult
    """
    gate = WorkflowGate(project_root)
    return gate.check(session_id)
