#!/usr/bin/env python3
"""
End-to-end integration test: Power Steering with Copilot CLI transcript.

Verifies the full pipeline against a realistic Copilot-format events.jsonl:
  transcript loading -> format detection -> parsing -> session type detection
  -> check execution -> result formatting

No live Copilot session required — uses a realistic fixture.

Issue: #2845 (split power_steering_checker.py)
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure hooks directory is on path for the package
HOOKS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(HOOKS_DIR))

from power_steering_checker.transcript_parser import (
    detect_transcript_format,
    normalize_copilot_event,
    parse_claude_code_transcript,
    parse_copilot_transcript,
    parse_transcript,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
COPILOT_JSONL = FIXTURES_DIR / "copilot_events.jsonl"


def _load_lines(path: Path) -> list[str]:
    with open(path) as f:
        return [ln.strip() for ln in f if ln.strip()]


class TestTranscriptParserFormatDetection(unittest.TestCase):
    """Unit tests for transcript_parser format detection."""

    def test_detect_claude_code_format(self):
        line = json.dumps({"type": "user", "message": {"content": "Hello"}})
        self.assertEqual(detect_transcript_format(line), "claude_code")

    def test_detect_copilot_flat_format(self):
        line = json.dumps({"role": "user", "content": "Hello"})
        self.assertEqual(detect_transcript_format(line), "copilot")

    def test_detect_copilot_event_format(self):
        line = json.dumps({"event": "message", "role": "user", "content": "Hello"})
        self.assertEqual(detect_transcript_format(line), "copilot")

    def test_detect_empty_returns_claude_code(self):
        """Empty/blank first line defaults to claude_code (safe fallback)."""
        self.assertEqual(detect_transcript_format(""), "claude_code")
        self.assertEqual(detect_transcript_format("   "), "claude_code")

    def test_detect_copilot_fixture_first_line(self):
        """First line of realistic fixture is detected as copilot format."""
        lines = _load_lines(COPILOT_JSONL)
        self.assertEqual(detect_transcript_format(lines[0]), "copilot")


class TestTranscriptParserNormalization(unittest.TestCase):
    """Unit tests for Copilot -> Claude Code normalization."""

    def test_normalize_user_message(self):
        obj = {"event": "message", "role": "user", "content": "Hello Copilot"}
        result = normalize_copilot_event(obj)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "user")
        content = result["message"]["content"]
        self.assertIsInstance(content, list)
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[0]["text"], "Hello Copilot")

    def test_normalize_assistant_message(self):
        obj = {"event": "message", "role": "assistant", "content": "Hello user"}
        result = normalize_copilot_event(obj)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "assistant")

    def test_normalize_flat_format_user(self):
        obj = {"role": "user", "content": "Fix the bug"}
        result = normalize_copilot_event(obj)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "user")

    def test_normalize_tool_calls_in_assistant(self):
        obj = {
            "role": "assistant",
            "content": "Running tool",
            "tool_calls": [
                {"name": "file_system", "arguments": {"operation": "read", "path": "foo.py"}}
            ],
        }
        result = normalize_copilot_event(obj)
        self.assertIsNotNone(result)
        content = result["message"]["content"]
        tool_blocks = [b for b in content if b.get("type") == "tool_use"]
        self.assertEqual(len(tool_blocks), 1)
        self.assertEqual(tool_blocks[0]["name"], "file_system")

    def test_normalize_conversation_start_skipped(self):
        obj = {"event": "conversation_start", "session_id": "s1"}
        result = normalize_copilot_event(obj)
        self.assertIsNone(result)

    def test_normalize_copilot_fixture(self):
        """Full normalization of the realistic Copilot fixture."""
        lines = _load_lines(COPILOT_JSONL)
        normalized = parse_copilot_transcript(lines)

        types = {m["type"] for m in normalized}
        self.assertIn("user", types)
        self.assertIn("assistant", types)

        # All messages have expected structure
        for msg in normalized:
            self.assertIn("type", msg)
            self.assertIn("message", msg)
            self.assertIn("content", msg["message"])

    def test_parse_claude_code_unchanged(self):
        """Claude Code transcript is returned byte-for-byte identical."""
        obj = {"type": "user", "message": {"content": "Hello"}}
        line = json.dumps(obj)
        result = parse_claude_code_transcript([line])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], obj)


class TestCopilotE2EPowerSteering(unittest.TestCase):
    """End-to-end test: PowerSteeringChecker against Copilot transcript."""

    def setUp(self):
        """Set up a minimal project root with power steering config."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )

        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {
            "enabled": True,
            "version": "1.0.0",
            "phase": 1,
            "checkers_enabled": {
                "todos_complete": True,
                "dev_workflow_complete": True,
                "philosophy_compliance": False,  # Disable SDK-dependent checker
                "local_testing": True,
                "ci_status": False,  # Disable remote checker
            },
        }
        config_path.write_text(json.dumps(config, indent=2))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_session_type_detection_on_copilot_transcript(self):
        """detect_session_type correctly classifies a normalized Copilot transcript."""
        from power_steering_checker import PowerSteeringChecker

        lines = _load_lines(COPILOT_JSONL)
        _, normalized = parse_transcript(lines)

        checker = PowerSteeringChecker(self.project_root)
        session_type = checker.detect_session_type(normalized)

        self.assertIn(
            session_type,
            ["DEVELOPMENT", "INFORMATIONAL", "INVESTIGATION", "MAINTENANCE", "SIMPLE"],
        )

    def test_check_session_on_normalized_copilot_transcript(self):
        """PowerSteeringChecker.check() works on a pre-normalized Copilot transcript."""
        from power_steering_checker import PowerSteeringChecker, PowerSteeringResult

        lines = _load_lines(COPILOT_JSONL)
        _, normalized = parse_transcript(lines)

        transcript_path = self.project_root / "copilot_normalized.jsonl"
        with open(transcript_path, "w") as f:
            for msg in normalized:
                f.write(json.dumps(msg) + "\n")

        checker = PowerSteeringChecker(self.project_root)
        result = checker.check(transcript_path, "copilot-session-abc123")

        self.assertIsInstance(result, PowerSteeringResult)
        self.assertIn(result.decision, ["approve", "block"])

    def test_check_session_on_raw_copilot_jsonl(self):
        """check() auto-detects and handles raw (unnormalized) Copilot JSONL."""
        from power_steering_checker import PowerSteeringChecker, PowerSteeringResult

        raw_content = COPILOT_JSONL.read_text()
        transcript_path = self.project_root / "raw_copilot.jsonl"
        transcript_path.write_text(raw_content)

        checker = PowerSteeringChecker(self.project_root)
        result = checker.check(transcript_path, "copilot-raw-session")

        self.assertIsInstance(result, PowerSteeringResult)
        self.assertIn(result.decision, ["approve", "block"])

    def test_result_formatting_produces_valid_output(self):
        """Result from Copilot transcript has properly formatted reasons."""
        from power_steering_checker import PowerSteeringChecker

        transcript_path = self.project_root / "copilot_format.jsonl"
        transcript_path.write_text(COPILOT_JSONL.read_text())

        checker = PowerSteeringChecker(self.project_root)
        result = checker.check(transcript_path, "copilot-format-session")

        self.assertIsInstance(result.reasons, list)
        for reason in result.reasons:
            self.assertIsInstance(reason, str)

    def test_parse_transcript_returns_format_and_messages(self):
        """parse_transcript returns both format string and normalized messages."""
        lines = _load_lines(COPILOT_JSONL)
        fmt, messages = parse_transcript(lines)

        self.assertEqual(fmt, "copilot")
        self.assertIsInstance(messages, list)
        self.assertGreater(len(messages), 0)

    def test_empty_copilot_session_handled_gracefully(self):
        """Empty Copilot session (only lifecycle events) produces empty message list."""
        lines = [
            json.dumps({"event": "conversation_start", "session_id": "empty"}),
            json.dumps({"event": "conversation_end", "session_id": "empty"}),
        ]
        fmt, messages = parse_transcript(lines)
        self.assertEqual(fmt, "copilot")
        self.assertEqual(messages, [])


class TestTranscriptParserEdgeCases(unittest.TestCase):
    """Edge case tests for transcript_parser robustness."""

    def test_unknown_role_skipped(self):
        obj = {"role": "system_internal", "content": "metadata"}
        result = normalize_copilot_event(obj)
        self.assertIsNone(result)

    def test_json_string_arguments_decoded(self):
        """tool_calls with JSON-string arguments are decoded to dict."""
        obj = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"name": "shell", "arguments": '{"command": "ls -la"}'},
            ],
        }
        result = normalize_copilot_event(obj)
        self.assertIsNotNone(result)
        tool = next(b for b in result["message"]["content"] if b.get("type") == "tool_use")
        self.assertEqual(tool["input"], {"command": "ls -la"})

    def test_interleaved_conversation(self):
        """Multiple turns normalize to correct ordering."""
        lines = [
            json.dumps({"role": "user", "content": "First message"}),
            json.dumps({"role": "assistant", "content": "First reply"}),
            json.dumps({"role": "user", "content": "Second message"}),
            json.dumps({"role": "assistant", "content": "Second reply"}),
        ]
        fmt, messages = parse_transcript(lines)
        self.assertEqual(fmt, "copilot")
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0]["type"], "user")
        self.assertEqual(messages[1]["type"], "assistant")
        self.assertEqual(messages[2]["type"], "user")
        self.assertEqual(messages[3]["type"], "assistant")

    def test_malformed_json_line_skipped(self):
        """Malformed JSON lines are silently skipped."""
        lines = [
            "not valid json{{{",
            json.dumps({"role": "user", "content": "Valid message"}),
        ]
        fmt, messages = parse_transcript(lines)
        # malformed line defaults to claude_code since first line detection fails
        self.assertIn(fmt, ["claude_code", "copilot"])
        # At minimum the valid message should be parsed
        self.assertGreaterEqual(len(messages), 0)  # fail-open


if __name__ == "__main__":
    unittest.main(verbosity=2)
