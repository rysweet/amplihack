"""Tests for claude-trace log analysis script."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project paths before imports
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))


class TestAnalyzeTraces:
    """Test trace log analysis functionality."""

    def test_find_jsonl_files_success(self, tmp_path):
        """Should find .jsonl files excluding already_processed directory."""
        from analyze_traces import find_unprocessed_logs

        # Create test structure
        trace_dir = tmp_path / ".claude-trace"
        trace_dir.mkdir()
        processed_dir = trace_dir / "already_processed"
        processed_dir.mkdir()

        # Create test files
        (trace_dir / "session1.jsonl").write_text("log1")
        (trace_dir / "session2.jsonl").write_text("log2")
        (processed_dir / "old.jsonl").write_text("old")
        (trace_dir / "other.txt").write_text("not jsonl")

        result = find_unprocessed_logs(str(trace_dir))

        assert len(result) == 2
        assert all(f.endswith(".jsonl") for f in result)
        assert all("already_processed" not in f for f in result)

    def test_find_jsonl_files_no_trace_dir(self, tmp_path):
        """Should return empty list when .claude-trace doesn't exist."""
        from analyze_traces import find_unprocessed_logs

        result = find_unprocessed_logs(str(tmp_path / "nonexistent"))

        assert result == []

    def test_build_analysis_prompt_structure(self):
        """Should build properly formatted prompt with all categories."""
        from analyze_traces import build_analysis_prompt

        log_files = ["/path/to/log1.jsonl", "/path/to/log2.jsonl"]
        prompt = build_analysis_prompt(log_files)

        # Check prompt structure
        assert "/ultrathink:" in prompt
        assert "analyze all of these logs" in prompt.lower()
        assert all(log in prompt for log in log_files)

        # Check all 5 categories are present
        assert "Agent Opportunities" in prompt
        assert "Frustration Points" in prompt
        assert "Failing Patterns" in prompt
        assert "Simplification" in prompt
        assert "New Commands" in prompt

    def test_process_log_moves_file(self, tmp_path):
        """Should move processed log to already_processed directory."""
        from analyze_traces import process_log

        # Create test structure
        trace_dir = tmp_path / ".claude-trace"
        trace_dir.mkdir()
        log_file = trace_dir / "session.jsonl"
        log_file.write_text("test log")
        processed_dir = trace_dir / "already_processed"
        processed_dir.mkdir()

        # Process the log
        process_log(str(log_file))

        # Verify file was moved
        assert not log_file.exists()
        moved_file = processed_dir / "session.jsonl"
        assert moved_file.exists()
        assert moved_file.read_text() == "test log"

    def test_process_log_creates_processed_dir_if_needed(self, tmp_path):
        """Should create already_processed directory if it doesn't exist."""
        from analyze_traces import process_log

        trace_dir = tmp_path / ".claude-trace"
        trace_dir.mkdir()
        log_file = trace_dir / "session.jsonl"
        log_file.write_text("test log")

        # Process without already_processed directory existing
        process_log(str(log_file))

        # Verify directory was created and file moved
        processed_dir = trace_dir / "already_processed"
        assert processed_dir.exists()
        assert (processed_dir / "session.jsonl").exists()

    @patch("subprocess.run")
    def test_main_invokes_ultrathink(self, mock_run, tmp_path, monkeypatch):
        """Should invoke /ultrathink command with proper prompt."""
        from analyze_traces import main

        # Create test structure
        trace_dir = tmp_path / ".claude-trace"
        trace_dir.mkdir()
        (trace_dir / "session.jsonl").write_text("log")

        # Mock subprocess to succeed
        mock_run.return_value = Mock(returncode=0)

        # Change to test directory
        monkeypatch.chdir(tmp_path)
        main()

        # Verify subprocess was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]
        assert "amplihack" in call_args
        assert any("/ultrathink" in str(arg) for arg in call_args)


class TestAnalyzeTracesErrorHandling:
    """Test error handling in trace analysis."""

    def test_process_log_handles_missing_file(self, tmp_path):
        """Should handle gracefully when log file doesn't exist."""
        from analyze_traces import process_log

        nonexistent = tmp_path / "nonexistent.jsonl"

        # Should not raise exception
        process_log(str(nonexistent))

    @patch("subprocess.run")
    def test_main_continues_on_subprocess_error(self, mock_run, tmp_path, monkeypatch):
        """Should handle subprocess errors gracefully."""
        from analyze_traces import main

        trace_dir = tmp_path / ".claude-trace"
        trace_dir.mkdir()
        log_file = trace_dir / "session.jsonl"
        log_file.write_text("log")

        # Mock subprocess to raise exception
        mock_run.side_effect = Exception("subprocess failed")

        # Change to test directory and run main
        monkeypatch.chdir(tmp_path)
        main()  # Should not crash

        # Logs should not be moved (error path)
        assert log_file.exists()
        assert not (trace_dir / "already_processed" / "session.jsonl").exists()

    @patch("subprocess.run")
    def test_main_does_not_process_logs_on_failure(self, mock_run, tmp_path, monkeypatch):
        """Should NOT move logs if amplihack fails with non-zero exit code."""
        from analyze_traces import main

        # Create test structure
        trace_dir = tmp_path / ".claude-trace"
        trace_dir.mkdir()
        log_file = trace_dir / "session.jsonl"
        log_file.write_text("log")

        # Mock subprocess to fail (exit code 1)
        mock_run.return_value = Mock(returncode=1)

        # Change to test directory
        monkeypatch.chdir(tmp_path)
        main()

        # Logs should NOT be moved
        assert log_file.exists()
        assert not (trace_dir / "already_processed" / "session.jsonl").exists()

    @patch("builtins.print")
    def test_main_handles_empty_log_list(self, mock_print, tmp_path, monkeypatch):
        """Should print message and exit when no logs found."""
        from analyze_traces import main

        # Create empty trace directory
        trace_dir = tmp_path / ".claude-trace"
        trace_dir.mkdir()

        # Change to test directory
        monkeypatch.chdir(tmp_path)
        main()

        # Should have printed the "no logs" message
        mock_print.assert_called_once_with("No unprocessed trace logs found.")

        # Should not crash
        with patch("analyze_traces.Path.home", return_value=tmp_path):
            main()
