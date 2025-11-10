"""Question generator using Socratic method."""

from typing import List

from amplihack.knowledge_builder.kb_types import Question
from amplihack.knowledge_builder.modules.claude_caller import ClaudeCaller


class QuestionGenerator(ClaudeCaller):
    """Generates questions using Socratic method (3 levels deep)."""

    # Depth 2 question limit to keep total around 270 questions
    # Structure: 10 initial + (10 * 3) depth-1 + (30 * 3) depth-2 + (DEPTH_2_LIMIT * 3) depth-3
    # = 10 + 30 + 90 + (47 * 3) = 10 + 30 + 90 + 141 = 271 questions total
    DEPTH_2_LIMIT = 47

    def __init__(self, claude_cmd: str = "claude"):
        """Initialize question generator.

        Args:
            claude_cmd: Claude command to use (default: "claude")
        """
        super().__init__(claude_cmd)

    def _parse_numbered_questions(self, output: str, max_questions: int, start_num: int = 1) -> List[str]:
        """Parse numbered questions from Claude output.

        Args:
            output: Raw output from Claude
            max_questions: Maximum number of questions to extract
            start_num: Starting number for question parsing (default: 1)

        Returns:
            List of parsed question texts (without numbering)
        """
        questions = []
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line or not any(c.isdigit() for c in line[:5]):
                continue

            # Remove numbering (e.g., "1. " or "1) ")
            text = line
            for i in range(start_num, start_num + max_questions):
                if text.startswith(f"{i}. ") or text.startswith(f"{i}) "):
                    text = text.split(" ", 1)[1] if " " in text else text
                    break

            if text:
                questions.append(text)

        return questions[:max_questions]

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

        success, stdout, stderr = self._call_claude(prompt)

        if not success:
            raise RuntimeError(f"Failed to generate questions: {stderr}")

        # Parse output using helper method
        parsed_texts = self._parse_numbered_questions(stdout, max_questions=10)

        # Convert to Question objects, avoiding duplicates
        questions = []
        for text in parsed_texts:
            if text not in [q.text for q in questions]:
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

        success, stdout, stderr = self._call_claude(prompt)

        if not success:
            # Non-fatal - return empty list
            return []

        # Parse output using helper method
        parsed_texts = self._parse_numbered_questions(stdout, max_questions=3)

        # Convert to Question objects
        questions = [
            Question(text=text, depth=depth, parent_index=parent_index)
            for text in parsed_texts
        ]

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

            # Limit depth 2 questions to keep total around 270
            if depth == 2:
                parent_questions = parent_questions[:self.DEPTH_2_LIMIT]

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
