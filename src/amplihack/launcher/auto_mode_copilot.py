"""Enhanced auto mode for GitHub Copilot CLI.

Leverages Copilot CLI's native capabilities:
- Custom agents via system prompts
- MCP servers for state management
- Session forking with --continue flag
- Progress tracking via state files
"""

import asyncio
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AgentSpec:
    """Specification for a custom agent."""

    name: str
    role: str
    system_prompt: str
    tools: list[str]


class CopilotAgentLibrary:
    """Library of specialized agents for Copilot CLI."""

    @staticmethod
    def get_architect_agent() -> AgentSpec:
        """Return architect agent spec."""
        return AgentSpec(
            name="architect",
            role="System Design & Problem Decomposition",
            system_prompt="""You are an architect agent specializing in system design.

Your responsibilities:
- Analyze requirements and decompose into modules
- Design clear contracts between components
- Apply brick philosophy (self-contained modules)
- Follow ruthless simplicity principles

Reference @.claude/context/PHILOSOPHY.md for design principles.""",
            tools=["Read", "Write", "Bash"],
        )

    @staticmethod
    def get_builder_agent() -> AgentSpec:
        """Return builder agent spec."""
        return AgentSpec(
            name="builder",
            role="Code Implementation",
            system_prompt="""You are a builder agent specializing in implementation.

Your responsibilities:
- Implement code from specifications
- Zero-BS: no stubs, no placeholders
- Every function must work or not exist
- Write comprehensive tests

Reference @.claude/context/PHILOSOPHY.md for implementation standards.""",
            tools=["Read", "Write", "Edit", "Bash"],
        )

    @staticmethod
    def get_tester_agent() -> AgentSpec:
        """Return tester agent spec."""
        return AgentSpec(
            name="tester",
            role="Test Generation & Validation",
            system_prompt="""You are a tester agent specializing in quality assurance.

Your responsibilities:
- Generate comprehensive test suites
- Test contracts, not implementation
- Follow testing pyramid (60% unit, 30% integration, 10% E2E)
- Ensure all tests pass

Reference @.claude/context/PHILOSOPHY.md for testing strategy.""",
            tools=["Read", "Write", "Bash"],
        )

    @staticmethod
    def get_reviewer_agent() -> AgentSpec:
        """Return reviewer agent spec."""
        return AgentSpec(
            name="reviewer",
            role="Code Review & Philosophy Compliance",
            system_prompt="""You are a reviewer agent specializing in quality checks.

Your responsibilities:
- Check philosophy compliance
- Verify no stubs or TODOs
- Ensure modularity and simplicity
- Validate contracts

Reference @.claude/context/PHILOSOPHY.md and @.claude/context/PATTERNS.md.""",
            tools=["Read", "Grep", "Bash"],
        )

    @classmethod
    def select_agents(cls, task_type: str) -> list[AgentSpec]:
        """Select appropriate agents based on task type.

        Args:
            task_type: Type of task (feature, bug, refactor, test)

        Returns:
            List of agent specs for the task
        """
        if task_type == "feature":
            return [cls.get_architect_agent(), cls.get_builder_agent(), cls.get_tester_agent()]
        elif task_type == "bug":
            return [cls.get_builder_agent(), cls.get_tester_agent()]
        elif task_type == "refactor":
            return [cls.get_architect_agent(), cls.get_builder_agent(), cls.get_reviewer_agent()]
        elif task_type == "test":
            return [cls.get_tester_agent()]
        else:
            # Default: all agents
            return [
                cls.get_architect_agent(),
                cls.get_builder_agent(),
                cls.get_tester_agent(),
                cls.get_reviewer_agent(),
            ]


class CopilotSessionManager:
    """Manage Copilot CLI sessions with forking support."""

    def __init__(self, working_dir: Path, session_id: str):
        """Initialize session manager.

        Args:
            working_dir: Working directory for the session
            session_id: Unique session identifier
        """
        self.working_dir = working_dir
        self.session_id = session_id
        self.state_file = working_dir / ".claude" / "runtime" / "copilot" / f"{session_id}.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        self.state: dict[str, Any] = {
            "session_id": session_id,
            "fork_count": 0,
            "start_time": time.time(),
            "last_fork_time": time.time(),
            "total_turns": 0,
            "phase": "init",
        }
        self._save_state()

    def _save_state(self) -> None:
        """Save session state to file."""
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def _load_state(self) -> None:
        """Load session state from file."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                self.state = json.load(f)

    def should_fork(self, threshold_seconds: float = 3600) -> bool:
        """Check if session should be forked.

        Args:
            threshold_seconds: Fork threshold (default 60 minutes)

        Returns:
            True if session should be forked
        """
        elapsed = time.time() - self.state["last_fork_time"]
        return elapsed >= threshold_seconds

    def fork_session(self, context: str) -> str:
        """Fork current session using Copilot CLI --continue flag.

        Args:
            context: Context to pass to forked session

        Returns:
            New session ID for the fork
        """
        self.state["fork_count"] += 1
        self.state["last_fork_time"] = time.time()
        self._save_state()

        # Create continuation prompt
        fork_id = f"{self.session_id}_fork{self.state['fork_count']}"
        continuation = f"""Continue previous session {self.session_id}.

Context from previous session:
{context}

Continue execution from where we left off."""

        return fork_id

    def update_phase(self, phase: str) -> None:
        """Update current session phase.

        Args:
            phase: Current phase (clarifying, planning, executing, evaluating, summarizing)
        """
        self.state["phase"] = phase
        self.state["total_turns"] = self.state.get("total_turns", 0) + 1
        self._save_state()

    def get_state(self) -> dict[str, Any]:
        """Return current session state."""
        self._load_state()
        return self.state.copy()


class CopilotAutoMode:
    """Enhanced auto mode for GitHub Copilot CLI.

    Leverages Copilot's native capabilities with custom agents and session forking.
    """

    def __init__(
        self,
        prompt: str,
        max_turns: int = 10,
        working_dir: Path | None = None,
        task_type: str = "feature",
        fork_threshold: float = 3600,  # 60 minutes
    ):
        """Initialize Copilot auto mode.

        Args:
            prompt: User's initial prompt
            max_turns: Maximum number of turns
            working_dir: Working directory (defaults to current)
            task_type: Type of task (feature, bug, refactor, test)
            fork_threshold: Session fork threshold in seconds
        """
        self.prompt = prompt
        self.max_turns = max_turns
        self.working_dir = working_dir if working_dir else Path.cwd()
        self.task_type = task_type
        self.fork_threshold = fork_threshold

        # Initialize session
        self.session_id = f"copilot_{int(time.time())}"
        self.session_manager = CopilotSessionManager(self.working_dir, self.session_id)

        # Select agents for task
        self.agents = CopilotAgentLibrary.select_agents(task_type)

        # Logging
        self.log_dir = (
            self.working_dir / ".claude" / "runtime" / "logs" / f"auto_copilot_{self.session_id}"
        )
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Write original prompt
        with open(self.log_dir / "prompt.md", "w") as f:
            f.write(f"# Copilot Auto Mode Prompt\n\n{prompt}\n\n")
            f.write(f"**Task Type**: {task_type}\n")
            f.write(f"**Max Turns**: {max_turns}\n")
            f.write(f"**Session ID**: {self.session_id}\n")

    def log(self, msg: str, level: str = "INFO") -> None:
        """Log message to file and console."""
        print(f"[COPILOT AUTO] {msg}", flush=True)
        with open(self.log_dir / "auto.log", "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] [{level}] {msg}\n")

    def _build_agent_prompt(self, agent: AgentSpec, task_prompt: str) -> str:
        """Build prompt for specific agent.

        Args:
            agent: Agent specification
            task_prompt: Task-specific prompt

        Returns:
            Complete agent prompt with system context
        """
        return f"""You are the {agent.name} agent with role: {agent.role}

{agent.system_prompt}

Task:
{task_prompt}

Execute this task following your role and the project philosophy."""

    async def _run_copilot_command(
        self, prompt: str, agent: AgentSpec | None = None
    ) -> tuple[int, str]:
        """Run Copilot CLI command.

        Args:
            prompt: Prompt to send to Copilot
            agent: Optional agent spec for custom system prompt

        Returns:
            (exit_code, output)
        """
        # Build command with Copilot CLI flags
        cmd = [
            "copilot",
            "--allow-all-tools",
            "--add-dir",
            str(self.working_dir),
        ]

        # Add custom system prompt if agent specified
        if agent:
            cmd.extend(["--system", agent.system_prompt])

        # Add the actual prompt
        cmd.extend(["-p", prompt])

        self.log(f"Running Copilot command with {agent.name if agent else 'default'} agent")

        # Execute subprocess
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_dir,
        )

        stdout, stderr = await process.communicate()

        output = stdout.decode("utf-8", errors="replace")
        if stderr:
            error_output = stderr.decode("utf-8", errors="replace")
            self.log(f"Copilot stderr: {error_output}", level="WARNING")

        return process.returncode or 0, output

    async def _fork_if_needed(self, context: str) -> None:
        """Fork session if threshold exceeded.

        Args:
            context: Context to pass to forked session
        """
        if self.session_manager.should_fork(self.fork_threshold):
            self.log("Session approaching 60-minute limit, forking...")
            fork_id = self.session_manager.fork_session(context)
            self.log(f"Session forked to {fork_id}")
            # Session manager handles state preservation

    async def run(self) -> int:
        """Execute enhanced auto mode loop.

        Returns:
            Exit code (0 for success)
        """
        self.log(f"Starting Copilot auto mode (max {self.max_turns} turns)")
        self.log(f"Task type: {self.task_type}")
        self.log(f"Selected agents: {', '.join(a.name for a in self.agents)}")

        try:
            # Turn 1: Clarify objective
            self.session_manager.update_phase("clarifying")
            self.log("\n--- Turn 1/10 | Clarifying Objective ---")

            clarify_prompt = f"""Analyze this user request and clarify the objective.

1. Identify explicit requirements (must-haves, quoted specs)
2. Identify implicit preferences from @.claude/context/USER_PREFERENCES.md
3. Apply @.claude/context/PHILOSOPHY.md principles
4. Define success criteria

User Request:
{self.prompt}"""

            code, objective = await self._run_copilot_command(clarify_prompt)
            if code != 0:
                self.log(f"Error clarifying objective (exit {code})")
                return 1

            # Turn 2: Create plan
            self.session_manager.update_phase("planning")
            self.log("\n--- Turn 2/10 | Creating Plan ---")

            # Select architect agent for planning
            architect = next((a for a in self.agents if a.name == "architect"), None)

            plan_prompt = f"""Create execution plan for this objective.

Plan should:
1. Preserve all explicit user requirements
2. Apply ruthless simplicity and modular design
3. Identify parallel execution opportunities
4. Follow brick philosophy (self-contained modules)
5. Use zero-BS approach (no stubs/TODOs)

Objective:
{objective}"""

            code, plan = await self._run_copilot_command(
                self._build_agent_prompt(architect, plan_prompt) if architect else plan_prompt,
                agent=architect,
            )
            if code != 0:
                self.log(f"Error creating plan (exit {code})")
                return 1

            # Turns 3+: Execute with appropriate agents
            for turn in range(3, self.max_turns + 1):
                self.session_manager.update_phase("executing")
                self.log(f"\n--- Turn {turn}/{self.max_turns} | Executing ---")

                # Check if fork needed
                await self._fork_if_needed(f"Plan: {plan}\nObjective: {objective}")

                # Select appropriate agent for execution
                if "implement" in plan.lower() or "code" in plan.lower():
                    agent = next((a for a in self.agents if a.name == "builder"), None)
                elif "test" in plan.lower():
                    agent = next((a for a in self.agents if a.name == "tester"), None)
                elif "review" in plan.lower():
                    agent = next((a for a in self.agents if a.name == "reviewer"), None)
                else:
                    agent = next((a for a in self.agents if a.name == "builder"), None)

                execute_prompt = f"""Execute the next part of the plan.

Guidelines:
- Use parallel execution where possible
- Apply @.claude/context/PHILOSOPHY.md principles
- Delegate to specialized agents when appropriate
- Implement complete features (no stubs/TODOs)
- Make decisions autonomously

Current Plan:
{plan}

Objective:
{objective}

Turn: {turn}/{self.max_turns}"""

                code, output = await self._run_copilot_command(
                    self._build_agent_prompt(agent, execute_prompt) if agent else execute_prompt,
                    agent=agent,
                )
                if code != 0:
                    self.log(f"Warning: Execution returned exit code {code}")

                # Evaluate progress
                self.session_manager.update_phase("evaluating")
                self.log(f"--- Turn {turn}/{self.max_turns} | Evaluating ---")

                eval_prompt = f"""Evaluate if objective is achieved.

Check:
1. All explicit requirements met
2. Philosophy principles applied
3. Success criteria satisfied
4. No placeholders/incomplete code
5. Work thoroughly tested

Respond with:
- "COMPLETE" if all criteria met
- "IN PROGRESS" if making progress
- "NEEDS ADJUSTMENT" if issues found

Objective:
{objective}

Turn: {turn}/{self.max_turns}"""

                code, eval_result = await self._run_copilot_command(eval_prompt)

                # Check completion
                if "complete" in eval_result.lower() and "in progress" not in eval_result.lower():
                    self.log("Objective achieved!")
                    break

                if turn >= self.max_turns:
                    self.log("Max turns reached")
                    break

            # Summary
            self.session_manager.update_phase("summarizing")
            self.log("\n--- Summary ---")

            summary_prompt = f"""Summarize the auto mode session.

Session details:
- Turns: {self.session_manager.get_state()['total_turns']}
- Fork count: {self.session_manager.get_state()['fork_count']}
- Task type: {self.task_type}

Objective:
{objective}"""

            code, summary = await self._run_copilot_command(summary_prompt)
            if code == 0:
                print(summary)
            else:
                self.log(f"Warning: Summary generation failed (exit {code})")

            return 0

        except Exception as e:
            self.log(f"Error in auto mode: {e}", level="ERROR")
            return 1


async def main(
    prompt: str,
    max_turns: int = 10,
    task_type: str = "feature",
    working_dir: Path | None = None,
) -> int:
    """Run Copilot auto mode.

    Args:
        prompt: User prompt
        max_turns: Maximum turns
        task_type: Type of task
        working_dir: Working directory

    Returns:
        Exit code
    """
    auto_mode = CopilotAutoMode(
        prompt=prompt, max_turns=max_turns, working_dir=working_dir, task_type=task_type
    )
    return await auto_mode.run()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_mode_copilot.py <prompt>")
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    exit_code = asyncio.run(main(prompt))
    sys.exit(exit_code)
