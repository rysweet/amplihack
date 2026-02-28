"""
Tests for dev_intent_router.py — LLM-based intent routing via UserPromptSubmit hook.

The classifier no longer uses regex. It injects a routing prompt that the LLM
evaluates with full natural language understanding. These tests verify:

1. The injection fires when expected (non-slash, non-disabled prompts)
2. The injection does NOT fire for slash commands, disabled state, or short messages
3. The injection text contains the correct routing categories
4. The semaphore file and env var disable mechanisms work
5. The first-run welcome banner appears once per session
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
    _WELCOME_BANNER,
    clear_workflow_active,
    disable_auto_dev,
    enable_auto_dev,
    is_auto_dev_enabled,
    is_workflow_active,
    set_workflow_active,
    should_auto_route,
)


class TestInjectionFires(unittest.TestCase):
    """Prompts that SHOULD receive the routing injection.

    All non-slash, non-empty, non-short string prompts get injected — the LLM
    handles classification. One representative test per routing category.
    """

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        self._tmp = tempfile.mkdtemp()
        self._patch = patch(
            "dev_intent_router._get_semaphore_path",
            return_value=Path(self._tmp) / ".auto_dev_active",
        )
        self._patch_banner = patch(
            "dev_intent_router._get_banner_flag_path",
            return_value=Path(self._tmp) / ".auto_dev_banner_shown",
        )
        self._patch_workflow = patch(
            "dev_intent_router._get_workflow_active_path",
            return_value=Path(self._tmp) / ".workflow_active",
        )
        self._patch.start()
        self._patch_banner.start()
        self._patch_workflow.start()
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        self._patch.stop()
        self._patch_banner.stop()
        self._patch_workflow.stop()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def _assert_injects(self, prompt: str):
        ok, ctx = should_auto_route(prompt)
        self.assertTrue(ok, f"Expected injection for: '{prompt}'")
        self.assertIn(_ROUTING_PROMPT, ctx)

    # One representative per routing category
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
        self._patch = patch(
            "dev_intent_router._get_semaphore_path",
            return_value=Path(self._tmp) / ".auto_dev_active",
        )
        self._patch_banner = patch(
            "dev_intent_router._get_banner_flag_path",
            return_value=Path(self._tmp) / ".auto_dev_banner_shown",
        )
        self._patch_workflow = patch(
            "dev_intent_router._get_workflow_active_path",
            return_value=Path(self._tmp) / ".workflow_active",
        )
        self._patch.start()
        self._patch_banner.start()
        self._patch_workflow.start()
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        self._patch.stop()
        self._patch_banner.stop()
        self._patch_workflow.stop()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def _assert_skips(self, prompt: str):
        ok, ctx = should_auto_route(prompt)
        self.assertFalse(ok, f"Expected NO injection for: '{prompt}'")
        self.assertEqual(ctx, "")

    # Existing slash commands — always respected
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

    # Short messages — token-saving skip
    def test_short_yes(self):
        self._assert_skips("yes")

    def test_short_ok(self):
        self._assert_skips("ok")

    def test_short_thanks(self):
        self._assert_skips("thanks")

    def test_short_no(self):
        self._assert_skips("no")

    def test_at_threshold(self):
        # Exactly _MIN_PROMPT_LENGTH chars should inject
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
        self._patch = patch(
            "dev_intent_router._get_semaphore_path",
            return_value=Path(self._tmp) / ".auto_dev_active",
        )
        self._patch_banner = patch(
            "dev_intent_router._get_banner_flag_path",
            return_value=Path(self._tmp) / ".auto_dev_banner_shown",
        )
        self._patch.start()
        self._patch_banner.start()
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)

    def tearDown(self):
        self._patch.stop()
        self._patch_banner.stop()
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
        # Disable without ever enabling — should not crash
        msg = disable_auto_dev()
        self.assertIn("disabled", msg.lower())

    def test_disable_preserves_workflow_active(self):
        """Disabling auto-routing does NOT clear an active workflow semaphore.
        The orchestrator is still running and will clear it when done."""
        enable_auto_dev()
        # Need to mock workflow path too for this test
        workflow_path = Path(self._tmp) / ".workflow_active"
        with patch(
            "dev_intent_router._get_workflow_active_path",
            return_value=workflow_path,
        ):
            set_workflow_active("Development", 1)
            disable_auto_dev()
            self.assertTrue(workflow_path.exists(), "Workflow semaphore must persist after disable")


class TestEnvVarFallback(unittest.TestCase):
    """AMPLIHACK_AUTO_DEV env var works when no semaphore dir exists (legacy)."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        # Point to a non-existent dir so locks dir doesn't exist
        self._patch = patch(
            "dev_intent_router._get_semaphore_path",
            return_value=Path(self._tmp) / "nonexistent" / ".auto_dev_active",
        )
        self._patch_banner = patch(
            "dev_intent_router._get_banner_flag_path",
            return_value=Path(self._tmp) / "nonexistent" / ".auto_dev_banner_shown",
        )
        self._patch.start()
        self._patch_banner.start()

    def tearDown(self):
        self._patch.stop()
        self._patch_banner.stop()
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


class TestWelcomeBanner(unittest.TestCase):
    """First-run welcome banner shows once per session."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._patch = patch(
            "dev_intent_router._get_semaphore_path",
            return_value=Path(self._tmp) / ".auto_dev_active",
        )
        self._patch_banner = patch(
            "dev_intent_router._get_banner_flag_path",
            return_value=Path(self._tmp) / ".auto_dev_banner_shown",
        )
        self._patch_workflow = patch(
            "dev_intent_router._get_workflow_active_path",
            return_value=Path(self._tmp) / ".workflow_active",
        )
        self._patch.start()
        self._patch_banner.start()
        self._patch_workflow.start()
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        self._patch.stop()
        self._patch_banner.stop()
        self._patch_workflow.stop()
        import shutil

        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_first_injection_includes_banner(self):
        ok, ctx = should_auto_route("fix the login timeout bug")
        self.assertTrue(ok)
        self.assertIn(_WELCOME_BANNER, ctx)
        self.assertIn(_ROUTING_PROMPT, ctx)

    def test_second_injection_no_banner(self):
        should_auto_route("fix the login timeout bug")  # first — shows banner
        ok, ctx = should_auto_route("add pagination to the API")  # second — no banner
        self.assertTrue(ok)
        self.assertNotIn(_WELCOME_BANNER, ctx)
        self.assertEqual(ctx, _ROUTING_PROMPT)

    def test_banner_creates_semaphore_when_missing(self):
        """Bug fix: banner must create auto-dev semaphore to prevent
        locks dir creation from accidentally disabling routing."""
        import shutil

        # Simulate truly fresh first run: no locks dir at all
        # This forces env-var fallback (enabled by default)
        fresh_tmp = tempfile.mkdtemp()
        sem_path = Path(fresh_tmp) / "locks" / ".auto_dev_active"
        banner_path = Path(fresh_tmp) / "locks" / ".auto_dev_banner_shown"
        workflow_path = Path(fresh_tmp) / "locks" / ".workflow_active"

        with (
            patch("dev_intent_router._get_semaphore_path", return_value=sem_path),
            patch("dev_intent_router._get_banner_flag_path", return_value=banner_path),
            patch("dev_intent_router._get_workflow_active_path", return_value=workflow_path),
        ):
            ok, ctx = should_auto_route("fix the login timeout bug")
            self.assertTrue(ok, "First injection should fire via env-var fallback")
            self.assertIn(_WELCOME_BANNER, ctx)
            self.assertTrue(sem_path.exists(), "Semaphore must be created by banner logic")

        shutil.rmtree(fresh_tmp, ignore_errors=True)


class TestRoutingPromptContent(unittest.TestCase):
    """The injection text must contain all 6 routing categories."""

    def test_contains_dev_category(self):
        self.assertIn("DEV", _ROUTING_PROMPT)
        self.assertIn("dev-orchestrator", _ROUTING_PROMPT)

    def test_contains_investigate_category(self):
        self.assertIn("INVESTIGATE", _ROUTING_PROMPT)
        self.assertIn("INVESTIGATION_WORKFLOW", _ROUTING_PROMPT)

    def test_contains_hybrid_category(self):
        self.assertIn("HYBRID", _ROUTING_PROMPT)
        self.assertIn("parallel workstreams", _ROUTING_PROMPT)

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
        self.assertTrue(_ROUTING_PROMPT.endswith("</system-reminder>"))

    def test_mentions_key_disambiguation_examples(self):
        """The prompt includes examples that help the LLM with tricky cases."""
        self.assertIn("make sure it works", _ROUTING_PROMPT)
        self.assertIn("write docs", _ROUTING_PROMPT)
        self.assertIn("tests are failing", _ROUTING_PROMPT)
        self.assertIn("review this PR", _ROUTING_PROMPT)
        self.assertIn("run tests", _ROUTING_PROMPT)

    def test_prompt_is_concise(self):
        """The routing prompt should not be excessively long."""
        self.assertLess(
            len(_ROUTING_PROMPT),
            1900,
            "Routing prompt should be concise to minimize token overhead",
        )

    def test_auto_routed_announcement(self):
        """DEV/INVESTIGATE/HYBRID categories instruct Claude to announce routing."""
        self.assertIn("[auto-routed]", _ROUTING_PROMPT)


class TestWorkflowActiveSemaphore(unittest.TestCase):
    """Skip injection when a workflow is already running."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._patch = patch(
            "dev_intent_router._get_semaphore_path",
            return_value=Path(self._tmp) / ".auto_dev_active",
        )
        self._patch_banner = patch(
            "dev_intent_router._get_banner_flag_path",
            return_value=Path(self._tmp) / ".auto_dev_banner_shown",
        )
        self._patch_workflow = patch(
            "dev_intent_router._get_workflow_active_path",
            return_value=Path(self._tmp) / ".workflow_active",
        )
        self._patch.start()
        self._patch_banner.start()
        self._patch_workflow.start()
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        (Path(self._tmp) / ".auto_dev_active").write_text("enabled\n")

    def tearDown(self):
        self._patch.stop()
        self._patch_banner.stop()
        self._patch_workflow.stop()
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
        """Semaphore with a dead PID is treated as orphaned."""
        set_workflow_active("Development", 1, pid=99999999)  # nonexistent PID
        self.assertFalse(is_workflow_active())

    def test_stale_semaphore_ignored(self):
        """Semaphore older than 2 hours is treated as stale even with live PID."""
        set_workflow_active("Development", 1, pid=os.getpid())
        path = Path(self._tmp) / ".workflow_active"
        import time

        old_time = time.time() - 7201  # 2 hours + 1 second
        os.utime(str(path), (old_time, old_time))
        self.assertFalse(is_workflow_active())


if __name__ == "__main__":
    unittest.main(verbosity=2)
