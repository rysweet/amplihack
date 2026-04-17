"""Lesson 7 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


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
