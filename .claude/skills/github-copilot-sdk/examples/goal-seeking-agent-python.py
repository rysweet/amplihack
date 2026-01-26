#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""
Goal-Seeking Agent using GitHub Copilot SDK

This example demonstrates how to build an autonomous goal-seeking agent
that can adapt its approach based on intermediate results.

The agent receives a high-level goal and:
1. Plans execution phases
2. Executes each phase with custom tools
3. Adapts strategy based on results
4. Self-assesses progress toward goal

Prerequisites:
- pip install github-copilot-sdk pydantic
- Copilot CLI installed and authenticated
"""

import asyncio
import random
import sys

from copilot import CopilotClient
from copilot.generated.session_events import SessionEventType
from copilot.tools import define_tool
from pydantic import BaseModel, Field

# ============================================================================
# PHASE 1: Define Goal-Seeking Tools (Pydantic Models)
# ============================================================================


class PlanExecutionParams(BaseModel):
    """Parameters for planning execution phases."""

    goal: str = Field(description="The high-level goal to achieve")
    current_state: str | None = Field(default=None, description="Current state of progress")
    completed_phases: list[str] | None = Field(default=None, description="List of completed phases")


class ExecutePhaseParams(BaseModel):
    """Parameters for executing a specific phase."""

    phase: str = Field(description="Phase name to execute")
    context: str | None = Field(default=None, description="Additional context for phase")


class AssessProgressParams(BaseModel):
    """Parameters for assessing progress toward goal."""

    goal: str = Field(description="The original goal")
    completed_phases: list[str] = Field(description="Phases completed so far")
    total_phases: int | None = Field(default=4, description="Total phases planned")


# ============================================================================
# PHASE 2: Define Tool Implementations
# ============================================================================


@define_tool(description="Analyze the current goal and plan the next execution phases")
async def plan_execution(params: PlanExecutionParams) -> dict:
    """Goal-seeking logic: determine next phases based on context."""
    phases = []
    completed = params.completed_phases or []

    if "research" not in completed:
        phases.append(
            {
                "phase": "research",
                "description": "Gather information about the problem space",
                "priority": 1,
            }
        )

    if "design" not in completed:
        phases.append(
            {
                "phase": "design",
                "description": "Design solution approach",
                "priority": 2,
            }
        )

    if "implement" not in completed:
        phases.append(
            {
                "phase": "implement",
                "description": "Implement the solution",
                "priority": 3,
            }
        )

    if "verify" not in completed:
        phases.append(
            {
                "phase": "verify",
                "description": "Verify solution meets goal",
                "priority": 4,
            }
        )

    return {
        "goal": params.goal,
        "current_state": params.current_state or "initial",
        "next_phases": phases,
        "recommended_action": (
            f"Execute phase: {phases[0]['phase']}" if phases else "Goal achieved!"
        ),
    }


@define_tool(description="Execute a specific phase and return results")
async def execute_phase(params: ExecutePhaseParams) -> dict:
    """Simulate phase execution with varying success rates."""
    success = random.random() > 0.2  # 80% success rate

    results = {
        "research": {
            "output": "Identified key requirements and constraints",
            "artifacts": ["requirements.md", "constraints.json"],
            "next_steps": ["Proceed to design phase"],
        },
        "design": {
            "output": "Created solution architecture",
            "artifacts": ["architecture.md", "api-spec.yaml"],
            "next_steps": ["Proceed to implementation"],
        },
        "implement": {
            "output": "Implemented core functionality",
            "artifacts": ["src/main.py", "tests/test_main.py"],
            "next_steps": ["Run verification"],
        },
        "verify": {
            "output": "All tests passing, solution validated",
            "artifacts": ["test-results.json"],
            "next_steps": ["Goal complete!"],
        },
    }

    phase_result = results.get(
        params.phase,
        {"output": f"Executed {params.phase}", "artifacts": [], "next_steps": []},
    )

    return {
        "phase": params.phase,
        "success": success,
        **phase_result,
        "failure_reason": None if success else "Recoverable error - retry recommended",
    }


@define_tool(description="Evaluate progress toward the goal and determine if complete")
async def assess_progress(params: AssessProgressParams) -> dict:
    """Assess overall progress toward the goal."""
    completed_count = len(params.completed_phases) if params.completed_phases else 0
    total = params.total_phases or 4
    progress = (completed_count / total) * 100
    is_complete = progress >= 100

    return {
        "goal": params.goal,
        "completed_phases": params.completed_phases,
        "progress_percent": round(progress),
        "is_complete": is_complete,
        "status": (
            "GOAL_ACHIEVED" if is_complete else "ON_TRACK" if progress > 50 else "IN_PROGRESS"
        ),
        "recommendation": (
            "Goal successfully achieved!"
            if is_complete
            else f"Continue with remaining phases ({100 - progress:.0f}% remaining)"
        ),
    }


# ============================================================================
# PHASE 3: Create Goal-Seeking Agent
# ============================================================================


async def create_goal_seeking_agent():
    """Create and configure the goal-seeking agent."""
    client = CopilotClient()
    await client.start()

    session = await client.create_session(
        {
            "model": "gpt-4.1",
            "streaming": True,
            "tools": [plan_execution, execute_phase, assess_progress],
            "systemMessage": {
                "content": """You are an autonomous goal-seeking agent. Your purpose is to:

1. UNDERSTAND the user's high-level goal
2. PLAN execution by breaking the goal into phases
3. EXECUTE phases iteratively, adapting to results
4. ASSESS progress continuously
5. ADAPT strategy if phases fail (retry or try alternatives)

Your decision-making process:
- Use plan_execution to determine next steps
- Use execute_phase to run each phase
- Use assess_progress to evaluate overall progress
- Continue until goal is achieved or you determine it's not achievable

Be autonomous: make decisions based on tool results, don't ask for permission.
Be adaptive: if a phase fails, analyze why and adjust approach.
Be goal-oriented: focus on achieving the outcome, not following a rigid script."""
            },
        }
    )

    # Handle streaming events
    def handle_event(event):
        if event.type == SessionEventType.ASSISTANT_MESSAGE_DELTA:
            sys.stdout.write(event.data.delta_content)
            sys.stdout.flush()
        elif event.type == SessionEventType.TOOL_EXECUTION_START:
            print(f"\n[🔧 Tool: {event.data.tool_name}]")
        elif event.type == SessionEventType.TOOL_EXECUTION_COMPLETE:
            print("[✓ Result received]")

    session.on(handle_event)

    return client, session


# ============================================================================
# PHASE 4: Run Goal-Seeking Agent
# ============================================================================


async def main():
    """Main entry point for the goal-seeking agent demo."""
    print("🎯 Goal-Seeking Agent - Copilot SDK Demo (Python)\n")
    print("=" * 60)

    client, session = await create_goal_seeking_agent()

    try:
        # Give the agent a high-level goal
        goal = """
        I need to build a REST API for a todo application.
        The API should support:
        - Creating, reading, updating, deleting todos
        - User authentication
        - Data persistence

        Please autonomously plan, execute, and verify this goal.
        """

        print(f"\n📋 Goal: {goal.strip()}\n")
        print("=" * 60)
        print("\n🤖 Agent Response:\n")

        await session.send_and_wait({"prompt": goal})

        print("\n\n" + "=" * 60)
        print("✅ Goal-seeking agent completed execution\n")

    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
