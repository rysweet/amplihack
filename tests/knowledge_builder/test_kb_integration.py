"""Integration tests for Knowledge Builder orchestrator."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.knowledge_builder import KnowledgeBuilder


class TestKnowledgeBuilderIntegration:
    """Test end-to-end Knowledge Builder workflow."""

    @patch("subprocess.run")
    def test_complete_workflow(self, mock_run, tmp_path):
        """Test complete workflow from topic to artifacts."""

        # Mock Claude responses for different stages
        def mock_subprocess(cmd, *args, **kwargs):
            """Mock subprocess.run based on command."""
            prompt = cmd[-1] if isinstance(cmd, list) else ""

            if "Generate exactly 10" in prompt:
                # Initial questions
                return MagicMock(
                    returncode=0,
                    stdout="\n".join([f"{i}. Initial question {i}?" for i in range(1, 11)]),
                )
            if "Using the Socratic method" in prompt:
                # Socratic follow-ups
                return MagicMock(
                    returncode=0,
                    stdout="1. Follow-up 1?\n2. Follow-up 2?\n3. Follow-up 3?",
                )
            if "Using web search" in prompt:
                # Answers
                return MagicMock(
                    returncode=0,
                    stdout="ANSWER: Test answer.\nSOURCES:\n- https://example.com",
                )
            return MagicMock(returncode=0, stdout="Generic response")

        mock_run.side_effect = mock_subprocess

        # Run workflow
        builder = KnowledgeBuilder(topic="Test Topic", claude_cmd="claude", output_base=tmp_path)
        output_dir = builder.build()

        # Verify output directory created
        assert output_dir.exists()
        assert output_dir.is_dir()

        # Verify all 5 artifact files created
        assert (output_dir / "Knowledge.md").exists()
        assert (output_dir / "Triplets.md").exists()
        assert (output_dir / "KeyInfo.md").exists()
        assert (output_dir / "Sources.md").exists()
        assert (output_dir / "HowToUseTheseFiles.md").exists()

        # Verify knowledge graph populated
        assert len(builder.kg.questions) > 0
        assert len(builder.kg.triplets) > 0
        assert builder.kg.timestamp != ""

    def test_output_directory_creation(self, tmp_path):
        """Test that output directory is created with sanitized name."""
        builder = KnowledgeBuilder(
            topic="Test Topic: With Special!@#$% Characters",
            claude_cmd="claude",
            output_base=tmp_path,
        )

        # Check sanitized directory name
        assert builder.output_dir.parent == tmp_path
        assert "test_topic" in str(builder.output_dir).lower()
        # Special characters should be replaced
        assert "!" not in str(builder.output_dir)
        assert "@" not in str(builder.output_dir)

    @patch("subprocess.run")
    def test_error_handling(self, mock_run, tmp_path):
        """Test error handling during workflow."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        builder = KnowledgeBuilder(topic="Test Topic", claude_cmd="claude", output_base=tmp_path)

        with pytest.raises(RuntimeError, match="Knowledge Builder failed"):
            builder.build()

    @patch("subprocess.run")
    def test_default_output_directory(self, mock_run, monkeypatch):
        """Test that default output directory is .claude/data."""
        # Mock Claude responses
        mock_run.return_value = MagicMock(
            returncode=0, stdout="1. Question 1?\n2. Question 2?\n3. Question 3?"
        )

        # Set current working directory for test
        test_cwd = Path("/tmp/test_workspace")
        monkeypatch.setattr(Path, "cwd", lambda: test_cwd)

        builder = KnowledgeBuilder(topic="Test")

        # Check default output path
        assert builder.output_dir.parent.parent == test_cwd / ".claude"
        assert builder.output_dir.parent.name == "data"

    @patch("subprocess.run")
    def test_artifact_content_quality(self, mock_run, tmp_path):
        """Test that generated artifacts contain expected content."""

        def mock_subprocess(cmd, *args, **kwargs):
            prompt = cmd[-1] if isinstance(cmd, list) else ""
            if "Generate exactly 10" in prompt:
                return MagicMock(
                    returncode=0, stdout="\n".join([f"{i}. Question {i}?" for i in range(1, 6)])
                )
            if "Using web search" in prompt:
                return MagicMock(
                    returncode=0,
                    stdout="ANSWER: Detailed answer here.\nSOURCES:\n- https://example.com\n- https://test.org",
                )
            return MagicMock(returncode=0, stdout="Response")

        mock_run.side_effect = mock_subprocess

        builder = KnowledgeBuilder(
            topic="Quantum Computing", claude_cmd="claude", output_base=tmp_path
        )
        output_dir = builder.build()

        # Check Knowledge.md content
        knowledge_content = (output_dir / "Knowledge.md").read_text()
        assert "Quantum Computing" in knowledge_content
        assert "```mermaid" in knowledge_content
        assert "Question" in knowledge_content

        # Check Triplets.md content
        triplets_content = (output_dir / "Triplets.md").read_text()
        assert "Subject" in triplets_content
        assert "Predicate" in triplets_content
        assert "Object" in triplets_content

        # Check KeyInfo.md content
        keyinfo_content = (output_dir / "KeyInfo.md").read_text()
        assert "Executive Summary" in keyinfo_content
        assert "Quantum Computing" in keyinfo_content
        assert "Total Questions" in keyinfo_content

        # Check Sources.md content
        sources_content = (output_dir / "Sources.md").read_text()
        assert "example.com" in sources_content or "Sources" in sources_content

        # Check HowToUseTheseFiles.md content
        howto_content = (output_dir / "HowToUseTheseFiles.md").read_text()
        assert "How To Use" in howto_content
        assert "Knowledge.md" in howto_content
        assert "Triplets.md" in howto_content
