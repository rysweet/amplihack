"""
Tests for amplifier-bundle/tools/orch_helper.py

Covers: extract_json, normalise_type, and CLI subcommands.
"""

import json
import os
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


class TestNormaliseTypePriority(unittest.TestCase):
    """Document keyword priority when input matches multiple categories.
    Priority order: Q&A > Operations > Investigation > Development
    """

    def test_qa_beats_operations_on_overlap(self):
        """Q&A keywords are checked first."""
        self.assertEqual(_h.normalise_type("question about operations"), "Q&A")

    def test_operations_beats_investigation_on_overlap(self):
        """Operations keywords are checked before Investigation.
        'investigate operations' -> Operations, not Investigation.
        """
        self.assertEqual(_h.normalise_type("investigate operations"), "Operations")
        self.assertEqual(_h.normalise_type("research command"), "Operations")

    def test_investigation_beats_development_on_overlap(self):
        """Investigation keywords win over the Development default."""
        self.assertEqual(_h.normalise_type("research and build"), "Investigation")


class TestHelperPathImport(unittest.TestCase):
    """Verify the recipe's HELPER_PATH import pattern works."""

    def test_import_via_helper_path_env_var(self):
        """Verify the recipe's import pattern works: HELPER_PATH must be importable."""
        tools_dir = str(Path(__file__).parent.parent / "amplifier-bundle" / "tools")
        r = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os,sys; sys.path.insert(0,os.path.dirname(os.environ['HELPER_PATH'])); import orch_helper; print('ok')",
            ],
            env={**os.environ, "HELPER_PATH": f"{tools_dir}/orch_helper.py"},
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, f"Import via HELPER_PATH failed: {r.stderr}")
        self.assertEqual(r.stdout.strip(), "ok")


class TestResolveHelperPathRegression(unittest.TestCase):
    """Regression tests for issue #3092: orch_helper.py path resolution.

    These tests document the old broken pattern and verify the new
    resolve_bundle_asset module fixes it.
    """

    def test_old_git_rev_parse_pattern_would_fail_in_tmp(self):
        """The old `git rev-parse --show-toplevel` pattern fails from /tmp.

        This test documents the root cause of issue #3092: when run from
        /tmp (not inside the amplihack git repo), git rev-parse returns a
        non-zero exit code, so the fallback `echo '.'` resolves to the
        current directory — which is /tmp, not the amplihack root.
        """
        original_cwd = os.getcwd()
        try:
            os.chdir("/tmp")
            # Simulate the broken bash pattern: $(git rev-parse ... || echo '.')
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                cwd="/tmp",
            )
            if result.returncode != 0:
                # git failed → broken pattern falls back to "."
                broken_path = Path("/tmp") / "amplifier-bundle" / "tools" / "orch_helper.py"
                self.assertFalse(
                    broken_path.is_file(),
                    "Broken pattern accidentally resolved correctly — test assumption invalid",
                )
            # If git happens to succeed (user's /tmp is inside a repo), skip.
        finally:
            os.chdir(original_cwd)

    def test_resolve_bundle_asset_finds_orch_helper(self):
        """resolve_bundle_asset finds orch_helper.py even from /tmp."""
        resolve_module_path = (
            Path(__file__).parent.parent / "src" / "amplihack" / "resolve_bundle_asset.py"
        )
        self.assertTrue(
            resolve_module_path.exists(),
            f"resolve_bundle_asset.py not found: {resolve_module_path}",
        )
        result = subprocess.run(
            [sys.executable, str(resolve_module_path), "amplifier-bundle/tools/orch_helper.py"],
            capture_output=True,
            text=True,
            cwd="/tmp",
        )
        self.assertEqual(result.returncode, 0, f"resolve_bundle_asset failed:\n{result.stderr}")
        resolved_path = Path(result.stdout.strip())
        self.assertTrue(resolved_path.is_file(), f"Resolved path is not a file: {resolved_path}")

    def test_resolved_path_importable_as_orch_helper(self):
        """orch_helper resolved via resolve_bundle_asset is importable."""
        import importlib.util as _ilu

        resolve_module_path = (
            Path(__file__).parent.parent / "src" / "amplihack" / "resolve_bundle_asset.py"
        )
        result = subprocess.run(
            [sys.executable, str(resolve_module_path), "amplifier-bundle/tools/orch_helper.py"],
            capture_output=True,
            text=True,
            cwd="/tmp",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        helper_path = result.stdout.strip()

        spec = _ilu.spec_from_file_location("orch_helper", helper_path)
        self.assertIsNotNone(spec)
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(
            callable(getattr(mod, "extract_json", None)),
            "extract_json not found in resolved orch_helper",
        )


if __name__ == "__main__":
    unittest.main()
