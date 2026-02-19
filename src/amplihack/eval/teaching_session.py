"""Teacher-student teaching session orchestrator.

Manages a multi-turn conversation between a teacher and student agent,
each with separate memory databases. The teacher retrieves knowledge
from its memory and explains it; the student stores what it learns
in its own memory and asks follow-up questions.

Philosophy:
- Separate memory databases enforce genuine knowledge transfer
- Multi-turn conversation enables scaffolding and adaptation
- Teacher's quality is measured by student's subsequent performance
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import litellm  # type: ignore[import-untyped]

from amplihack.agents.goal_seeking import LearningAgent

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """A single turn in the teaching conversation."""

    role: str  # "teacher" or "student"
    content: str
    turn_number: int


@dataclass
class TeachingResult:
    """Result of a teaching session."""

    transcript: list[ConversationTurn]
    teacher_facts_count: int
    student_facts_count: int
    total_turns: int
    topics_covered: list[str]


class TeachingSession:
    """Orchestrates a multi-turn teaching conversation.

    The teacher and student are separate LearningAgent instances
    with separate memory databases. Knowledge transfer happens
    ONLY through the conversation - no shared memory.

    Teaching strategy (informed by learning theory):
    1. Teacher opens with a structured overview (advance organizer - Ausubel)
    2. Student asks clarifying questions (elaborative interrogation)
    3. Teacher adapts explanation (scaffolding - Vygotsky)
    4. Student summarizes understanding (self-explanation - Chi)
    5. Teacher corrects and deepens (reciprocal teaching - Palinscar & Brown)
    6. Loop continues until student signals readiness or max turns

    Args:
        teacher: LearningAgent with content already learned
        student: LearningAgent with empty memory
        model: LLM model for generating conversation
        max_turns: Maximum conversation turns
    """

    def __init__(
        self,
        teacher: LearningAgent,
        student: LearningAgent,
        model: str = "anthropic/claude-sonnet-4-5-20250929",
        max_turns: int = 10,
    ):
        self.teacher = teacher
        self.student = student
        self.model = model
        self.max_turns = max_turns
        self.transcript: list[ConversationTurn] = []

    def run(self) -> TeachingResult:
        """Run the complete teaching session.

        Returns:
            TeachingResult with transcript and statistics
        """
        turn_num = 0

        # Step 1: Teacher generates opening overview
        teacher_opening = self._teacher_generate_opening()
        self.transcript.append(
            ConversationTurn(role="teacher", content=teacher_opening, turn_number=turn_num)
        )
        turn_num += 1

        # Student processes the opening and stores what it learns
        self._student_learn_from_message(teacher_opening)

        teacher_msg = teacher_opening  # Initialize for first iteration
        for _ in range(self.max_turns - 1):
            # Student generates a response (question, summary, or "I understand")
            student_response = self._student_respond(teacher_msg)
            self.transcript.append(
                ConversationTurn(role="student", content=student_response, turn_number=turn_num)
            )
            turn_num += 1

            # Check if student signals readiness
            if self._student_signals_ready(student_response):
                logger.debug("Student signaled readiness at turn %d", turn_num)
                break

            # Teacher responds to student
            teacher_msg = self._teacher_respond(student_response)
            self.transcript.append(
                ConversationTurn(role="teacher", content=teacher_msg, turn_number=turn_num)
            )
            turn_num += 1

            # Student processes teacher's response
            self._student_learn_from_message(teacher_msg)

        # Get statistics
        teacher_stats = self.teacher.get_memory_stats()
        student_stats = self.student.get_memory_stats()

        return TeachingResult(
            transcript=self.transcript,
            teacher_facts_count=teacher_stats.get("total_experiences", 0),
            student_facts_count=student_stats.get("total_experiences", 0),
            total_turns=len(self.transcript),
            topics_covered=self._extract_topics(),
        )

    def _teacher_generate_opening(self) -> str:
        """Teacher generates structured opening based on its memory.

        Uses the advance organizer pattern: overview first, then details.
        Teacher retrieves its knowledge and organizes it for teaching.
        """
        # Get teacher's knowledge
        all_facts = []
        if hasattr(self.teacher.memory, "get_all_facts"):
            all_facts = self.teacher.memory.get_all_facts(limit=50)

        if not all_facts:
            return "I don't have enough knowledge to teach about this topic."

        facts_text = "\n".join(
            f"- [{f.get('context', 'General')}] {f.get('outcome', '')[:150]}"
            for f in all_facts[:30]
        )

        prompt = f"""You are a teacher preparing to explain a topic to a student who knows nothing about it.

Here is everything you know about this topic:
{facts_text}

Create a structured teaching introduction that:
1. Opens with a brief overview of the main topic (1-2 sentences)
2. Lists 3-5 key concepts the student needs to understand
3. Explains the most fundamental concept first in detail
4. Uses concrete examples or analogies
5. Ends with a question to check the student's understanding

Be conversational and encouraging. Don't dump all facts at once -
introduce the topic and invite the student to engage."""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert teacher who explains clearly and engages students actively.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Teacher opening generation failed: %s", e)
            return f"Let me teach you about what I've learned. Here are the key points: {facts_text[:500]}"

    def _teacher_respond(self, student_message: str) -> str:
        """Teacher responds to student's question or summary.

        Retrieves relevant facts from memory and adapts the explanation.
        """
        # Search teacher's memory for relevant facts
        relevant_facts = []
        if hasattr(self.teacher.memory, "search"):
            relevant_facts = self.teacher.memory.search(query=student_message, limit=15)

        if not relevant_facts and hasattr(self.teacher.memory, "get_all_facts"):
            relevant_facts = self.teacher.memory.get_all_facts(limit=20)

        facts_text = "\n".join(
            f"- [{f.get('context', 'General')}] {f.get('outcome', '')[:150]}"
            for f in relevant_facts[:20]
        )

        # Build conversation history for context
        history = self._format_recent_history(last_n=6)

        prompt = f"""You are a teacher in a conversation with a student.

Your knowledge about this topic:
{facts_text}

Recent conversation:
{history}

Student just said: {student_message}

Respond as the teacher:
1. If the student asked a question, answer it using your knowledge
2. If the student summarized, correct any mistakes and add missing details
3. If the student seems confused, simplify and use analogies
4. Include at least one new piece of information the student doesn't know yet
5. End with a question or prompt to keep the student engaged
6. If you've covered the main topics, start going deeper into details

Be specific with facts and numbers. Don't just give vague encouragement."""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert teacher responding to a student.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Teacher response failed: %s", e)
            return "Let me clarify that point..."

    def _student_respond(self, teacher_message: str) -> str:
        """Student processes teacher's message and responds.

        The student retrieves what it has learned so far from its OWN memory,
        then generates a thoughtful response (question, summary, or confirmation).
        """
        # Get what the student has learned so far
        student_knowledge = []
        if hasattr(self.student.memory, "get_all_facts"):
            student_knowledge = self.student.memory.get_all_facts(limit=30)

        knowledge_text = ""
        if student_knowledge:
            knowledge_text = "What I've learned so far:\n" + "\n".join(
                f"- {f.get('outcome', '')[:100]}" for f in student_knowledge[:15]
            )

        history = self._format_recent_history(last_n=6)

        prompt = f"""You are a student learning a new topic from a teacher.

{knowledge_text}

Recent conversation:
{history}

Teacher just said: {teacher_message}

As the student, respond naturally:
- If you understood, briefly summarize what you learned, then ask about something specific you want to know more about
- If something was unclear, ask for clarification with a specific question
- If you think you understand the topic well, say "I think I understand the main concepts now" and summarize everything you've learned
- Show genuine curiosity - ask "why" and "how" questions, not just "what"
- If the teacher mentioned numbers or dates, try to repeat them to confirm understanding

Keep your response concise (3-5 sentences max)."""

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a curious, engaged student."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Student response failed: %s", e)
            return "Can you explain that in more detail?"

    def _student_learn_from_message(self, message: str) -> None:
        """Student stores what it learned from a teacher message in its own memory."""
        try:
            self.student.learn_from_content(f"Teacher explained: {message}")
        except Exception as e:
            logger.debug("Student learning from message failed: %s", e)

    def _student_signals_ready(self, response: str) -> bool:
        """Check if student indicates they've understood enough."""
        ready_phrases = [
            "i understand the main concepts",
            "i think i understand",
            "i've got a good grasp",
            "that covers everything",
            "i understand now",
            "i feel confident",
        ]
        response_lower = response.lower()
        return any(phrase in response_lower for phrase in ready_phrases)

    def _format_recent_history(self, last_n: int = 6) -> str:
        """Format recent conversation turns."""
        recent = self.transcript[-last_n:]
        lines = []
        for turn in recent:
            prefix = "Teacher" if turn.role == "teacher" else "Student"
            lines.append(f"{prefix}: {turn.content[:200]}")
        return "\n\n".join(lines) if lines else "(start of conversation)"

    def _extract_topics(self) -> list[str]:
        """Extract topic keywords mentioned in the teaching transcript."""
        all_text = " ".join(t.content for t in self.transcript)
        # Simple keyword extraction - could be enhanced with LLM
        words = all_text.lower().split()
        # Count word frequency (excluding common words)
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "and",
            "or",
            "but",
            "not",
            "with",
            "from",
            "by",
            "this",
            "that",
            "it",
            "i",
            "you",
            "we",
            "they",
            "he",
            "she",
            "my",
            "your",
            "his",
            "her",
            "can",
            "will",
            "do",
            "does",
            "did",
            "has",
            "have",
            "had",
            "been",
            "being",
            "about",
            "just",
            "so",
            "also",
            "more",
            "than",
            "very",
            "too",
            "some",
            "any",
        }
        word_counts: dict[str, int] = {}
        for w in words:
            clean = w.strip(".,!?;:'\"()-")
            if len(clean) > 3 and clean not in stop_words:
                word_counts[clean] = word_counts.get(clean, 0) + 1

        # Return top 10 most frequent topic words
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:10]]


__all__ = ["TeachingSession", "TeachingResult", "ConversationTurn"]
