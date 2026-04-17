"""Lesson 13 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


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
