#!/usr/bin/env python3
"""
Unit tests for power-steering redirect functionality.

Tests redirect persistence, loading, formatting, and edge cases.
"""

import json
import tempfile
from pathlib import Path

import pytest
from power_steering_checker import PowerSteeringChecker, PowerSteeringRedirect


class TestRedirectPersistence:
    """Test redirect save and load operations."""

    def test_save_redirect(self):
        """Test saving a redirect creates proper JSONL file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir()

            checker = PowerSteeringChecker(project_root)
            session_id = "test_session_001"

            # Save a redirect
            checker._save_redirect(
                session_id=session_id,
                failed_considerations=["todos_complete", "ci_status"],
                continuation_prompt="Please complete TODOs and fix CI",
                work_summary="Implemented feature X",
            )

            # Verify file was created
            redirects_file = checker._get_redirect_file(session_id)
            assert redirects_file.exists()

            # Verify file permissions (owner read/write only)
            assert oct(redirects_file.stat().st_mode)[-3:] == "600"

            # Verify content
            with open(redirects_file) as f:
                line = f.readline().strip()
                data = json.loads(line)

            assert data["redirect_number"] == 1
            assert data["failed_considerations"] == ["todos_complete", "ci_status"]
            assert data["continuation_prompt"] == "Please complete TODOs and fix CI"
            assert data["work_summary"] == "Implemented feature X"
            assert "timestamp" in data

    def test_save_multiple_redirects(self):
        """Test saving multiple redirects increments redirect_number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir()

            checker = PowerSteeringChecker(project_root)
            session_id = "test_session_002"

            # Save first redirect
            checker._save_redirect(
                session_id=session_id,
                failed_considerations=["todos_complete"],
                continuation_prompt="Complete TODOs",
            )

            # Save second redirect
            checker._save_redirect(
                session_id=session_id,
                failed_considerations=["ci_status"],
                continuation_prompt="Fix CI",
            )

            # Verify both redirects exist with correct numbers
            redirects = checker._load_redirects(session_id)
            assert len(redirects) == 2
            assert redirects[0].redirect_number == 1
            assert redirects[1].redirect_number == 2

    def test_load_redirects(self):
        """Test loading redirects works correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir()

            checker = PowerSteeringChecker(project_root)
            session_id = "test_session_003"

            # Save some redirects
            checker._save_redirect(
                session_id=session_id,
                failed_considerations=["todos_complete"],
                continuation_prompt="Complete TODOs",
                work_summary="Did some work",
            )

            checker._save_redirect(
                session_id=session_id,
                failed_considerations=["ci_status", "local_testing"],
                continuation_prompt="Fix CI and run tests",
            )

            # Load redirects
            redirects = checker._load_redirects(session_id)

            assert len(redirects) == 2
            assert isinstance(redirects[0], PowerSteeringRedirect)
            assert isinstance(redirects[1], PowerSteeringRedirect)
            assert redirects[0].failed_considerations == ["todos_complete"]
            assert redirects[1].failed_considerations == ["ci_status", "local_testing"]


class TestRedirectEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_redirects(self):
        """Test loading when no redirects file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir()

            checker = PowerSteeringChecker(project_root)
            session_id = "nonexistent_session"

            # Should return empty list, not error
            redirects = checker._load_redirects(session_id)
            assert redirects == []

    def test_malformed_jsonl(self):
        """Test loading skips malformed JSONL lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            runtime_dir = project_root / ".claude" / "runtime" / "power-steering"
            runtime_dir.mkdir(parents=True)

            session_id = "test_malformed"
            session_dir = runtime_dir / session_id
            session_dir.mkdir()
            redirects_file = session_dir / "redirects.jsonl"

            # Write mixed valid and invalid JSONL
            with open(redirects_file, "w") as f:
                # Valid line
                f.write(
                    json.dumps(
                        {
                            "redirect_number": 1,
                            "timestamp": "2024-01-01T00:00:00",
                            "failed_considerations": ["test"],
                            "continuation_prompt": "test",
                        }
                    )
                    + "\n"
                )
                # Malformed JSON
                f.write("not valid json\n")
                # Empty line
                f.write("\n")
                # Another valid line
                f.write(
                    json.dumps(
                        {
                            "redirect_number": 2,
                            "timestamp": "2024-01-01T00:01:00",
                            "failed_considerations": ["test2"],
                            "continuation_prompt": "test2",
                        }
                    )
                    + "\n"
                )

            checker = PowerSteeringChecker(project_root)
            redirects = checker._load_redirects(session_id)

            # Should load only valid entries
            assert len(redirects) == 2
            assert redirects[0].redirect_number == 1
            assert redirects[1].redirect_number == 2

    def test_missing_required_fields(self):
        """Test loading skips entries with missing required fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            runtime_dir = project_root / ".claude" / "runtime" / "power-steering"
            runtime_dir.mkdir(parents=True)

            session_id = "test_missing_fields"
            session_dir = runtime_dir / session_id
            session_dir.mkdir()
            redirects_file = session_dir / "redirects.jsonl"

            # Write JSONL with missing fields
            with open(redirects_file, "w") as f:
                # Missing continuation_prompt (required)
                f.write(
                    json.dumps(
                        {
                            "redirect_number": 1,
                            "timestamp": "2024-01-01T00:00:00",
                            "failed_considerations": ["test"],
                        }
                    )
                    + "\n"
                )
                # Valid entry
                f.write(
                    json.dumps(
                        {
                            "redirect_number": 2,
                            "timestamp": "2024-01-01T00:01:00",
                            "failed_considerations": ["test2"],
                            "continuation_prompt": "test2",
                        }
                    )
                    + "\n"
                )

            checker = PowerSteeringChecker(project_root)
            redirects = checker._load_redirects(session_id)

            # Should skip entry with missing field
            assert len(redirects) == 1
            assert redirects[0].redirect_number == 2

    def test_save_redirect_fails_gracefully(self):
        """Test saving redirect fails gracefully (fail-open)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir()

            checker = PowerSteeringChecker(project_root)

            # Use invalid session ID (contains path traversal)
            session_id = "../../../etc/passwd"

            # Should not raise exception (fail-open)
            checker._save_redirect(
                session_id=session_id,
                failed_considerations=["test"],
                continuation_prompt="test",
            )

            # No exception = test passes


class TestRedirectFormatting:
    """Test formatting redirects for display."""

    def test_format_redirects_context(self):
        """Test formatting redirect history for context."""
        from claude_reflection import format_redirects_context

        redirects = [
            {
                "redirect_number": 1,
                "timestamp": "2024-01-01T10:00:00",
                "failed_considerations": ["todos_complete", "ci_status"],
                "continuation_prompt": "Please complete TODOs and fix CI",
            },
            {
                "redirect_number": 2,
                "timestamp": "2024-01-01T10:30:00",
                "failed_considerations": ["local_testing"],
                "continuation_prompt": "Run local tests",
            },
        ]

        result = format_redirects_context(redirects)

        # Verify structure
        assert "## Power-Steering Redirect History" in result
        assert "Redirect #1" in result
        assert "Redirect #2" in result
        assert "todos_complete, ci_status" in result
        assert "local_testing" in result
        assert "Please complete TODOs and fix CI" in result
        assert "Run local tests" in result

    def test_format_redirects_context_single_redirect(self):
        """Test formatting with single redirect uses correct plural."""
        from claude_reflection import format_redirects_context

        redirects = [
            {
                "redirect_number": 1,
                "timestamp": "2024-01-01T10:00:00",
                "failed_considerations": ["todos_complete"],
                "continuation_prompt": "Complete TODOs",
            }
        ]

        result = format_redirects_context(redirects)

        # Should use singular form (after fix)
        assert "1 power-steering redirect" in result

    def test_format_redirects_context_multiple_redirects(self):
        """Test formatting with multiple redirects uses correct plural."""
        from claude_reflection import format_redirects_context

        redirects = [
            {
                "redirect_number": 1,
                "timestamp": "2024-01-01T10:00:00",
                "failed_considerations": ["todos_complete"],
                "continuation_prompt": "Complete TODOs",
            },
            {
                "redirect_number": 2,
                "timestamp": "2024-01-01T10:30:00",
                "failed_considerations": ["ci_status"],
                "continuation_prompt": "Fix CI",
            },
        ]

        result = format_redirects_context(redirects)

        # Should use plural form
        assert "2 power-steering redirects" in result

    def test_format_redirects_context_empty(self):
        """Test formatting with empty redirects list."""
        from claude_reflection import format_redirects_context

        result = format_redirects_context(None)
        assert result == ""

        result = format_redirects_context([])
        assert result == ""


class TestRedirectIntegration:
    """Integration tests for redirect flow."""

    def test_redirect_saved_on_block_decision(self):
        """Test that redirects are saved when session is blocked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir()

            # Create minimal transcript with incomplete TODOs and file operations
            # to avoid Q&A session detection
            transcript_file = project_root / "transcript.jsonl"
            with open(transcript_file, "w") as f:
                # User request
                f.write(
                    json.dumps(
                        {
                            "type": "user",
                            "message": {"content": "Implement feature X"},
                        }
                    )
                    + "\n"
                )
                # Assistant creates TODOs
                f.write(
                    json.dumps(
                        {
                            "type": "assistant",
                            "message": {
                                "content": [
                                    {
                                        "type": "tool_use",
                                        "id": "tool_1",
                                        "name": "TodoWrite",
                                        "input": {
                                            "todos": [
                                                {
                                                    "content": "Write code",
                                                    "status": "pending",
                                                    "activeForm": "Writing code",
                                                }
                                            ]
                                        },
                                    },
                                    {
                                        "type": "tool_use",
                                        "id": "tool_2",
                                        "name": "Write",
                                        "input": {
                                            "file_path": "/tmp/test.py",
                                            "content": "print('hello')",
                                        },
                                    },
                                ]
                            },
                        }
                    )
                    + "\n"
                )
                # Tool results
                f.write(
                    json.dumps(
                        {
                            "type": "tool_result",
                            "message": {"tool_use_id": "tool_1", "content": "TODOs created"},
                        }
                    )
                    + "\n"
                )
                f.write(
                    json.dumps(
                        {
                            "type": "tool_result",
                            "message": {"tool_use_id": "tool_2", "content": "File written"},
                        }
                    )
                    + "\n"
                )

            # Mock SDK_AVAILABLE to use heuristic checkers (Issue #2196)
            # Without this, SDK may return unexpected results for test data
            from unittest.mock import patch

            with patch("power_steering_checker.SDK_AVAILABLE", False):
                checker = PowerSteeringChecker(project_root)
                session_id = "test_integration_001"

                # Run check (should block due to incomplete TODOs)
                result = checker.check(transcript_file, session_id)

                # Verify blocked
                assert result.decision == "block"
                assert "todos_complete" in result.reasons

            # Verify redirect was saved
            redirects = checker._load_redirects(session_id)
            assert len(redirects) == 1
            assert "todos_complete" in redirects[0].failed_considerations

    def test_no_redirect_saved_on_approve_decision(self):
        """Test that no redirects are saved when session is approved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / ".claude").mkdir()

            # Create minimal transcript with Q&A pattern (will be approved)
            transcript_file = project_root / "transcript.jsonl"
            with open(transcript_file, "w") as f:
                f.write(
                    json.dumps(
                        {
                            "type": "user",
                            "message": {"content": "What is Python?"},
                        }
                    )
                    + "\n"
                )
                f.write(
                    json.dumps(
                        {
                            "type": "assistant",
                            "message": {
                                "content": [
                                    {"type": "text", "text": "Python is a programming language"}
                                ]
                            },
                        }
                    )
                    + "\n"
                )

            checker = PowerSteeringChecker(project_root)
            session_id = "test_integration_002"

            # Run check (should approve as Q&A)
            result = checker.check(transcript_file, session_id)

            # Verify approved
            assert result.decision == "approve"

            # Verify no redirects saved
            redirects_file = checker._get_redirect_file(session_id)
            assert not redirects_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
