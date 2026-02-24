"""Tests for evaluation harness runner."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from amplihack.eval.harness_runner import HarnessConfig, HarnessResult, run_harness


def test_run_harness_executes_all_phases(tmp_path):
    """Test that harness executes learning and testing phases."""
    news_file = tmp_path / "news.json"
    news_file.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "url": "https://example.com/1",
                        "title": "News",
                        "content": "Content",
                        "published": "2026-02-15T10:00:00Z",
                    }
                ]
            }
        )
    )

    config = HarnessConfig(
        news_file=str(news_file),
        output_dir=str(tmp_path / "output"),
        agent_name="test-agent",
        memory_backend="amplihack-memory-lib",
    )

    with patch("amplihack.eval.harness_runner.subprocess.run") as mock_run:
        # Mock learning phase
        learning_response = {"status": "success", "stored_count": 1, "total_articles": 1}
        # Mock testing phase
        testing_response = {
            "status": "success",
            "answers": [{"question": "Q1", "answer": "A1", "confidence": 0.9}],
        }

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout=json.dumps(learning_response)),
            MagicMock(returncode=0, stdout=json.dumps(testing_response)),
        ]

        with patch("amplihack.eval.harness_runner.grade_answer") as mock_grade:
            mock_grade.return_value = MagicMock(score=0.85, reasoning="Good")

            result = run_harness(config)

            assert isinstance(result, HarnessResult)
            assert result.success
            # Count only agent_subprocess calls (ignore platform-detection calls like uname)
            agent_calls = [
                c
                for c in mock_run.call_args_list
                if any("agent_subprocess" in str(a) for a in c[0])
            ]
            assert len(agent_calls) == 2  # Learning + testing phases


def test_run_harness_creates_output_directory(tmp_path):
    """Test that harness creates output directory."""
    news_file = tmp_path / "news.json"
    news_file.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "url": "https://example.com/1",
                        "title": "News",
                        "content": "Content",
                        "published": "2026-02-15T10:00:00Z",
                    }
                ]
            }
        )
    )

    output_dir = tmp_path / "output"
    config = HarnessConfig(
        news_file=str(news_file),
        output_dir=str(output_dir),
        agent_name="test-agent",
        memory_backend="amplihack-memory-lib",
    )

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout=json.dumps({"status": "success", "stored_count": 1, "total_articles": 1}),
            ),
            MagicMock(returncode=0, stdout=json.dumps({"status": "success", "answers": []})),
        ]

        run_harness(config)

        assert output_dir.exists()


def test_run_harness_generates_quiz(tmp_path):
    """Test that harness generates quiz file."""
    news_file = tmp_path / "news.json"
    news_file.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "url": "https://example.com/1",
                        "title": "News",
                        "content": "Important content here.",
                        "published": "2026-02-15T10:00:00Z",
                    }
                ]
            }
        )
    )

    config = HarnessConfig(
        news_file=str(news_file),
        output_dir=str(tmp_path / "output"),
        agent_name="test-agent",
        memory_backend="amplihack-memory-lib",
    )

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout=json.dumps({"status": "success", "stored_count": 1, "total_articles": 1}),
            ),
            MagicMock(returncode=0, stdout=json.dumps({"status": "success", "answers": []})),
        ]

        run_harness(config)

        quiz_file = Path(config.output_dir) / "quiz.json"
        assert quiz_file.exists()


def test_run_harness_subprocess_isolation(tmp_path):
    """Test that phases run in separate subprocesses."""
    news_file = tmp_path / "news.json"
    news_file.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "url": "https://example.com/1",
                        "title": "News",
                        "content": "Content",
                        "published": "2026-02-15T10:00:00Z",
                    }
                ]
            }
        )
    )

    config = HarnessConfig(
        news_file=str(news_file),
        output_dir=str(tmp_path / "output"),
        agent_name="test-agent",
        memory_backend="amplihack-memory-lib",
    )

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout=json.dumps({"status": "success", "stored_count": 1, "total_articles": 1}),
            ),
            MagicMock(returncode=0, stdout=json.dumps({"status": "success", "answers": []})),
        ]

        run_harness(config)

        # Filter to only agent_subprocess calls (ignore platform-detection calls like uname)
        calls = [
            c for c in mock_run.call_args_list if any("agent_subprocess" in str(a) for a in c[0])
        ]
        assert len(calls) == 2

        # Check learning phase
        learning_args = calls[0][0][0]
        assert "--phase" in learning_args
        assert "learning" in learning_args

        # Check testing phase
        testing_args = calls[1][0][0]
        assert "--phase" in testing_args
        assert "testing" in testing_args


def test_run_harness_handles_subprocess_failure(tmp_path):
    """Test harness handles subprocess failures gracefully."""
    news_file = tmp_path / "news.json"
    news_file.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "url": "https://example.com/1",
                        "title": "News",
                        "content": "Content",
                        "published": "2026-02-15T10:00:00Z",
                    }
                ]
            }
        )
    )

    config = HarnessConfig(
        news_file=str(news_file),
        output_dir=str(tmp_path / "output"),
        agent_name="test-agent",
        memory_backend="amplihack-memory-lib",
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="Error occurred")

        result = run_harness(config)

        assert not result.success
        assert "Error" in result.error_message or result.error_message is not None


def test_run_harness_returns_scores(tmp_path):
    """Test that harness returns grading scores."""
    news_file = tmp_path / "news.json"
    news_file.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "url": "https://example.com/1",
                        "title": "News",
                        "content": "Content",
                        "published": "2026-02-15T10:00:00Z",
                    }
                ]
            }
        )
    )

    config = HarnessConfig(
        news_file=str(news_file),
        output_dir=str(tmp_path / "output"),
        agent_name="test-agent",
        memory_backend="amplihack-memory-lib",
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"answers": [{"question": "Q1", "answer": "A1", "confidence": 0.9}]}),
        )

        with patch("amplihack.eval.grader.grade_answer") as mock_grade:
            mock_grade.return_value = MagicMock(score=0.85, reasoning="Good answer")

            result = run_harness(config)

            assert result.success
            assert hasattr(result, "scores")
            assert len(result.scores) > 0
