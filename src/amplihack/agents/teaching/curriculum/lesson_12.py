"""Lesson 12 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


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
