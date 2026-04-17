"""Lesson 5 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


def _build_lesson_5() -> Lesson:
    """Lesson 5: Agent Spawning."""
    return Lesson(
        id="L05",
        title="Agent Spawning",
        description="Enable dynamic sub-agent creation at runtime.",
        content=textwrap.dedent("""\
            # Lesson 5: Agent Spawning

            ## What Is Spawning?

            Spawning allows the coordinator to **create new sub-agents at runtime**
            based on the task at hand. Instead of a fixed set of sub-agents, the
            system can dynamically generate specialists.

            ## Enabling Spawning

            ```bash
            amplihack new --file goal.md --sdk copilot --multi-agent --enable-spawning
            ```

            Note: `--enable-spawning` requires `--multi-agent`. If you pass
            `--enable-spawning` alone, the CLI automatically adds `--multi-agent`.

            ## How It Works

            1. Coordinator receives a task that no existing sub-agent can handle.
            2. Coordinator generates a new sub-agent specification.
            3. The new sub-agent is instantiated with appropriate tools and memory.
            4. The sub-agent executes the task and returns results.
            5. Optionally, the spawned agent persists for future similar tasks.

            ## When to Use Spawning

            - **Dynamic domains**: When you cannot predict all needed specialties.
            - **Exploration**: Agent needs to discover what sub-tasks exist.
            - **Scaling**: More sub-agents for parallel work.

            ## When NOT to Use Spawning

            - **Fixed workflows**: When you know exactly what agents you need.
            - **Cost-sensitive**: Each spawn is an additional LLM call.
            - **Determinism**: Spawning introduces non-deterministic behaviour.

            ## Example Output

            ```
            + Goal agent created successfully in 4.2s
              Multi-Agent: Enabled
              Sub-agents: 3
              Spawning: Enabled
            ```
        """),
        prerequisites=["L04"],
        exercises=[
            Exercise(
                id="E05-01",
                instruction=(
                    "Write the full CLI command to generate a spawning-enabled agent "
                    "for a research assistant using the Claude SDK."
                ),
                expected_output=(
                    "amplihack new --file research_assistant.md "
                    "--sdk claude --multi-agent --enable-spawning"
                ),
                hint="You need all three flags: --sdk, --multi-agent, --enable-spawning.",
                validation_fn="validate_spawning_command",
            ),
            Exercise(
                id="E05-02",
                instruction=(
                    "Explain in two sentences why --enable-spawning requires --multi-agent."
                ),
                expected_output=(
                    "Spawning creates new sub-agents at runtime, which only makes sense "
                    "in a multi-agent architecture that has a coordinator to manage them. "
                    "Without a coordinator, there is no mechanism to dispatch tasks to "
                    "spawned agents."
                ),
                hint="Think about what manages the spawned agents.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What happens if you pass --enable-spawning without --multi-agent?",
                correct_answer="The CLI automatically adds --multi-agent and warns you",
                wrong_answers=[
                    "The CLI raises an error",
                    "Spawning is silently ignored",
                    "A single agent with spawning is created",
                ],
                explanation="The CLI prints a warning and enables multi-agent automatically.",
            ),
            QuizQuestion(
                question="Name one scenario where spawning is NOT recommended.",
                correct_answer="Fixed workflows where you know exactly what agents you need",
                wrong_answers=[
                    "Dynamic research tasks",
                    "Exploration of unknown domains",
                    "Parallel processing workloads",
                ],
                explanation="Spawning adds overhead; use fixed agents when tasks are known.",
            ),
            QuizQuestion(
                question="What triggers the coordinator to spawn a new agent?",
                correct_answer="Receiving a task that no existing sub-agent can handle",
                wrong_answers=[
                    "A scheduled timer",
                    "User explicitly requests a new agent",
                    "Memory reaching capacity",
                ],
                explanation="Spawning is triggered by capability gaps in existing agents.",
            ),
        ],
    )
