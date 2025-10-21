"""Real-world scenario test: Generate Rust Programming Expert agent artifacts.

This test verifies the knowledge-builder can create comprehensive, usable
expert agent artifacts for a real domain (Rust programming).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.knowledge_builder import KnowledgeBuilder


class TestRustExpertScenario:
    """Test creating a Rust Programming Expert agent using knowledge-builder."""

    @pytest.fixture
    def rust_mock_responses(self):
        """Provide realistic Rust-specific mock responses."""

        # Initial questions about Rust (realistic questions)
        initial_questions = """1. What is Rust's ownership system and why is it unique?
2. How does Rust's borrow checker work and what problems does it solve?
3. What are Rust's key advantages for systems programming?"""

        # Socratic follow-up questions (realistic depth)
        socratic_questions = """1. What are the trade-offs between Rust's compile-time safety and developer ergonomics?
2. How does Rust's ownership model compare to garbage collection approaches?
3. What scenarios might warrant choosing C++ over Rust despite Rust's safety guarantees?"""

        # Answer with sources (realistic content)
        answer_ownership = """ANSWER: Rust's ownership system is a compile-time memory management approach that ensures memory safety without a garbage collector. Each value has a single owner, and ownership can be transferred (moved) or temporarily borrowed. This prevents data races, null pointer dereferences, and use-after-free bugs at compile time.
SOURCES:
- https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html
- https://www.rust-lang.org/learn
- https://stackoverflow.com/questions/tagged/rust+ownership"""

        answer_borrow_checker = """ANSWER: The borrow checker enforces Rust's borrowing rules: you can have either one mutable reference or multiple immutable references to data at a time, preventing data races. It analyzes code at compile time to ensure references don't outlive their data and validates that aliasing and mutation don't occur simultaneously.
SOURCES:
- https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html
- https://blog.rust-lang.org/2020/08/27/Rust-1.46.0.html
- https://fasterthanli.me/articles/a-half-hour-to-learn-rust"""

        answer_advantages = """ANSWER: Rust offers memory safety without garbage collection, zero-cost abstractions, fearless concurrency through ownership types, and excellent performance comparable to C/C++. Its strong type system catches errors at compile time, and the package manager (Cargo) provides modern tooling for dependency management, testing, and documentation.
SOURCES:
- https://www.rust-lang.org/
- https://survey.stackoverflow.co/2024/#technology-most-loved-dreaded-and-wanted
- https://microsoft.github.io/code-with-engineering-playbook/rust/"""

        answer_tradeoffs = """ANSWER: Rust's strict borrow checker can lead to longer development times initially, especially for developers learning the ownership model. Complex lifetime annotations can make code harder to read. However, these compile-time checks prevent entire classes of runtime bugs, making the trade-off worthwhile for safety-critical systems.
SOURCES:
- https://www.reddit.com/r/rust/
- https://matklad.github.io/2020/01/02/spinlocks-considered-harmful.html
- https://web.stanford.edu/class/cs140e/"""

        answer_comparison = """ANSWER: Unlike garbage collection (GC) which pauses execution unpredictably, Rust's ownership provides deterministic resource cleanup with zero runtime overhead. GC is easier for rapid prototyping but unsuitable for real-time systems. Rust's approach requires more upfront thought but eliminates an entire category of bugs and performance issues.
SOURCES:
- https://discord.com/blog/why-discord-is-switching-from-go-to-rust
- https://blog.discordapp.com/using-rust-to-scale-elixir-for-11-million-concurrent-users-c6f19fc029d3
- https://aws.amazon.com/blogs/opensource/why-aws-loves-rust/"""

        answer_cpp_vs_rust = """ANSWER: C++ may be preferred when: existing C++ codebases are massive and rewriting isn't viable, specific third-party libraries only exist in C++, team expertise is entirely C++-focused, or compile times must be absolutely minimized. However, for new projects, Rust's safety guarantees usually outweigh C++'s maturity.
SOURCES:
- https://chromium.googlesource.com/chromium/src/+/main/docs/security/rust-toolchain.md
- https://security.googleblog.com/2021/04/rust-in-android-platform.html
- https://www.chromium.org/Home/chromium-security/memory-safety/"""

        return {
            "initial_questions": initial_questions,
            "socratic_questions": socratic_questions,
            "answers": {
                "ownership": answer_ownership,
                "borrow_checker": answer_borrow_checker,
                "advantages": answer_advantages,
                "tradeoffs": answer_tradeoffs,
                "comparison": answer_comparison,
                "cpp_vs_rust": answer_cpp_vs_rust,
            },
        }

    def mock_subprocess_rust(self, rust_mock_responses):
        """Create mock subprocess function for Rust scenario."""
        answer_index = [0]  # Track which answer to return

        def mock_subprocess(cmd, *args, **kwargs):
            prompt = cmd[-1] if isinstance(cmd, list) else ""

            if "Generate exactly 10" in prompt or "Generate exactly 3" in prompt:
                # Return initial questions
                return MagicMock(returncode=0, stdout=rust_mock_responses["initial_questions"])

            if "Using the Socratic method" in prompt:
                # Return follow-up questions
                return MagicMock(returncode=0, stdout=rust_mock_responses["socratic_questions"])

            if "Using web search" in prompt:
                # Rotate through realistic answers
                answers = list(rust_mock_responses["answers"].values())
                answer = answers[answer_index[0] % len(answers)]
                answer_index[0] += 1
                return MagicMock(returncode=0, stdout=answer)

            return MagicMock(returncode=0, stdout="Generic response")

        return mock_subprocess

    @patch("subprocess.run")
    def test_rust_expert_artifact_generation(self, mock_run, tmp_path, rust_mock_responses):
        """Test complete Rust expert artifact generation with realistic content."""

        # Setup mock with Rust-specific responses
        mock_run.side_effect = self.mock_subprocess_rust(rust_mock_responses)

        # Create knowledge builder for Rust
        topic = "Rust programming language tooling, ecosystem, and best practices"
        builder = KnowledgeBuilder(topic=topic, claude_cmd="claude", output_base=tmp_path)

        # Monkey-patch to generate fewer questions for faster testing
        original_generate = builder.question_gen.generate_initial_questions

        def limited_generate(topic_arg):
            questions = original_generate(topic_arg)
            return questions[:3]  # Only 3 initial questions for speed

        builder.question_gen.generate_initial_questions = limited_generate

        # Execute workflow
        output_dir = builder.build()

        # Verify all 5 artifacts created
        assert (output_dir / "Knowledge.md").exists()
        assert (output_dir / "Triplets.md").exists()
        assert (output_dir / "KeyInfo.md").exists()
        assert (output_dir / "Sources.md").exists()
        assert (output_dir / "HowToUseTheseFiles.md").exists()

        # Verify content quality
        self._verify_knowledge_md(output_dir, topic)
        self._verify_triplets_md(output_dir)
        self._verify_keyinfo_md(output_dir, topic)
        self._verify_sources_md(output_dir)
        self._verify_howto_md(output_dir)

        # Verify knowledge graph populated correctly
        assert len(builder.kg.questions) >= 3, "Should have at least 3 questions"
        assert len(builder.kg.triplets) > 0, "Should have extracted triplets"
        assert builder.kg.timestamp != "", "Should have timestamp"

    def _verify_knowledge_md(self, output_dir: Path, topic: str):
        """Verify Knowledge.md contains proper structure and content."""
        content = (output_dir / "Knowledge.md").read_text()

        # Must have topic
        assert topic in content or "Rust" in content, "Should mention Rust"

        # Must have mermaid diagram
        assert "```mermaid" in content, "Should have mermaid diagram"
        assert "graph TD" in content, "Mermaid should be directed graph"

        # Must have questions and answers
        assert "?" in content, "Should have questions"
        assert "Answer:" in content or "ownership" in content.lower(), "Should have answers"

        # Should have hierarchy structure
        assert "##" in content, "Should have markdown headers"

    def _verify_triplets_md(self, output_dir: Path):
        """Verify Triplets.md contains proper triplet structure."""
        content = (output_dir / "Triplets.md").read_text()

        # Must have triplet table headers
        assert "Subject" in content, "Should have Subject column"
        assert "Predicate" in content, "Should have Predicate column"
        assert "Object" in content, "Should have Object column"
        assert "Source" in content, "Should have Source column"

        # Must have table formatting
        assert "|" in content, "Should use markdown table format"
        assert "---" in content, "Should have table divider"

    def _verify_keyinfo_md(self, output_dir: Path, topic: str):
        """Verify KeyInfo.md contains executive summary."""
        content = (output_dir / "KeyInfo.md").read_text()

        # Must have executive summary
        assert "Executive Summary" in content, "Should have Executive Summary"
        assert topic in content or "Rust" in content, "Should mention topic"

        # Must have statistics
        assert "Total Questions" in content, "Should report question count"
        assert "Unique Sources" in content, "Should report source count"

        # Must have core concepts section
        assert "Core Concepts" in content or "###" in content, "Should have concept sections"

    def _verify_sources_md(self, output_dir: Path):
        """Verify Sources.md contains properly formatted sources."""
        content = (output_dir / "Sources.md").read_text()

        # Must have sources header
        assert "Sources:" in content or "Overview" in content, "Should have sources header"

        # Should have actual URLs (from our mocked responses)
        assert "rust-lang.org" in content or "http" in content, "Should have domain names or URLs"

        # Should be grouped by domain
        assert "###" in content or "##" in content, "Should have domain groupings"

    def _verify_howto_md(self, output_dir: Path):
        """Verify HowToUseTheseFiles.md contains usage guide."""
        content = (output_dir / "HowToUseTheseFiles.md").read_text()

        # Must reference all artifact files
        assert "Knowledge.md" in content, "Should reference Knowledge.md"
        assert "Triplets.md" in content, "Should reference Triplets.md"
        assert "KeyInfo.md" in content, "Should reference KeyInfo.md"
        assert "Sources.md" in content, "Should reference Sources.md"

        # Must have usage instructions
        assert "Quick Start" in content or "Overview" in content, "Should have quick start"
        assert "Structure" in content or "organized" in content.lower(), "Should explain structure"

    @patch("subprocess.run")
    def test_artifacts_suitable_for_expert_agent(self, mock_run, tmp_path, rust_mock_responses):
        """Verify generated artifacts could be used to create an expert agent."""

        mock_run.side_effect = self.mock_subprocess_rust(rust_mock_responses)

        topic = "Rust programming language tooling, ecosystem, and best practices"
        builder = KnowledgeBuilder(topic=topic, claude_cmd="claude", output_base=tmp_path)

        # Limit questions for speed
        original_generate = builder.question_gen.generate_initial_questions

        def limited_generate(topic_arg):
            questions = original_generate(topic_arg)
            return questions[:3]

        builder.question_gen.generate_initial_questions = limited_generate

        output_dir = builder.build()

        # Check that artifacts contain expert-level content indicators
        knowledge_content = (output_dir / "Knowledge.md").read_text()
        keyinfo_content = (output_dir / "KeyInfo.md").read_text()

        # Should have technical depth
        technical_terms = ["ownership", "borrow", "safety", "memory", "compile"]
        assert any(term in knowledge_content.lower() for term in technical_terms), (
            "Should contain technical Rust terminology"
        )

        # Should have structured knowledge
        assert knowledge_content.count("#") >= 3, (
            "Should have hierarchical structure (multiple headers)"
        )

        # Should have answerable questions with citations
        triplets_content = (output_dir / "Triplets.md").read_text()
        assert triplets_content.count("|") >= 10, "Should have multiple triplets in table"

        # Should have verifiable sources
        sources_content = (output_dir / "Sources.md").read_text()
        assert sources_content.count("http") >= 3, "Should have multiple source URLs"

        # Key info should provide quick expert context
        assert len(keyinfo_content) > 500, "KeyInfo should be substantial (>500 chars)"
        assert "statistics" in keyinfo_content.lower() or "Total Questions" in keyinfo_content, (
            "Should have quantitative metrics"
        )

    @patch("subprocess.run")
    def test_artifact_file_quality_metrics(self, mock_run, tmp_path, rust_mock_responses):
        """Test that artifacts meet quality metrics for expert agent use."""

        mock_run.side_effect = self.mock_subprocess_rust(rust_mock_responses)

        topic = "Rust programming language tooling, ecosystem, and best practices"
        builder = KnowledgeBuilder(topic=topic, claude_cmd="claude", output_base=tmp_path)

        # Limit for speed
        original_generate = builder.question_gen.generate_initial_questions

        def limited_generate(topic_arg):
            questions = original_generate(topic_arg)
            return questions[:3]

        builder.question_gen.generate_initial_questions = limited_generate

        output_dir = builder.build()

        # Quality metrics
        metrics = {
            "Knowledge.md": {"min_size": 1000, "must_have": ["mermaid", "Answer:", "Rust"]},
            "Triplets.md": {
                "min_size": 300,
                "must_have": ["Subject", "Predicate", "Object", "has answer"],
            },
            "KeyInfo.md": {
                "min_size": 500,
                "must_have": ["Executive Summary", "Core Concepts", "Total Questions"],
            },
            "Sources.md": {"min_size": 200, "must_have": ["Sources:", "http"]},
            "HowToUseTheseFiles.md": {
                "min_size": 800,
                "must_have": ["Quick Start", "Knowledge.md", "Structure"],
            },
        }

        for filename, requirements in metrics.items():
            filepath = output_dir / filename
            assert filepath.exists(), f"{filename} should exist"

            content = filepath.read_text()
            content_size = len(content)

            assert content_size >= requirements["min_size"], (
                f"{filename} should be at least {requirements['min_size']} bytes (got {content_size})"
            )

            for must_have in requirements["must_have"]:
                assert must_have in content, (
                    f"{filename} should contain '{must_have}' (case-sensitive)"
                )

        # Additional quality checks
        knowledge_md = (output_dir / "Knowledge.md").read_text()
        assert knowledge_md.count("```") >= 2, (
            "Knowledge.md should have code blocks (mermaid diagram)"
        )

        triplets_md = (output_dir / "Triplets.md").read_text()
        table_rows = triplets_md.count("\n|") - 2  # Minus header and separator
        assert table_rows >= 3, f"Should have at least 3 triplet rows (got {table_rows})"
