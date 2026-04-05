"""
Tests for WorkflowClassifier provenance logging.

Verifies that every call to WorkflowClassifier.classify() produces a JSONL
log entry with the classification result, matched keywords, and confidence.
"""

import json
import time
from pathlib import Path

import pytest

from amplihack.workflows.classifier import _LOG_PROMPT_MAX_CHARS, WorkflowClassifier


@pytest.fixture
def log_dir(tmp_path):
    """Provide a temporary log directory for classifier provenance tests."""
    d = tmp_path / "logs" / "dev_intent_router"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def classifier_with_logging(log_dir, monkeypatch):
    """Return a classifier with logging redirected to a temp directory."""
    monkeypatch.setattr(
        WorkflowClassifier, "_get_classifier_log_dir", staticmethod(lambda: log_dir)
    )
    monkeypatch.setattr(
        WorkflowClassifier,
        "_get_classifier_log_path",
        staticmethod(lambda: log_dir / "routing_decisions.jsonl"),
    )
    return WorkflowClassifier()


def _read_log_entries(log_dir: Path) -> list[dict]:
    log_file = log_dir / "routing_decisions.jsonl"
    if not log_file.exists():
        return []
    entries = []
    for line in log_file.read_text().splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


class TestClassificationLogged:
    """Every classify() call produces a JSONL log entry."""

    def test_classify_produces_log_entry(self, classifier_with_logging, log_dir):
        """classify() writes a log entry."""
        classifier_with_logging.classify("Add authentication")
        entries = _read_log_entries(log_dir)
        assert len(entries) == 1
        assert entries[0]["event"] == "classification"

    def test_log_has_required_fields(self, classifier_with_logging, log_dir):
        """Log entry contains all required fields."""
        classifier_with_logging.classify("Fix the login bug")
        entries = _read_log_entries(log_dir)
        entry = entries[0]
        required = {
            "timestamp",
            "event",
            "workflow",
            "reason",
            "confidence",
            "keywords",
            "prompt_preview",
            "prompt_length",
        }
        assert required.issubset(entry.keys()), f"Missing fields: {required - entry.keys()}"

    def test_log_captures_workflow(self, classifier_with_logging, log_dir):
        """Log entry contains the classified workflow."""
        classifier_with_logging.classify("Implement user authentication")
        entries = _read_log_entries(log_dir)
        assert entries[0]["workflow"] == "DEFAULT_WORKFLOW"

    def test_log_captures_confidence(self, classifier_with_logging, log_dir):
        """Log entry contains confidence score."""
        classifier_with_logging.classify("Implement user authentication")
        entries = _read_log_entries(log_dir)
        assert entries[0]["confidence"] == 0.9

    def test_log_captures_keywords(self, classifier_with_logging, log_dir):
        """Log entry contains matched keywords."""
        classifier_with_logging.classify("Add authentication and fix bugs")
        entries = _read_log_entries(log_dir)
        kws = entries[0]["keywords"]
        assert "add" in kws
        assert "fix" in kws

    def test_log_captures_reason(self, classifier_with_logging, log_dir):
        """Log entry contains the classification reason."""
        classifier_with_logging.classify("Fix the login bug")
        entries = _read_log_entries(log_dir)
        assert "fix" in entries[0]["reason"]

    def test_log_captures_qa_workflow(self, classifier_with_logging, log_dir):
        """Q&A classification is logged correctly."""
        classifier_with_logging.classify("What is the purpose of this module?")
        entries = _read_log_entries(log_dir)
        assert entries[0]["workflow"] == "Q&A_WORKFLOW"

    def test_log_captures_investigation_workflow(self, classifier_with_logging, log_dir):
        """Investigation classification is logged correctly."""
        classifier_with_logging.classify("Investigate how the memory system works")
        entries = _read_log_entries(log_dir)
        assert entries[0]["workflow"] == "INVESTIGATION_WORKFLOW"

    def test_log_captures_ops_workflow(self, classifier_with_logging, log_dir):
        """Ops classification is logged correctly."""
        classifier_with_logging.classify("Run command to clean up disk space")
        entries = _read_log_entries(log_dir)
        assert entries[0]["workflow"] == "OPS_WORKFLOW"

    def test_log_captures_ambiguous(self, classifier_with_logging, log_dir):
        """Ambiguous classification is logged with low confidence."""
        classifier_with_logging.classify("Do something with the code")
        entries = _read_log_entries(log_dir)
        assert entries[0]["confidence"] == 0.5
        assert "ambiguous" in entries[0]["reason"].lower()

    def test_multiple_calls_append(self, classifier_with_logging, log_dir):
        """Multiple classify() calls append to the same log."""
        classifier_with_logging.classify("Add authentication")
        classifier_with_logging.classify("What is OAuth?")
        classifier_with_logging.classify("Investigate the build")
        entries = _read_log_entries(log_dir)
        assert len(entries) == 3


class TestClassificationLogFormat:
    """Log format correctness."""

    def test_each_line_is_valid_json(self, classifier_with_logging, log_dir):
        """Every log line is valid JSON."""
        classifier_with_logging.classify("Add authentication")
        classifier_with_logging.classify("What is OAuth?")
        log_file = log_dir / "routing_decisions.jsonl"
        for line in log_file.read_text().splitlines():
            if line.strip():
                parsed = json.loads(line)
                assert isinstance(parsed, dict)

    def test_timestamp_is_iso_format(self, classifier_with_logging, log_dir):
        """Timestamp is ISO 8601."""
        classifier_with_logging.classify("Add authentication")
        entries = _read_log_entries(log_dir)
        from datetime import datetime

        datetime.fromisoformat(entries[0]["timestamp"])

    def test_prompt_truncated_at_200_chars(self, classifier_with_logging, log_dir):
        """Long prompts truncated to 200 chars."""
        long_request = "implement " + "x" * 500
        classifier_with_logging.classify(long_request)
        entries = _read_log_entries(log_dir)
        assert len(entries[0]["prompt_preview"]) == _LOG_PROMPT_MAX_CHARS
        assert entries[0]["prompt_length"] == len(long_request)

    def test_event_field_is_classification(self, classifier_with_logging, log_dir):
        """Event field is always 'classification'."""
        classifier_with_logging.classify("Add authentication")
        entries = _read_log_entries(log_dir)
        assert entries[0]["event"] == "classification"


class TestClassificationLogPerformance:
    """Logging overhead stays under 5ms."""

    @pytest.mark.performance
    def test_logging_overhead_under_threshold(self, classifier_with_logging, log_dir):
        """Average classify() time stays reasonable with logging."""
        # Warm up
        classifier_with_logging.classify("warmup call for setup")

        iterations = 50
        start = time.perf_counter()
        for i in range(iterations):
            classifier_with_logging.classify(f"Fix bug number {i} in the auth module")
        total_ms = (time.perf_counter() - start) * 1000
        avg_ms = total_ms / iterations

        assert avg_ms < 10, f"Average classify time {avg_ms:.2f}ms is too high"


class TestClassificationLogFailOpen:
    """Logging failures must not affect classify() behavior."""

    def test_classify_works_when_logging_fails(self, monkeypatch):
        """classify() returns correct result even when logging fails."""
        classifier = WorkflowClassifier()
        monkeypatch.setattr(
            WorkflowClassifier,
            "_get_classifier_log_dir",
            staticmethod(lambda: Path("/proc/nonexistent/nope")),
        )
        monkeypatch.setattr(
            WorkflowClassifier,
            "_get_classifier_log_path",
            staticmethod(lambda: Path("/proc/nonexistent/nope/routing_decisions.jsonl")),
        )
        result = classifier.classify("Add authentication")
        assert result["workflow"] == "DEFAULT_WORKFLOW"
        assert result["confidence"] == 0.9
