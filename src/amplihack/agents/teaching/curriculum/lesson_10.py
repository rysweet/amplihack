"""Lesson 10 content builder."""

from __future__ import annotations

import textwrap

from amplihack.agents.teaching.models import Exercise, Lesson, QuizQuestion


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
            from amplihack.eval.test_levels import TestLevel, TestArticle, TestQuestion

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
                explanation="These are the exact class names from test_levels.py.",
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
