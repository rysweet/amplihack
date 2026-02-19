"""Teacher-student evaluation runner.

Runs the L7 evaluation:
1. Teacher learns content
2. Teacher teaches student via multi-turn conversation
3. Student answers questions from its own memory
4. Grade student answers + measure teaching quality

Philosophy: Evaluate knowledge transfer, not just recall.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from amplihack.agents.goal_seeking import LearningAgent

from .grader import grade_answer
from .teaching_session import TeachingSession
from .test_levels import LEVEL_7, TestLevel

logger = logging.getLogger(__name__)


@dataclass
class TeachingEvalResult:
    """Complete result of the teacher-student evaluation."""

    # Teaching quality metrics
    student_avg_score: float
    teacher_avg_score: float  # Teacher's own score on same questions (baseline)
    transfer_ratio: float  # student_score / teacher_score
    total_teaching_turns: int
    student_facts_learned: int

    # Per-question details
    student_grades: list[dict[str, Any]]
    teacher_grades: list[dict[str, Any]]

    # Conversation transcript
    transcript: list[dict[str, str]]

    # Topics covered
    topics_covered: list[str]


def run_teaching_eval(
    level: TestLevel | None = None,
    model: str | None = None,
    max_teaching_turns: int = 8,
) -> TeachingEvalResult:
    """Run the complete teacher-student evaluation.

    Args:
        level: Test level to use (default: LEVEL_7)
        model: LLM model (default from EVAL_MODEL env var)
        max_teaching_turns: Maximum conversation turns

    Returns:
        TeachingEvalResult with all metrics
    """
    level = level or LEVEL_7
    model = model or os.environ.get("EVAL_MODEL", "anthropic/claude-sonnet-4-5-20250929")

    # Create separate storage directories for teacher and student
    base_dir = Path(tempfile.gettempdir()) / "amplihack_eval_teaching"
    teacher_dir = base_dir / f"teacher_{os.getpid()}"
    student_dir = base_dir / f"student_{os.getpid()}"
    teacher_dir.mkdir(parents=True, exist_ok=True)
    student_dir.mkdir(parents=True, exist_ok=True)

    # Initialize teacher and student with SEPARATE memory databases
    teacher = LearningAgent(
        agent_name="teacher",
        model=model,
        storage_path=teacher_dir,
        use_hierarchical=True,
    )
    student = LearningAgent(
        agent_name="student",
        model=model,
        storage_path=student_dir,
        use_hierarchical=True,
    )

    try:
        # Phase 1: Teacher learns the content
        print("  Phase 1: Teacher learning content...")
        for article in level.articles:
            content = f"Title: {article.title}\n\n{article.content}"
            result = teacher.learn_from_content(content)
            logger.debug(
                "Teacher learned %d facts from '%s'",
                result["facts_stored"],
                article.title[:40],
            )

        # Phase 1b: Verify teacher learned by answering questions
        print("  Phase 1b: Verifying teacher's knowledge...")
        teacher_grades = []
        for q in level.questions:
            answer = str(teacher.answer_question(q.question, question_level="L2"))
            grade = grade_answer(
                question=q.question,
                expected=q.expected_answer,
                actual=answer,
                level=q.level,
            )
            teacher_grades.append(
                {
                    "question": q.question,
                    "answer": answer,
                    "expected": q.expected_answer,
                    "score": grade.score,
                    "reasoning": grade.reasoning,
                }
            )

        teacher_avg = (
            sum(g["score"] for g in teacher_grades) / len(teacher_grades) if teacher_grades else 0
        )

        print(f"  Teacher score: {teacher_avg:.2%}")
        if teacher_avg < 0.5:
            print("  WARNING: Teacher scored poorly - teaching quality will be limited")

        # Phase 2: Teaching session
        print(f"  Phase 2: Teaching session (max {max_teaching_turns} turns)...")
        session = TeachingSession(
            teacher=teacher,
            student=student,
            model=model,
            max_turns=max_teaching_turns,
        )
        teaching_result = session.run()
        print(
            f"  Teaching completed: {teaching_result.total_turns} turns, "
            f"student learned {teaching_result.student_facts_count} facts"
        )

        # Phase 3: Test student's knowledge (from its OWN memory only)
        print("  Phase 3: Testing student's knowledge...")
        student_grades = []
        for q in level.questions:
            answer = str(student.answer_question(q.question, question_level="L2"))
            grade = grade_answer(
                question=q.question,
                expected=q.expected_answer,
                actual=answer,
                level=q.level,
            )
            student_grades.append(
                {
                    "question": q.question,
                    "answer": answer,
                    "expected": q.expected_answer,
                    "score": grade.score,
                    "reasoning": grade.reasoning,
                }
            )

        student_avg = (
            sum(g["score"] for g in student_grades) / len(student_grades) if student_grades else 0
        )

        # Calculate transfer ratio
        transfer_ratio = student_avg / teacher_avg if teacher_avg > 0 else 0

        # Serialize transcript
        transcript = [
            {"role": t.role, "content": t.content, "turn": t.turn_number}
            for t in teaching_result.transcript
        ]

        return TeachingEvalResult(
            student_avg_score=student_avg,
            teacher_avg_score=teacher_avg,
            transfer_ratio=transfer_ratio,
            total_teaching_turns=teaching_result.total_turns,
            student_facts_learned=teaching_result.student_facts_count,
            student_grades=student_grades,
            teacher_grades=teacher_grades,
            transcript=transcript,
            topics_covered=teaching_result.topics_covered,
        )

    finally:
        teacher.close()
        student.close()


def main():
    """CLI entry point for teacher-student evaluation."""
    import argparse

    parser = argparse.ArgumentParser(description="Teacher-Student Learning Evaluation")
    parser.add_argument("--model", default=None, help="LLM model to use")
    parser.add_argument("--max-turns", type=int, default=8, help="Max teaching turns")
    parser.add_argument("--output-dir", default="/tmp/teaching_eval", help="Output directory")

    args = parser.parse_args()

    print("=" * 70)
    print("TEACHER-STUDENT LEARNING EVALUATION (L7)")
    print("=" * 70)

    result = run_teaching_eval(
        model=args.model,
        max_teaching_turns=args.max_turns,
    )

    # Print results
    print(f"\n{'=' * 70}")
    print("RESULTS")
    print(f"{'=' * 70}")
    print(f"Teacher Score: {result.teacher_avg_score:.2%}")
    print(f"Student Score: {result.student_avg_score:.2%}")
    print(f"Transfer Ratio: {result.transfer_ratio:.2%}")
    print(f"Teaching Turns: {result.total_teaching_turns}")
    print(f"Student Facts Learned: {result.student_facts_learned}")

    print("\nStudent Question Scores:")
    for g in result.student_grades:
        print(f"  {g['question'][:60]}... → {g['score']:.2%}")

    print(f"\nTopics Covered: {', '.join(result.topics_covered[:8])}")

    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "teaching_eval_result.json", "w") as f:
        json.dump(
            {
                "student_avg_score": result.student_avg_score,
                "teacher_avg_score": result.teacher_avg_score,
                "transfer_ratio": result.transfer_ratio,
                "total_teaching_turns": result.total_teaching_turns,
                "student_facts_learned": result.student_facts_learned,
                "student_grades": result.student_grades,
                "teacher_grades": result.teacher_grades,
                "transcript": result.transcript,
                "topics_covered": result.topics_covered,
            },
            f,
            indent=2,
        )

    print(f"\nResults saved to: {output_dir}")

    # Success criteria
    print(f"\n{'=' * 70}")
    print("SUCCESS CRITERIA")
    print(f"{'=' * 70}")
    criteria = [
        ("Student > 50% (minimum viable)", result.student_avg_score > 0.5),
        ("Student > 60% of teacher (good transfer)", result.transfer_ratio > 0.6),
        ("Student > 75% (good)", result.student_avg_score > 0.75),
        ("Student > 80% of teacher (excellent)", result.transfer_ratio > 0.8),
    ]
    for desc, met in criteria:
        status = "MET" if met else "NOT MET"
        print(f"  [{status}] {desc}")


if __name__ == "__main__":
    main()


__all__ = ["run_teaching_eval", "TeachingEvalResult"]
