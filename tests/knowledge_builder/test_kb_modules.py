"""Unit tests for Knowledge Builder modules."""

from unittest.mock import MagicMock, patch

from amplihack.knowledge_builder.kb_types import KnowledgeGraph, KnowledgeTriplet, Question
from amplihack.knowledge_builder.modules.artifact_generator import ArtifactGenerator
from amplihack.knowledge_builder.modules.knowledge_acquirer import KnowledgeAcquirer
from amplihack.knowledge_builder.modules.question_generator import QuestionGenerator


class TestQuestionGenerator:
    """Test question generation."""

    @patch("subprocess.run")
    def test_generate_initial_questions(self, mock_run):
        """Test generating 10 initial questions."""
        # Mock Claude response
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="\n".join([f"{i}. Question {i}?" for i in range(1, 11)]),
        )

        gen = QuestionGenerator(claude_cmd="claude")
        questions = gen.generate_initial_questions("Test Topic")

        assert len(questions) == 10
        assert all(q.depth == 0 for q in questions)
        assert all(q.parent_index is None for q in questions)
        assert mock_run.called

    @patch("subprocess.run")
    def test_generate_socratic_questions(self, mock_run):
        """Test generating Socratic follow-up questions."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="1. Follow-up 1?\n2. Follow-up 2?\n3. Follow-up 3?"
        )

        gen = QuestionGenerator(claude_cmd="claude")
        parent = Question(text="Parent question?", depth=0, parent_index=None)
        questions = gen.generate_socratic_questions(parent, 0)

        assert len(questions) == 3
        assert all(q.depth == 1 for q in questions)
        assert all(q.parent_index == 0 for q in questions)

    @patch("subprocess.run")
    def test_max_depth_limit(self, mock_run):
        """Test that Socratic method stops at depth 3."""
        gen = QuestionGenerator(claude_cmd="claude")
        parent = Question(text="Deep question?", depth=3, parent_index=0)
        questions = gen.generate_socratic_questions(parent, 0)

        assert len(questions) == 0  # No questions beyond depth 3
        assert not mock_run.called


class TestKnowledgeAcquirer:
    """Test knowledge acquisition via web search."""

    @patch("subprocess.run")
    def test_answer_question(self, mock_run):
        """Test answering a single question."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="ANSWER: This is the answer.\nSOURCES:\n- https://example.com\n- https://test.org",
        )

        acq = KnowledgeAcquirer(claude_cmd="claude")
        question = Question(text="What is this?", depth=0, parent_index=None)
        answer, sources = acq.answer_question(question, "Topic")

        assert answer == "This is the answer."
        assert len(sources) == 2
        assert "https://example.com" in sources
        assert mock_run.called

    @patch("subprocess.run")
    def test_answer_question_no_sources(self, mock_run):
        """Test answering when no sources are provided."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ANSWER: Just an answer.")

        acq = KnowledgeAcquirer(claude_cmd="claude")
        question = Question(text="What?", depth=0, parent_index=None)
        answer, sources = acq.answer_question(question, "Topic")

        assert answer == "Just an answer."
        assert len(sources) == 0

    @patch("subprocess.run")
    def test_answer_question_failure(self, mock_run):
        """Test handling of failed answer attempt."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        acq = KnowledgeAcquirer(claude_cmd="claude")
        question = Question(text="What?", depth=0, parent_index=None)
        answer, sources = acq.answer_question(question, "Topic")

        assert answer.startswith("Unable to answer")
        assert len(sources) == 0


class TestArtifactGenerator:
    """Test artifact generation."""

    def test_extract_triplets(self, tmp_path):
        """Test extracting knowledge triplets from Q&A pairs."""
        gen = ArtifactGenerator(tmp_path)

        questions = [
            Question(text="What is X?", depth=0, parent_index=None, answer="X is a thing."),
            Question(text="Why Y?", depth=1, parent_index=0, answer="Y happens because Z."),
            Question(
                text="Unable question?", depth=0, parent_index=None, answer="Unable to answer"
            ),
        ]

        triplets = gen.extract_triplets(questions)

        assert len(triplets) == 2  # Third question excluded (Unable)
        assert all(isinstance(t, KnowledgeTriplet) for t in triplets)
        assert triplets[0].subject == "What is X"
        assert triplets[0].predicate == "has answer"

    def test_generate_knowledge_md(self, tmp_path):
        """Test generating Knowledge.md file."""
        gen = ArtifactGenerator(tmp_path)

        kg = KnowledgeGraph(
            topic="Test Topic",
            questions=[Question(text="Q1?", depth=0, parent_index=None, answer="A1")],
            triplets=[],
            sources=[],
            timestamp="2025-01-01 00:00:00",
        )

        output_file = gen.generate_knowledge_md(kg)

        assert output_file.exists()
        content = output_file.read_text()
        assert "Test Topic" in content
        assert "```mermaid" in content
        assert "Q1?" in content

    def test_generate_triplets_md(self, tmp_path):
        """Test generating Triplets.md file."""
        gen = ArtifactGenerator(tmp_path)

        kg = KnowledgeGraph(
            topic="Test Topic",
            questions=[],
            triplets=[
                KnowledgeTriplet(subject="S1", predicate="P1", object="O1", source="source1")
            ],
            sources=[],
            timestamp="2025-01-01 00:00:00",
        )

        output_file = gen.generate_triplets_md(kg)

        assert output_file.exists()
        content = output_file.read_text()
        assert "S1" in content
        assert "P1" in content
        assert "O1" in content

    def test_generate_keyinfo_md(self, tmp_path):
        """Test generating KeyInfo.md file."""
        gen = ArtifactGenerator(tmp_path)

        kg = KnowledgeGraph(
            topic="Test Topic",
            questions=[Question(text="Q1?", depth=0, parent_index=None, answer="A1")],
            triplets=[],
            sources=[],
            timestamp="2025-01-01 00:00:00",
        )

        output_file = gen.generate_keyinfo_md(kg)

        assert output_file.exists()
        content = output_file.read_text()
        assert "Executive Summary" in content
        assert "Test Topic" in content
        assert "Q1?" in content

    def test_generate_sources_md(self, tmp_path):
        """Test generating Sources.md file."""
        gen = ArtifactGenerator(tmp_path)

        kg = KnowledgeGraph(
            topic="Test Topic",
            questions=[],
            triplets=[],
            sources=["https://example.com/page1", "https://test.org/page2"],
            timestamp="2025-01-01 00:00:00",
        )

        output_file = gen.generate_sources_md(kg)

        assert output_file.exists()
        content = output_file.read_text()
        assert "example.com" in content
        assert "test.org" in content
        assert "https://example.com/page1" in content

    def test_generate_howto_md(self, tmp_path):
        """Test generating HowToUseTheseFiles.md file."""
        gen = ArtifactGenerator(tmp_path)

        kg = KnowledgeGraph(
            topic="Test Topic",
            questions=[],
            triplets=[],
            sources=[],
            timestamp="2025-01-01 00:00:00",
        )

        output_file = gen.generate_howto_md(kg)

        assert output_file.exists()
        content = output_file.read_text()
        assert "How To Use These Files" in content
        assert "Knowledge.md" in content
        assert "Triplets.md" in content

    def test_generate_all(self, tmp_path):
        """Test generating all 5 artifact files."""
        gen = ArtifactGenerator(tmp_path)

        kg = KnowledgeGraph(
            topic="Test Topic",
            questions=[Question(text="Q1?", depth=0, parent_index=None, answer="A1")],
            triplets=[],
            sources=["https://example.com"],
        )

        files = gen.generate_all(kg)

        assert len(files) == 5
        assert all(f.exists() for f in files)
        assert kg.timestamp != ""  # Timestamp added
        assert len(kg.triplets) > 0  # Triplets extracted


class TestKnowledgeGraph:
    """Test KnowledgeGraph data structure."""

    def test_initialization(self):
        """Test KnowledgeGraph initialization."""
        kg = KnowledgeGraph(topic="Test")

        assert kg.topic == "Test"
        assert len(kg.questions) == 0
        assert len(kg.triplets) == 0
        assert len(kg.sources) == 0
        assert kg.timestamp == ""

    def test_add_questions(self):
        """Test adding questions to knowledge graph."""
        kg = KnowledgeGraph(topic="Test")

        q1 = Question(text="Q1?", depth=0, parent_index=None)
        q2 = Question(text="Q2?", depth=1, parent_index=0)

        kg.questions = [q1, q2]

        assert len(kg.questions) == 2
        assert kg.questions[0].depth == 0
        assert kg.questions[1].parent_index == 0
