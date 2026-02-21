"""Tests for the teaching agent curriculum and exercise validation.

Covers:
- All 10 lessons load correctly
- Exercises have valid expected outputs and validators
- Quiz questions have correct answers and explanations
- Prerequisite chain is acyclic and valid
- Progress tracking works correctly
- Self-validation method catches structural issues
- Integration: walk through lessons 1-2 with mock user
"""

from __future__ import annotations

import json

import pytest

from amplihack.agents.teaching.generator_teacher import (
    VALIDATORS,
    GeneratorTeacher,
    Lesson,
    LessonResult,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def teacher() -> GeneratorTeacher:
    """Fresh GeneratorTeacher instance."""
    return GeneratorTeacher()


@pytest.fixture
def curriculum(teacher: GeneratorTeacher) -> list[Lesson]:
    return teacher.curriculum


# ---------------------------------------------------------------------------
# Lesson structure tests
# ---------------------------------------------------------------------------


class TestCurriculumStructure:
    """Verify all 10 lessons are present and well-formed."""

    def test_has_10_lessons(self, curriculum: list[Lesson]) -> None:
        assert len(curriculum) == 10

    def test_lesson_ids_are_unique(self, curriculum: list[Lesson]) -> None:
        ids = [lesson.id for lesson in curriculum]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_lesson_ids_sequential(self, curriculum: list[Lesson]) -> None:
        expected = [f"L{i:02d}" for i in range(1, 11)]
        actual = [lesson.id for lesson in curriculum]
        assert actual == expected

    def test_every_lesson_has_title(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            assert lesson.title.strip(), f"{lesson.id} has empty title"

    def test_every_lesson_has_description(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            assert lesson.description.strip(), f"{lesson.id} has empty description"

    def test_every_lesson_has_content(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            assert len(lesson.content.strip()) > 100, (
                f"{lesson.id} content too short ({len(lesson.content)} chars)"
            )

    def test_first_lesson_has_no_prerequisites(self, curriculum: list[Lesson]) -> None:
        assert curriculum[0].prerequisites == []


# ---------------------------------------------------------------------------
# Exercise tests
# ---------------------------------------------------------------------------


class TestExercises:
    """Verify exercises across all lessons."""

    def test_every_lesson_has_at_least_2_exercises(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            assert len(lesson.exercises) >= 2, (
                f"{lesson.id} has only {len(lesson.exercises)} exercises"
            )

    def test_exercise_ids_are_unique_within_lesson(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            ids = [ex.id for ex in lesson.exercises]
            assert len(ids) == len(set(ids)), f"{lesson.id} has duplicate exercise IDs: {ids}"

    def test_exercises_have_instructions(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            for ex in lesson.exercises:
                assert ex.instruction.strip(), f"{lesson.id}/{ex.id} has empty instruction"

    def test_exercises_have_expected_output(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            for ex in lesson.exercises:
                assert ex.expected_output.strip(), f"{lesson.id}/{ex.id} has empty expected_output"

    def test_validators_exist_for_referenced_functions(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            for ex in lesson.exercises:
                if ex.validation_fn:
                    assert ex.validation_fn in VALIDATORS, (
                        f"{lesson.id}/{ex.id} references unknown validator: {ex.validation_fn}"
                    )

    def test_validator_functions_are_callable(self) -> None:
        for name, fn in VALIDATORS.items():
            assert callable(fn), f"Validator {name} is not callable"


# ---------------------------------------------------------------------------
# Quiz tests
# ---------------------------------------------------------------------------


class TestQuizzes:
    """Verify quiz questions across all lessons."""

    def test_every_lesson_has_at_least_3_quiz_questions(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            assert len(lesson.quiz) >= 3, f"{lesson.id} has only {len(lesson.quiz)} quiz questions"

    def test_quiz_questions_have_correct_answer(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            for q in lesson.quiz:
                assert q.correct_answer.strip(), (
                    f"{lesson.id}: quiz question missing correct_answer"
                )

    def test_quiz_questions_have_wrong_answers(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            for q in lesson.quiz:
                assert len(q.wrong_answers) >= 2, (
                    f"{lesson.id}: quiz question has fewer than 2 wrong answers"
                )

    def test_correct_answer_not_in_wrong_answers(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            for q in lesson.quiz:
                assert q.correct_answer not in q.wrong_answers, (
                    f"{lesson.id}: correct answer appears in wrong_answers"
                )

    def test_quiz_questions_have_explanations(self, curriculum: list[Lesson]) -> None:
        for lesson in curriculum:
            for q in lesson.quiz:
                assert q.explanation.strip(), f"{lesson.id}: quiz question missing explanation"


# ---------------------------------------------------------------------------
# Prerequisite chain tests
# ---------------------------------------------------------------------------


class TestPrerequisites:
    """Verify the prerequisite dependency graph."""

    def test_no_circular_dependencies(self, teacher: GeneratorTeacher) -> None:
        assert not teacher._has_circular_prerequisites()

    def test_prerequisites_reference_valid_lessons(self, curriculum: list[Lesson]) -> None:
        valid_ids = {lesson.id for lesson in curriculum}
        for lesson in curriculum:
            for prereq in lesson.prerequisites:
                assert prereq in valid_ids, f"{lesson.id} has unknown prerequisite: {prereq}"

    def test_prerequisites_reference_earlier_lessons(self, curriculum: list[Lesson]) -> None:
        """Prerequisites should only reference lessons that come before."""
        lesson_order = {lesson.id: i for i, lesson in enumerate(curriculum)}
        for lesson in curriculum:
            for prereq in lesson.prerequisites:
                assert lesson_order[prereq] < lesson_order[lesson.id], (
                    f"{lesson.id} has prerequisite {prereq} that comes after it in the curriculum"
                )

    def test_lesson_1_has_no_prerequisites(self, curriculum: list[Lesson]) -> None:
        assert curriculum[0].prerequisites == []

    def test_prerequisite_chain_reachability(self, curriculum: list[Lesson]) -> None:
        """Every lesson should be reachable by completing prerequisites in order."""
        completed: set[str] = set()
        for lesson in curriculum:
            for prereq in lesson.prerequisites:
                assert prereq in completed, (
                    f"{lesson.id} requires {prereq} which has not been completed"
                )
            completed.add(lesson.id)


# ---------------------------------------------------------------------------
# Progress tracking tests
# ---------------------------------------------------------------------------


class TestProgressTracking:
    """Verify progress tracking and lesson navigation."""

    def test_initial_next_lesson_is_L01(self, teacher: GeneratorTeacher) -> None:
        next_lesson = teacher.get_next_lesson()
        assert next_lesson is not None
        assert next_lesson.id == "L01"

    def test_after_completing_L01_next_is_L02(self, teacher: GeneratorTeacher) -> None:
        teacher.progress["L01"] = LessonResult(
            lesson_id="L01",
            exercises_completed=2,
            exercises_total=2,
            quiz_score=1.0,
            passed=True,
        )
        next_lesson = teacher.get_next_lesson()
        assert next_lesson is not None
        assert next_lesson.id == "L02"

    def test_locked_lessons_are_skipped(self, teacher: GeneratorTeacher) -> None:
        """L03 requires L02, which requires L01. Without completing L01,
        get_next_lesson should not return L03."""
        next_lesson = teacher.get_next_lesson()
        assert next_lesson is not None
        assert next_lesson.id == "L01"  # First available

    def test_all_complete_returns_none(self, teacher: GeneratorTeacher) -> None:
        for lesson in teacher.curriculum:
            teacher.progress[lesson.id] = LessonResult(
                lesson_id=lesson.id,
                exercises_completed=2,
                exercises_total=2,
                quiz_score=1.0,
                passed=True,
            )
        assert teacher.get_next_lesson() is None

    def test_progress_report_format(self, teacher: GeneratorTeacher) -> None:
        report = teacher.get_progress_report()
        assert "Progress Report" in report
        assert "Completed: 0/10" in report
        assert "L01" in report
        assert "Available" in report  # L01 should be available

    def test_progress_report_after_completing_lessons(self, teacher: GeneratorTeacher) -> None:
        teacher.progress["L01"] = LessonResult(
            lesson_id="L01",
            exercises_completed=2,
            exercises_total=2,
            quiz_score=0.8,
            passed=True,
        )
        report = teacher.get_progress_report()
        assert "Completed: 1/10" in report
        assert "PASSED" in report


# ---------------------------------------------------------------------------
# Teaching & exercise checking tests
# ---------------------------------------------------------------------------


class TestTeaching:
    """Verify teach_lesson and check_exercise methods."""

    def test_teach_lesson_returns_content(self, teacher: GeneratorTeacher) -> None:
        content = teacher.teach_lesson("L01")
        assert "Introduction to Goal-Seeking Agents" in content
        assert "Exercise" in content
        assert "Quiz" in content

    def test_teach_unknown_lesson_raises(self, teacher: GeneratorTeacher) -> None:
        with pytest.raises(ValueError, match="Unknown lesson"):
            teacher.teach_lesson("NONEXISTENT")

    def test_teach_locked_lesson_raises(self, teacher: GeneratorTeacher) -> None:
        """L02 requires L01. Teaching L02 without completing L01 should fail."""
        with pytest.raises(ValueError, match="Prerequisites not met"):
            teacher.teach_lesson("L02")

    def test_check_exercise_with_validator(self, teacher: GeneratorTeacher) -> None:
        # E02-01 uses validate_prompt_file: needs "# goal", "constraint", "success"
        result = teacher.check_exercise(
            "L02",
            "E02-01",
            "# Goal: Docker Security\n## Constraints\n- Focus on containers\n## Success Criteria\n- Done",
        )
        assert "PASS" in result

    def test_check_exercise_failing(self, teacher: GeneratorTeacher) -> None:
        result = teacher.check_exercise(
            "L02",
            "E02-01",
            "This is not a valid prompt file",
        )
        assert "NOT YET" in result

    def test_check_unknown_exercise(self, teacher: GeneratorTeacher) -> None:
        result = teacher.check_exercise("L01", "NONEXISTENT", "answer")
        assert "Error" in result

    def test_check_unknown_lesson(self, teacher: GeneratorTeacher) -> None:
        result = teacher.check_exercise("NONEXISTENT", "E01-01", "answer")
        assert "Error" in result


# ---------------------------------------------------------------------------
# Quiz tests
# ---------------------------------------------------------------------------


class TestQuizExecution:
    """Verify quiz running and grading."""

    def test_quiz_self_grading_mode(self, teacher: GeneratorTeacher) -> None:
        result = teacher.run_quiz("L01", answers=None)
        assert not result.passed
        assert "Self-grading mode" in result.feedback
        assert "PromptAnalyzer" in result.feedback  # Correct answer for Q1

    def test_quiz_perfect_score(self, teacher: GeneratorTeacher) -> None:
        # L01 quiz: provide correct answers
        lesson = teacher.get_lesson("L01")
        assert lesson is not None
        correct = [q.correct_answer for q in lesson.quiz]
        result = teacher.run_quiz("L01", answers=correct)
        assert result.quiz_score == 1.0
        assert result.passed

    def test_quiz_failing_score(self, teacher: GeneratorTeacher) -> None:
        lesson = teacher.get_lesson("L01")
        assert lesson is not None
        wrong = ["wrong answer"] * len(lesson.quiz)
        result = teacher.run_quiz("L01", answers=wrong)
        assert result.quiz_score < 1.0

    def test_quiz_records_progress(self, teacher: GeneratorTeacher) -> None:
        lesson = teacher.get_lesson("L01")
        assert lesson is not None
        correct = [q.correct_answer for q in lesson.quiz]
        teacher.run_quiz("L01", answers=correct)
        assert "L01" in teacher.progress
        assert teacher.progress["L01"].passed

    def test_quiz_unknown_lesson_raises(self, teacher: GeneratorTeacher) -> None:
        with pytest.raises(ValueError, match="Unknown lesson"):
            teacher.run_quiz("NONEXISTENT")


# ---------------------------------------------------------------------------
# Self-validation tests
# ---------------------------------------------------------------------------


class TestSelfValidation:
    """Verify the validate_tutorial self-check."""

    def test_default_curriculum_is_valid(self, teacher: GeneratorTeacher) -> None:
        result = teacher.validate_tutorial()
        assert result["valid"], f"Issues found: {result['issues']}"

    def test_validation_counts_lessons(self, teacher: GeneratorTeacher) -> None:
        result = teacher.validate_tutorial()
        assert result["stats"]["total_lessons"] == 10

    def test_validation_counts_exercises(self, teacher: GeneratorTeacher) -> None:
        result = teacher.validate_tutorial()
        assert result["stats"]["total_exercises"] >= 20  # At least 2 per lesson

    def test_validation_counts_quiz_questions(self, teacher: GeneratorTeacher) -> None:
        result = teacher.validate_tutorial()
        assert result["stats"]["total_quiz_questions"] >= 30  # At least 3 per lesson

    def test_validation_counts_validators(self, teacher: GeneratorTeacher) -> None:
        result = teacher.validate_tutorial()
        assert result["stats"]["exercises_with_validators"] > 0

    def test_validation_counts_explanations(self, teacher: GeneratorTeacher) -> None:
        result = teacher.validate_tutorial()
        assert result["stats"]["quiz_questions_with_explanations"] > 0

    def test_no_circular_prerequisites(self, teacher: GeneratorTeacher) -> None:
        result = teacher.validate_tutorial()
        assert "Circular" not in str(result["issues"])


# ---------------------------------------------------------------------------
# Validator unit tests
# ---------------------------------------------------------------------------


class TestValidators:
    """Test individual exercise validators."""

    def test_validate_prompt_file_pass(self) -> None:
        answer = "# Goal: Test\n## Constraints\n- None\n## Success Criteria\n- Pass"
        assert VALIDATORS["validate_prompt_file"](answer)

    def test_validate_prompt_file_fail(self) -> None:
        assert not VALIDATORS["validate_prompt_file"]("not a prompt file")

    def test_validate_cli_command_pass(self) -> None:
        assert VALIDATORS["validate_cli_command"]("amplihack new --file my_goal.md")

    def test_validate_cli_command_fail(self) -> None:
        assert not VALIDATORS["validate_cli_command"]("python run.py")

    def test_validate_sdk_choice_copilot(self) -> None:
        assert VALIDATORS["validate_sdk_choice"]("Use the copilot SDK")

    def test_validate_sdk_choice_claude(self) -> None:
        assert VALIDATORS["validate_sdk_choice"]("claude is best for this")

    def test_validate_sdk_choice_fail(self) -> None:
        assert not VALIDATORS["validate_sdk_choice"]("use the default")

    def test_validate_multi_agent_pass(self) -> None:
        assert VALIDATORS["validate_multi_agent_command"]("amplihack new --file x.md --multi-agent")

    def test_validate_multi_agent_fail(self) -> None:
        assert not VALIDATORS["validate_multi_agent_command"]("amplihack new --file x.md")

    def test_validate_spawning_pass(self) -> None:
        assert VALIDATORS["validate_spawning_command"](
            "amplihack new --file x.md --multi-agent --enable-spawning"
        )

    def test_validate_spawning_fail_missing_multi(self) -> None:
        assert not VALIDATORS["validate_spawning_command"](
            "amplihack new --file x.md --enable-spawning"
        )

    def test_validate_eval_command_pass(self) -> None:
        assert VALIDATORS["validate_eval_command"](
            "python -m amplihack.eval.progressive_test_suite"
        )

    def test_validate_level_explanation_pass(self) -> None:
        assert VALIDATORS["validate_level_explanation"](
            "L1 tests recall. L2 tests synthesis. L3 tests temporal."
        )

    def test_validate_level_explanation_fail(self) -> None:
        assert not VALIDATORS["validate_level_explanation"]("Only L1 recall.")

    def test_validate_self_improve_pass(self) -> None:
        assert VALIDATORS["validate_self_improve"](
            "1. eval baseline 2. analyze failures 3. improve code"
        )

    def test_validate_security_prompt_pass(self) -> None:
        assert VALIDATORS["validate_security_prompt"](
            "# Goal: Security Scanner\nAnalyze for vulnerabilities"
        )

    def test_validate_custom_level_pass(self) -> None:
        assert VALIDATORS["validate_custom_level"](
            "Define TestArticle with content and TestQuestion with expected answer"
        )


# ---------------------------------------------------------------------------
# Serialization tests
# ---------------------------------------------------------------------------


class TestSerialization:
    """Verify JSON serialization."""

    def test_to_json_is_valid(self, teacher: GeneratorTeacher) -> None:
        data = json.loads(teacher.to_json())
        assert data["model"] == "claude-sonnet-4-5-20250929"
        assert len(data["curriculum"]) == 10
        assert data["progress"] == {}

    def test_to_json_includes_progress(self, teacher: GeneratorTeacher) -> None:
        teacher.progress["L01"] = LessonResult(
            lesson_id="L01",
            exercises_completed=2,
            exercises_total=2,
            quiz_score=1.0,
            passed=True,
        )
        data = json.loads(teacher.to_json())
        assert "L01" in data["progress"]
        assert data["progress"]["L01"]["passed"] is True


# ---------------------------------------------------------------------------
# Integration test: walk through lessons 1-2 with mock user
# ---------------------------------------------------------------------------


class TestIntegrationWalkthrough:
    """Simulate a user going through lessons 1 and 2."""

    def test_complete_lesson_1_and_2(self, teacher: GeneratorTeacher) -> None:
        # Start: next lesson should be L01
        assert teacher.get_next_lesson().id == "L01"  # type: ignore[union-attr]

        # Teach lesson 1
        content = teacher.teach_lesson("L01")
        assert "Goal-Seeking Agents" in content

        # Check exercise E01-01 (no validator, uses fallback)
        result = teacher.check_exercise(
            "L01",
            "E01-01",
            "Learn: Extract facts from articles. "
            "Remember: Retrieve stored knowledge. "
            "Teach: Explain topics. "
            "Apply: Use tools to solve problems.",
        )
        # Fallback validator should pass for reasonable answer
        assert "E01-01" in result

        # Run quiz for L01 with correct answers
        lesson_1 = teacher.get_lesson("L01")
        assert lesson_1 is not None
        correct_1 = [q.correct_answer for q in lesson_1.quiz]
        result_1 = teacher.run_quiz("L01", answers=correct_1)
        assert result_1.passed
        assert result_1.quiz_score == 1.0

        # Now L02 should be available
        next_lesson = teacher.get_next_lesson()
        assert next_lesson is not None
        assert next_lesson.id == "L02"

        # Teach lesson 2
        content_2 = teacher.teach_lesson("L02")
        assert "First Agent" in content_2

        # Check exercise E02-01 with validator
        result_2 = teacher.check_exercise(
            "L02",
            "E02-01",
            "# Goal: Docker Security\n## Constraints\n- Containers\n## Success Criteria\n- Isolation",
        )
        assert "PASS" in result_2

        # Check exercise E02-02 with validator
        result_3 = teacher.check_exercise(
            "L02",
            "E02-02",
            "amplihack new --file docker_security.md --verbose",
        )
        assert "PASS" in result_3

        # Run quiz for L02 with correct answers
        lesson_2 = teacher.get_lesson("L02")
        assert lesson_2 is not None
        correct_2 = [q.correct_answer for q in lesson_2.quiz]
        result_2_quiz = teacher.run_quiz("L02", answers=correct_2)
        assert result_2_quiz.passed

        # Progress report should show 2 completed
        report = teacher.get_progress_report()
        assert "Completed: 2/10" in report

    def test_cannot_skip_to_lesson_3_without_prerequisites(self, teacher: GeneratorTeacher) -> None:
        """L03 requires L02 which requires L01."""
        with pytest.raises(ValueError, match="Prerequisites not met"):
            teacher.teach_lesson("L03")

    def test_get_lesson_returns_none_for_invalid_id(self, teacher: GeneratorTeacher) -> None:
        assert teacher.get_lesson("INVALID") is None
