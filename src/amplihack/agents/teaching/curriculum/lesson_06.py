"""Lesson 6 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


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
