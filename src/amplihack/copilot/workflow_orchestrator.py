"""Workflow orchestration for Copilot CLI.

Reads workflow markdown files, parses steps, and executes them sequentially via Copilot CLI.

Philosophy:
- Ruthless simplicity - parse markdown, execute steps
- Zero-BS - every function works or doesn't exist
- Regeneratable - workflows are markdown, orchestrator is stateless
- File-based state - persist to survive interruptions

Public API (the "studs"):
    WorkflowOrchestrator: Main orchestration engine
    WorkflowStep: Individual workflow step
    WorkflowExecutionResult: Results from execution
"""

import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Literal

from .workflow_state import (
    WorkflowState,
    WorkflowStateManager,
    TodoItem,
    StepStatus,
)


@dataclass
class WorkflowStep:
    """Individual workflow step parsed from markdown.

    Attributes:
        number: Step number (e.g., 0, 1, 2...)
        name: Step name from heading
        content: Step content (checklist items, descriptions)
        checklist_items: List of checklist items
        agent_references: Agents mentioned in step (e.g., architect, builder)
        file_references: Files mentioned with @ notation
    """
    number: int
    name: str
    content: str
    checklist_items: List[str] = field(default_factory=list)
    agent_references: List[str] = field(default_factory=list)
    file_references: List[str] = field(default_factory=list)


@dataclass
class WorkflowExecutionResult:
    """Results from workflow execution.

    Attributes:
        success: Whether execution succeeded
        session_id: Session identifier
        workflow_name: Name of workflow executed
        steps_completed: Number of steps completed
        total_steps: Total number of steps
        current_step: Current step number
        state_path: Path to state file
        error: Error message if failed
    """
    success: bool
    session_id: str
    workflow_name: str
    steps_completed: int
    total_steps: int
    current_step: int
    state_path: Path
    error: Optional[str] = None


class WorkflowOrchestrator:
    """Orchestrates workflow execution for Copilot CLI.

    Reads workflow markdown files, parses steps, executes them sequentially,
    and manages state persistence.

    Example:
        >>> orchestrator = WorkflowOrchestrator()
        >>> result = orchestrator.execute_workflow(
        ...     "DEFAULT_WORKFLOW",
        ...     "Add authentication feature"
        ... )
        >>> result.success
        True
    """

    def __init__(
        self,
        workflows_dir: Path = Path(".claude/workflow"),
        state_dir: Path = Path(".claude/runtime/copilot-state"),
    ):
        """Initialize orchestrator.

        Args:
            workflows_dir: Directory containing workflow markdown files
            state_dir: Directory for state persistence
        """
        self.workflows_dir = workflows_dir
        self.state_dir = state_dir
        self.state_manager = WorkflowStateManager(state_dir)

    def parse_workflow(self, workflow_path: Path) -> List[WorkflowStep]:
        """Parse workflow markdown file into steps.

        Extracts step headings (### Step N:), content, checklist items,
        agent references, and file references.

        Args:
            workflow_path: Path to workflow markdown file

        Returns:
            List of WorkflowStep objects

        Raises:
            FileNotFoundError: If workflow file doesn't exist
            ValueError: If workflow format is invalid

        Example:
            >>> steps = orchestrator.parse_workflow(
            ...     Path(".claude/workflow/DEFAULT_WORKFLOW.md")
            ... )
            >>> len(steps)
            22
        """
        if not workflow_path.exists():
            raise FileNotFoundError(f"Workflow not found: {workflow_path}")

        content = workflow_path.read_text(encoding='utf-8')

        # Extract steps using regex (matches ### Step N: Name)
        step_pattern = r'###\s+Step\s+(\d+):\s+([^\n]+)'
        matches = list(re.finditer(step_pattern, content, re.MULTILINE))

        if not matches:
            raise ValueError(f"No steps found in workflow: {workflow_path}")

        steps = []
        for i, match in enumerate(matches):
            step_number = int(match.group(1))
            step_name = match.group(2).strip()

            # Extract content between this step and next step (or end of file)
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            step_content = content[start_pos:end_pos].strip()

            # Extract checklist items (lines starting with "- [ ]")
            checklist_items = re.findall(
                r'^\s*-\s+\[\s*\]\s+(.+)$',
                step_content,
                re.MULTILINE
            )

            # Extract agent references (e.g., "architect agent", "builder agent")
            agent_refs = re.findall(
                r'(?:Use|use|Always use|ALWAYS use)\s+(?:the\s+)?(\w+(?:-\w+)*)\s+agent',
                step_content
            )
            agent_refs = list(set(agent_refs))  # Remove duplicates

            # Extract @ file references
            file_refs = re.findall(r'@([\w\.\-/]+(?:\.md)?)', step_content)
            file_refs = list(set(file_refs))  # Remove duplicates

            steps.append(WorkflowStep(
                number=step_number,
                name=step_name,
                content=step_content,
                checklist_items=checklist_items,
                agent_references=agent_refs,
                file_references=file_refs,
            ))

        return steps

    def execute_workflow(
        self,
        workflow_name: str,
        task_description: str,
        session_id: Optional[str] = None,
        start_step: int = 0,
    ) -> WorkflowExecutionResult:
        """Execute workflow via Copilot CLI.

        Process:
        1. Load or create session state
        2. Parse workflow into steps
        3. Execute steps sequentially (or resume from checkpoint)
        4. Update state after each step
        5. Return execution result

        Args:
            workflow_name: Name of workflow (e.g., "DEFAULT_WORKFLOW")
            task_description: User's task description
            session_id: Optional session ID for resuming
            start_step: Step number to start from (0 = beginning)

        Returns:
            WorkflowExecutionResult with execution details

        Example:
            >>> result = orchestrator.execute_workflow(
            ...     "DEFAULT_WORKFLOW",
            ...     "Add authentication to API"
            ... )
            >>> print(f"Completed {result.steps_completed}/{result.total_steps} steps")
        """
        # Determine workflow path
        workflow_path = self.workflows_dir / f"{workflow_name}.md"
        if not workflow_path.exists():
            return WorkflowExecutionResult(
                success=False,
                session_id="",
                workflow_name=workflow_name,
                steps_completed=0,
                total_steps=0,
                current_step=0,
                state_path=Path(),
                error=f"Workflow not found: {workflow_path}"
            )

        # Load or create state
        if session_id:
            state = self.state_manager.load_state(session_id)
            if not state:
                return WorkflowExecutionResult(
                    success=False,
                    session_id=session_id,
                    workflow_name=workflow_name,
                    steps_completed=0,
                    total_steps=0,
                    current_step=0,
                    state_path=Path(),
                    error=f"Session not found: {session_id}"
                )
        else:
            session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            state = self.state_manager.create_session(
                session_id=session_id,
                workflow=workflow_name,
                task_description=task_description,
            )

        # Parse workflow steps
        try:
            steps = self.parse_workflow(workflow_path)
        except Exception as e:
            return WorkflowExecutionResult(
                success=False,
                session_id=session_id,
                workflow_name=workflow_name,
                steps_completed=0,
                total_steps=0,
                current_step=0,
                state_path=state.state_path,
                error=f"Failed to parse workflow: {str(e)}"
            )

        # Initialize todos if starting fresh
        if not state.todos:
            for step in steps:
                state.todos.append(TodoItem(
                    step=step.number,
                    content=f"Step {step.number}: {step.name}",
                    status="pending",
                    timestamp=datetime.now().isoformat(),
                ))
            state.total_steps = len(steps)
            self.state_manager.save_state(state)

        # Execute steps starting from start_step
        steps_completed = sum(1 for todo in state.todos if todo.status == "completed")

        for step in steps:
            if step.number < start_step:
                continue

            # Check if already completed
            todo = next((t for t in state.todos if t.step == step.number), None)
            if todo and todo.status == "completed":
                continue

            # Update state to in_progress
            if todo:
                todo.status = "in_progress"
                todo.timestamp = datetime.now().isoformat()
            state.current_step = step.number
            self.state_manager.save_state(state)

            # Execute step via Copilot CLI
            try:
                self._execute_step(step, state, task_description)

                # Mark step completed
                if todo:
                    todo.status = "completed"
                    todo.timestamp = datetime.now().isoformat()
                steps_completed += 1
                self.state_manager.save_state(state)

            except Exception as e:
                # Step failed - keep state as in_progress for resume
                return WorkflowExecutionResult(
                    success=False,
                    session_id=session_id,
                    workflow_name=workflow_name,
                    steps_completed=steps_completed,
                    total_steps=len(steps),
                    current_step=step.number,
                    state_path=state.state_path,
                    error=f"Step {step.number} failed: {str(e)}"
                )

        # All steps completed successfully
        return WorkflowExecutionResult(
            success=True,
            session_id=session_id,
            workflow_name=workflow_name,
            steps_completed=steps_completed,
            total_steps=len(steps),
            current_step=state.current_step,
            state_path=state.state_path,
        )

    def _execute_step(
        self,
        step: WorkflowStep,
        state: WorkflowState,
        task_description: str,
    ) -> None:
        """Execute single workflow step via Copilot CLI.

        Builds prompt with:
        - Task description
        - Current step details
        - Checklist items
        - Agent references
        - File references
        - State context

        Args:
            step: WorkflowStep to execute
            state: Current workflow state
            task_description: User's task description

        Raises:
            subprocess.CalledProcessError: If copilot command fails
            FileNotFoundError: If copilot not installed
        """
        # Build prompt for Copilot CLI
        prompt = self._build_step_prompt(step, state, task_description)

        # Build command with file references
        cmd = ["copilot", "--allow-all-tools", "--add-dir", "/"]

        # Add workflow file reference
        workflow_path = self.workflows_dir / f"{state.workflow}.md"
        cmd.extend(["-f", f"@{workflow_path}"])

        # Add agent references
        for agent in step.agent_references:
            agent_path = Path(f".github/agents/{agent}.md")
            if agent_path.exists():
                cmd.extend(["-f", f"@{agent_path}"])

        # Add additional file references
        for file_ref in step.file_references:
            # Normalize file reference (add .claude/ prefix if needed)
            if not file_ref.startswith("."):
                file_ref = f".claude/context/{file_ref}"
            if Path(file_ref).exists():
                cmd.extend(["-f", f"@{file_ref}"])

        # Add prompt
        cmd.extend(["-p", prompt])

        # Execute via subprocess
        # Note: Interactive mode - let copilot handle terminal I/O
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Let output flow to terminal
            text=True,
        )

    def _build_step_prompt(
        self,
        step: WorkflowStep,
        state: WorkflowState,
        task_description: str,
    ) -> str:
        """Build prompt for step execution.

        Args:
            step: WorkflowStep to execute
            state: Current workflow state
            task_description: User's task description

        Returns:
            Formatted prompt string
        """
        prompt_parts = [
            f"# Task: {task_description}",
            f"",
            f"# Workflow: {state.workflow}",
            f"# Step {step.number} of {state.total_steps}: {step.name}",
            f"",
            f"## Context",
            f"- Session ID: {state.session_id}",
            f"- Steps completed: {sum(1 for t in state.todos if t.status == 'completed')}/{state.total_steps}",
            f"- Current step: {step.number}",
            f"",
            f"## Step Instructions",
            step.content,
            f"",
        ]

        # Add checklist if present
        if step.checklist_items:
            prompt_parts.append("## Checklist")
            for item in step.checklist_items:
                prompt_parts.append(f"- [ ] {item}")
            prompt_parts.append("")

        # Add agent guidance if agents referenced
        if step.agent_references:
            prompt_parts.append("## Agents to Leverage")
            for agent in step.agent_references:
                prompt_parts.append(f"- {agent}")
            prompt_parts.append("")

        # Add state file location for manual updates
        prompt_parts.append("## State Management")
        prompt_parts.append(f"Update state file: {state.state_path}")
        prompt_parts.append("")
        prompt_parts.append("Mark this step complete when finished:")
        prompt_parts.append(f"jq '(.todos[] | select(.step == {step.number}) | .status) = \"completed\"' {state.state_path} > state.tmp && mv state.tmp {state.state_path}")

        return "\n".join(prompt_parts)

    def resume_workflow(self, session_id: str) -> WorkflowExecutionResult:
        """Resume workflow from last checkpoint.

        Loads state and continues from current_step.

        Args:
            session_id: Session ID to resume

        Returns:
            WorkflowExecutionResult

        Example:
            >>> result = orchestrator.resume_workflow("20240115-143052")
            >>> result.success
            True
        """
        state = self.state_manager.load_state(session_id)
        if not state:
            return WorkflowExecutionResult(
                success=False,
                session_id=session_id,
                workflow_name="",
                steps_completed=0,
                total_steps=0,
                current_step=0,
                state_path=Path(),
                error=f"Session not found: {session_id}"
            )

        # Resume from current step
        return self.execute_workflow(
            workflow_name=state.workflow,
            task_description=state.context.get("task_description", "Resumed session"),
            session_id=session_id,
            start_step=state.current_step,
        )

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all workflow sessions.

        Returns:
            List of session summaries with metadata

        Example:
            >>> sessions = orchestrator.list_sessions()
            >>> for session in sessions:
            ...     print(f"{session['session_id']}: {session['workflow']}")
        """
        sessions = []

        if not self.state_dir.exists():
            return sessions

        for session_dir in self.state_dir.iterdir():
            if not session_dir.is_dir():
                continue

            state_file = session_dir / "state.json"
            if not state_file.exists():
                continue

            try:
                state = self.state_manager.load_state(session_dir.name)
                if state:
                    steps_completed = sum(1 for t in state.todos if t.status == "completed")
                    sessions.append({
                        "session_id": state.session_id,
                        "workflow": state.workflow,
                        "current_step": state.current_step,
                        "total_steps": state.total_steps,
                        "steps_completed": steps_completed,
                        "created": state.context.get("created", "unknown"),
                        "state_path": str(state.state_path),
                    })
            except Exception:
                # Skip corrupted state files
                continue

        return sorted(sessions, key=lambda s: s["session_id"], reverse=True)


__all__ = [
    "WorkflowOrchestrator",
    "WorkflowStep",
    "WorkflowExecutionResult",
]
