"""Curriculum package — one module per lesson."""

from __future__ import annotations

from amplihack.agents.teaching.curriculum.lesson_01 import _build_lesson_1
from amplihack.agents.teaching.curriculum.lesson_02 import _build_lesson_2
from amplihack.agents.teaching.curriculum.lesson_03 import _build_lesson_3
from amplihack.agents.teaching.curriculum.lesson_04 import _build_lesson_4
from amplihack.agents.teaching.curriculum.lesson_05 import _build_lesson_5
from amplihack.agents.teaching.curriculum.lesson_06 import _build_lesson_6
from amplihack.agents.teaching.curriculum.lesson_07 import _build_lesson_7
from amplihack.agents.teaching.curriculum.lesson_08 import _build_lesson_8
from amplihack.agents.teaching.curriculum.lesson_09 import _build_lesson_9
from amplihack.agents.teaching.curriculum.lesson_10 import _build_lesson_10
from amplihack.agents.teaching.curriculum.lesson_11 import _build_lesson_11
from amplihack.agents.teaching.curriculum.lesson_12 import _build_lesson_12
from amplihack.agents.teaching.curriculum.lesson_13 import _build_lesson_13
from amplihack.agents.teaching.curriculum.lesson_14 import _build_lesson_14
from amplihack.agents.teaching.models import Lesson

ALL_LESSON_BUILDERS: list = [
    _build_lesson_1,
    _build_lesson_2,
    _build_lesson_3,
    _build_lesson_4,
    _build_lesson_5,
    _build_lesson_6,
    _build_lesson_7,
    _build_lesson_8,
    _build_lesson_9,
    _build_lesson_10,
    _build_lesson_11,
    _build_lesson_12,
    _build_lesson_13,
    _build_lesson_14,
]


def build_curriculum() -> list[Lesson]:
    """Build the complete 14-lesson curriculum."""
    return [builder() for builder in ALL_LESSON_BUILDERS]


__all__ = ["build_curriculum", "ALL_LESSON_BUILDERS"]
