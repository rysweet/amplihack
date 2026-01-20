"""Tool gate enforcement logic."""

from dataclasses import dataclass
from enum import Enum

from .overrides import OverrideManager


class EnforcementLevel(Enum):
    """Enforcement levels for workflow prerequisites."""

    SOFT = "soft"  # Warnings only
    MEDIUM = "medium"  # Warnings + tracking
    HARD = "hard"  # Blocking


@dataclass
class GateDecision:
    """Decision from gate check."""

    allowed: bool
    reason: str
    enforcement_level: EnforcementLevel
    suggested_action: str
    severity: str  # 'info', 'warning', 'error'


class ToolGate:
    """Enforces workflow prerequisites before tool execution."""

    # Tools that require workflow when used for implementation
    IMPLEMENTATION_TOOLS = ["write_file", "edit_file", "bash"]

    # File patterns that are exempt from workflow requirements
    DOCUMENTATION_PATTERNS = [".md", ".txt", ".rst", ".adoc"]

    def __init__(self, tracker, enforcement_level: EnforcementLevel = EnforcementLevel.HARD):
        """Initialize gate with tracker and enforcement level."""
        self.tracker = tracker
        self.enforcement_level = enforcement_level

    def check_tool_allowed(self, tool_name: str, tool_input: dict, context: dict) -> GateDecision:
        """
        Check if tool usage is allowed.

        Enforcement logic:
        1. Check if user override active (always allow)
        2. Check if tool requires workflow
        3. Check if workflow is active (allow if yes)
        4. Return decision based on enforcement level
        """
        # Check for user override first
        override_active, override_reason = OverrideManager.is_override_active()
        if override_active:
            OverrideManager.record_override_usage(tool_name, context)
            return GateDecision(
                allowed=True,
                reason=f"user override active: {override_reason}",
                enforcement_level=self.enforcement_level,
                suggested_action="",
                severity="info",
            )

        # Check if tool requires workflow
        if not self._requires_workflow(tool_name, tool_input):
            return GateDecision(
                allowed=True,
                reason="tool does not require workflow",
                enforcement_level=self.enforcement_level,
                suggested_action="",
                severity="info",
            )

        # Check if workflow is active
        session_id = context.get("session_id", "")
        if self.tracker.is_workflow_active(session_id):
            return GateDecision(
                allowed=True,
                reason="workflow is active",
                enforcement_level=self.enforcement_level,
                suggested_action="",
                severity="info",
            )

        # Workflow not active - apply enforcement based on level
        if self.enforcement_level == EnforcementLevel.SOFT:
            # Soft: Just inform
            return GateDecision(
                allowed=True,
                reason="workflow not active (soft enforcement - advisory only)",
                enforcement_level=self.enforcement_level,
                suggested_action="Consider starting workflow first",
                severity="info",
            )

        elif self.enforcement_level == EnforcementLevel.MEDIUM:
            # Medium: Track and warn
            self.tracker.record_bypass_attempt(tool_name, session_id, blocked=False)
            return GateDecision(
                allowed=True,
                reason="workflow not active - bypass attempt recorded",
                enforcement_level=self.enforcement_level,
                suggested_action="Execute default-workflow recipe first",
                severity="warning",
            )

        else:  # HARD
            # Hard: Block
            self.tracker.record_bypass_attempt(tool_name, session_id, blocked=True)
            return GateDecision(
                allowed=False,
                reason="workflow required but not active",
                enforcement_level=self.enforcement_level,
                suggested_action='Execute: recipes(operation="execute", recipe_path="@amplihack:recipes/default-workflow.yaml")',
                severity="error",
            )

    def _requires_workflow(self, tool_name: str, tool_input: dict) -> bool:
        """Check if tool usage requires active workflow."""
        if tool_name not in self.IMPLEMENTATION_TOOLS:
            return False

        # Check for documentation-only changes (exempt)
        if tool_name in ["write_file", "edit_file"]:
            file_path = tool_input.get("file_path", "")
            if any(file_path.endswith(pattern) for pattern in self.DOCUMENTATION_PATTERNS):
                return False

        # Bash requires workflow only for git commands
        if tool_name == "bash":
            command = tool_input.get("command", "")
            git_commands = ["git commit", "git push", "git merge"]
            return any(git_cmd in command for git_cmd in git_commands)

        # All other implementation tool usage requires workflow
        return True
