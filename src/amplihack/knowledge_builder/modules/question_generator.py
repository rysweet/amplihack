"""Question generator using Socratic method."""

import subprocess
from typing import List

from amplihack.knowledge_builder.kb_types import Question


class QuestionGenerator:
    """Generates questions using Socratic method (3 levels deep)."""

    def __init__(self, claude_cmd: str = "claude"):
        """Initialize question generator.

        Args:
            claude_cmd: Claude command to use (default: "claude")
        """
        self.claude_cmd = claude_cmd

    def generate_initial_questions(self, topic: str) -> List[Question]:
        """Generate 10 initial questions about a topic.

        Args:
            topic: Topic to ask questions about

        Returns:
            List of 10 initial questions (depth=0)
        """
        prompt = f"""Generate exactly 10 fundamental questions about: {topic}

Requirements:
- Each question should explore a different aspect
- Questions should be open-ended and thought-provoking
- Cover: definition, history, mechanics, applications, implications, comparisons
- Format: One question per line, numbered 1-10
- No additional commentary"""

        result = subprocess.run(
            [self.claude_cmd, "--dangerously-skip-permissions", "-p", prompt],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Failed to generate questions: {result.stderr}")

        # Parse output into questions
        questions = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line or not any(c.isdigit() for c in line[:5]):
                continue

            # Remove numbering (e.g., "1. " or "1) ")
            text = line
            for i in range(1, 11):
                if text.startswith(f"{i}. ") or text.startswith(f"{i}) "):
                    text = text.split(" ", 1)[1] if " " in text else text
                    break

            if text and text not in [q.text for q in questions]:
                questions.append(Question(text=text, depth=0, parent_index=None))

        return questions[:10]  # Ensure exactly 10

    def generate_socratic_questions(
        self, parent_question: Question, parent_index: int
    ) -> List[Question]:
        """Generate 3 follow-up questions using Socratic method.

        Args:
            parent_question: Parent question to drill down on
            parent_index: Index of parent question

        Returns:
            List of 3 Socratic follow-up questions
        """
        depth = parent_question.depth + 1
        if depth > 3:
            return []  # Max depth reached

        prompt = f"""Using the Socratic method, generate exactly 3 follow-up questions that drill deeper into this question:

"{parent_question.text}"

Requirements:
- Challenge assumptions
- Explore implications
- Seek clarification
- Test logical consistency
- Format: One question per line, numbered 1-3
- No additional commentary"""

        result = subprocess.run(
            [self.claude_cmd, "--dangerously-skip-permissions", "-p", prompt],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            # Non-fatal - return empty list
            return []

        # Parse output into questions
        questions = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line or not any(c.isdigit() for c in line[:5]):
                continue

            # Remove numbering
            text = line
            for i in range(1, 4):
                if text.startswith(f"{i}. ") or text.startswith(f"{i}) "):
                    text = text.split(" ", 1)[1] if " " in text else text
                    break

            if text:
                questions.append(Question(text=text, depth=depth, parent_index=parent_index))

        return questions[:3]  # Ensure exactly 3

    def generate_all_questions(self, topic: str) -> List[Question]:
        """Generate complete question tree (270 total questions).

        Structure:
        - 10 initial questions (depth 0)
        - 30 questions at depth 1 (3 per initial question)
        - 90 questions at depth 2 (3 per depth-1 question)
        - 140 questions at depth 3 (3 per depth-2 question, but limited to first 50)

        Args:
            topic: Topic to explore

        Returns:
            List of all questions in the tree
        """
        print(f"Generating questions for: {topic}")
        all_questions = []

        # Generate 10 initial questions
        print("Generating 10 initial questions...")
        initial = self.generate_initial_questions(topic)
        all_questions.extend(initial)
        print(f"  Generated {len(initial)} initial questions")

        # Generate Socratic follow-ups (3 levels deep)
        for depth in range(3):
            print(f"Generating depth {depth + 1} questions...")
            count = 0

            # Find all questions at current depth
            parent_questions = [q for q in all_questions if q.depth == depth]

            # Limit to first 50 questions at depth 2 to keep total ~270
            if depth == 2:
                parent_questions = parent_questions[:47]  # 47 * 3 = 141, total ~271

            for parent_idx, parent_q in enumerate(parent_questions):
                # Calculate actual parent index in all_questions
                actual_parent_idx = all_questions.index(parent_q)

                # Generate 3 follow-up questions
                follow_ups = self.generate_socratic_questions(parent_q, actual_parent_idx)
                all_questions.extend(follow_ups)
                count += len(follow_ups)

            print(f"  Generated {count} questions at depth {depth + 1}")

        print(f"Total questions generated: {len(all_questions)}")
        return all_questions
