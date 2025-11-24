"""Unit tests for logger module.

Tests structured logging in JSONL format for auto-ultrathink pipeline.
"""

import json

import pytest


class TestLogger:
    """Unit tests for logger."""

    def test_log_auto_ultrathink_creates_file(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Test logging creates file successfully."""
        from logger import log_auto_ultrathink

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Log
        log_auto_ultrathink(
            session_id="test",
            prompt="test prompt",
            classification=create_test_classification(),
            preference=create_test_preference(),
            decision=create_test_decision(),
            result=create_test_result(),
            execution_time_ms=95.5,
        )

        # Verify file was created
        assert log_file.exists()

    def test_log_auto_ultrathink_writes_json(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Test logging writes valid JSON."""
        from logger import log_auto_ultrathink, parse_log_file

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Log
        log_auto_ultrathink(
            session_id="test",
            prompt="test prompt",
            classification=create_test_classification(),
            preference=create_test_preference(),
            decision=create_test_decision(),
            result=create_test_result(),
            execution_time_ms=95.5,
        )

        # Verify valid JSON
        entries = parse_log_file(log_file)
        assert len(entries) == 1
        assert entries[0]["prompt"] == "test prompt"

    def test_log_auto_ultrathink_includes_all_fields(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Test log entry includes all required fields."""
        from logger import log_auto_ultrathink, parse_log_file

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Log
        log_auto_ultrathink(
            session_id="test",
            prompt="test prompt",
            classification=create_test_classification(),
            preference=create_test_preference(),
            decision=create_test_decision(),
            result=create_test_result(),
            execution_time_ms=95.5,
        )

        # Verify fields
        entries = parse_log_file(log_file)
        entry = entries[0]

        assert "timestamp" in entry
        assert "session_id" in entry
        assert "prompt" in entry
        assert "classification" in entry
        assert "preference" in entry
        assert "decision" in entry
        assert "result" in entry
        assert "execution_time_ms" in entry

    def test_log_error_creates_error_entry(self, tmp_path, monkeypatch):
        """Test error logging."""
        from logger import log_error, parse_log_file

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Log error
        log_error(
            session_id="test",
            stage="classification",
            error=ValueError("Test error"),
            prompt="test prompt",
        )

        # Verify
        entries = parse_log_file(log_file)
        assert len(entries) == 1
        assert entries[0]["type"] == "error"
        assert entries[0]["stage"] == "classification"
        assert "test error" in entries[0]["error"].lower()

    def test_log_error_includes_traceback(self, tmp_path, monkeypatch):
        """Test error logging includes traceback."""
        from logger import log_error, parse_log_file

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Create error with traceback
        try:
            raise ValueError("Test error")
        except Exception as e:
            log_error(
                session_id="test", stage="classification", error=e, prompt="test prompt"
            )

        # Verify
        entries = parse_log_file(log_file)
        assert "traceback" in entries[0]
        assert len(entries[0]["traceback"]) > 0

    def test_log_multiple_entries_append(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Test multiple log entries are appended."""
        from logger import log_auto_ultrathink, parse_log_file

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Log multiple times
        for i in range(10):
            log_auto_ultrathink(
                session_id="test",
                prompt=f"prompt {i}",
                classification=create_test_classification(),
                preference=create_test_preference(),
                decision=create_test_decision(),
                result=create_test_result(),
                execution_time_ms=100.0 + i,
            )

        # Verify all entries
        entries = parse_log_file(log_file)
        assert len(entries) == 10
        assert entries[0]["prompt"] == "prompt 0"
        assert entries[9]["prompt"] == "prompt 9"

    def test_log_never_raises(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Test logging never raises exceptions."""
        from logger import log_auto_ultrathink

        # Setup invalid log path
        invalid_path = tmp_path / "nonexistent" / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: invalid_path)

        # Log should not crash
        try:
            log_auto_ultrathink(
                session_id="test",
                prompt="test prompt",
                classification=create_test_classification(),
                preference=create_test_preference(),
                decision=create_test_decision(),
                result=create_test_result(),
                execution_time_ms=95.5,
            )
            # Should complete without error
            assert True
        except Exception as e:
            pytest.fail(f"Logging raised exception: {e}")


class TestMetricsSummary:
    """Test metrics computation."""

    def test_get_metrics_summary_empty(self, tmp_path, monkeypatch):
        """Test metrics with no log entries."""
        from logger import get_metrics_summary

        monkeypatch.setattr("logger.find_all_log_files", lambda: [])

        metrics = get_metrics_summary()

        assert metrics["total_entries"] == 0

    def test_get_metrics_summary_counts(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Test metrics counts actions correctly."""
        from logger import get_metrics_summary, log_auto_ultrathink

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)
        monkeypatch.setattr("logger.find_all_log_files", lambda: [log_file])

        # Log multiple entries with different actions
        for action in ["skip", "invoke", "ask", "skip", "invoke"]:
            decision = create_test_decision(action=action)
            result = create_test_result(action_taken=action)
            log_auto_ultrathink(
                session_id="test",
                prompt=f"prompt {action}",
                classification=create_test_classification(),
                preference=create_test_preference(),
                decision=decision,
                result=result,
                execution_time_ms=100.0,
            )

        # Get metrics
        metrics = get_metrics_summary()

        assert metrics["total_entries"] == 5
        assert metrics["action_counts"]["skip"] == 2
        assert metrics["action_counts"]["invoke"] == 2
        assert metrics["action_counts"]["ask"] == 1

    def test_get_metrics_summary_confidence_stats(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Test metrics calculates confidence statistics."""
        from logger import get_metrics_summary, log_auto_ultrathink

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)
        monkeypatch.setattr("logger.find_all_log_files", lambda: [log_file])

        # Log entries with known confidences
        confidences = [0.80, 0.85, 0.90, 0.95]
        for conf in confidences:
            classification = create_test_classification(confidence=conf)
            log_auto_ultrathink(
                session_id="test",
                prompt="test",
                classification=classification,
                preference=create_test_preference(),
                decision=create_test_decision(),
                result=create_test_result(),
                execution_time_ms=100.0,
            )

        # Get metrics
        metrics = get_metrics_summary()

        assert "confidence_stats" in metrics
        assert metrics["confidence_stats"]["min"] == 0.80
        assert metrics["confidence_stats"]["max"] == 0.95
        assert 0.80 <= metrics["confidence_stats"]["mean"] <= 0.95

    def test_get_metrics_summary_execution_time_stats(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Test metrics calculates execution time statistics."""
        from logger import get_metrics_summary, log_auto_ultrathink

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)
        monkeypatch.setattr("logger.find_all_log_files", lambda: [log_file])

        # Log entries with known execution times
        times = [50.0, 100.0, 150.0, 200.0]
        for time_ms in times:
            log_auto_ultrathink(
                session_id="test",
                prompt="test",
                classification=create_test_classification(),
                preference=create_test_preference(),
                decision=create_test_decision(),
                result=create_test_result(),
                execution_time_ms=time_ms,
            )

        # Get metrics
        metrics = get_metrics_summary()

        assert "execution_time_stats" in metrics
        assert 50.0 <= metrics["execution_time_stats"]["mean"] <= 200.0
        assert metrics["execution_time_stats"]["max"] == 200.0


class TestLogFilePath:
    """Test log file path resolution."""

    def test_get_log_file_path_creates_dirs(self, tmp_path, monkeypatch):
        """Test log file path creation."""
        from logger import get_log_file_path

        # Mock project root
        monkeypatch.setattr("logger.find_project_root", lambda x: tmp_path)

        # Get log path
        log_path = get_log_file_path("test_session")

        # Verify structure
        expected = tmp_path / ".claude" / "runtime" / "logs" / "test_session" / "auto_ultrathink.jsonl"
        assert log_path == expected

        # Verify directories were created
        assert log_path.parent.exists()

    def test_find_project_root_finds_claude_dir(self, tmp_path):
        """Test finding project root with .claude directory."""
        from logger import find_project_root

        # Create .claude directory
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        # Create subdirectory
        subdir = tmp_path / "sub" / "dir"
        subdir.mkdir(parents=True)

        # Find root from subdirectory
        root = find_project_root(subdir)

        assert root == tmp_path

    def test_find_project_root_fallback_to_cwd(self, tmp_path):
        """Test fallback to current directory if no .claude found."""
        from logger import find_project_root

        # No .claude directory
        root = find_project_root(tmp_path)

        # Should fallback to provided path
        assert root == tmp_path


class TestPromptHashing:
    """Test prompt hashing for deduplication."""

    def test_hash_prompt_consistent(self):
        """Same prompt should hash to same value."""
        from logger import hash_prompt

        hash1 = hash_prompt("test prompt")
        hash2 = hash_prompt("test prompt")

        assert hash1 == hash2

    def test_hash_prompt_different_for_different_prompts(self):
        """Different prompts should hash to different values."""
        from logger import hash_prompt

        hash1 = hash_prompt("prompt 1")
        hash2 = hash_prompt("prompt 2")

        assert hash1 != hash2

    def test_hash_prompt_fixed_length(self):
        """Hash should be fixed length."""
        from logger import hash_prompt

        hash1 = hash_prompt("short")
        hash2 = hash_prompt("very long prompt " * 1000)

        assert len(hash1) == len(hash2)
        assert len(hash1) == 16  # As specified

    def test_hash_prompt_handles_unicode(self):
        """Hash should handle unicode."""
        from logger import hash_prompt

        hash_result = hash_prompt("添加功能 🚀 с features")

        assert len(hash_result) == 16
        assert isinstance(hash_result, str)


class TestParseLogFile:
    """Test log file parsing."""

    def test_parse_log_file_valid_jsonl(self, tmp_path):
        """Test parsing valid JSONL file."""
        from logger import parse_log_file

        # Create JSONL file
        log_file = tmp_path / "test.jsonl"
        with open(log_file, "w") as f:
            f.write(json.dumps({"entry": 1}) + "\n")
            f.write(json.dumps({"entry": 2}) + "\n")

        # Parse
        entries = parse_log_file(log_file)

        assert len(entries) == 2
        assert entries[0]["entry"] == 1
        assert entries[1]["entry"] == 2

    def test_parse_log_file_skips_malformed_lines(self, tmp_path):
        """Test parsing skips malformed JSON lines."""
        from logger import parse_log_file

        # Create JSONL file with malformed line
        log_file = tmp_path / "test.jsonl"
        with open(log_file, "w") as f:
            f.write(json.dumps({"entry": 1}) + "\n")
            f.write("not valid json\n")
            f.write(json.dumps({"entry": 2}) + "\n")

        # Parse
        entries = parse_log_file(log_file)

        # Should skip malformed line
        assert len(entries) == 2
        assert entries[0]["entry"] == 1
        assert entries[1]["entry"] == 2

    def test_parse_log_file_empty_file(self, tmp_path):
        """Test parsing empty file."""
        from logger import parse_log_file

        # Create empty file
        log_file = tmp_path / "test.jsonl"
        log_file.write_text("")

        # Parse
        entries = parse_log_file(log_file)

        assert len(entries) == 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_log_with_none_values(
        self, tmp_path, monkeypatch, create_test_classification, create_test_preference
    ):
        """Test logging with None values."""
        from logger import log_auto_ultrathink

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Log with None execution_time_ms
        try:
            log_auto_ultrathink(
                session_id="test",
                prompt="test",
                classification=create_test_classification(),
                preference=create_test_preference(),
                decision=None,  # None value
                result=None,  # None value
                execution_time_ms=None,
            )
            # Should not crash
            assert True
        except Exception as e:
            pytest.fail(f"Logging with None values raised exception: {e}")

    def test_log_permission_error_silent(self, tmp_path, monkeypatch, create_test_classification):
        """Test logging handles permission errors silently."""
        from logger import log_error

        # Setup read-only file
        log_file = tmp_path / "test.jsonl"
        log_file.write_text("")
        log_file.chmod(0o000)  # No permissions

        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        try:
            # Should not crash
            log_error(
                session_id="test", stage="test", error=Exception("test"), prompt="test"
            )
            assert True
        except Exception as e:
            pytest.fail(f"Logging raised exception: {e}")
        finally:
            # Restore permissions for cleanup
            log_file.chmod(0o644)


class TestPerformance:
    """Performance tests for logger."""

    def test_logging_speed(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Logging should be fast (<50ms per call)."""
        import time

        from logger import log_auto_ultrathink

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Time logging
        start = time.time()
        for i in range(100):
            log_auto_ultrathink(
                session_id="test",
                prompt=f"prompt {i}",
                classification=create_test_classification(),
                preference=create_test_preference(),
                decision=create_test_decision(),
                result=create_test_result(),
                execution_time_ms=100.0,
            )
        elapsed = time.time() - start

        avg_time_ms = (elapsed / 100) * 1000
        assert avg_time_ms < 50, f"Logging too slow: {avg_time_ms:.2f}ms per call"

    def test_log_file_size_reasonable(
        self,
        tmp_path,
        monkeypatch,
        create_test_classification,
        create_test_preference,
        create_test_decision,
        create_test_result,
    ):
        """Log file size should be reasonable."""
        from logger import log_auto_ultrathink

        # Setup
        log_file = tmp_path / "test.jsonl"
        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Log 100 entries
        for i in range(100):
            log_auto_ultrathink(
                session_id="test",
                prompt=f"prompt {i}",
                classification=create_test_classification(),
                preference=create_test_preference(),
                decision=create_test_decision(),
                result=create_test_result(),
                execution_time_ms=100.0,
            )

        # Check file size
        file_size = log_file.stat().st_size

        # Should be reasonable (< 100KB for 100 entries)
        assert file_size < 100 * 1024, f"Log file too large: {file_size} bytes"
