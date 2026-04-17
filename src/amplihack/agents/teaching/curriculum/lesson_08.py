"""Lesson 8 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


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
