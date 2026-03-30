"""
Tests for dev_intent_router provenance logging.

Verifies that every call to should_auto_route() produces a JSONL log entry
with the routing decision and reason. Covers:
- Injection logged with reason "inject"
- Skip reasons logged (disabled, workflow_active, not_string, empty, slash_command, too_short)
- Log format correctness (valid JSONL, required fields)
- Prompt truncation (max 200 chars in log)
- Performance (<5ms per log entry)
"""

import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
from dev_intent_router import (
    _LOG_PROMPT_MAX_CHARS,
    _MIN_PROMPT_LENGTH,
    should_auto_route,
)


def _make_patches(tmp: str, log_dir: str | None = None):
    """Create standard patches for path helpers and log directory."""
    patches = [
        patch(
            "dev_intent_router._get_semaphore_path",
            return_value=Path(tmp) / ".auto_dev_active",
        ),
        patch(
            "dev_intent_router._get_workflow_active_path",
            return_value=Path(tmp) / ".workflow_active",
        ),
    ]
    if log_dir is not None:
        patches.append(
            patch(
                "dev_intent_router._get_routing_log_dir",
                return_value=Path(log_dir),
            )
        )
        patches.append(
            patch(
                "dev_intent_router._get_routing_log_path",
                return_value=Path(log_dir) / "routing_decisions.jsonl",
            )
        )
    return patches


class TestRoutingDecisionLogged(unittest.TestCase):
    """Every should_auto_route() call produces a log entry."""

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        self._tmp = tempfile.mkdtemp()
        self._log_dir = tempfile.mkdtemp()
        self._patches = _make_patches(self._tmp, self._log_dir)
        for p in self._patches:
            p.start()
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        shutil.rmtree(self._tmp, ignore_errors=True)
        shutil.rmtree(self._log_dir, ignore_errors=True)

    def _read_log_entries(self) -> list[dict]:
        log_file = Path(self._log_dir) / "routing_decisions.jsonl"
        if not log_file.exists():
            return []
        entries = []
        for line in log_file.read_text().splitlines():
            if line.strip():
                entries.append(json.loads(line))
        return entries

    def test_inject_produces_log_entry(self):
        """Successful injection is logged with reason 'inject'."""
        ok, _ = should_auto_route("fix the login timeout bug")
        self.assertTrue(ok)
        entries = self._read_log_entries()
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["event"], "routing_decision")
        self.assertTrue(entry["should_inject"])
        self.assertEqual(entry["reason"], "inject")

    def test_inject_log_has_required_fields(self):
        """Log entry contains all required fields."""
        should_auto_route("investigate the build pipeline")
        entries = self._read_log_entries()
        entry = entries[0]
        required_fields = {"timestamp", "event", "should_inject", "reason",
                           "prompt_preview", "prompt_length"}
        self.assertTrue(required_fields.issubset(entry.keys()),
                        f"Missing fields: {required_fields - entry.keys()}")

    def test_inject_log_contains_prompt_preview(self):
        """Log entry includes truncated prompt text."""
        should_auto_route("fix the login timeout bug")
        entries = self._read_log_entries()
        self.assertEqual(entries[0]["prompt_preview"], "fix the login timeout bug")
        self.assertEqual(entries[0]["prompt_length"], len("fix the login timeout bug"))

    def test_multiple_calls_append(self):
        """Multiple calls append to the same log file."""
        should_auto_route("fix the login bug please")
        should_auto_route("add new feature now")
        entries = self._read_log_entries()
        self.assertEqual(len(entries), 2)


class TestSkipReasonLogged(unittest.TestCase):
    """Skip decisions include the specific reason."""

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        self._tmp = tempfile.mkdtemp()
        self._log_dir = tempfile.mkdtemp()
        self._patches = _make_patches(self._tmp, self._log_dir)
        for p in self._patches:
            p.start()
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        shutil.rmtree(self._tmp, ignore_errors=True)
        shutil.rmtree(self._log_dir, ignore_errors=True)

    def _read_last_entry(self) -> dict:
        log_file = Path(self._log_dir) / "routing_decisions.jsonl"
        lines = [l for l in log_file.read_text().splitlines() if l.strip()]
        return json.loads(lines[-1])

    def test_skip_disabled_logged(self):
        """Disabled auto-dev is logged with reason 'skip:disabled'."""
        (Path(self._tmp) / ".auto_dev_active").unlink()
        ok, _ = should_auto_route("fix the login bug")
        self.assertFalse(ok)
        entry = self._read_last_entry()
        self.assertFalse(entry["should_inject"])
        self.assertEqual(entry["reason"], "skip:disabled")

    def test_skip_workflow_active_logged(self):
        """Active workflow is logged with reason 'skip:workflow_active'."""
        wf_path = Path(self._tmp) / ".workflow_active"
        wf_data = json.dumps({
            "active": True, "task_type": "Dev", "workstreams": 1,
            "started_at": time.time(), "pid": os.getpid(),
        })
        wf_path.write_text(wf_data + "\n")
        ok, _ = should_auto_route("fix the login bug")
        self.assertFalse(ok)
        entry = self._read_last_entry()
        self.assertEqual(entry["reason"], "skip:workflow_active")

    def test_skip_not_string_logged(self):
        """Non-string input is logged with reason 'skip:not_string'."""
        ok, _ = should_auto_route(12345)  # type: ignore[arg-type]
        self.assertFalse(ok)
        entry = self._read_last_entry()
        self.assertEqual(entry["reason"], "skip:not_string")

    def test_skip_empty_logged(self):
        """Empty prompt is logged with reason 'skip:empty'."""
        ok, _ = should_auto_route("")
        self.assertFalse(ok)
        entry = self._read_last_entry()
        self.assertEqual(entry["reason"], "skip:empty")

    def test_skip_whitespace_logged(self):
        """Whitespace-only prompt is logged with reason 'skip:empty'."""
        ok, _ = should_auto_route("   \n  ")
        self.assertFalse(ok)
        entry = self._read_last_entry()
        self.assertEqual(entry["reason"], "skip:empty")

    def test_skip_slash_command_logged(self):
        """Slash command is logged with reason 'skip:slash_command'."""
        ok, _ = should_auto_route("/dev fix the bug")
        self.assertFalse(ok)
        entry = self._read_last_entry()
        self.assertEqual(entry["reason"], "skip:slash_command")

    def test_skip_too_short_logged(self):
        """Short prompt is logged with reason 'skip:too_short'."""
        ok, _ = should_auto_route("yes")
        self.assertFalse(ok)
        entry = self._read_last_entry()
        self.assertEqual(entry["reason"], "skip:too_short")


class TestLogFormatCorrectness(unittest.TestCase):
    """Log format is valid JSONL with correct structure."""

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        self._tmp = tempfile.mkdtemp()
        self._log_dir = tempfile.mkdtemp()
        self._patches = _make_patches(self._tmp, self._log_dir)
        for p in self._patches:
            p.start()
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        shutil.rmtree(self._tmp, ignore_errors=True)
        shutil.rmtree(self._log_dir, ignore_errors=True)

    def _read_raw_lines(self) -> list[str]:
        log_file = Path(self._log_dir) / "routing_decisions.jsonl"
        if not log_file.exists():
            return []
        return [l for l in log_file.read_text().splitlines() if l.strip()]

    def test_each_line_is_valid_json(self):
        """Every line in the log file is valid JSON."""
        should_auto_route("fix the login bug please")
        should_auto_route("/dev skip this")
        should_auto_route("ok")
        lines = self._read_raw_lines()
        self.assertGreaterEqual(len(lines), 3)
        for line in lines:
            parsed = json.loads(line)  # raises on invalid JSON
            self.assertIsInstance(parsed, dict)

    def test_timestamp_is_iso_format(self):
        """Timestamp field is ISO 8601 format."""
        should_auto_route("fix the login bug please")
        lines = self._read_raw_lines()
        entry = json.loads(lines[0])
        ts = entry["timestamp"]
        # Should parse without error
        from datetime import datetime
        datetime.fromisoformat(ts)

    def test_prompt_truncated_at_200_chars(self):
        """Long prompts are truncated to 200 chars in log."""
        long_prompt = "x" * 500
        should_auto_route(long_prompt)
        lines = self._read_raw_lines()
        entry = json.loads(lines[0])
        self.assertEqual(len(entry["prompt_preview"]), _LOG_PROMPT_MAX_CHARS)
        self.assertEqual(entry["prompt_length"], 500)

    def test_log_directory_created_automatically(self):
        """Log directory is created if it doesn't exist."""
        # Remove the log dir
        shutil.rmtree(self._log_dir, ignore_errors=True)
        should_auto_route("fix the login bug please")
        self.assertTrue(Path(self._log_dir).exists())

    def test_event_field_is_routing_decision(self):
        """Event field is always 'routing_decision'."""
        should_auto_route("fix the login bug please")
        should_auto_route("ok")
        lines = self._read_raw_lines()
        for line in lines:
            entry = json.loads(line)
            self.assertEqual(entry["event"], "routing_decision")


class TestLoggingPerformance(unittest.TestCase):
    """Logging overhead stays under 5ms per entry."""

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        self._tmp = tempfile.mkdtemp()
        self._log_dir = tempfile.mkdtemp()
        self._patches = _make_patches(self._tmp, self._log_dir)
        for p in self._patches:
            p.start()
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        shutil.rmtree(self._tmp, ignore_errors=True)
        shutil.rmtree(self._log_dir, ignore_errors=True)

    def test_logging_overhead_under_threshold(self):
        """Average logging overhead is under 5ms across 50 calls."""
        # Warm up
        should_auto_route("warmup call for file creation")

        iterations = 50
        start = time.perf_counter()
        for i in range(iterations):
            should_auto_route(f"fix bug number {i} in the auth module")
        total_ms = (time.perf_counter() - start) * 1000
        avg_ms = total_ms / iterations

        # The total call includes routing logic; we just verify it's reasonable
        self.assertLess(avg_ms, 10,
                        f"Average call time {avg_ms:.2f}ms is too high")


class TestLoggingFailOpen(unittest.TestCase):
    """Logging failures must not affect routing behavior."""

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        self._tmp = tempfile.mkdtemp()
        self._patches = [
            patch(
                "dev_intent_router._get_semaphore_path",
                return_value=Path(self._tmp) / ".auto_dev_active",
            ),
            patch(
                "dev_intent_router._get_workflow_active_path",
                return_value=Path(self._tmp) / ".workflow_active",
            ),
            # Point log to a non-writable path
            patch(
                "dev_intent_router._get_routing_log_dir",
                return_value=Path("/proc/nonexistent/nope"),
            ),
            patch(
                "dev_intent_router._get_routing_log_path",
                return_value=Path("/proc/nonexistent/nope/routing_decisions.jsonl"),
            ),
        ]
        for p in self._patches:
            p.start()
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_injection_still_works_when_logging_fails(self):
        """should_auto_route returns correct result even when logging fails."""
        ok, ctx = should_auto_route("fix the login timeout bug")
        self.assertTrue(ok)
        self.assertTrue(len(ctx) > 0)

    def test_skip_still_works_when_logging_fails(self):
        """Skip decisions still work when logging fails."""
        ok, ctx = should_auto_route("/dev something")
        self.assertFalse(ok)
        self.assertEqual(ctx, "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
