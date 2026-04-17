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
from typing import Any

from amplihack.agents.teaching.curriculum import build_curriculum
from amplihack.agents.teaching.models import (
    Lesson,
    LessonResult,
)
from amplihack.agents.teaching.validators import VALIDATORS


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
        self.model = model or "claude-sonnet-4-5-20250929"
        self.curriculum = build_curriculum()
        self.progress: dict[str, LessonResult] = {}

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
