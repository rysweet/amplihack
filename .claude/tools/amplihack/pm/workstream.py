"""PM workstream management with ClaudeProcess integration.

This module manages workstream lifecycle and delegates work to AI agents
through ClaudeProcess. It creates delegation packages that contain all
context needed for an agent to complete work autonomously.

Public API:
    - DelegationPackage: Structured context for agent work
    - WorkstreamManager: Manages workstream lifecycle and agent delegation

Philosophy:
    - Template-based delegation (predictable, testable)
    - ClaudeProcess integration for agent execution
    - Simple synchronous execution (no async complexity)
    - Ruthless simplicity
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

from .state import PMStateManager, BacklogItem, WorkstreamState

try:
    # Try importing from installed package or sys.path first
    from amplihack.orchestration.claude_process import ClaudeProcess, ProcessResult
except ImportError:
    # Fallback for direct execution in .claude/tools/
    import sys
    from pathlib import Path as _Path

    _tools_dir = _Path(__file__).parent.parent
    if str(_tools_dir) not in sys.path:
        sys.path.insert(0, str(_tools_dir))
    from orchestration.claude_process import ClaudeProcess, ProcessResult


__all__ = [
    "DelegationPackage",
    "WorkstreamManager",
]


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class DelegationPackage:
    """Structured delegation package for agent.

    Contains everything agent needs to complete work.
    """

    backlog_item: BacklogItem
    agent_role: str  # builder, reviewer, etc.
    project_context: str  # From .pm/config.yaml + roadmap.md
    instructions: str  # Generated instructions
    success_criteria: List[str]  # What defines done
    estimated_hours: int

    def to_prompt(self) -> str:
        """Convert package to Claude prompt string."""
        return (
            f"""# Work Assignment: {self.backlog_item.title}

## Context

{self.project_context}

## Your Task

{self.backlog_item.description}

**Priority**: {self.backlog_item.priority}
**Estimated**: {self.estimated_hours} hours
**Tags**: {", ".join(self.backlog_item.tags) if self.backlog_item.tags else "None"}

## Success Criteria

"""
            + "\n".join(f"- {criterion}" for criterion in self.success_criteria)
            + f"""

## Instructions

{self.instructions}

## Philosophy Reminder

- Ruthless simplicity
- Zero-BS implementation (no stubs, no placeholders)
- Every function works or doesn't exist
- Question every abstraction
- Test behavior, not implementation

---

Begin implementation now. Report when complete.
"""
        )


# =============================================================================
# Workstream Manager
# =============================================================================


class WorkstreamManager:
    """Manages workstream execution and ClaudeProcess integration.

    Responsibilities:
    - Create delegation packages
    - Spawn ClaudeProcess for agent work
    - Monitor workstream progress
    - Update workstream state

    Usage:
        manager = WorkstreamManager(
            state_manager=state_mgr,
            project_root=Path.cwd(),
            log_dir=Path(".pm/logs")
        )

        # Start workstream
        result = manager.start_workstream(
            backlog_id="BL-001",
            agent="builder"
        )

        # Check status
        status = manager.get_workstream_status("ws-001")
    """

    def __init__(
        self,
        state_manager: PMStateManager,
        project_root: Path,
        log_dir: Optional[Path] = None,
    ):
        """Initialize workstream manager.

        Args:
            state_manager: PM state manager
            project_root: Project root directory
            log_dir: Directory for process logs (default: .pm/logs)
        """
        self.state_manager = state_manager
        self.project_root = project_root
        self.log_dir = log_dir or (project_root / ".pm" / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def start_workstream(
        self,
        backlog_id: str,
        agent: str = "builder",
        timeout: Optional[int] = None,
    ) -> WorkstreamState:
        """Start new workstream for backlog item.

        Process:
        1. Validate no active workstream (Phase 1 limit)
        2. Load backlog item
        3. Create delegation package
        4. Create workstream state
        5. Spawn ClaudeProcess
        6. Return workstream state

        Args:
            backlog_id: Backlog item ID (BL-001)
            agent: Agent role (builder, reviewer, etc.)
            timeout: Process timeout in seconds

        Returns:
            WorkstreamState object

        Raises:
            ValueError: If active workstream exists or item not found
        """
        # Phase 1: Only one active workstream allowed
        active = self.state_manager.get_active_workstream()
        if active:
            raise ValueError(
                f"Active workstream exists: {active.id} - {active.title}. "
                "Complete or stop it first."
            )

        # Load backlog item
        backlog_item = self.state_manager.get_backlog_item(backlog_id)
        if not backlog_item:
            raise ValueError(f"Backlog item {backlog_id} not found")

        # Create workstream
        workstream = self.state_manager.create_workstream(
            backlog_id=backlog_id,
            agent=agent,
        )

        # Create delegation package
        delegation_package = self.create_delegation_package(
            backlog_item=backlog_item,
            agent=agent,
        )

        # Spawn agent process
        result = self.spawn_agent_process(
            delegation_package=delegation_package,
            workstream=workstream,
            timeout=timeout,
        )

        # Update workstream with process info and duration
        self.state_manager.update_workstream(
            workstream.id,
            process_id=result.process_id,
            elapsed_minutes=int(result.duration / 60),
        )

        return self.state_manager.get_workstream(workstream.id)

    def get_workstream_status(self, ws_id: str) -> Dict[str, Any]:
        """Get detailed workstream status.

        Returns:
            {
                "workstream": WorkstreamState,
                "elapsed_time": "30 min",
                "progress": "60%",
                "status": "RUNNING",
            }
        """
        workstream = self.state_manager.get_workstream(ws_id)
        if not workstream:
            raise ValueError(f"Workstream {ws_id} not found")

        # Calculate elapsed time
        elapsed_str = f"{workstream.elapsed_minutes} min"
        if workstream.elapsed_minutes >= 60:
            hours = workstream.elapsed_minutes // 60
            mins = workstream.elapsed_minutes % 60
            elapsed_str = f"{hours}h {mins}m"

        # Estimate progress (simple heuristic based on status)
        progress = "0%"
        if workstream.status == "RUNNING":
            # Rough estimate based on elapsed time vs estimated
            backlog_item = self.state_manager.get_backlog_item(workstream.backlog_id)
            if backlog_item:
                estimated_mins = backlog_item.estimated_hours * 60
                progress_pct = min(int((workstream.elapsed_minutes / estimated_mins) * 100), 99)
                progress = f"{progress_pct}%"
        elif workstream.status == "COMPLETED":
            progress = "100%"
        elif workstream.status == "FAILED":
            progress = "N/A"

        return {
            "workstream": workstream,
            "elapsed_time": elapsed_str,
            "progress": progress,
            "status": workstream.status,
        }

    def stop_workstream(self, ws_id: str, reason: str = "") -> WorkstreamState:
        """Stop active workstream.

        Updates state to PAUSED, adds note about reason.
        """
        workstream = self.state_manager.get_workstream(ws_id)
        if not workstream:
            raise ValueError(f"Workstream {ws_id} not found")

        # Add stop reason to notes
        notes = workstream.progress_notes.copy()
        if reason:
            notes.append(f"Stopped: {reason}")
        else:
            notes.append("Stopped by user")

        # Update status
        return self.state_manager.update_workstream(
            ws_id,
            status="PAUSED",
            progress_notes=notes,
        )

    def complete_workstream(
        self,
        ws_id: str,
        success: bool = True,
        notes: Optional[List[str]] = None,
    ) -> WorkstreamState:
        """Mark workstream as completed.

        Delegates to state_manager.complete_workstream()
        """
        workstream = self.state_manager.get_workstream(ws_id)
        if not workstream:
            raise ValueError(f"Workstream {ws_id} not found")

        # Add completion notes if provided
        if notes:
            all_notes = workstream.progress_notes + notes
            self.state_manager.update_workstream(
                ws_id,
                progress_notes=all_notes,
            )

        # Complete workstream
        return self.state_manager.complete_workstream(ws_id, success=success)

    # =========================================================================
    # Delegation Package Creation
    # =========================================================================

    def create_delegation_package(
        self,
        backlog_item: BacklogItem,
        agent: str,
    ) -> DelegationPackage:
        """Create delegation package for agent.

        Builds package from:
        - Backlog item details
        - Project config
        - Roadmap context
        - Agent-specific instructions (template)
        """
        # Load project context
        project_context = self._load_project_context()

        # Generate agent-specific instructions
        instructions = self._generate_agent_instructions(agent, backlog_item)

        # Define success criteria
        success_criteria = [
            "All requirements implemented and working",
            "Tests pass (if applicable)",
            "Code follows project philosophy (ruthless simplicity)",
            "No stubs or placeholders",
            "Documentation updated",
        ]

        return DelegationPackage(
            backlog_item=backlog_item,
            agent_role=agent,
            project_context=project_context,
            instructions=instructions,
            success_criteria=success_criteria,
            estimated_hours=backlog_item.estimated_hours,
        )

    # =========================================================================
    # ClaudeProcess Integration
    # =========================================================================

    def spawn_agent_process(
        self,
        delegation_package: DelegationPackage,
        workstream: WorkstreamState,
        timeout: Optional[int] = None,
    ) -> ProcessResult:
        """Spawn ClaudeProcess for agent work.

        Creates ClaudeProcess with:
        - Prompt from delegation package
        - Working directory = project_root
        - Log directory = .pm/logs
        - Process ID = pm-{agent}-{ws_id}

        Returns:
            ProcessResult from ClaudeProcess.run()
        """
        # Build prompt from delegation package
        prompt = delegation_package.to_prompt()

        # Create process
        process = ClaudeProcess(
            prompt=prompt,
            process_id=f"pm-{workstream.agent}-{workstream.id}",
            working_dir=self.project_root,
            log_dir=self.log_dir,
            model=None,  # Use default
            stream_output=True,
            timeout=timeout,
        )

        # Log start
        print(f"\n{'=' * 60}")
        print(f"PM: Starting {workstream.agent} agent for workstream {workstream.id}")
        print(f"PM: Title: {workstream.title}")
        print(f"PM: Log: {self.log_dir / f'{process.process_id}.log'}")
        print(f"{'=' * 60}\n")

        # Run and capture result
        result = process.run()

        # Log completion
        print(f"\n{'=' * 60}")
        print(f"PM: Agent completed (exit code: {result.exit_code})")
        print(f"PM: Duration: {result.duration:.1f}s")
        print(f"{'=' * 60}\n")

        return result

    # =========================================================================
    # Template Generation
    # =========================================================================

    def _generate_agent_instructions(
        self,
        agent: str,
        backlog_item: BacklogItem,
    ) -> str:
        """Generate agent-specific instructions.

        Templates by agent role:
        - builder: Implementation focus
        - reviewer: Quality checks
        - tester: Test coverage
        """
        templates = {
            "builder": """1. Analyze the requirements carefully
2. Design solution following project patterns
3. Implement working code (no stubs or placeholders)
4. Add tests to verify behavior
5. Check philosophy compliance
6. Update documentation as needed

Focus on ruthless simplicity. Start with the simplest solution that works.""",
            "reviewer": """1. Review code for philosophy compliance
2. Check for stubs, placeholders, or dead code
3. Verify tests cover behavior (not implementation)
4. Look for unnecessary abstractions
5. Suggest simplifications
6. Verify documentation accuracy

Focus on ruthless simplicity and zero-BS implementation.""",
            "tester": """1. Analyze code behavior and contracts
2. Design tests for edge cases
3. Implement comprehensive test coverage
4. Verify tests pass
5. Document test scenarios

Focus on testing behavior, not implementation details.""",
        }

        return templates.get(
            agent,
            """1. Complete the assigned task following project philosophy
2. Focus on ruthless simplicity
3. Verify all requirements are met
4. Test your work
5. Document any important decisions""",
        )

    def _load_project_context(self) -> str:
        """Load project context from config + roadmap."""
        # Load config
        config = self.state_manager.get_config()

        # Load roadmap if exists
        roadmap_path = self.state_manager.pm_dir / "roadmap.md"
        roadmap_content = ""
        if roadmap_path.exists():
            roadmap_content = roadmap_path.read_text()

        # Build context string
        context = f"""**Project**: {config.project_name}
**Type**: {config.project_type}
**Quality Bar**: {config.quality_bar}

**Primary Goals**:
"""
        for goal in config.primary_goals:
            context += f"- {goal}\n"

        if roadmap_content:
            context += f"\n**Roadmap**:\n{roadmap_content[:1000]}"  # First 1000 chars

        return context
