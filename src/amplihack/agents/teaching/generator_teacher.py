"""Teaching agent for the goal-seeking agent generator and eval system.

This agent teaches users how to:
1. Generate goal-seeking agents using the amplihack CLI
2. Configure SDK selection and multi-agent architecture
3. Run progressive evaluations (L1-L12)
4. Use the self-improvement loop
5. Interpret eval results
6. Understand the retrieval architecture (entity, concept, simple, tiered)
7. Understand intent classification and math code generation
8. Run the self-improvement loop with patch proposer and reviewer voting
9. Export and import memory snapshots

Uses a structured curriculum with exercises and quizzes.
Each lesson builds on the previous one, with prerequisite checking.

Philosophy: Ruthless simplicity -- dataclasses for data, plain functions for
logic, no external dependencies beyond the standard library.
"""

from __future__ import annotations

import json
import os
import textwrap
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Exercise:
    """A hands-on exercise for the user."""

    id: str
    instruction: str
    expected_output: str
    hint: str = ""
    validation_fn: str = ""  # Name of validation function


@dataclass
class QuizQuestion:
    """A quiz question to check understanding."""

    question: str
    correct_answer: str
    wrong_answers: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class Lesson:
    """A single lesson in the teaching curriculum."""

    id: str
    title: str
    description: str
    content: str  # Full teaching content (markdown)
    prerequisites: list[str] = field(default_factory=list)
    exercises: list[Exercise] = field(default_factory=list)
    quiz: list[QuizQuestion] = field(default_factory=list)


@dataclass
class LessonResult:
    """Result of a user completing a lesson."""

    lesson_id: str
    exercises_completed: int
    exercises_total: int
    quiz_score: float
    passed: bool
    feedback: str = ""


# ---------------------------------------------------------------------------
# Exercise validators
# ---------------------------------------------------------------------------


def _validate_contains(user_answer: str, required_fragments: list[str]) -> bool:
    """Return True when *user_answer* contains all *required_fragments* (case-insensitive)."""
    lower = user_answer.lower()
    return all(frag.lower() in lower for frag in required_fragments)


def _validate_prompt_file(user_answer: str) -> bool:
    """Check that user_answer looks like a valid prompt.md file."""
    return _validate_contains(user_answer, ["# goal", "constraint", "success"])


def _validate_cli_command(user_answer: str) -> bool:
    """Check that user_answer contains a valid CLI invocation."""
    return _validate_contains(user_answer, ["amplihack", "new", "--file"])


def _validate_sdk_choice(user_answer: str) -> bool:
    """Check that user_answer names one of the four SDKs."""
    sdks = ["copilot", "claude", "microsoft", "mini"]
    lower = user_answer.lower()
    return any(sdk in lower for sdk in sdks)


def _validate_multi_agent_command(user_answer: str) -> bool:
    """Check that user_answer includes --multi-agent flag."""
    return _validate_contains(user_answer, ["--multi-agent"])


def _validate_spawning_command(user_answer: str) -> bool:
    """Check that user_answer includes both --multi-agent and --enable-spawning."""
    return _validate_contains(user_answer, ["--multi-agent", "--enable-spawning"])


def _validate_eval_command(user_answer: str) -> bool:
    """Check that user_answer invokes the progressive test suite."""
    return _validate_contains(user_answer, ["python", "amplihack"]) and _validate_contains(
        user_answer, ["eval"]
    )


def _validate_level_explanation(user_answer: str) -> bool:
    """Check that user_answer mentions at least three eval levels."""
    levels_found = sum(1 for lvl in ["L1", "L2", "L3", "L4", "L5", "L6"] if lvl in user_answer)
    return levels_found >= 3


def _validate_self_improve(user_answer: str) -> bool:
    """Check that user_answer describes the self-improvement loop steps."""
    return _validate_contains(user_answer, ["eval", "analy", "improv"])


def _validate_security_prompt(user_answer: str) -> bool:
    """Check that user_answer contains security-related prompt content."""
    return _validate_contains(user_answer, ["security"]) and _validate_contains(
        user_answer, ["goal"]
    )


def _validate_custom_level(user_answer: str) -> bool:
    """Check that user_answer describes a custom eval level structure."""
    return _validate_contains(user_answer, ["article"]) and _validate_contains(
        user_answer, ["question"]
    )


def _validate_retrieval_strategy(user_answer: str) -> bool:
    """Check that user_answer names retrieval strategies correctly."""
    strategies = ["simple", "entity", "concept", "tiered"]
    lower = user_answer.lower()
    return sum(1 for s in strategies if s in lower) >= 2


def _validate_intent_types(user_answer: str) -> bool:
    """Check that user_answer lists intent types correctly."""
    intents = ["simple_recall", "mathematical", "temporal", "multi_source", "contradiction"]
    lower = user_answer.lower()
    return sum(1 for i in intents if i.replace("_", " ") in lower or i in lower) >= 3


def _validate_patch_proposer(user_answer: str) -> bool:
    """Check that user_answer describes the patch proposer workflow."""
    return _validate_contains(user_answer, ["patch"]) and _validate_contains(
        user_answer, ["review"]
    )


def _validate_runner_config(user_answer: str) -> bool:
    """Check that user_answer describes RunnerConfig fields."""
    return _validate_contains(user_answer, ["iteration"]) and _validate_contains(
        user_answer, ["threshold"]
    )


def _validate_memory_export(user_answer: str) -> bool:
    """Check that user_answer describes memory export/import concepts."""
    return _validate_contains(user_answer, ["export"]) or _validate_contains(
        user_answer, ["snapshot"]
    )


# Map from validation function name to callable
VALIDATORS: dict[str, Any] = {
    "validate_prompt_file": _validate_prompt_file,
    "validate_cli_command": _validate_cli_command,
    "validate_sdk_choice": _validate_sdk_choice,
    "validate_multi_agent_command": _validate_multi_agent_command,
    "validate_spawning_command": _validate_spawning_command,
    "validate_eval_command": _validate_eval_command,
    "validate_level_explanation": _validate_level_explanation,
    "validate_self_improve": _validate_self_improve,
    "validate_security_prompt": _validate_security_prompt,
    "validate_custom_level": _validate_custom_level,
    "validate_retrieval_strategy": _validate_retrieval_strategy,
    "validate_intent_types": _validate_intent_types,
    "validate_patch_proposer": _validate_patch_proposer,
    "validate_runner_config": _validate_runner_config,
    "validate_memory_export": _validate_memory_export,
}

# ---------------------------------------------------------------------------
# Curriculum builder
# ---------------------------------------------------------------------------


def _build_lesson_1() -> Lesson:
    """Lesson 1: Introduction to Goal-Seeking Agents."""
    return Lesson(
        id="L01",
        title="Introduction to Goal-Seeking Agents",
        description="What goal-seeking agents are, why they matter, and the high-level architecture.",
        content=textwrap.dedent("""\
            # Lesson 1: Introduction to Goal-Seeking Agents

            ## What Is a Goal-Seeking Agent?

            A goal-seeking agent is an autonomous program that pursues an objective
            by *learning*, *remembering*, *teaching*, and *applying* knowledge.

            Unlike a static script, it:
            - Extracts facts from content and stores them in persistent memory.
            - Retrieves and verifies stored knowledge.
            - Explains what it knows to other agents (or humans).
            - Uses tools and stored knowledge to solve new problems.

            ## Architecture Overview

            ```
            Prompt (.md) --> PromptAnalyzer --> GoalDefinition
                                                    |
                                        ObjectivePlanner --> ExecutionPlan
                                                    |
                                       SkillSynthesizer --> Skills + SDK Tools
                                                    |
                                        AgentAssembler --> GoalAgentBundle
                                                    |
                                      GoalAgentPackager --> /goal_agents/<name>/
            ```

            The pipeline has five stages:
            1. **Analyze** -- Extract goal, domain, constraints from a markdown file.
            2. **Plan** -- Break the goal into phases with capabilities.
            3. **Synthesize** -- Match skills and SDK-native tools.
            4. **Assemble** -- Build the agent bundle.
            5. **Package** -- Write the bundle to disk as a runnable project.

            ## The GoalSeekingAgent Interface

            Every generated agent implements the same interface regardless of SDK:

            ```python
            class GoalSeekingAgent(ABC):
                def learn_from_content(self, content: str) -> dict[str, Any]
                def answer_question(self, question: str) -> str
                async def run(self, task: str, max_turns: int = 10) -> AgentResult
                def form_goal(self, user_intent: str) -> Goal
                def get_memory_stats(self) -> dict[str, Any]
                def close(self) -> None
            ```

            This means you write your agent logic once and swap SDKs freely.

            ## Think About It

            Before moving on, consider:
            - What kind of tasks would benefit from a learning agent vs. a static script?
            - Why is persistent memory important for goal-seeking behaviour?
        """),
        exercises=[
            Exercise(
                id="E01-01",
                instruction=(
                    "In your own words, list the four capabilities of a goal-seeking agent "
                    "and give a one-sentence example for each."
                ),
                expected_output=(
                    "Learn: Extract facts from articles. "
                    "Remember: Retrieve stored knowledge. "
                    "Teach: Explain topics to other agents. "
                    "Apply: Use tools to solve problems."
                ),
                hint="The four verbs are: learn, remember, teach, apply.",
            ),
            Exercise(
                id="E01-02",
                instruction=(
                    "Draw (or describe) the five-stage pipeline that converts a prompt file "
                    "into a packaged agent. Name each stage and its output."
                ),
                expected_output=(
                    "1. PromptAnalyzer -> GoalDefinition, "
                    "2. ObjectivePlanner -> ExecutionPlan, "
                    "3. SkillSynthesizer -> Skills + SDK Tools, "
                    "4. AgentAssembler -> GoalAgentBundle, "
                    "5. GoalAgentPackager -> runnable project on disk."
                ),
                hint="Check the architecture diagram in the lesson content.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="Which component extracts the goal and domain from a markdown file?",
                correct_answer="PromptAnalyzer",
                wrong_answers=["ObjectivePlanner", "SkillSynthesizer", "AgentAssembler"],
                explanation="PromptAnalyzer reads the .md file and produces a GoalDefinition.",
            ),
            QuizQuestion(
                question="What does the GoalSeekingAgent.answer_question() method do?",
                correct_answer="Retrieves facts from memory and synthesizes an answer using LLM",
                wrong_answers=[
                    "Trains a model on new data",
                    "Writes documentation to disk",
                    "Runs the eval suite",
                ],
                explanation="answer_question() uses intent detection, retrieval strategies, and LLM synthesis.",
            ),
            QuizQuestion(
                question="True or False: Each SDK requires a different agent interface.",
                correct_answer="False -- all SDKs implement the same GoalSeekingAgent interface",
                wrong_answers=[
                    "True -- each SDK has its own API",
                    "True -- Copilot uses a different loop",
                    "True -- Mini has fewer methods",
                ],
                explanation="The whole point of the abstraction is SDK-agnostic code.",
            ),
        ],
    )


def _build_lesson_2() -> Lesson:
    """Lesson 2: Your First Agent (CLI basics)."""
    return Lesson(
        id="L02",
        title="Your First Agent (CLI Basics)",
        description="Write a prompt file and use the CLI to generate your first agent.",
        content=textwrap.dedent("""\
            # Lesson 2: Your First Agent

            ## Step 1 -- Write a Prompt File

            Create a file called `my_goal.md`:

            ```markdown
            # Goal: Learn and Summarize Python Best Practices

            ## Objective
            Build an agent that reads Python style guides and can answer
            questions about best practices.

            ## Domain
            software-engineering

            ## Constraints
            - Focus on PEP-8 and type-hinting
            - Keep answers concise

            ## Success Criteria
            - Can explain PEP-8 naming conventions
            - Can describe when to use type hints
            ```

            The file needs four sections: Goal/Objective, Domain, Constraints,
            and Success Criteria.

            ## Step 2 -- Run the CLI

            ```bash
            amplihack new --file my_goal.md
            ```

            This runs the full pipeline and creates a directory under
            `./goal_agents/` with a runnable `main.py`.

            ## Step 3 -- Run Your Agent

            ```bash
            cd goal_agents/<agent-name>
            python main.py
            ```

            ## What Happens Under the Hood

            1. PromptAnalyzer parses `my_goal.md` and extracts:
               - goal = "Learn and Summarize Python Best Practices"
               - domain = "software-engineering"
               - complexity = "moderate"
            2. ObjectivePlanner creates an ExecutionPlan with phases.
            3. SkillSynthesizer matches skills from `.claude/agents/amplihack/`.
            4. AgentAssembler builds the GoalAgentBundle.
            5. GoalAgentPackager writes the agent directory to disk.
        """),
        prerequisites=["L01"],
        exercises=[
            Exercise(
                id="E02-01",
                instruction=(
                    "Write a complete prompt.md file for an agent that learns about "
                    "Docker container security. Include all four required sections."
                ),
                expected_output=(
                    "# Goal: Learn Docker Container Security\n\n"
                    "## Objective\nBuild an agent that learns Docker security...\n\n"
                    "## Constraints\n- Focus on container isolation...\n\n"
                    "## Success Criteria\n- Can explain Docker namespaces..."
                ),
                hint="You need: # Goal, ## Constraints, ## Success Criteria at minimum.",
                validation_fn="validate_prompt_file",
            ),
            Exercise(
                id="E02-02",
                instruction=(
                    "Write the exact CLI command to generate an agent from "
                    "a file called docker_security.md with verbose output."
                ),
                expected_output="amplihack new --file docker_security.md --verbose",
                hint="Use the --file flag and --verbose for extra output.",
                validation_fn="validate_cli_command",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What are the four required sections in a prompt.md file?",
                correct_answer="Goal/Objective, Domain, Constraints, Success Criteria",
                wrong_answers=[
                    "Title, Body, Footer, Appendix",
                    "Input, Output, Config, Tests",
                    "Goal, Steps, Results, Metrics",
                ],
                explanation="The PromptAnalyzer expects these specific sections.",
            ),
            QuizQuestion(
                question="Where does the CLI output the generated agent by default?",
                correct_answer="./goal_agents/<agent-name>/",
                wrong_answers=[
                    "./agents/output/",
                    "./build/agents/",
                    "~/.amplihack/agents/",
                ],
                explanation="The default output directory is ./goal_agents/.",
            ),
            QuizQuestion(
                question="Which flag overrides the default output directory?",
                correct_answer="--output or -o",
                wrong_answers=["--dir", "--target", "--path"],
                explanation="Use --output or -o to specify a custom output path.",
            ),
        ],
    )


def _build_lesson_3() -> Lesson:
    """Lesson 3: SDK Selection Guide."""
    return Lesson(
        id="L03",
        title="SDK Selection Guide",
        description="Understand the four SDK backends and when to use each one.",
        content=textwrap.dedent("""\
            # Lesson 3: SDK Selection Guide

            The agent generator supports four SDK backends. Each has different
            strengths and trade-offs.

            ## Copilot SDK (default)

            ```bash
            amplihack new --file goal.md --sdk copilot
            ```

            - **Strengths**: Tight GitHub integration, file_system/git/web tools.
            - **Best for**: Repository automation, code review agents, CI/CD.
            - **Trade-off**: Requires GitHub Copilot access.

            ## Claude SDK

            ```bash
            amplihack new --file goal.md --sdk claude
            ```

            - **Strengths**: Rich tool set (bash, read/write/edit files, glob, grep).
            - **Best for**: General-purpose agents, code analysis, file manipulation.
            - **Trade-off**: Needs ANTHROPIC_API_KEY.

            ## Microsoft Agent Framework

            ```bash
            amplihack new --file goal.md --sdk microsoft
            ```

            - **Strengths**: Enterprise integration, AI function primitives.
            - **Best for**: Enterprise workflows, Azure-connected agents.
            - **Trade-off**: Heavier setup, fewer built-in tools.

            ## Mini SDK

            ```bash
            amplihack new --file goal.md --sdk mini
            ```

            - **Strengths**: Lightweight, minimal dependencies, fast iteration.
            - **Best for**: Prototyping, testing, learning, eval benchmarks.
            - **Trade-off**: No native tools -- relies on learning tools only.

            ## Decision Matrix

            | Need                        | Recommended SDK |
            |-----------------------------|-----------------|
            | GitHub automation           | copilot         |
            | File analysis / code tools  | claude          |
            | Enterprise / Azure          | microsoft       |
            | Prototyping / eval          | mini            |
            | Maximum tool coverage       | claude          |
            | Minimum setup               | mini            |

            ## Native Tools by SDK

            - **claude**: bash, read_file, write_file, edit_file, glob, grep
            - **copilot**: file_system, git, web_requests
            - **microsoft**: ai_function
            - **mini**: (none -- learning tools only)
        """),
        prerequisites=["L02"],
        exercises=[
            Exercise(
                id="E03-01",
                instruction=(
                    "A teammate needs an agent that reviews GitHub PRs and posts comments. "
                    "Which SDK should they use? Write the CLI command."
                ),
                expected_output=(
                    "copilot -- it has GitHub integration.\n"
                    "amplihack new --file pr_reviewer.md --sdk copilot"
                ),
                hint="Think about which SDK has git and GitHub tooling built in.",
                validation_fn="validate_sdk_choice",
            ),
            Exercise(
                id="E03-02",
                instruction=(
                    "You want to quickly prototype a learning agent with no API keys. "
                    "Which SDK and why? Write the command."
                ),
                expected_output=(
                    "mini -- minimal dependencies, no API keys needed.\n"
                    "amplihack new --file prototype.md --sdk mini"
                ),
                hint="Which SDK has zero external dependencies?",
                validation_fn="validate_sdk_choice",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="Which SDK has the most built-in tools?",
                correct_answer="claude (bash, read_file, write_file, edit_file, glob, grep)",
                wrong_answers=[
                    "copilot (only 3 tools)",
                    "microsoft (only ai_function)",
                    "mini (no tools)",
                ],
                explanation="Claude SDK exposes 6 native tools for file and system operations.",
            ),
            QuizQuestion(
                question="When should you choose the mini SDK?",
                correct_answer="For prototyping, testing, or running eval benchmarks quickly",
                wrong_answers=[
                    "When you need file operations",
                    "When you need GitHub integration",
                    "When deploying to production",
                ],
                explanation="Mini is lightweight with zero dependencies, ideal for dev loops.",
            ),
            QuizQuestion(
                question="What happens if you specify --sdk copilot without GitHub access?",
                correct_answer="The agent may fail at runtime when trying to use GitHub tools",
                wrong_answers=[
                    "The CLI refuses to generate",
                    "It silently falls back to mini",
                    "It generates but without tools",
                ],
                explanation=(
                    "The generator produces the agent bundle regardless; "
                    "runtime failures happen when tools cannot authenticate."
                ),
            ),
        ],
    )


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


def _build_lesson_6() -> Lesson:
    """Lesson 6: Running Evaluations."""
    return Lesson(
        id="L06",
        title="Running Evaluations",
        description="Run the progressive evaluation suite against your agent.",
        content=textwrap.dedent("""\
            # Lesson 6: Running Evaluations

            ## Why Evaluate?

            You cannot improve what you cannot measure. The eval system provides
            objective scores for your agent across multiple cognitive dimensions.

            ## The Progressive Test Suite

            Run all 12 levels:

            ```bash
            python -m amplihack.eval.progressive_test_suite \\
                --agent-name my-agent \\
                --output-dir eval_results/ \\
                --sdk mini
            ```

            Run specific levels:

            ```bash
            python -m amplihack.eval.progressive_test_suite \\
                --agent-name my-agent \\
                --output-dir eval_results/ \\
                --levels L1 L2 L3 \\
                --sdk mini
            ```

            ## Understanding Output

            The suite produces a JSON report:

            ```json
            {
                "agent_name": "my-agent",
                "overall_score": 0.82,
                "level_scores": {
                    "L1": 0.95,
                    "L2": 0.80,
                    "L3": 0.70,
                    "L4": 0.85,
                    "L5": 0.90,
                    "L6": 0.75
                },
                "pass_threshold": 0.70,
                "passed": true
            }
            ```

            - **overall_score**: Weighted average across all levels.
            - **level_scores**: Individual score per level (0.0 to 1.0).
            - **pass_threshold**: Minimum score to pass (default 0.70).

            ## SDK-Specific Eval Loop

            Compare SDKs head-to-head:

            ```bash
            python -m amplihack.eval.sdk_eval_loop \\
                --sdks mini claude copilot \\
                --loops 3 \\
                --levels L1 L2 L3
            ```

            This runs 3 iterations per SDK and produces a comparison report.

            ## Multi-Seed Evaluation

            For statistical significance, run multiple seeds:

            ```bash
            python -m amplihack.eval.long_horizon_multi_seed \\
                --seeds 3 \\
                --agent-name my-agent
            ```

            Use 3-run medians to smooth out LLM stochasticity.
        """),
        prerequisites=["L02"],
        exercises=[
            Exercise(
                id="E06-01",
                instruction=(
                    "Write the command to evaluate an agent called 'security-scanner' "
                    "on levels L1 through L6 using the mini SDK, saving results to ./results/."
                ),
                expected_output=(
                    "python -m amplihack.eval.progressive_test_suite "
                    "--agent-name security-scanner "
                    "--output-dir ./results/ "
                    "--levels L1 L2 L3 L4 L5 L6 "
                    "--sdk mini"
                ),
                hint="Use --agent-name, --output-dir, --levels, and --sdk flags.",
                validation_fn="validate_eval_command",
            ),
            Exercise(
                id="E06-02",
                instruction=(
                    "An agent scored L1=0.95, L2=0.60, L3=0.45, L4=0.80. "
                    "Which levels need the most improvement and why?"
                ),
                expected_output=(
                    "L3 (0.45) needs the most work -- it tests temporal reasoning. "
                    "L2 (0.60) also needs improvement -- it tests multi-source synthesis. "
                    "L1 and L4 are passing (above 0.70 threshold)."
                ),
                hint="The pass threshold is 0.70. Look for scores below it.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What is the default pass threshold for eval levels?",
                correct_answer="0.70 (70%)",
                wrong_answers=["0.50 (50%)", "0.80 (80%)", "0.90 (90%)"],
                explanation="Levels scoring 0.70 or above are considered passing.",
            ),
            QuizQuestion(
                question="Why use 3-run medians instead of single runs?",
                correct_answer="To smooth out LLM stochasticity -- single runs are unreliable",
                wrong_answers=[
                    "To speed up evaluation",
                    "Because the API rate-limits single runs",
                    "To generate more training data",
                ],
                explanation="LLM outputs vary between runs; medians give stable measurements.",
            ),
            QuizQuestion(
                question="What does the SDK eval loop compare?",
                correct_answer="Performance of the same agent across different SDK backends",
                wrong_answers=[
                    "Different agents on the same SDK",
                    "Different eval levels against each other",
                    "Training data quality across SDKs",
                ],
                explanation="It runs the same eval against multiple SDKs for comparison.",
            ),
        ],
    )


def _build_lesson_7() -> Lesson:
    """Lesson 7: Understanding Eval Levels."""
    return Lesson(
        id="L07",
        title="Understanding Eval Levels L1-L12",
        description="Deep dive into what each evaluation level tests and measures.",
        content=textwrap.dedent("""\
            # Lesson 7: Understanding Eval Levels

            ## Core Levels (L1-L6)

            | Level | Name                   | What It Tests                         |
            |-------|------------------------|---------------------------------------|
            | L1    | Single Source Recall    | Direct fact retrieval from one source  |
            | L2    | Multi-Source Synthesis  | Combining info from multiple articles  |
            | L3    | Temporal Reasoning     | Tracking changes over time             |
            | L4    | Procedural Learning    | Learning and applying step-by-step     |
            | L5    | Contradiction Handling | Detecting conflicting information      |
            | L6    | Incremental Learning   | Updating knowledge with new info       |

            ## Advanced Levels (L7-L12)

            | Level | Name                    | What It Tests                          |
            |-------|-------------------------|----------------------------------------|
            | L7    | Knowledge Transfer      | Teaching another agent what was learned |
            | L8    | Metacognition           | Knowing what it knows and does not know |
            | L9    | Causal Reasoning        | Understanding why things happened       |
            | L10   | Counterfactual          | Reasoning about "what if" scenarios     |
            | L11   | Novel Skill Acquisition | Learning entirely new skills from docs  |
            | L12   | Far Transfer            | Applying reasoning to a new domain      |

            ## Difficulty Progression

            Levels are ordered by cognitive complexity:
            - **L1-L3**: Foundation (recall, synthesis, time)
            - **L4-L6**: Application (procedures, conflicts, updates)
            - **L7-L9**: Higher-order (teaching, metacognition, causality)
            - **L10-L12**: Transfer (counterfactuals, novel skills, cross-domain)

            ## How Each Level Works

            Each level has:
            1. **Articles**: Content the agent must learn.
            2. **Questions**: Questions the agent must answer from memory.
            3. **Expected answers**: Reference answers for grading.
            4. **Reasoning type**: The cognitive skill being tested.

            ## Grading

            The grader compares the agent's answer against the expected answer using
            semantic similarity. Scores range from 0.0 (completely wrong) to 1.0
            (perfect match). The grader accounts for paraphrasing -- exact wording
            is not required.
        """),
        prerequisites=["L06"],
        exercises=[
            Exercise(
                id="E07-01",
                instruction=(
                    "For each of L1, L3, L5, and L7, write one sentence explaining "
                    "what cognitive skill it tests. Include the level IDs."
                ),
                expected_output=(
                    "L1: Tests direct fact retrieval from a single source. "
                    "L3: Tests tracking changes and computing differences over time. "
                    "L5: Tests detecting and reasoning about conflicting information. "
                    "L7: Tests teaching learned knowledge to another agent."
                ),
                hint="Refer to the level tables in the lesson content.",
                validation_fn="validate_level_explanation",
            ),
            Exercise(
                id="E07-02",
                instruction=(
                    "Your agent scores 0.90 on L1 but 0.30 on L3. "
                    "What does this tell you about the agent's capabilities?"
                ),
                expected_output=(
                    "The agent is good at basic recall (L1) but poor at temporal "
                    "reasoning (L3). It likely stores facts but cannot track how "
                    "those facts change over time or compute differences between "
                    "time-stamped data."
                ),
                hint="L1 is recall; L3 is about time-based changes.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="Which level tests whether an agent can detect conflicting information?",
                correct_answer="L5 -- Contradiction Handling",
                wrong_answers=[
                    "L2 -- Multi-Source Synthesis",
                    "L6 -- Incremental Learning",
                    "L8 -- Metacognition",
                ],
                explanation="L5 presents two sources with conflicting claims.",
            ),
            QuizQuestion(
                question="What is the difference between L11 and L12?",
                correct_answer=(
                    "L11 tests learning new skills from documentation; "
                    "L12 tests applying learned reasoning to a completely different domain"
                ),
                wrong_answers=[
                    "L11 is harder than L12",
                    "L11 is about code; L12 is about text",
                    "They test the same thing with different data",
                ],
                explanation="L11 = novel skill acquisition; L12 = far transfer.",
            ),
            QuizQuestion(
                question="How does the grader score answers?",
                correct_answer=(
                    "Semantic similarity against expected answers (0.0-1.0), "
                    "accounting for paraphrasing"
                ),
                wrong_answers=[
                    "Exact string match only",
                    "Keyword counting",
                    "Manual human review",
                ],
                explanation="The grader uses LLM-based semantic comparison.",
            ),
            QuizQuestion(
                question="Which levels form the 'Foundation' tier?",
                correct_answer="L1, L2, L3 (recall, synthesis, temporal reasoning)",
                wrong_answers=[
                    "L1, L4, L7",
                    "L1, L2, L3, L4, L5, L6",
                    "L7, L8, L9",
                ],
                explanation="Foundation = L1-L3, Application = L4-L6.",
            ),
        ],
    )


def _build_lesson_8() -> Lesson:
    """Lesson 8: Self-Improvement Loop."""
    return Lesson(
        id="L08",
        title="Self-Improvement Loop",
        description="Use the automated eval-analyze-improve cycle to iterate on agent quality.",
        content=textwrap.dedent("""\
            # Lesson 8: Self-Improvement Loop

            ## The Closed Loop

            The self-improvement system runs a cycle:

            ```
            EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE
            ```

            1. **EVAL**: Run L1-L12 to get baseline scores.
            2. **ANALYZE**: ErrorAnalyzer identifies failure patterns.
            3. **RESEARCH**: Generate hypothesis, gather evidence, consider counter-args.
            4. **IMPROVE**: Apply the best change.
            5. **RE-EVAL**: Run the same levels again.
            6. **DECIDE**: Accept if improved, revert if regressed.

            ## Running the Loop

            ```bash
            python -m amplihack.eval.self_improve.runner \\
                --sdk mini \\
                --iterations 5 \\
                --output-dir improve_results/ \\
                --agent-name my-agent
            ```

            Key CLI flags:
            - `--sdk`: SDK to evaluate (mini, claude, copilot, microsoft)
            - `--iterations`: Max improvement iterations (default: 5)
            - `--improvement-threshold`: Min % improvement to commit (default: 2.0)
            - `--regression-tolerance`: Max % regression on any level (default: 5.0)
            - `--levels`: Levels to evaluate (default: L1 L2 L3 L4 L5 L6)
            - `--dry-run`: Evaluate and analyze without applying changes

            ## Key Principles

            - **Measure first, change second**: Never make a change without a baseline.
            - **Every change has a hypothesis**: "L3 fails because temporal ordering
              is lost during retrieval" is a hypothesis.
            - **Revert on regression**: If a change hurts other levels, revert it.
            - **Log everything**: Every iteration is recorded for reproducibility.

            ## What the Error Analyzer Finds

            The ErrorAnalyzer produces an `ErrorAnalysis` with:
            - **failure_mode**: e.g., "retrieval_insufficient", "temporal_ordering_wrong",
              "intent_misclassification", "synthesis_hallucination"
            - **affected_level**: Which level failed (e.g., "L3").
            - **affected_component**: Which code component to fix
              (e.g., "learning_agent.py::_synthesize_with_llm").
            - **prompt_template**: Which prompt template to modify.

            ## Example Iteration

            ```
            Iteration 1:
              Baseline: L1=0.83, L2=0.67, L3=0.50
              Analysis: L3 fails because temporal ordering is lost
              Change: Add timestamp-based sorting to retrieval
              Post-change: L1=0.83, L2=0.70, L3=0.75
              Result: ACCEPT (+0.05 L2, +0.25 L3, no regression)
            ```

            ## Historical Results

            A 5-loop cycle improved overall scores from 83.2% to 96.6% (+13.4%).
            The biggest single win was source-specific fact filtering (+53.3% on L2).
        """),
        prerequisites=["L06", "L07"],
        exercises=[
            Exercise(
                id="E08-01",
                instruction=(
                    "Describe the six steps of the self-improvement loop in order. "
                    "For each step, write one sentence about what it does."
                ),
                expected_output=(
                    "1. EVAL: Run progressive test suite for baseline scores. "
                    "2. ANALYZE: ErrorAnalyzer identifies failure patterns. "
                    "3. RESEARCH: Generate hypothesis and gather evidence. "
                    "4. IMPROVE: Apply the best code change. "
                    "5. RE-EVAL: Run the same tests again. "
                    "6. DECIDE: Accept improvement or revert regression."
                ),
                hint="The steps are: EVAL, ANALYZE, RESEARCH, IMPROVE, RE-EVAL, DECIDE.",
                validation_fn="validate_self_improve",
            ),
            Exercise(
                id="E08-02",
                instruction=(
                    "An agent has baseline L1=0.90, L2=0.40. After a change, "
                    "L1=0.70, L2=0.80. Should you accept or revert? Explain why."
                ),
                expected_output=(
                    "REVERT. While L2 improved by +0.40, L1 regressed by -0.20. "
                    "The self-improvement loop requires no regression on passing levels. "
                    "A change that improves one level but breaks another is not acceptable."
                ),
                hint="Check if any level regressed below its baseline.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What is the first step in the self-improvement loop?",
                correct_answer="EVAL -- run the test suite to establish a baseline",
                wrong_answers=[
                    "ANALYZE -- look at existing code",
                    "IMPROVE -- make a change",
                    "RESEARCH -- hypothesize about failures",
                ],
                explanation="You must measure before you can improve.",
            ),
            QuizQuestion(
                question="When should a change be reverted?",
                correct_answer="When it causes regression on any previously passing level",
                wrong_answers=[
                    "When the overall score drops by more than 10%",
                    "When the change is too complex",
                    "Never -- all changes are kept",
                ],
                explanation="The loop is conservative: any regression means revert.",
            ),
            QuizQuestion(
                question="What did the biggest single improvement in historical results fix?",
                correct_answer="Source-specific fact filtering, improving L2 by 53.3%",
                wrong_answers=[
                    "Temporal ordering for L3",
                    "Contradiction detection for L5",
                    "Memory retrieval threshold",
                ],
                explanation="L2 multi-source synthesis benefited most from better filtering.",
            ),
        ],
    )


def _build_lesson_9() -> Lesson:
    """Lesson 9: Advanced -- Security Domain Agents."""
    return Lesson(
        id="L09",
        title="Advanced: Security Domain Agents",
        description="Generate agents specialized for security analysis with domain-specific eval.",
        content=textwrap.dedent("""\
            # Lesson 9: Security Domain Agents

            ## Domain-Specific Agents

            The agent generator can produce agents specialized for specific domains.
            Security analysis is a common use case that benefits from:
            - Domain-specific knowledge bases.
            - Security-focused eval questions.
            - Threat modeling capabilities.

            ## Creating a Security Agent

            ```markdown
            # Goal: Security Vulnerability Analyzer

            ## Objective
            Analyze codebases for common vulnerabilities (OWASP Top 10,
            CWE-25) and generate remediation recommendations.

            ## Domain
            security-analysis

            ## Constraints
            - Must identify injection, XSS, CSRF, and auth issues
            - Must provide severity ratings (Critical/High/Medium/Low)
            - Must cite CWE numbers for each finding

            ## Success Criteria
            - Identifies SQL injection in test code
            - Provides correct CWE references
            - Generates actionable remediation steps
            ```

            ```bash
            amplihack new --file security_analyzer.md \\
                --sdk claude --multi-agent --enable-memory
            ```

            ## Domain-Specific Eval

            The eval system supports domain-specific test suites:

            ```bash
            python -m amplihack.eval.domain_eval_harness \\
                --domain security \\
                --agent-name security-analyzer \\
                --output-dir security_eval/
            ```

            ## Security Eval Dimensions

            Security agents are evaluated on:
            1. **Vulnerability detection**: Can it find known vulnerabilities?
            2. **Classification accuracy**: Does it assign correct CWE numbers?
            3. **Severity assessment**: Are severity ratings appropriate?
            4. **Remediation quality**: Are fixes actionable and correct?

            ## Multi-Agent Security Setup

            A security-focused multi-agent system might have:
            - **Coordinator**: Dispatches files to sub-agents.
            - **Static analyzer**: Scans code patterns.
            - **Dependency checker**: Reviews package vulnerabilities.
            - **Compliance auditor**: Checks against security standards.
        """),
        prerequisites=["L03", "L04", "L06"],
        exercises=[
            Exercise(
                id="E09-01",
                instruction=(
                    "Write a complete prompt.md for a security agent that focuses on "
                    "API security. Include Goal, Domain, Constraints, and Success Criteria."
                ),
                expected_output=(
                    "# Goal: API Security Analyzer\n\n"
                    "## Domain\nsecurity-analysis\n\n"
                    "## Constraints\n- Focus on auth, rate limiting, input validation\n\n"
                    "## Success Criteria\n- Detects missing authentication on endpoints"
                ),
                hint="Include OWASP-relevant constraints and measurable success criteria.",
                validation_fn="validate_security_prompt",
            ),
            Exercise(
                id="E09-02",
                instruction=(
                    "Write the CLI command to generate a multi-agent security analyzer "
                    "with memory enabled, using the Claude SDK."
                ),
                expected_output=(
                    "amplihack new --file api_security.md "
                    "--sdk claude --multi-agent --enable-memory"
                ),
                hint="Combine --sdk, --multi-agent, and --enable-memory flags.",
                validation_fn="validate_multi_agent_command",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What four dimensions are security agents evaluated on?",
                correct_answer=(
                    "Vulnerability detection, classification accuracy, "
                    "severity assessment, remediation quality"
                ),
                wrong_answers=[
                    "Speed, accuracy, coverage, cost",
                    "Input, output, throughput, latency",
                    "Detection, prevention, response, recovery",
                ],
                explanation="These match the security eval harness dimensions.",
            ),
            QuizQuestion(
                question="Why use --enable-memory for a security agent?",
                correct_answer=(
                    "To persist vulnerability knowledge across sessions and build "
                    "a cumulative understanding of the codebase's security posture"
                ),
                wrong_answers=[
                    "Memory is always required",
                    "To cache API responses",
                    "To store user credentials securely",
                ],
                explanation="Persistent memory lets the agent build domain knowledge.",
            ),
            QuizQuestion(
                question="Which SDK is best suited for security agents that need file access?",
                correct_answer="claude -- it has read_file, write_file, grep, and bash tools",
                wrong_answers=[
                    "mini -- it is the simplest",
                    "copilot -- it has git integration",
                    "microsoft -- it has enterprise features",
                ],
                explanation="Claude SDK's file tools are essential for code analysis.",
            ),
        ],
    )


def _build_lesson_10() -> Lesson:
    """Lesson 10: Advanced -- Custom Eval Levels."""
    return Lesson(
        id="L10",
        title="Advanced: Custom Eval Levels",
        description="Create custom evaluation levels for your specific domain.",
        content=textwrap.dedent("""\
            # Lesson 10: Custom Eval Levels

            ## Why Custom Levels?

            The built-in L1-L12 levels test general cognitive capabilities. But
            your domain may need specialized evaluation:
            - **Medical**: Test diagnosis reasoning from symptoms.
            - **Legal**: Test contract clause interpretation.
            - **Security**: Test vulnerability classification accuracy.

            ## Anatomy of a Test Level

            Each level is defined with three data classes:

            ```python
            from amplihack_eval.data.progressive_levels import TestLevel, TestArticle, TestQuestion

            CUSTOM_LEVEL = TestLevel(
                level_id="CUSTOM-1",
                level_name="Domain-Specific Reasoning",
                description="Tests reasoning specific to your domain",
                articles=[
                    TestArticle(
                        title="Article Title",
                        content="The content the agent must learn...",
                        url="https://example.com/article",
                        published="2026-02-20T10:00:00Z",
                    ),
                ],
                questions=[
                    TestQuestion(
                        question="What should the agent be able to answer?",
                        expected_answer="The reference answer for grading",
                        level="CUSTOM-1",
                        reasoning_type="domain_specific_reasoning",
                    ),
                ],
            )
            ```

            ## Step-by-Step: Creating a Custom Level

            1. **Define articles**: Write or collect domain content.
            2. **Write questions**: Create questions at the right difficulty.
            3. **Set expected answers**: Write reference answers for grading.
            4. **Choose reasoning types**: Label each question's cognitive skill.
            5. **Register the level**: Add it to your eval configuration.
            6. **Run and iterate**: Test the level with your agent.

            ## Tips for Good Eval Levels

            - **One skill per question**: Do not mix temporal reasoning with synthesis.
            - **Clear expected answers**: The grader uses semantic similarity;
              vague answers produce unreliable grades.
            - **Multiple questions per level**: At least 3 questions for stable scores.
            - **Progressive difficulty**: Start with recall, then synthesis, then reasoning.

            ## Integrating Custom Levels

            ```python
            from amplihack.eval.progressive_test_suite import ProgressiveConfig

            config = ProgressiveConfig(
                output_dir="./custom_eval/",
                agent_name="my-agent",
                levels_to_run=["CUSTOM-1", "CUSTOM-2"],
                sdk="mini",
            )
            ```
        """),
        prerequisites=["L07", "L08"],
        exercises=[
            Exercise(
                id="E10-01",
                instruction=(
                    "Create a custom eval level for testing whether an agent "
                    "can learn cooking recipes. Include at least one article "
                    "and two questions with expected answers."
                ),
                expected_output=(
                    'TestLevel(level_id="COOKING-1", ..., '
                    "articles=[TestArticle(title='Pasta Recipe', ...)], "
                    "questions=[TestQuestion(question='What temperature...', "
                    "expected_answer='...'), ...])"
                ),
                hint="Use TestLevel, TestArticle, TestQuestion dataclasses.",
                validation_fn="validate_custom_level",
            ),
            Exercise(
                id="E10-02",
                instruction=(
                    "What reasoning_type would you assign to these questions?\n"
                    "a) 'What ingredient is used for the sauce?'\n"
                    "b) 'How does this recipe differ from the Italian version?'\n"
                    "c) 'If you substitute butter for oil, what changes?'"
                ),
                expected_output=(
                    "a) direct_recall -- simple fact retrieval.\n"
                    "b) cross_source_synthesis -- comparing two sources.\n"
                    "c) counterfactual_reasoning -- hypothetical scenario."
                ),
                hint="Match each question to the closest L1-L12 reasoning type.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What three data classes define a custom eval level?",
                correct_answer="TestLevel, TestArticle, TestQuestion",
                wrong_answers=[
                    "Level, Article, Question",
                    "EvalConfig, TestCase, Answer",
                    "TestSuite, TestSource, TestAssertion",
                ],
                explanation="These are the exact class names from amplihack_eval.data.progressive_levels.",
            ),
            QuizQuestion(
                question="How many questions should a custom level have at minimum?",
                correct_answer="At least 3 for stable scores",
                wrong_answers=["Just 1 is fine", "At least 10", "At least 20"],
                explanation="Fewer than 3 questions makes scores unreliable.",
            ),
            QuizQuestion(
                question="Why should each question test only one cognitive skill?",
                correct_answer=(
                    "Mixing skills makes it impossible to diagnose which "
                    "capability failed when the agent gets it wrong"
                ),
                wrong_answers=[
                    "The grader cannot handle mixed skills",
                    "It is a Python limitation",
                    "Single-skill questions are faster to grade",
                ],
                explanation="Diagnostic clarity requires isolated skill testing.",
            ),
            QuizQuestion(
                question="What happens if expected answers are vague?",
                correct_answer="The grader produces unreliable scores due to ambiguous similarity",
                wrong_answers=[
                    "The grader rejects the test level",
                    "Scores are always 1.0",
                    "The agent is penalized extra",
                ],
                explanation="Semantic similarity grading needs clear reference answers.",
            ),
        ],
    )


def _build_lesson_11() -> Lesson:
    """Lesson 11: Retrieval Architecture."""
    return Lesson(
        id="L11",
        title="Retrieval Architecture",
        description="Understand the four retrieval strategies and when each is used.",
        content=textwrap.dedent("""\
            # Lesson 11: Retrieval Architecture

            ## The Retrieval Problem

            A goal-seeking agent stores facts in memory. When answering a question,
            it must decide *which* facts to retrieve. Different questions require
            different retrieval strategies.

            ## Four Retrieval Strategies

            ### 1. Simple Retrieval

            ```python
            def _simple_retrieval(self, question: str) -> list[dict]:
            ```

            - **How it works**: Returns all facts from memory (up to 15,000).
            - **Used when**: KB has <= 500 facts, or intent is in `SIMPLE_INTENTS`
              (simple_recall, incremental_update, contradiction_resolution,
              multi_source_synthesis).
            - **Why**: For small KBs, the LLM can handle all facts in context.
              Keyword-based filtering can miss facts whose text does not match
              the query. Simple retrieval guarantees completeness.

            ### 2. Entity Retrieval

            ```python
            def _entity_retrieval(self, question: str) -> list[dict]:
            ```

            - **How it works**: Extracts proper nouns from the question using regex,
              then calls `memory.retrieve_by_entity(name)` for each entity.
            - **Used when**: Question contains proper nouns (capitalized names) and
              KB has > 500 facts.
            - **Why**: Large KBs cannot fit in context. Entity retrieval targets
              the specific person/project the question is about.
            - **Fallback**: If entity retrieval returns nothing, falls back to
              simple retrieval + reranking.

            ### 3. Concept Retrieval

            ```python
            def _concept_retrieval(self, question: str) -> list[dict]:
            ```

            - **How it works**: Extracts key noun phrases (not proper nouns) by
              filtering stop-words, then searches memory with bigrams and unigrams.
            - **Used when**: Question has no proper nouns but has domain concepts.
            - **Why**: Handles questions like "What is the temperature threshold?"
              where there are no named entities but specific domain terms.

            ### 4. Tiered Retrieval (Progressive Summarization)

            ```python
            def _tiered_retrieval(self, question: str, all_facts: list) -> list:
            ```

            - **How it works**: Splits facts into three tiers by recency:
              - Tier 1 (most recent 200): returned verbatim
              - Tier 2 (facts 201-1000): entity-level summaries
              - Tier 3 (facts 1000+): topic-level summaries
            - **Used when**: KB has > 1000 facts and simple retrieval is triggered.
            - **Why**: Keeps recent facts detailed while compressing old facts.
              Summaries preserve numbers, names, dates, and status values.

            ## Retrieval Selection Flow

            ```
            answer_question()
                |
                +-- _detect_intent() -> intent_type
                |
                +-- if intent_type in AGGREGATION_INTENTS:
                |       -> _aggregation_retrieval() (Cypher graph queries)
                |
                +-- elif intent_type in SIMPLE_INTENTS or KB <= 500:
                |       -> _simple_retrieval()
                |           |
                |           +-- if KB > 1000: _tiered_retrieval()
                |
                +-- else (large KB, complex intent):
                        -> _entity_retrieval()
                        |
                        +-- if empty: _simple_retrieval() + rerank
            ```

            ## Reranking

            After retrieval, `rerank_facts_by_query()` sorts facts by relevance
            to the question using token overlap scoring. This ensures the most
            relevant facts appear first in the LLM context.

            ## Source-Specific Filtering

            If the question references a specific article (e.g., "mentioned in the
            athlete achievements article"), `_filter_facts_by_source_reference()`
            extracts the source name and filters facts whose metadata has a matching
            `source_label`. This filtered subset is passed to the LLM as extra context.
        """),
        prerequisites=["L07"],
        exercises=[
            Exercise(
                id="E11-01",
                instruction=(
                    "List the four retrieval strategies (simple, entity, concept, tiered) "
                    "and write one sentence for each explaining when it is used."
                ),
                expected_output=(
                    "Simple: Used for small KBs (<=500 facts) or simple intents; returns all facts. "
                    "Entity: Used when question has proper nouns and KB > 500; targets named entities. "
                    "Concept: Used when no proper nouns but domain terms exist; searches bigrams. "
                    "Tiered: Used when KB > 1000 facts; progressive summarization by recency."
                ),
                hint="Each strategy targets a different KB size and question type.",
                validation_fn="validate_retrieval_strategy",
            ),
            Exercise(
                id="E11-02",
                instruction=(
                    "An agent with 2000 facts receives the question 'What is Sarah Chen's role?'. "
                    "Trace the retrieval path: which strategy is tried first, and what happens "
                    "if it returns no results?"
                ),
                expected_output=(
                    "1. Intent detection classifies as simple_recall. "
                    "2. But KB has 2000 facts (> 500), so entity retrieval is tried first. "
                    "3. 'Sarah Chen' is extracted as a proper noun. "
                    "4. memory.retrieve_by_entity('Sarah Chen') is called. "
                    "5. If entity retrieval returns nothing, fallback to simple retrieval + rerank."
                ),
                hint="Check the retrieval selection flow diagram in the lesson.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What is the KB size threshold where simple retrieval always applies?",
                correct_answer="500 facts or fewer -- all facts are returned verbatim",
                wrong_answers=[
                    "100 facts or fewer",
                    "1000 facts or fewer",
                    "There is no threshold -- intent determines it",
                ],
                explanation="For KBs <= 500 facts, simple retrieval is always used regardless of intent.",
            ),
            QuizQuestion(
                question="What does tiered retrieval do with facts older than the most recent 200?",
                correct_answer="Summarizes them: entity-level summaries for 201-1000, topic-level for 1000+",
                wrong_answers=[
                    "Discards them entirely",
                    "Returns them verbatim but at the end",
                    "Compresses them with gzip",
                ],
                explanation="Tiered retrieval uses progressive summarization preserving key details.",
            ),
            QuizQuestion(
                question="Why does entity retrieval fall back to simple retrieval when it finds nothing?",
                correct_answer=(
                    "The question may not have proper nouns in the memory's entity index, "
                    "so simple retrieval with reranking surfaces the correct facts"
                ),
                wrong_answers=[
                    "Entity retrieval always finds something",
                    "It falls back to concept retrieval first",
                    "Empty results mean the agent has no relevant knowledge",
                ],
                explanation="Entity extraction is regex-based and can miss names not in the index.",
            ),
        ],
    )


def _build_lesson_12() -> Lesson:
    """Lesson 12: Intent Classification and Math Code Generation."""
    return Lesson(
        id="L12",
        title="Intent Classification and Math Code Generation",
        description="How the agent classifies question intent and pre-computes math results.",
        content=textwrap.dedent("""\
            # Lesson 12: Intent Classification and Math Code Generation

            ## Why Intent Classification?

            Different questions need different handling. A simple recall question
            should not trigger temporal reasoning logic, and a math question needs
            arithmetic verification. The `_detect_intent()` method classifies every
            question before retrieval.

            ## Intent Types

            The agent recognizes nine intent types:

            | Intent                    | Example                                      | Retrieval Strategy |
            |---------------------------|----------------------------------------------|-------------------|
            | `simple_recall`           | "What is X?"                                 | Simple             |
            | `mathematical_computation`| "What percentage increase?"                  | Simple + math      |
            | `temporal_comparison`     | "How did X change between Day 7 and 9?"      | Simple + temporal  |
            | `multi_source_synthesis`  | "Combine info from two articles"             | Simple (all facts) |
            | `contradiction_resolution`| "Which source is more reliable?"             | Simple (all facts) |
            | `incremental_update`      | "What is the latest value of X?"             | Simple             |
            | `causal_counterfactual`   | "What if X had not happened?"                | Iterative          |
            | `ratio_trend_analysis`    | "Which metric has the best trend?"           | Simple + math      |
            | `meta_memory`             | "How many projects are tracked?"             | Aggregation (Cypher)|

            ## How Intent Detection Works

            ```python
            def _detect_intent(self, question: str) -> dict:
                # Single LLM call with few-shot examples
                # Returns: {intent, needs_math, needs_temporal, math_type, reasoning}
            ```

            The LLM classifies the question using a prompt with few-shot examples
            and returns a JSON object. The `needs_math` and `needs_temporal` flags
            control downstream processing.

            ## Math Code Generation Pipeline

            When `needs_math=True`, the agent runs a three-step pipeline:

            ### Step 1: Number Extraction

            ```python
            def _compute_math_result(self, question, facts, intent) -> str | None:
            ```

            An LLM call extracts the specific numbers from facts and builds an
            arithmetic expression. For example:

            - Question: "What percentage did Norway improve?"
            - Numbers: `{{"old_medals": 18, "new_medals": 26}}`
            - Expression: `(26 - 18) / 18 * 100`

            ### Step 2: Safe Evaluation

            The expression is evaluated using the AST-based `calculate()` function
            (NOT Python `eval()`). This prevents code injection.

            ```python
            from .action_executor import calculate
            result = calculate("(26 - 18) / 18 * 100")
            # {"result": 44.4444, "expression": "(26 - 18) / 18 * 100"}
            ```

            ### Step 3: Injection into Synthesis

            The pre-computed result is injected into the synthesis prompt:

            ```
            PRE-COMPUTED RESULT (use this, do NOT re-calculate):
            COMPUTED: (26 - 18) / 18 * 100 = 44.44 (percentage increase)
            ```

            The LLM uses this result directly instead of doing arithmetic itself.

            ### Step 4: Post-Synthesis Validation

            After synthesis, `_validate_arithmetic()` scans the answer for
            expressions like `26 - 18 = 9` and verifies them with the calculator.
            Wrong results are corrected in-place.

            ## Intent Routing Summary

            | Intent needs   | Retrieval used        | Extra processing            |
            |---------------|-----------------------|-----------------------------|
            | needs_math     | Simple retrieval      | _compute_math_result + validate |
            | needs_temporal | Simple retrieval      | Temporal sort + worksheet   |
            | meta_memory    | Aggregation (Cypher)  | Direct count/enumeration    |
            | contradiction  | Simple (all facts)    | Contradiction instructions  |
            | causal/counter | Iterative or entity   | Counterfactual prompt       |
        """),
        prerequisites=["L07", "L11"],
        exercises=[
            Exercise(
                id="E12-01",
                instruction=(
                    "For each of these questions, write the intent type:\n"
                    "a) 'How many total medals does Norway have?'\n"
                    "b) 'What percentage did Germany's gold medals increase?'\n"
                    "c) 'How did the medal count change from Day 7 to Day 9?'\n"
                    "d) 'How many projects are being tracked?'\n"
                    "e) 'If Norway had not competed, who would lead?'"
                ),
                expected_output=(
                    "a) simple_recall -- direct fact lookup.\n"
                    "b) mathematical_computation -- percentage calculation needed.\n"
                    "c) temporal_comparison -- comparing values across time periods.\n"
                    "d) meta_memory -- asking about the structure of stored knowledge.\n"
                    "e) causal_counterfactual -- hypothetical reasoning."
                ),
                hint="Match each question to the nine intent types in the table.",
                validation_fn="validate_intent_types",
            ),
            Exercise(
                id="E12-02",
                instruction=(
                    "Describe the three steps of the math code generation pipeline "
                    "and explain why the LLM does not do the arithmetic itself."
                ),
                expected_output=(
                    "1. Number extraction: LLM extracts numbers and builds expression. "
                    "2. Safe evaluation: AST-based calculator evaluates the expression. "
                    "3. Injection: Pre-computed result is inserted into the synthesis prompt. "
                    "The LLM does not do arithmetic because it is unreliable at computation; "
                    "the calculator provides exact results."
                ),
                hint="The pipeline is: extract -> calculate -> inject.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="How many intent types does the agent recognize?",
                correct_answer="Nine: simple_recall, mathematical_computation, temporal_comparison, "
                "multi_source_synthesis, contradiction_resolution, incremental_update, "
                "causal_counterfactual, ratio_trend_analysis, meta_memory",
                wrong_answers=[
                    "Four: recall, inference, synthesis, application",
                    "Six: one per eval level L1-L6",
                    "Three: simple, complex, meta",
                ],
                explanation="The intent classifier uses nine types with specific retrieval strategies.",
            ),
            QuizQuestion(
                question="Why is the calculate() function used instead of Python eval()?",
                correct_answer="calculate() uses AST-based safe evaluation to prevent code injection",
                wrong_answers=[
                    "eval() is slower",
                    "eval() cannot do floating-point arithmetic",
                    "calculate() supports more operations",
                ],
                explanation="Security: eval() could execute arbitrary code from LLM output.",
            ),
            QuizQuestion(
                question="What happens after synthesis when needs_math=True?",
                correct_answer="_validate_arithmetic() scans the answer for expressions and corrects wrong results",
                wrong_answers=[
                    "Nothing -- the pre-computed result is sufficient",
                    "The answer is re-generated from scratch",
                    "A human reviews the math",
                ],
                explanation="Post-synthesis validation catches LLM arithmetic errors in the answer text.",
            ),
        ],
    )


def _build_lesson_13() -> Lesson:
    """Lesson 13: Self-Improvement with Patch Proposer and Reviewer Voting."""
    return Lesson(
        id="L13",
        title="Self-Improvement: Patch Proposer and Reviewer Voting",
        description="Deep dive into the automated patch proposal and multi-perspective review system.",
        content=textwrap.dedent("""\
            # Lesson 13: Patch Proposer and Reviewer Voting

            ## Beyond the Basic Loop

            Lesson 8 introduced the high-level self-improvement cycle:
            EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE.

            This lesson goes deeper into the IMPROVE step: how the system generates
            specific code patches and reviews them before applying.

            ## The Patch Proposer

            ```python
            from amplihack.eval.self_improve.patch_proposer import (
                propose_patch, PatchProposal, PatchHistory
            )
            ```

            The `propose_patch()` function takes:
            - **category**: The failing eval category (e.g., "temporal_comparison")
            - **category_score**: Current average score (e.g., 0.45)
            - **failed_questions**: Details of what went wrong
            - **bottleneck**: Component identifier (e.g., "retrieval:keyword_search")
            - **history**: Previous patches (applied, reverted, rejected)
            - **llm_call**: A callable for LLM inference

            It returns a `PatchProposal`:

            ```python
            @dataclass
            class PatchProposal:
                target_file: str      # e.g., "src/amplihack/agents/goal_seeking/learning_agent.py"
                hypothesis: str       # Why this category fails
                description: str      # What the patch does
                diff: str             # Unified diff format
                expected_impact: dict  # {category: expected_score_delta}
                risk_assessment: str   # What could go wrong
                confidence: float      # 0.0 to 1.0
            ```

            ## Patch History Tracking

            The `PatchHistory` dataclass prevents repeating failed fixes:

            ```python
            @dataclass
            class PatchHistory:
                applied_patches: list   # Patches that were applied and kept
                reverted_patches: list   # Patches that were applied then reverted
                rejected_patches: list   # Patches rejected by reviewer voting
            ```

            The history is passed to the LLM prompt so it avoids re-proposing
            the same changes that were previously reverted.

            ## Reviewer Voting

            Before a patch is applied, three reviewer perspectives vote:

            ```python
            from amplihack.eval.self_improve.reviewer_voting import ReviewVote
            ```

            | Reviewer     | Perspective                                  |
            |-------------|----------------------------------------------|
            | **Quality** | Does this patch address the root cause?      |
            | **Regression** | Could this break other passing levels?    |
            | **Simplicity** | Is this the smallest effective change?    |

            Each reviewer casts a vote: `accept`, `reject`, or `modify`.
            Majority vote determines the outcome.

            After voting, there is a **challenge phase** where a devil's advocate
            argues against the patch. The proposer must defend the change.

            ## RunnerConfig

            The self-improvement runner is configured with `RunnerConfig`:

            ```python
            @dataclass
            class RunnerConfig:
                sdk_type: str = "mini"
                max_iterations: int = 5
                improvement_threshold: float = 2.0   # min % improvement to commit
                regression_tolerance: float = 5.0    # max % regression allowed
                levels: list[str] = ["L1", "L2", "L3", "L4", "L5", "L6"]
                output_dir: str = "./eval_results/self_improve"
                agent_name: str = "self-improve-agent"
                score_threshold: float = 0.6         # threshold for failure classification
                dry_run: bool = False
            ```

            ## Practical: Running the Self-Improvement Loop

            ```bash
            # Full run with 3 iterations on L1-L6
            python -m amplihack.eval.self_improve.runner \\
                --sdk mini \\
                --iterations 3 \\
                --levels L1 L2 L3 L4 L5 L6 \\
                --output-dir ./self_improve_results/

            # Dry run (analyze only, no changes applied)
            python -m amplihack.eval.self_improve.runner \\
                --sdk mini \\
                --iterations 1 \\
                --dry-run \\
                --output-dir ./dry_run_results/
            ```

            ## Output Structure

            Each iteration writes to its own directory:

            ```
            self_improve_results/
            +-- iteration_1/
            |   +-- eval/              # Progressive suite results
            |   +-- baseline_scores.json
            |   +-- analyses.json      # ErrorAnalyzer output
            |   +-- research_decisions.json
            |   +-- patch_*.json       # Individual patch descriptions
            |   +-- re_eval/           # Post-change eval results
            |   +-- post_scores.json
            |   +-- iteration_result.json
            +-- iteration_2/
            +-- self_improve_summary.json  # Final summary
            ```
        """),
        prerequisites=["L08"],
        exercises=[
            Exercise(
                id="E13-01",
                instruction=(
                    "Describe the role of each component in the patch pipeline: "
                    "PatchProposer, PatchHistory, and ReviewerVoting. "
                    "Explain how they work together."
                ),
                expected_output=(
                    "PatchProposer: Generates specific code patches with hypothesis, diff, "
                    "and confidence. PatchHistory: Tracks applied, reverted, and rejected "
                    "patches to avoid repeating failures. ReviewerVoting: Three perspectives "
                    "(quality, regression, simplicity) vote on each patch before application. "
                    "Flow: ErrorAnalyzer -> PatchProposer -> ReviewerVoting -> Apply/Reject."
                ),
                hint="Each component has a specific role in the pipeline.",
                validation_fn="validate_patch_proposer",
            ),
            Exercise(
                id="E13-02",
                instruction=(
                    "Write a RunnerConfig for a dry run that evaluates L1-L3 with "
                    "the mini SDK, maximum 2 iterations, 3% improvement threshold."
                ),
                expected_output=(
                    "RunnerConfig(\n"
                    "    sdk_type='mini',\n"
                    "    max_iterations=2,\n"
                    "    improvement_threshold=3.0,\n"
                    "    levels=['L1', 'L2', 'L3'],\n"
                    "    dry_run=True,\n"
                    ")"
                ),
                hint="Set dry_run=True and adjust improvement_threshold.",
                validation_fn="validate_runner_config",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="What three perspectives vote on a patch proposal?",
                correct_answer="Quality (root cause), Regression (breaking other levels), Simplicity (minimal change)",
                wrong_answers=[
                    "Speed, Accuracy, Completeness",
                    "Security, Performance, Reliability",
                    "Proposer, Reviewer, Manager",
                ],
                explanation="The three perspectives catch different categories of problems.",
            ),
            QuizQuestion(
                question="Why does PatchHistory track reverted patches?",
                correct_answer="To prevent the LLM from re-proposing the same failed fix in later iterations",
                wrong_answers=[
                    "For auditing purposes only",
                    "To compute total regression",
                    "Reverted patches are not tracked",
                ],
                explanation="The history is injected into the LLM prompt to avoid repetition.",
            ),
            QuizQuestion(
                question="What is the default regression_tolerance in RunnerConfig?",
                correct_answer="5.0% -- any level regressing more than 5% triggers a revert",
                wrong_answers=[
                    "0% -- any regression triggers revert",
                    "10% -- generous tolerance",
                    "2.0% -- same as improvement_threshold",
                ],
                explanation="The default allows up to 5% regression on any individual level.",
            ),
        ],
    )


def _build_lesson_14() -> Lesson:
    """Lesson 14: Memory Export, Import, and Cross-Session Persistence."""
    return Lesson(
        id="L14",
        title="Memory Export, Import, and Cross-Session Persistence",
        description="Export agent knowledge as snapshots, import into new agents, and persist across sessions.",
        content=textwrap.dedent("""\
            # Lesson 14: Memory Export, Import, and Cross-Session Persistence

            ## Why Export/Import?

            Agents accumulate knowledge over time. You need to:
            - **Back up** knowledge before risky operations.
            - **Share** knowledge between agents or team members.
            - **Replay** learning to reproduce eval results.
            - **Migrate** from one backend to another.

            ## Memory Architecture

            The agent uses `MemoryRetriever` backed by the Kuzu graph database
            (with SQLite fallback). Each agent has isolated storage:

            ```
            ~/.amplihack/memory/<agent_name>/
            ```

            Storage can be overridden with the `storage_path` parameter:

            ```python
            from amplihack.agents.goal_seeking.memory_retrieval import MemoryRetriever

            retriever = MemoryRetriever(
                agent_name="my-agent",
                storage_path=Path("/tmp/test_memory"),
            )
            ```

            ## ExperienceStore API

            The underlying `ExperienceStore` provides the core storage interface:

            ```python
            from amplihack_memory import ExperienceStore, Experience, ExperienceType

            store = ExperienceStore(agent_name="my-agent")

            # Store a fact
            exp = Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Photosynthesis",
                outcome="Plants convert light energy to chemical energy",
                confidence=0.9,
                tags=["biology"],
            )
            exp_id = store.connector.store_experience(exp)

            # Search
            results = store.search(query="photosynthesis", limit=5)

            # Statistics
            stats = store.get_statistics()
            ```

            ## Export as JSON Snapshot

            To export an agent's knowledge, retrieve all facts and serialize:

            ```python
            retriever = MemoryRetriever("my-agent")
            all_facts = retriever.get_all_facts(limit=50000)

            import json
            with open("knowledge_snapshot.json", "w") as f:
                json.dump(all_facts, f, indent=2)
            ```

            ## Import from Snapshot

            To import into a new agent:

            ```python
            import json

            with open("knowledge_snapshot.json") as f:
                facts = json.load(f)

            new_retriever = MemoryRetriever("new-agent")
            for fact in facts:
                new_retriever.store_fact(
                    context=fact["context"],
                    fact=fact["outcome"],
                    confidence=fact.get("confidence", 0.8),
                    tags=fact.get("tags", []),
                )
            ```

            ## Eval-Specific Memory Isolation

            The progressive test suite creates fresh memory for each eval run by
            using unique agent names with timestamps:

            ```python
            agent_name = f"eval_agent_{int(time.time())}"
            ```

            This prevents cross-contamination between eval runs. Each run starts
            with an empty knowledge base.

            ## Memory Statistics

            ```python
            retriever = MemoryRetriever("my-agent")
            stats = retriever.get_statistics()
            # {
            #     "total_experiences": 142,
            #     "by_type": {"SUCCESS": 130, "FAILURE": 12},
            #     "storage_size_kb": 256
            # }
            ```

            ## Practical: Comparing Agent Knowledge

            After running the self-improvement loop, compare what two agent
            versions know:

            ```python
            v1 = MemoryRetriever("agent-v1")
            v2 = MemoryRetriever("agent-v2")

            v1_facts = v1.get_all_facts()
            v2_facts = v2.get_all_facts()

            print(f"v1: {len(v1_facts)} facts, v2: {len(v2_facts)} facts")
            ```
        """),
        prerequisites=["L06"],
        exercises=[
            Exercise(
                id="E14-01",
                instruction=(
                    "Write Python code to export all facts from an agent called "
                    "'security-scanner' to a JSON file, then import them into a "
                    "new agent called 'security-scanner-v2'."
                ),
                expected_output=(
                    "# Export\n"
                    "retriever = MemoryRetriever('security-scanner')\n"
                    "facts = retriever.get_all_facts(limit=50000)\n"
                    "with open('snapshot.json', 'w') as f:\n"
                    "    json.dump(facts, f)\n\n"
                    "# Import\n"
                    "new_ret = MemoryRetriever('security-scanner-v2')\n"
                    "for fact in facts:\n"
                    "    new_ret.store_fact(context=fact['context'], "
                    "fact=fact['outcome'])"
                ),
                hint="Use get_all_facts() to export and store_fact() to import.",
                validation_fn="validate_memory_export",
            ),
            Exercise(
                id="E14-02",
                instruction=(
                    "Explain why the eval suite uses unique agent names with timestamps "
                    "and what would happen if all eval runs shared the same agent name."
                ),
                expected_output=(
                    "Unique names ensure each eval run starts with an empty knowledge base. "
                    "If eval runs shared the same name, facts from previous runs would "
                    "persist, inflating scores because the agent would 'remember' answers "
                    "from past evaluations instead of learning fresh from the articles."
                ),
                hint="Think about what happens when facts from run N persist into run N+1.",
            ),
        ],
        quiz=[
            QuizQuestion(
                question="Where does MemoryRetriever store data by default?",
                correct_answer="~/.amplihack/memory/<agent_name>/ using the Kuzu graph database",
                wrong_answers=[
                    "In a SQLite file in the current directory",
                    "In memory only -- no persistence",
                    "In a PostgreSQL database",
                ],
                explanation="The default backend is Kuzu with storage under ~/.amplihack/memory/.",
            ),
            QuizQuestion(
                question="What method retrieves all facts without keyword filtering?",
                correct_answer="get_all_facts(limit=N) -- bypasses search and returns all experiences",
                wrong_answers=[
                    "search('*') with a wildcard query",
                    "retrieve_all() method",
                    "dump_memory() method",
                ],
                explanation="get_all_facts() is specifically designed for export and simple retrieval.",
            ),
            QuizQuestion(
                question="Why is memory isolation important during eval?",
                correct_answer=(
                    "Without isolation, facts from previous runs would persist and inflate "
                    "scores because the agent remembers past answers"
                ),
                wrong_answers=[
                    "To save disk space",
                    "Because Kuzu cannot handle concurrent access",
                    "To prevent the agent from learning too many facts",
                ],
                explanation="Cross-contamination makes eval results unreliable.",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Main teacher class
# ---------------------------------------------------------------------------


class GeneratorTeacher:
    """Interactive teaching agent for the goal-seeking agent generator.

    Curriculum:
    1. Introduction to Goal-Seeking Agents
    2. Your First Agent (CLI basics)
    3. SDK Selection Guide
    4. Multi-Agent Architecture
    5. Agent Spawning
    6. Running Evaluations
    7. Understanding Eval Levels
    8. Self-Improvement Loop
    9. Advanced: Security Domain Agents
    10. Advanced: Custom Eval Levels
    11. Retrieval Architecture
    12. Intent Classification and Math Code Generation
    13. Self-Improvement: Patch Proposer and Reviewer Voting
    14. Memory Export, Import, and Cross-Session Persistence
    """

    def __init__(self, model: str = "") -> None:
        self.model = model or os.environ.get("EVAL_MODEL", "claude-opus-4-6")
        self.curriculum = self._build_curriculum()
        self.progress: dict[str, LessonResult] = {}

    # -- Curriculum construction -------------------------------------------

    def _build_curriculum(self) -> list[Lesson]:
        """Build the complete 14-lesson curriculum."""
        return [
            _build_lesson_1(),
            _build_lesson_2(),
            _build_lesson_3(),
            _build_lesson_4(),
            _build_lesson_5(),
            _build_lesson_6(),
            _build_lesson_7(),
            _build_lesson_8(),
            _build_lesson_9(),
            _build_lesson_10(),
            _build_lesson_11(),
            _build_lesson_12(),
            _build_lesson_13(),
            _build_lesson_14(),
        ]

    # -- Lesson access -----------------------------------------------------

    def get_lesson(self, lesson_id: str) -> Lesson | None:
        """Get a lesson by its ID."""
        for lesson in self.curriculum:
            if lesson.id == lesson_id:
                return lesson
        return None

    def get_next_lesson(self) -> Lesson | None:
        """Get the next lesson the user should take based on progress.

        Returns None when all lessons are complete.
        """
        for lesson in self.curriculum:
            if lesson.id not in self.progress:
                # Check prerequisites
                if self._prerequisites_met(lesson):
                    return lesson
        return None

    def _prerequisites_met(self, lesson: Lesson) -> bool:
        """Check whether all prerequisites for *lesson* are passed."""
        for prereq_id in lesson.prerequisites:
            result = self.progress.get(prereq_id)
            if result is None or not result.passed:
                return False
        return True

    # -- Teaching ----------------------------------------------------------

    def teach_lesson(self, lesson_id: str) -> str:
        """Return the full teaching content for a lesson.

        Raises ValueError if lesson_id is unknown or prerequisites are not met.
        """
        lesson = self.get_lesson(lesson_id)
        if lesson is None:
            raise ValueError(f"Unknown lesson: {lesson_id}")

        if not self._prerequisites_met(lesson):
            unmet = [
                pid
                for pid in lesson.prerequisites
                if pid not in self.progress or not self.progress[pid].passed
            ]
            raise ValueError(
                f"Prerequisites not met for {lesson_id}. Complete these first: {', '.join(unmet)}"
            )

        sections = [
            f"# {lesson.title}",
            "",
            lesson.content,
            "",
            "---",
            f"## Exercises ({len(lesson.exercises)})",
            "",
        ]
        for i, ex in enumerate(lesson.exercises, 1):
            sections.append(f"### Exercise {i}: {ex.id}")
            sections.append(ex.instruction)
            if ex.hint:
                sections.append(f"*Hint*: {ex.hint}")
            sections.append("")

        sections.append(f"## Quiz ({len(lesson.quiz)} questions)")
        sections.append("")
        for i, q in enumerate(lesson.quiz, 1):
            sections.append(f"**Q{i}**: {q.question}")
            sections.append("")

        return "\n".join(sections)

    # -- Exercise checking -------------------------------------------------

    def check_exercise(self, lesson_id: str, exercise_id: str, user_answer: str) -> str:
        """Check a user's exercise submission and return feedback.

        Returns a string with pass/fail status and guidance.
        """
        lesson = self.get_lesson(lesson_id)
        if lesson is None:
            return f"Error: Unknown lesson {lesson_id}"

        exercise = None
        for ex in lesson.exercises:
            if ex.id == exercise_id:
                exercise = ex
                break

        if exercise is None:
            return f"Error: Unknown exercise {exercise_id} in lesson {lesson_id}"

        # Use validator if available, otherwise check key fragments
        if exercise.validation_fn and exercise.validation_fn in VALIDATORS:
            passed = VALIDATORS[exercise.validation_fn](user_answer)
        else:
            # Fallback: check that answer contains key phrases from expected output
            key_phrases = [
                phrase.strip()
                for phrase in exercise.expected_output.split(".")
                if len(phrase.strip()) > 10
            ]
            if key_phrases:
                matches = sum(
                    1 for phrase in key_phrases if phrase.lower()[:20] in user_answer.lower()
                )
                passed = matches >= max(1, len(key_phrases) // 2)
            else:
                passed = len(user_answer.strip()) > 20

        if passed:
            return (
                f"PASS: Exercise {exercise_id} completed successfully.\n"
                f"Reference answer: {exercise.expected_output}"
            )
        feedback = f"NOT YET: Exercise {exercise_id} needs more work.\n"
        if exercise.hint:
            feedback += f"Hint: {exercise.hint}\n"
        feedback += f"Expected: {exercise.expected_output}"
        return feedback

    # -- Quiz --------------------------------------------------------------

    def run_quiz(self, lesson_id: str, answers: list[str] | None = None) -> LessonResult:
        """Run the quiz for a lesson.

        If *answers* is provided, grade them. If None, return a result with
        the correct answers (for self-grading mode).

        The quiz also counts completed exercises to determine pass/fail.
        """
        lesson = self.get_lesson(lesson_id)
        if lesson is None:
            raise ValueError(f"Unknown lesson: {lesson_id}")

        quiz = lesson.quiz
        if not quiz:
            # Lesson has no quiz -- auto-pass
            result = LessonResult(
                lesson_id=lesson_id,
                exercises_completed=len(lesson.exercises),
                exercises_total=len(lesson.exercises),
                quiz_score=1.0,
                passed=True,
                feedback="No quiz for this lesson. Auto-passed.",
            )
            self.progress[lesson_id] = result
            return result

        if answers is None:
            # Self-grading mode: return correct answers
            correct = [q.correct_answer for q in quiz]
            result = LessonResult(
                lesson_id=lesson_id,
                exercises_completed=0,
                exercises_total=len(lesson.exercises),
                quiz_score=0.0,
                passed=False,
                feedback="Self-grading mode. Correct answers:\n"
                + "\n".join(f"Q{i + 1}: {a}" for i, a in enumerate(correct)),
            )
            return result

        # Grade answers
        correct_count = 0
        feedback_lines: list[str] = []
        for i, (q, user_ans) in enumerate(zip(quiz, answers, strict=False)):
            # Case-insensitive substring match on the correct answer's key phrase
            correct_lower = q.correct_answer.lower()
            user_lower = user_ans.lower()

            # Extract key phrase (first 40 chars or first sentence)
            key_phrase = correct_lower.split("--")[0].strip()[:40]
            is_correct = key_phrase in user_lower or user_lower in correct_lower

            if is_correct:
                correct_count += 1
                feedback_lines.append(f"Q{i + 1}: CORRECT")
            else:
                feedback_lines.append(f"Q{i + 1}: INCORRECT. Expected: {q.correct_answer}")
                if q.explanation:
                    feedback_lines.append(f"  Explanation: {q.explanation}")

        score = correct_count / len(quiz) if quiz else 0.0
        passed = score >= 0.60  # 60% pass threshold for quiz

        result = LessonResult(
            lesson_id=lesson_id,
            exercises_completed=len(lesson.exercises),  # Assume all attempted
            exercises_total=len(lesson.exercises),
            quiz_score=score,
            passed=passed,
            feedback="\n".join(feedback_lines),
        )
        self.progress[lesson_id] = result
        return result

    # -- Progress tracking -------------------------------------------------

    def get_progress_report(self) -> str:
        """Get a summary of the user's progress through the curriculum."""
        total = len(self.curriculum)
        completed = sum(1 for r in self.progress.values() if r.passed)
        lines = [
            "# Progress Report",
            "",
            f"Completed: {completed}/{total} lessons",
            "",
            "| Lesson | Title | Status | Quiz Score |",
            "|--------|-------|--------|------------|",
        ]

        for lesson in self.curriculum:
            result = self.progress.get(lesson.id)
            if result is None:
                # Check if prerequisites are met
                if self._prerequisites_met(lesson):
                    status = "Available"
                else:
                    status = "Locked"
                score_str = "--"
            elif result.passed:
                status = "PASSED"
                score_str = f"{result.quiz_score:.0%}"
            else:
                status = "ATTEMPTED"
                score_str = f"{result.quiz_score:.0%}"
            lines.append(f"| {lesson.id} | {lesson.title} | {status} | {score_str} |")

        lines.append("")

        # Next recommended lesson
        next_lesson = self.get_next_lesson()
        if next_lesson:
            lines.append(f"**Next recommended**: {next_lesson.id} -- {next_lesson.title}")
        else:
            lines.append("**All lessons complete!** You are now a generator expert.")

        return "\n".join(lines)

    # -- Self-validation ---------------------------------------------------

    def validate_tutorial(self) -> dict[str, Any]:
        """Self-validate: verify all lessons, exercises, and quizzes are well-formed.

        Returns a dict with validation results.
        """
        issues: list[str] = []
        stats = {
            "total_lessons": len(self.curriculum),
            "total_exercises": 0,
            "total_quiz_questions": 0,
            "lessons_with_content": 0,
            "exercises_with_validators": 0,
            "quiz_questions_with_explanations": 0,
        }

        lesson_ids = {lesson.id for lesson in self.curriculum}

        for lesson in self.curriculum:
            # Check content
            if not lesson.content.strip():
                issues.append(f"{lesson.id}: Empty content")
            else:
                stats["lessons_with_content"] += 1

            # Check prerequisites reference valid lessons
            for prereq in lesson.prerequisites:
                if prereq not in lesson_ids:
                    issues.append(f"{lesson.id}: Unknown prerequisite {prereq}")

            # Check exercises
            if len(lesson.exercises) < 2:
                issues.append(f"{lesson.id}: Fewer than 2 exercises ({len(lesson.exercises)})")
            for ex in lesson.exercises:
                stats["total_exercises"] += 1
                if not ex.instruction.strip():
                    issues.append(f"{lesson.id}/{ex.id}: Empty instruction")
                if not ex.expected_output.strip():
                    issues.append(f"{lesson.id}/{ex.id}: Empty expected_output")
                if ex.validation_fn:
                    if ex.validation_fn in VALIDATORS:
                        stats["exercises_with_validators"] += 1
                    else:
                        issues.append(f"{lesson.id}/{ex.id}: Unknown validator {ex.validation_fn}")

            # Check quiz
            if len(lesson.quiz) < 3:
                issues.append(f"{lesson.id}: Fewer than 3 quiz questions ({len(lesson.quiz)})")
            for q in lesson.quiz:
                stats["total_quiz_questions"] += 1
                if not q.correct_answer.strip():
                    issues.append(f"{lesson.id}: Quiz question missing correct_answer")
                if len(q.wrong_answers) < 2:
                    issues.append(f"{lesson.id}: Quiz question has fewer than 2 wrong answers")
                if q.explanation:
                    stats["quiz_questions_with_explanations"] += 1

        # Check prerequisite DAG is acyclic
        if self._has_circular_prerequisites():
            issues.append("CRITICAL: Circular prerequisite dependency detected")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "stats": stats,
        }

    def _has_circular_prerequisites(self) -> bool:
        """Check for circular dependencies in the prerequisite graph."""
        # Build adjacency list
        graph: dict[str, list[str]] = {}
        for lesson in self.curriculum:
            graph[lesson.id] = list(lesson.prerequisites)

        # DFS-based cycle detection
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor in in_stack:
                    return True
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
            in_stack.discard(node)
            return False

        for node in graph:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    # -- Serialization -----------------------------------------------------

    def to_json(self) -> str:
        """Serialize the curriculum and progress to JSON."""
        data = {
            "model": self.model,
            "curriculum": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "description": lesson.description,
                    "prerequisites": lesson.prerequisites,
                    "exercise_count": len(lesson.exercises),
                    "quiz_count": len(lesson.quiz),
                }
                for lesson in self.curriculum
            ],
            "progress": {
                lid: {
                    "exercises_completed": r.exercises_completed,
                    "exercises_total": r.exercises_total,
                    "quiz_score": r.quiz_score,
                    "passed": r.passed,
                }
                for lid, r in self.progress.items()
            },
        }
        return json.dumps(data, indent=2)
