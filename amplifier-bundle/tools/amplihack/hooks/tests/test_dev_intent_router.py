"""
Tests for dev_intent_router.py — LLM-based intent routing via UserPromptSubmit hook.

The classifier no longer uses regex. It injects a routing prompt that the LLM
evaluates with full natural language understanding. These tests verify:

1. The injection fires when expected (non-slash, non-disabled prompts)
2. The injection does NOT fire for slash commands, disabled state, or short messages
3. The injection text contains the correct routing categories
4. The semaphore file and env var disable mechanisms work
5. The workflow-active semaphore blocks injection during orchestration
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
from dev_intent_router import (
    _MIN_PROMPT_LENGTH,
    _ROUTING_PROMPT,
    _TEMPLATE_DIR,
    _load_routing_prompt,
    clear_workflow_active,
    disable_auto_dev,
    enable_auto_dev,
    is_auto_dev_enabled,
    is_workflow_active,
    set_workflow_active,
    should_auto_route,
)


def _make_patches(tmp: str):
    """Create standard patches for all path helpers pointing to a temp dir."""
    return [
        patch(
            "dev_intent_router._get_semaphore_path",
            return_value=Path(tmp) / ".auto_dev_active",
        ),
        patch(
            "dev_intent_router._get_workflow_active_path",
            return_value=Path(tmp) / ".workflow_active",
        ),
    ]


class TestInjectionFires(unittest.TestCase):
    """Prompts that SHOULD receive the routing injection."""

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        self._tmp = tempfile.mkdtemp()
        self._patches = _make_patches(self._tmp)
        for p in self._patches:
            p.start()
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def _assert_injects(self, prompt: str):
        ok, ctx = should_auto_route(prompt)
        self.assertTrue(ok, f"Expected injection for: '{prompt}'")
        self.assertEqual(ctx, _ROUTING_PROMPT)

    def test_dev_task(self):
        self._assert_injects("fix the login timeout bug")

    def test_investigate_task(self):
        self._assert_injects("investigate why the build is failing")

    def test_hybrid_task(self):
        self._assert_injects("investigate auth then add OAuth")

    def test_qa_task(self):
        self._assert_injects("what is OAuth?")

    def test_ops_task(self):
        self._assert_injects("run git status please")

    def test_ambiguous_task(self):
        self._assert_injects("the tests are failing")


class TestInjectionSkips(unittest.TestCase):
    """Prompts that should NOT receive the routing injection."""

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        self._tmp = tempfile.mkdtemp()
        self._patches = _make_patches(self._tmp)
        for p in self._patches:
            p.start()
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def _assert_skips(self, prompt: str):
        ok, ctx = should_auto_route(prompt)
        self.assertFalse(ok, f"Expected NO injection for: '{prompt}'")
        self.assertEqual(ctx, "")

    # Slash commands
    def test_dev_command(self):
        self._assert_skips("/dev fix the bug")

    def test_analyze_command(self):
        self._assert_skips("/analyze the auth module")

    def test_fix_command(self):
        self._assert_skips("/fix import errors")

    def test_multitask_command(self):
        self._assert_skips("/multitask - run 3 tasks")

    def test_amplihack_command(self):
        self._assert_skips("/amplihack:ddd:1-plan")

    # Empty/whitespace/type guards
    def test_empty(self):
        self._assert_skips("")

    def test_whitespace_only(self):
        self._assert_skips("   ")

    def test_newlines_only(self):
        self._assert_skips("\n\n\n")

    def test_none_input(self):
        ok, ctx = should_auto_route(None)  # type: ignore[arg-type]
        self.assertFalse(ok)

    def test_int_input(self):
        ok, ctx = should_auto_route(123)  # type: ignore[arg-type]
        self.assertFalse(ok)

    def test_slash_with_whitespace(self):
        self._assert_skips("   /dev fix the bug   ")

    # Short messages
    def test_short_yes(self):
        self._assert_skips("yes")

    def test_short_ok(self):
        self._assert_skips("ok")

    def test_short_thanks(self):
        self._assert_skips("thanks")

    def test_short_no(self):
        self._assert_skips("no")

    def test_at_threshold(self):
        prompt = "x" * _MIN_PROMPT_LENGTH
        ok, _ = should_auto_route(prompt)
        self.assertTrue(ok)

    def test_below_threshold(self):
        prompt = "x" * (_MIN_PROMPT_LENGTH - 1)
        ok, _ = should_auto_route(prompt)
        self.assertFalse(ok)


class TestSemaphoreToggle(unittest.TestCase):
    """File-based semaphore for dynamic enable/disable during a session."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._patches = _make_patches(self._tmp)
        for p in self._patches:
            p.start()
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)

    def tearDown(self):
        for p in self._patches:
            p.stop()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_enable_creates_semaphore(self):
        enable_auto_dev()
        self.assertTrue(is_auto_dev_enabled())

    def test_disable_removes_semaphore(self):
        enable_auto_dev()
        disable_auto_dev()
        self.assertFalse(is_auto_dev_enabled())

    def test_disable_blocks_injection(self):
        enable_auto_dev()
        disable_auto_dev()
        ok, ctx = should_auto_route("fix the login bug please")
        self.assertFalse(ok)
        self.assertEqual(ctx, "")

    def test_re_enable_restores_injection(self):
        enable_auto_dev()
        disable_auto_dev()
        enable_auto_dev()
        ok, _ = should_auto_route("fix the login bug please")
        self.assertTrue(ok)

    def test_enable_idempotent(self):
        enable_auto_dev()
        msg2 = enable_auto_dev()
        self.assertIn("already", msg2)

    def test_disable_idempotent(self):
        msg = disable_auto_dev()
        self.assertIn("disabled", msg.lower())

    def test_disable_preserves_workflow_active(self):
        """Disabling auto-routing does NOT clear an active workflow semaphore."""
        enable_auto_dev()
        set_workflow_active("Development", 1)
        disable_auto_dev()
        self.assertTrue(
            (Path(self._tmp) / ".workflow_active").exists(),
            "Workflow semaphore must persist after disable",
        )

    def test_first_injection_creates_semaphore(self):
        """First injection auto-creates the semaphore if locks dir doesn't exist."""
        import shutil

        fresh = tempfile.mkdtemp()
        sem = Path(fresh) / "locks" / ".auto_dev_active"
        wf = Path(fresh) / "locks" / ".workflow_active"
        with (
            patch("dev_intent_router._get_semaphore_path", return_value=sem),
            patch("dev_intent_router._get_workflow_active_path", return_value=wf),
        ):
            ok, _ = should_auto_route("fix the login timeout bug")
            self.assertTrue(ok)
            self.assertTrue(sem.exists(), "Semaphore must be auto-created on first injection")
        shutil.rmtree(fresh, ignore_errors=True)


class TestEnvVarFallback(unittest.TestCase):
    """AMPLIHACK_AUTO_DEV env var works when no semaphore dir exists (legacy)."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._patches = [
            patch(
                "dev_intent_router._get_semaphore_path",
                return_value=Path(self._tmp) / "nonexistent" / ".auto_dev_active",
            ),
            patch(
                "dev_intent_router._get_workflow_active_path",
                return_value=Path(self._tmp) / "nonexistent" / ".workflow_active",
            ),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_env_false_disables(self):
        os.environ["AMPLIHACK_AUTO_DEV"] = "false"
        self.assertFalse(is_auto_dev_enabled())

    def test_env_zero_disables(self):
        os.environ["AMPLIHACK_AUTO_DEV"] = "0"
        self.assertFalse(is_auto_dev_enabled())

    def test_env_default_enables(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        self.assertTrue(is_auto_dev_enabled())


class TestRoutingPromptContent(unittest.TestCase):
    """The injection text must contain all 6 routing categories."""

    def test_contains_dev_category(self):
        self.assertIn("DEV", _ROUTING_PROMPT)
        self.assertIn("dev-orchestrator", _ROUTING_PROMPT)

    def test_contains_investigate_category(self):
        self.assertIn("INVESTIGATE", _ROUTING_PROMPT)
        self.assertIn("dev-orchestrator", _ROUTING_PROMPT)

    def test_contains_hybrid_category(self):
        self.assertIn("HYBRID", _ROUTING_PROMPT)
        self.assertIn("Investigate/understand THEN implement/fix", _ROUTING_PROMPT)

    def test_contains_qa_category(self):
        self.assertIn("Q&A", _ROUTING_PROMPT)
        self.assertIn("Answer directly", _ROUTING_PROMPT)

    def test_contains_ops_category(self):
        self.assertIn("OPS", _ROUTING_PROMPT)
        self.assertIn("Execute directly", _ROUTING_PROMPT)

    def test_contains_skip_category(self):
        self.assertIn("SKIP", _ROUTING_PROMPT)
        self.assertIn("just answer", _ROUTING_PROMPT)

    def test_contains_system_reminder_tags(self):
        self.assertTrue(_ROUTING_PROMPT.startswith("<system-reminder"))
        self.assertTrue(_ROUTING_PROMPT.strip().endswith("</system-reminder>"))

    def test_mentions_key_disambiguation_examples(self):
        self.assertIn("make sure it works", _ROUTING_PROMPT)
        self.assertIn("write docs", _ROUTING_PROMPT)
        self.assertIn("review this PR", _ROUTING_PROMPT)
        self.assertIn("run tests", _ROUTING_PROMPT)
        self.assertIn("what is OAuth?", _ROUTING_PROMPT)

    def test_prompt_is_concise(self):
# New prompt is longer due to MANDATORY RULE section for code/docs changes
        self.assertLess(len(_ROUTING_PROMPT), 2500)

    def test_auto_routed_announcement(self):
        self.assertIn("[auto-routed]", _ROUTING_PROMPT)

    def test_contains_mandatory_code_edit_rule(self):
        """The prompt must enforce that ALL file changes use DEV workflow."""
        self.assertIn("MANDATORY RULE", _ROUTING_PROMPT)
        self.assertIn("ALWAYS DEV", _ROUTING_PROMPT)
        self.assertIn("NO exceptions", _ROUTING_PROMPT)

    def test_routing_prompt_is_not_empty(self):
        """The prompt must load from external template file successfully."""
        self.assertTrue(len(_ROUTING_PROMPT) > 0, "Routing prompt should not be empty")


class TestRoutingPromptFileLoading(unittest.TestCase):
    """Verify the prompt loads from external template file correctly."""

    def test_template_file_exists(self):
        """The routing_prompt.txt template file must exist."""
        prompt_file = _TEMPLATE_DIR / "routing_prompt.txt"
        self.assertTrue(prompt_file.exists(), f"Template file not found: {prompt_file}")

    def test_template_loads_matching_content(self):
        """The loaded prompt must match the file content."""
        prompt_file = _TEMPLATE_DIR / "routing_prompt.txt"
        file_content = prompt_file.read_text()
        loaded = _load_routing_prompt()
        self.assertEqual(loaded, file_content)

    def test_load_handles_missing_file(self):
        """_load_routing_prompt returns empty string when template file is missing."""
        import dev_intent_router

        saved = dev_intent_router._TEMPLATE_DIR
        try:
            dev_intent_router._TEMPLATE_DIR = Path("/nonexistent/path")
            result = dev_intent_router._load_routing_prompt()
            self.assertEqual(result, "")
        finally:
            dev_intent_router._TEMPLATE_DIR = saved


class TestWorkflowActiveSemaphore(unittest.TestCase):
    """Skip injection when a workflow is already running."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._patches = _make_patches(self._tmp)
        for p in self._patches:
            p.start()
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        for p in self._patches:
            p.stop()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_set_creates_semaphore(self):
        set_workflow_active("Development", 1)
        self.assertTrue(is_workflow_active())

    def test_clear_removes_semaphore(self):
        set_workflow_active("Development", 1)
        clear_workflow_active()
        self.assertFalse(is_workflow_active())

    def test_active_workflow_blocks_injection(self):
        set_workflow_active("Development", 1)
        ok, ctx = should_auto_route("fix the login bug please")
        self.assertFalse(ok)
        self.assertEqual(ctx, "")

    def test_cleared_workflow_restores_injection(self):
        set_workflow_active("Development", 1)
        clear_workflow_active()
        ok, _ = should_auto_route("fix the login bug please")
        self.assertTrue(ok)

    def test_semaphore_contains_json(self):
        set_workflow_active("Investigation", 2)
        import json

        data = json.loads((Path(self._tmp) / ".workflow_active").read_text())
        self.assertEqual(data["task_type"], "Investigation")
        self.assertEqual(data["workstreams"], 2)
        self.assertTrue(data["active"])

    def test_dead_pid_clears_semaphore(self):
        set_workflow_active("Development", 1, pid=99999999)
        self.assertFalse(is_workflow_active())

    def test_stale_semaphore_ignored(self):
        """Semaphore older than 2 hours is treated as stale even with live PID."""
        set_workflow_active("Development", 1, pid=os.getpid())
        path = Path(self._tmp) / ".workflow_active"
        import time

        old_time = time.time() - 7201
        os.utime(str(path), (old_time, old_time))
        self.assertFalse(is_workflow_active())


class TestIssue2662DeadCodeRemoved(unittest.TestCase):
    """Regression test: Issue #2662 — dead code in classify() must stay removed.

    The old regex-based dev_intent_router had a classify() function with:
      - _AMBIGUOUS_QA_RE: a regex constant used only by dead Step 7
      - has_ambiguous: a variable set from _AMBIGUOUS_QA_RE
      - Step 7 block: `if has_ambiguous and has_action:` — provably unreachable
        because Steps 5+6 exhausted all has_action=True cases first

    These were removed in commit e5cfbbdd as part of PR #2653 (closes #2662).
    This test ensures they are never reintroduced.
    """

    def test_ambiguous_qa_re_not_in_module(self):
        """_AMBIGUOUS_QA_RE must not exist in dev_intent_router."""
        import dev_intent_router

        self.assertFalse(
            hasattr(dev_intent_router, "_AMBIGUOUS_QA_RE"),
            "_AMBIGUOUS_QA_RE is dead code (issue #2662) and must not be reintroduced",
        )

    def test_classify_function_not_in_module(self):
        """The old regex-based classify() function must not exist in dev_intent_router.

        The function was replaced by should_auto_route() + LLM-based routing prompt.
        """
        import dev_intent_router

        self.assertFalse(
            hasattr(dev_intent_router, "classify"),
            "classify() is the old regex classifier (dead code) and must not be reintroduced",
        )

    def test_should_auto_route_is_the_routing_entrypoint(self):
        """should_auto_route() is the current routing entrypoint (not classify())."""
        import dev_intent_router

        self.assertTrue(
            hasattr(dev_intent_router, "should_auto_route"),
            "should_auto_route() must exist as the routing entrypoint",
        )
        self.assertTrue(callable(dev_intent_router.should_auto_route))


if __name__ == "__main__":
    unittest.main(verbosity=2)
