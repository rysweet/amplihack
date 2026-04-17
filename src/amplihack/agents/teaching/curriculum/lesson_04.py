"""Lesson 4 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


def _build_lesson_4() -> Lesson:
    """Lesson 4: Multi-Agent Architecture."""
    return Lesson(
        id="L04",
        title="Multi-Agent Architecture",
        description="Enable and configure multi-agent setups with coordinators and sub-agents.",
        content=textwrap.dedent("""\
            # Lesson 4: Multi-Agent Architecture

            ## Why Multi-Agent?

            Single agents work well for focused tasks. Multi-agent setups shine
            when you need:
            - **Specialization**: Different agents handle different capabilities.
            - **Coordination**: A coordinator delegates tasks and merges results.
            - **Memory isolation**: Each sub-agent can have its own memory scope.

            ## Enabling Multi-Agent

            ```bash
            amplihack new --file goal.md --sdk copilot --multi-agent
            ```

            This generates:
            - A **coordinator** agent that dispatches tasks.
            - A **memory agent** that manages shared knowledge.
            - One or more **sub-agents** for specialized work.

            ## Generated Structure

            ```
            goal_agents/<name>/
            +-- main.py                # Entry point
            +-- coordinator.yaml       # Coordinator config
            +-- memory_agent.yaml      # Memory agent config
            +-- sub_agents/
            |   +-- researcher.yaml    # Research sub-agent
            |   +-- writer.yaml        # Writing sub-agent
            +-- shared_memory/         # Shared memory store
            ```

            ## How Coordination Works

            1. User sends a request to the coordinator.
            2. Coordinator decomposes the request into sub-tasks.
            3. Each sub-task is dispatched to the appropriate sub-agent.
            4. Sub-agents execute and return results.
            5. Coordinator merges results and responds to the user.

            ## Configuration

            The coordinator config in `coordinator.yaml` defines:
            - Which sub-agents are available.
            - Routing rules (which sub-agent handles which task type).
            - Memory sharing policy.
        """),
        prerequisites=["L02", "L03"],
        exercises=[
            Exercise(
                id="E04-01",
                instruction=(
                    "Write the CLI command to generate a multi-agent system using "
                    "the Claude SDK for an agent that analyzes codebases."
                ),
                expected_output=(
                    "amplihack new --file codebase_analyzer.md --sdk claude --multi-agent"
                ),
                hint="You need both --sdk and --multi-agent flags.",
                validation_fn="validate_multi_agent_command",
            ),
            Exercise(
                id="E04-02",
                instruction=(
                    "Describe what files are generated when --multi-agent is used. "
                    "Name at least four files or directories."
                ),
                expected_output=(
                    "main.py, coordinator.yaml, memory_agent.yaml, "
                    "sub_agents/ directory with researcher.yaml and writer.yaml, "
                    "shared_memory/ directory."
                ),
                hint="Look at the 'Generated Structure' section in the lesson.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What role does the coordinator agent play?",
                correct_answer="Decomposes requests into sub-tasks and dispatches them to sub-agents",
                wrong_answers=[
                    "Stores all memory for the system",
                    "Runs evaluations on sub-agents",
                    "Generates new sub-agents at runtime",
                ],
                explanation="The coordinator is the orchestration layer.",
            ),
            QuizQuestion(
                question="What flag enables multi-agent architecture?",
                correct_answer="--multi-agent",
                wrong_answers=["--agents", "--distributed", "--multi"],
                explanation="The --multi-agent flag activates multi-agent generation.",
            ),
            QuizQuestion(
                question="Can sub-agents share memory?",
                correct_answer="Yes, through the shared_memory/ directory managed by the memory agent",
                wrong_answers=[
                    "No, each agent has isolated memory",
                    "Only the coordinator can access memory",
                    "Memory is not supported in multi-agent mode",
                ],
                explanation="The memory agent manages a shared knowledge store.",
            ),
        ],
    )
