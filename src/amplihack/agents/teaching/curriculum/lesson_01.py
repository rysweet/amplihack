"""Lesson 1 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


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
            class GoalSeekingAgent:
                async def learn(self, content: str) -> list[str]
                async def remember(self, query: str) -> str
                async def teach(self, topic: str) -> str
                async def execute(self, instruction: str) -> str
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
                question="What does the GoalSeekingAgent.teach() method do?",
                correct_answer="Explains stored knowledge to another agent or human",
                wrong_answers=[
                    "Trains a model on new data",
                    "Writes documentation to disk",
                    "Runs the eval suite",
                ],
                explanation="teach() is about knowledge transfer, not model training.",
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
