"""
Unit tests for blarify progress indicator functionality.

Tests the progress indicator added to run_blarify function to ensure:
- Progress is displayed during long-running operations
- JSON output is still captured correctly
- Fallback works when rich is not available
- No interference with subprocess execution
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestBlarifyProgressIndicator:
    """Test blarify progress indicator functionality."""

    def test_WHEN_run_blarify_with_rich_THEN_progress_indicator_used(self):
        """Test that progress indicator is used when rich is available."""
        # Import the module directly to avoid test directory conflict
        import amplihack.memory.neo4j.code_graph as code_graph

        with patch.object(code_graph, "RICH_AVAILABLE", True):
            with patch.object(code_graph, "_run_with_progress_indicator") as mock_progress_runner:
                with patch("subprocess.run") as mock_version_check:
                    # Mock successful subprocess result
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = '{"files": []}'
                    mock_result.stderr = ""
                    mock_progress_runner.return_value = mock_result
                    mock_version_check.return_value = Mock(returncode=0)

                    codebase_path = Path("/tmp/test")
                    output_path = Path("/tmp/output.json")

                    result = code_graph.run_blarify(codebase_path, output_path)

                    # Verify progress indicator was called
                    assert result is True
                    mock_progress_runner.assert_called_once()

    def test_WHEN_run_blarify_without_rich_THEN_fallback_used(self):
        """Test that fallback execution is used when rich is not available."""
        import amplihack.memory.neo4j.code_graph as code_graph

        with patch.object(code_graph, "RICH_AVAILABLE", False):
            with patch("subprocess.run") as mock_run:
                # Mock successful subprocess result
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = '{"files": []}'
                mock_result.stderr = ""
                mock_run.return_value = mock_result

                codebase_path = Path("/tmp/test")
                output_path = Path("/tmp/output.json")

                result = code_graph.run_blarify(codebase_path, output_path)

                # Verify standard subprocess.run was used
                assert result is True
                assert mock_run.call_count >= 2  # Version check + execution

    def test_WHEN_progress_indicator_runs_THEN_json_output_captured(self):
        """Test that JSON output is still captured with progress indicator."""
        import amplihack.memory.neo4j.code_graph as code_graph

        # Mock the subprocess and threading components
        expected_json = '{"files": [{"path": "test.py"}], "classes": []}'

        with patch("subprocess.run") as mock_subprocess_run:
            with patch.object(code_graph, "Console") as mock_console:
                with patch.object(code_graph, "Live") as mock_live:
                    with patch("threading.Thread") as mock_thread_class:
                        # Mock successful subprocess with JSON output
                        mock_result = Mock()
                        mock_result.returncode = 0
                        mock_result.stdout = expected_json
                        mock_result.stderr = ""
                        mock_subprocess_run.return_value = mock_result

                        # Setup mock thread that completes immediately
                        mock_thread = Mock()
                        mock_thread.is_alive.return_value = False
                        mock_thread_class.return_value = mock_thread

                        # Setup mock live display
                        mock_live_instance = MagicMock()
                        mock_live.return_value.__enter__ = Mock(return_value=mock_live_instance)
                        mock_live.return_value.__exit__ = Mock(return_value=False)

                        cmd = ["blarify", "create", "/tmp/test"]
                        codebase_path = Path("/tmp/test")

                        result = code_graph._run_with_progress_indicator(cmd, codebase_path)

                        # Verify JSON output was captured
                        assert result is not None
                        assert result.stdout == expected_json
                        assert result.returncode == 0

    def test_WHEN_blarify_fails_THEN_error_handled_correctly(self):
        """Test that errors are properly handled with progress indicator."""
        import amplihack.memory.neo4j.code_graph as code_graph

        with patch("subprocess.run") as mock_run:
            with patch.object(code_graph, "Console"):
                with patch.object(code_graph, "Live") as mock_live:
                    with patch("threading.Thread") as mock_thread_class:
                        # Mock subprocess that fails
                        mock_result = Mock()
                        mock_result.returncode = 1
                        mock_result.stdout = ""
                        mock_result.stderr = "Error: blarify failed"
                        mock_run.return_value = mock_result

                        # Setup mock thread that completes immediately
                        mock_thread = Mock()
                        mock_thread.is_alive.return_value = False
                        mock_thread_class.return_value = mock_thread

                        # Setup mock live display
                        mock_live_instance = MagicMock()
                        mock_live.return_value.__enter__ = Mock(return_value=mock_live_instance)
                        mock_live.return_value.__exit__ = Mock(return_value=False)

                        cmd = ["blarify", "create", "/tmp/test"]
                        codebase_path = Path("/tmp/test")

                        result = code_graph._run_with_progress_indicator(cmd, codebase_path)

                        # Verify error is captured
                        assert result.returncode == 1
                        assert "Error" in result.stderr

    def test_WHEN_progress_runs_THEN_elapsed_time_updated(self):
        """Test that elapsed time is displayed during progress."""
        import amplihack.memory.neo4j.code_graph as code_graph

        with patch("subprocess.run") as mock_subprocess_run:
            with patch.object(code_graph, "Console"):
                with patch.object(code_graph, "Live") as mock_live:
                    with patch("threading.Thread") as mock_thread_class:
                        # Mock successful subprocess
                        mock_result = Mock()
                        mock_result.returncode = 0
                        mock_result.stdout = '{"files": []}'
                        mock_result.stderr = ""
                        mock_subprocess_run.return_value = mock_result

                        # Setup mock thread that runs for a bit
                        mock_thread = Mock()
                        # First call returns True (still alive), second returns False (completed)
                        mock_thread.is_alive.side_effect = [True, False]
                        mock_thread_class.return_value = mock_thread

                        # Setup mock live display
                        mock_live_instance = MagicMock()
                        mock_live.return_value.__enter__ = Mock(return_value=mock_live_instance)
                        mock_live.return_value.__exit__ = Mock(return_value=False)

                        cmd = ["blarify", "create", "/tmp/test"]
                        codebase_path = Path("/tmp/test")

                        result = code_graph._run_with_progress_indicator(cmd, codebase_path)

                        # Verify live display was updated
                        assert mock_live_instance.update.called
                        assert result.returncode == 0


class TestBlarifyProgressIntegration:
    """Integration tests for blarify progress indicator."""

    def test_WHEN_progress_indicator_available_THEN_no_import_errors(self):
        """Test that imports work correctly when rich is available."""
        try:
            from amplihack.memory.neo4j.code_graph import (
                RICH_AVAILABLE,
                _run_with_progress_indicator,
            )

            # Should import successfully
            assert True
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")

    def test_WHEN_module_loads_THEN_rich_availability_detected(self):
        """Test that RICH_AVAILABLE is properly set based on rich installation."""
        from amplihack.memory.neo4j.code_graph import RICH_AVAILABLE

        # Rich should be available in our test environment
        assert isinstance(RICH_AVAILABLE, bool)

    def test_WHEN_blarify_not_found_THEN_graceful_error(self):
        """Test that missing blarify command is handled gracefully."""
        import amplihack.memory.neo4j.code_graph as code_graph

        with patch("subprocess.run") as mock_run:
            # Mock blarify not found
            mock_run.side_effect = FileNotFoundError("blarify not found")

            codebase_path = Path("/tmp/test")
            output_path = Path("/tmp/output.json")

            result = code_graph.run_blarify(codebase_path, output_path)

            # Should return False, not raise exception
            assert result is False
