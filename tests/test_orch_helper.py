"""
Tests for amplifier-bundle/tools/orch_helper.py

Covers: extract_json, normalise_type, and CLI subcommands.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

_TOOLS_DIR = Path(__file__).parent.parent / "amplifier-bundle" / "tools"
sys.path.insert(0, str(_TOOLS_DIR))
import orch_helper as _h

_SCRIPT = str(_TOOLS_DIR / "orch_helper.py")


class TestExtractJson(unittest.TestCase):
    """extract_json handles diverse LLM output formats."""

    def test_extract_from_json_code_block(self):
        """Standard ```json ... ``` code block is parsed correctly."""
        obj = {"task_type": "Development", "workstreams": [{"name": "api"}]}
        text = f"Here is the plan:\n```json\n{json.dumps(obj)}\n```\n"
        result = _h.extract_json(text)
        self.assertEqual(result.get("task_type"), "Development")
        self.assertEqual(len(result.get("workstreams", [])), 1)

    def test_extract_with_backtick_in_json_string(self):
        """JSON containing a backtick in a string value is handled via prose fallback."""
        # Code block regex requires no backtick inside the block, so this falls through
        # to the balanced-brace prose scanner.
        obj = {"task_type": "Development", "note": "use `grep` to find", "workstreams": []}
        # Do NOT wrap in code block — use raw JSON in prose
        text = f"The plan: {json.dumps(obj)} proceed."
        result = _h.extract_json(text)
        self.assertEqual(result.get("task_type"), "Development")
        self.assertIn("grep", result.get("note", ""))

    def test_extract_with_multiple_prose_braces_before_json(self):
        """Multiple failed brace candidates in prose; real JSON is found eventually."""
        actual = {"task_type": "Investigation", "goal": "research X", "workstreams": []}
        text = f"Notes {{WIP}} and {{TODO}} then: {json.dumps(actual)}"
        result = _h.extract_json(text)
        self.assertEqual(result.get("task_type"), "Investigation")
        self.assertEqual(result.get("goal"), "research X")

    def test_extract_returns_empty_dict_on_no_json(self):
        """Garbage input returns empty dict."""
        result = _h.extract_json("no json here at all")
        self.assertEqual(result, {})

    def test_extract_returns_empty_dict_on_empty_string(self):
        result = _h.extract_json("")
        self.assertEqual(result, {})

    def test_extract_first_of_two_code_blocks(self):
        """When two valid code blocks exist, the first is returned."""
        block1 = json.dumps({"task_type": "Q&A", "goal": "first"})
        block2 = json.dumps({"task_type": "Development", "goal": "second"})
        text = f"```json\n{block1}\n```\n\n```json\n{block2}\n```"
        result = _h.extract_json(text)
        self.assertEqual(result.get("goal"), "first")
        self.assertEqual(result.get("task_type"), "Q&A")

    def test_extract_raw_json_no_code_block(self):
        """Plain JSON without code block wrapping is extracted."""
        obj = {"task_type": "Operations", "workstreams": []}
        result = _h.extract_json(json.dumps(obj))
        self.assertEqual(result.get("task_type"), "Operations")


class TestNormaliseType(unittest.TestCase):
    """normalise_type maps LLM output to canonical task type strings."""

    def test_qa_variants(self):
        for raw in ("qa", "Q&A", "question", "answer"):
            with self.subTest(raw=raw):
                self.assertEqual(_h.normalise_type(raw), "Q&A")

    def test_operations_variants(self):
        for raw in ("ops", "Operations", "operation", "admin", "command"):
            with self.subTest(raw=raw):
                self.assertEqual(_h.normalise_type(raw), "Operations")

    def test_investigation_variants(self):
        for raw in ("invest", "Investigation", "research", "explore", "understand", "analysis"):
            with self.subTest(raw=raw):
                self.assertEqual(_h.normalise_type(raw), "Investigation")

    def test_development_default(self):
        for raw in ("dev", "Development", "build", "implement", "unknown", ""):
            with self.subTest(raw=raw):
                self.assertEqual(_h.normalise_type(raw), "Development")


class TestCLIExtractSubcommand(unittest.TestCase):
    """CLI `extract` subcommand outputs valid JSON."""

    def _run(self, args, stdin_text=""):
        return subprocess.run(
            [sys.executable, _SCRIPT] + args,
            input=stdin_text,
            capture_output=True,
            text=True,
        )

    def test_extract_subcommand_outputs_valid_json(self):
        obj = {"task_type": "Development", "workstreams": [{"name": "ws1"}]}
        r = self._run(["extract"], stdin_text=json.dumps(obj))
        self.assertEqual(r.returncode, 0, f"extract exited non-zero: {r.stderr}")
        parsed = json.loads(r.stdout.strip())
        self.assertEqual(parsed.get("task_type"), "Development")

    def test_extract_subcommand_with_code_block(self):
        obj = {"task_type": "Investigation", "goal": "research"}
        text = f"```json\n{json.dumps(obj)}\n```"
        r = self._run(["extract"], stdin_text=text)
        self.assertEqual(r.returncode, 0)
        parsed = json.loads(r.stdout.strip())
        self.assertEqual(parsed.get("task_type"), "Investigation")

    def test_extract_default_no_arg_runs_extract(self):
        """Default (no subcommand arg) behaves as extract."""
        obj = {"task_type": "Q&A", "workstreams": []}
        r = self._run([], stdin_text=json.dumps(obj))
        self.assertEqual(r.returncode, 0)
        parsed = json.loads(r.stdout.strip())
        self.assertEqual(parsed.get("task_type"), "Q&A")


class TestCLINormaliseSubcommand(unittest.TestCase):
    """CLI `normalise` subcommand maps types correctly."""

    def _run(self, args, stdin_text=""):
        return subprocess.run(
            [sys.executable, _SCRIPT] + args,
            input=stdin_text,
            capture_output=True,
            text=True,
        )

    def test_normalise_dev(self):
        r = self._run(["normalise"], stdin_text="dev")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "Development")

    def test_normalise_ops(self):
        r = self._run(["normalise"], stdin_text="ops")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "Operations")

    def test_normalise_qa(self):
        r = self._run(["normalise"], stdin_text="Q&A")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "Q&A")

    def test_normalise_investigation(self):
        r = self._run(["normalise"], stdin_text="research")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "Investigation")


class TestCLIUnknownSubcommand(unittest.TestCase):
    """CLI unknown subcommand exits rc=1."""

    def test_unknown_subcommand_exits_one(self):
        r = subprocess.run(
            [sys.executable, _SCRIPT, "bogus-command"],
            input="",
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 1, f"Expected rc=1 for unknown command, got {r.returncode}")
        self.assertIn("Unknown", r.stderr)


if __name__ == "__main__":
    unittest.main()
