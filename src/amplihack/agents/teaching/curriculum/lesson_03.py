"""Lesson 3 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


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
