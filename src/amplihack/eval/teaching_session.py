"""Multi-turn teacher-student session framework.

Orchestrates a structured dialogue where a teacher agent
transfers knowledge to a student agent across multiple turns.
Student provides self-explanations (Chi 1994) for metacognition grading.

Philosophy:
- Single responsibility: Orchestrate teaching dialogue
- LLM-powered teacher and student via litellm
- Self-explanation prompts for metacognition evaluation
- Stateless turns; accumulated via history list
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import litellm  # type: ignore[import-unresolved]

logger = logging.getLogger(__name__)


@dataclass
class TeachingConfig:
    """Configuration for a teaching session.

    Attributes:
        max_turns: Number of teacher-student exchanges
        model: LLM model identifier (litellm format)
        teacher_system_prompt: System prompt for teacher role
        student_system_prompt: System prompt for student role
    """

    max_turns: int = 6
    model: str = "claude-sonnet-4-5-20250929"
    teacher_system_prompt: str = (
        "You are an expert teacher. Your job is to teach the student about a topic "
        "using the knowledge base provided. Each turn, teach one or two key concepts. "
        "Build on what the student already knows. Be concise and clear."
    )
    student_system_prompt: str = (
        "You are a student learning a new topic. After each teaching message, "
        "respond with your understanding and explain your reasoning. "
        "Always respond with a JSON object: "
        '{"response": "your understanding", "self_explanation": "why you think this is correct"}'
    )


@dataclass
class Turn:
    """One turn of teacher-student dialogue.

    Attributes:
        turn_number: Sequential turn number (1-indexed)
        teacher_message: What the teacher taught
        student_response: Student's response
        self_explanation: Student's self-explanation of understanding
    """

    turn_number: int
    teacher_message: str
    student_response: str
    self_explanation: str


@dataclass
class TeachingResult:
    """Result of a complete teaching session.

    Attributes:
        turns: All dialogue turns
        knowledge_transferred: Key concepts the teacher covered
        student_accuracy: Rough estimate of student understanding
    """

    turns: list[Turn]
    knowledge_transferred: list[str]
    student_accuracy: float


class TeachingSession:
    """Orchestrates multi-turn teacher-student dialogue.

    Creates a structured teaching session where a teacher agent
    transfers knowledge from a provided knowledge base to a student
    agent. The student provides self-explanations for each response
    to enable metacognition evaluation.

    Args:
        knowledge_base: List of facts/concepts to teach
        config: Teaching session configuration

    Raises:
        ValueError: If knowledge_base is empty

    Example:
        >>> session = TeachingSession(
        ...     knowledge_base=["L1 tests direct recall.", "L2 tests inference."],
        ...     config=TeachingConfig(max_turns=3),
        ... )
        >>> result = session.run()
        >>> print(len(result.turns))  # 3
    """

    def __init__(self, knowledge_base: list[str], config: TeachingConfig) -> None:
        if not knowledge_base:
            raise ValueError("knowledge_base cannot be empty")

        self.knowledge_base = knowledge_base
        self.config = config

    def run(self) -> TeachingResult:
        """Run the full teaching session.

        Returns:
            TeachingResult with all turns and knowledge transfer metrics
        """
        turns: list[Turn] = []
        history: list[dict[str, str]] = []
        knowledge_transferred: list[str] = []

        for turn_num in range(1, self.config.max_turns + 1):
            try:
                # Teacher generates a teaching message
                teacher_msg = self._generate_teacher_message(turn_num, history)

                # Student responds with self-explanation
                student_resp, self_explanation = self._generate_student_response(
                    teacher_msg, history
                )

                # Record the turn
                turn = Turn(
                    turn_number=turn_num,
                    teacher_message=teacher_msg,
                    student_response=student_resp,
                    self_explanation=self_explanation,
                )
                turns.append(turn)

                # Update history for context accumulation
                history.append({"role": "teacher", "content": teacher_msg})
                history.append({"role": "student", "content": student_resp})

                # Track what was taught
                knowledge_transferred.append(teacher_msg[:200])

            except Exception as e:
                logger.warning("Turn %d failed: %s", turn_num, e)
                break

        # Estimate student accuracy from self-explanations
        accuracy = self._estimate_accuracy(turns)

        return TeachingResult(
            turns=turns,
            knowledge_transferred=knowledge_transferred,
            student_accuracy=accuracy,
        )

    def _generate_teacher_message(self, turn_number: int, history: list[dict[str, str]]) -> str:
        """Generate the teacher's message for this turn.

        Args:
            turn_number: Current turn number
            history: Previous dialogue history

        Returns:
            Teacher's teaching message
        """
        # Build knowledge context
        kb_text = "\n".join(f"- {fact}" for fact in self.knowledge_base)

        # Build conversation history
        hist_text = ""
        if history:
            hist_text = "\n\nPrevious conversation:\n"
            for entry in history:
                role = entry["role"].capitalize()
                hist_text += f"{role}: {entry['content']}\n"

        prompt = (
            f"Knowledge base to teach from:\n{kb_text}\n"
            f"{hist_text}\n"
            f"This is turn {turn_number} of {self.config.max_turns}. "
            f"Teach the next concept(s). Do not repeat what was already taught."
        )

        response = litellm.completion(
            model=self.config.model,
            messages=[
                {"role": "system", "content": self.config.teacher_system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        return response.choices[0].message.content.strip()

    def _generate_student_response(
        self,
        teacher_message: str,
        history: list[dict[str, str]],
    ) -> tuple[str, str]:
        """Generate the student's response with self-explanation.

        Args:
            teacher_message: What the teacher just said
            history: Previous dialogue history

        Returns:
            Tuple of (response, self_explanation)
        """
        # Build conversation history for student
        hist_text = ""
        if history:
            hist_text = "\nPrevious conversation:\n"
            for entry in history:
                role = entry["role"].capitalize()
                hist_text += f"{role}: {entry['content']}\n"

        prompt = (
            f"{hist_text}\n"
            f"Teacher: {teacher_message}\n\n"
            f"Respond with your understanding. "
            f"Remember to include both your response and self-explanation as JSON."
        )

        response = litellm.completion(
            model=self.config.model,
            messages=[
                {"role": "system", "content": self.config.student_system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )

        response_text = response.choices[0].message.content.strip()

        # Parse JSON response
        try:
            parsed = json.loads(response_text)
            return (
                parsed.get("response", response_text),
                parsed.get("self_explanation", ""),
            )
        except json.JSONDecodeError:
            # Try extracting from markdown code block
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
                try:
                    parsed = json.loads(json_str)
                    return (
                        parsed.get("response", response_text),
                        parsed.get("self_explanation", ""),
                    )
                except json.JSONDecodeError:
                    pass
            # Fallback: use raw text
            return response_text, ""

    def _estimate_accuracy(self, turns: list[Turn]) -> float:
        """Rough estimate of student understanding based on self-explanations.

        Turns with non-empty self-explanations score higher.

        Args:
            turns: Completed dialogue turns

        Returns:
            Accuracy score 0.0-1.0
        """
        if not turns:
            return 0.0

        scores = []
        for turn in turns:
            if turn.self_explanation and len(turn.self_explanation.strip()) > 10:
                scores.append(1.0)
            elif turn.student_response and len(turn.student_response.strip()) > 10:
                scores.append(0.5)
            else:
                scores.append(0.0)

        return sum(scores) / len(scores)


__all__ = ["TeachingSession", "TeachingConfig", "TeachingResult", "Turn"]
