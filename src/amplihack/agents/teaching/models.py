"""Data models for the teaching agent curriculum."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Exercise:
    """A hands-on exercise for the user."""

    id: str
    instruction: str
    expected_output: str
    hint: str = ""
    validation_fn: str = ""  # Name of validation function


@dataclass
class QuizQuestion:
    """A quiz question to check understanding."""

    question: str
    correct_answer: str
    wrong_answers: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class Lesson:
    """A single lesson in the teaching curriculum."""

    id: str
    title: str
    description: str
    content: str  # Full teaching content (markdown)
    prerequisites: list[str] = field(default_factory=list)
    exercises: list[Exercise] = field(default_factory=list)
    quiz: list[QuizQuestion] = field(default_factory=list)


@dataclass
class LessonResult:
    """Result of a user completing a lesson."""

    lesson_id: str
    exercises_completed: int
    exercises_total: int
    quiz_score: float
    passed: bool
    feedback: str = ""
