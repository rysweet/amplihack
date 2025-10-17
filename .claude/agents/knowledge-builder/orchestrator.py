"""Knowledge Builder orchestrator - main entry point."""

import sys
from pathlib import Path

from .kb_types import KnowledgeGraph
from .modules.artifact_generator import ArtifactGenerator
from .modules.knowledge_acquirer import KnowledgeAcquirer
from .modules.question_generator import QuestionGenerator


class KnowledgeBuilder:
    """Main orchestrator for Knowledge Builder workflow."""

    def __init__(self, topic: str, claude_cmd: str = "claude", output_base: Path | None = None):
        """Initialize Knowledge Builder.

        Args:
            topic: Topic to build knowledge about (1-2 sentences)
            claude_cmd: Claude command to use (default: "claude")
            output_base: Base directory for output (default: .claude/data)
        """
        self.topic = topic.strip()
        self.claude_cmd = claude_cmd

        # Sanitize topic for directory name
        topic_slug = "".join(c if c.isalnum() or c in " -_" else "_" for c in self.topic[:50])
        topic_slug = topic_slug.strip().replace(" ", "_").lower()

        # Setup output directory
        if output_base is None:
            output_base = Path.cwd() / ".claude" / "data"
        self.output_dir = output_base / topic_slug

        # Initialize modules
        self.question_gen = QuestionGenerator(claude_cmd)
        self.knowledge_acq = KnowledgeAcquirer(claude_cmd)
        self.artifact_gen = ArtifactGenerator(self.output_dir)

        # Initialize knowledge graph
        self.kg = KnowledgeGraph(topic=self.topic)

    def build(self) -> Path:
        """Execute complete Knowledge Builder workflow.

        Returns:
            Path to output directory containing all artifacts

        Raises:
            RuntimeError: If workflow fails
        """
        print("=" * 70)
        print(f"Knowledge Builder: {self.topic}")
        print("=" * 70)
        print()

        try:
            # Step 1: Generate questions (270 total)
            print("STEP 1: Generating questions using Socratic method...")
            print("-" * 70)
            self.kg.questions = self.question_gen.generate_all_questions(self.topic)
            print()

            # Step 2: Answer questions via web search
            print("STEP 2: Answering questions via web search...")
            print("-" * 70)
            self.kg.questions = self.knowledge_acq.answer_all_questions(
                self.kg.questions, self.topic
            )

            # Collect all unique sources
            all_sources = set()
            for q in self.kg.questions:
                # Sources would be attached during answer_question if we tracked them
                pass  # Sources are collected in answer_question but not stored in Question
            self.kg.sources = sorted(all_sources)
            print()

            # Step 3: Generate artifacts (5 files)
            print("STEP 3: Generating artifacts...")
            print("-" * 70)
            artifact_files = self.artifact_gen.generate_all(self.kg)
            print()

            # Summary
            print("=" * 70)
            print("COMPLETE")
            print("=" * 70)
            print(f"Topic: {self.topic}")
            print(f"Questions: {len(self.kg.questions)}")
            print(f"Triplets: {len(self.kg.triplets)}")
            print(f"Sources: {len(self.kg.sources)}")
            print(f"Output: {self.output_dir}")
            print()
            print("Generated files:")
            for f in artifact_files:
                print(f"  - {f.name}")
            print()

            return self.output_dir

        except Exception as e:
            print(f"ERROR: Knowledge Builder workflow failed: {e}", file=sys.stderr)
            raise RuntimeError(f"Knowledge Builder failed: {e}") from e


def main():
    """CLI entry point for Knowledge Builder."""
    if len(sys.argv) < 2:
        print("Usage: python -m orchestrator '<topic (1-2 sentences)>'", file=sys.stderr)
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    builder = KnowledgeBuilder(topic)
    output_dir = builder.build()

    print(f"Knowledge base created: {output_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
