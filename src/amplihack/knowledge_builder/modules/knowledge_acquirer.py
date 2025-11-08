"""Knowledge acquirer using web search."""

import subprocess
from typing import List

from amplihack.knowledge_builder.kb_types import Question


class KnowledgeAcquirer:
    """Acquires knowledge by answering questions via web search."""

    def __init__(self, claude_cmd: str = "claude"):
        """Initialize knowledge acquirer.

        Args:
            claude_cmd: Claude command to use (default: "claude")
        """
        self.claude_cmd = claude_cmd

    def answer_question(self, question: Question, topic: str) -> tuple[str, List[str]]:
        """Answer a question using web search.

        Args:
            question: Question to answer
            topic: Main topic for context

        Returns:
            Tuple of (answer_text, list_of_source_urls)
        """
        prompt = f"""Using web search, answer this question about {topic}:

"{question.text}"

Requirements:
- Provide a comprehensive but concise answer (2-4 sentences)
- Cite specific sources with URLs
- Focus on facts and evidence
- Format:
  ANSWER: [your answer here]
  SOURCES:
  - [url1]
  - [url2]
  - [url3]"""

        result = subprocess.run(
            [self.claude_cmd, "--dangerously-skip-permissions", "-p", prompt],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return f"Unable to answer: {question.text}", []

        # Parse output
        output = result.stdout.strip()
        answer = ""
        sources = []

        # Extract answer
        if "ANSWER:" in output:
            answer_section = output.split("ANSWER:", 1)[1]
            if "SOURCES:" in answer_section:
                answer = answer_section.split("SOURCES:")[0].strip()
            else:
                answer = answer_section.strip()
        else:
            # Fallback: take first paragraph
            answer = output.split("\n\n")[0].strip()

        # Extract sources
        if "SOURCES:" in output:
            sources_section = output.split("SOURCES:", 1)[1].strip()
            for line in sources_section.split("\n"):
                line = line.strip()
                if line.startswith("- ") or line.startswith("* "):
                    url = line[2:].strip()
                    if url.startswith("http"):
                        sources.append(url)
                elif line.startswith("http"):
                    sources.append(line)

        return answer or "Unable to provide answer", sources

    def answer_all_questions(self, questions: List[Question], topic: str) -> tuple[List[Question], List[str]]:
        """Answer all questions via web search.

        Args:
            questions: List of questions to answer
            topic: Main topic

        Returns:
            Tuple of (updated questions with answers populated, list of unique source URLs)
        """
        print(f"Answering {len(questions)} questions...")
        all_sources = set()

        for i, question in enumerate(questions, 1):
            print(f"  [{i}/{len(questions)}] Answering: {question.text[:60]}...")

            answer, sources = self.answer_question(question, topic)
            question.answer = answer
            all_sources.update(sources)

            # Progress feedback every 10 questions
            if i % 10 == 0:
                print(f"    Progress: {i}/{len(questions)} questions answered")

        print(f"Answered all questions. Found {len(all_sources)} unique sources")
        return questions, sorted(all_sources)
