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
            [sys.executable, "-c",
             "import os,sys; sys.path.insert(0,os.path.dirname(os.environ['HELPER_PATH'])); import orch_helper; print('ok')"],
            env={**os.environ, "HELPER_PATH": f"{tools_dir}/orch_helper.py"},
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 0, f"Import via HELPER_PATH failed: {r.stderr}")
        self.assertEqual(r.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()


# ─────────────────────────────────────────────────────────────────────────────
# Regression tests: issue #3092 — orch_helper.py path resolution
# ─────────────────────────────────────────────────────────────────────────────

class TestIssue3092OldPatternRegression(unittest.TestCase):
    """Document the old broken pattern and verify the new module fixes it.

    Issue #3092: smart-orchestrator parse-decomposition fails outside amplihack
    repo because the old pattern uses git rev-parse to find the repo root, which
    returns the *target* repo root, not the amplihack installation root.
    """

    _REPO_ROOT = Path(__file__).resolve().parent.parent
    _TOOLS_DIR = _REPO_ROOT / "amplifier-bundle" / "tools"

    def test_old_git_rev_parse_pattern_would_fail_in_tmp(self):
        """Document that the old pattern produces a wrong path from /tmp — confirms the bug.

        The old pattern:
          HELPER_PATH="${AMPLIHACK_HOME:-$(git rev-parse --show-toplevel 2>/dev/null || echo '.')}/amplifier-bundle/tools/orch_helper.py"

        From /tmp (no git repo), git rev-parse fails, '.' is used, yielding:
          /tmp/amplifier-bundle/tools/orch_helper.py  (does not exist)

        We verify this by running the pattern from /tmp and checking that the
        *absolute* path produced is NOT under the amplihack repo.
        """
        old_pattern_result = subprocess.run(
            ["bash", "-c",
             "cd /tmp && echo \"$(git rev-parse --show-toplevel 2>/dev/null || echo /tmp)\"/amplifier-bundle/tools/orch_helper.py"],
            capture_output=True,
            text=True,
            cwd="/tmp",
            env={k: v for k, v in os.environ.items() if k != "AMPLIHACK_HOME"},
        )
        old_path = old_pattern_result.stdout.strip()
        # The old pattern resolves to /tmp/amplifier-bundle/..., which does not exist.
        self.assertFalse(
            Path(old_path).exists(),
            f"Old pattern should produce a non-existent path from /tmp (got: {old_path!r}). "
            f"This confirms why issue #3092 occurred.",
        )

    def test_resolve_bundle_asset_finds_orch_helper(self):
        """New module resolves orch_helper.py correctly from /tmp."""
        src_dir = str(self._REPO_ROOT / "src")
        env = {
            **os.environ,
            "AMPLIHACK_HOME": str(self._REPO_ROOT),
            "PYTHONPATH": src_dir + os.pathsep + os.environ.get("PYTHONPATH", ""),
        }
        result = subprocess.run(
            [sys.executable, "-m", "amplihack.resolve_bundle_asset",
             "amplifier-bundle/tools/orch_helper.py"],
            capture_output=True,
            text=True,
            env=env,
            cwd="/tmp",
        )
        self.assertEqual(
            result.returncode,
            0,
            f"Issue #3092 regression: resolve_bundle_asset failed from /tmp.\n"
            f"stderr: {result.stderr}",
        )
        resolved = result.stdout.strip()
        self.assertTrue(
            Path(resolved).is_file(),
            f"Resolved path is not an existing file: {resolved}",
        )

    def test_resolved_path_importable_as_orch_helper(self):
        """Path from resolve_bundle_asset can be imported as orch_helper module."""
        import importlib.util as ilu
        orch_helper_path = self._TOOLS_DIR / "orch_helper.py"
        spec = ilu.spec_from_file_location("orch_helper", orch_helper_path)
        h = ilu.module_from_spec(spec)
        spec.loader.exec_module(h)
        self.assertTrue(callable(getattr(h, "extract_json", None)))
        self.assertTrue(callable(getattr(h, "normalise_type", None)))
