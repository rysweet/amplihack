"""
Tests for dev_intent_router.py — LLM-based intent routing via UserPromptSubmit hook.

The classifier no longer uses regex. It injects a routing prompt that the LLM
evaluates with full natural language understanding. These tests verify:

1. The injection fires when expected (non-slash, non-disabled prompts)
2. The injection does NOT fire for slash commands and disabled state
3. The injection text contains the correct routing categories
4. The env var disable mechanism works for all accepted values
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dev_intent_router import should_auto_route, _ROUTING_PROMPT


class TestInjectionFires(unittest.TestCase):
    """Prompts that SHOULD receive the routing injection."""

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)

    def _assert_injects(self, prompt: str):
        ok, ctx = should_auto_route(prompt)
        self.assertTrue(ok, f"Expected injection for: '{prompt}'")
        self.assertEqual(ctx, _ROUTING_PROMPT)

    # Development tasks
    def test_fix_bug(self):               self._assert_injects("fix the login timeout bug")
    def test_build_api(self):             self._assert_injects("build a REST API")
    def test_write_docs(self):            self._assert_injects("write the docs")
    def test_make_sure(self):             self._assert_injects("make sure it works")
    def test_deploy(self):                self._assert_injects("deploy to staging")

    # Investigation tasks
    def test_investigate(self):           self._assert_injects("investigate why the build is failing")
    def test_understand(self):            self._assert_injects("understand how the caching layer works")
    def test_analyze(self):               self._assert_injects("analyze the performance bottlenecks")

    # Hybrid tasks
    def test_hybrid(self):                self._assert_injects("investigate auth then add OAuth")

    # Q&A (still gets injection — LLM routes to "answer directly")
    def test_qa_what_is(self):            self._assert_injects("what is OAuth?")
    def test_qa_how_does(self):           self._assert_injects("how does JWT work?")
    def test_qa_what_does(self):          self._assert_injects("what does this function do?")
    def test_qa_where_is(self):           self._assert_injects("where is the database config?")

    # Ops (still gets injection — LLM routes to "execute directly")
    def test_ops_git(self):               self._assert_injects("run git status")
    def test_ops_disk(self):              self._assert_injects("show me the disk usage")

    # Ambiguous (LLM handles it, hook just injects)
    def test_tests_are_failing(self):     self._assert_injects("the tests are failing")
    def test_this_is_broken(self):        self._assert_injects("this is broken")
    def test_greeting_with_task(self):    self._assert_injects("hey can you fix the login?")
    def test_make_it_work(self):          self._assert_injects("make it work")
    def test_whats_wrong(self):           self._assert_injects("what's wrong with the tests?")


class TestInjectionSkips(unittest.TestCase):
    """Prompts that should NOT receive the routing injection."""

    def setUp(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)

    def _assert_skips(self, prompt: str):
        ok, ctx = should_auto_route(prompt)
        self.assertFalse(ok, f"Expected NO injection for: '{prompt}'")
        self.assertEqual(ctx, "")

    # Existing slash commands — always respected
    def test_dev_command(self):            self._assert_skips("/dev fix the bug")
    def test_analyze_command(self):        self._assert_skips("/analyze the auth module")
    def test_fix_command(self):            self._assert_skips("/fix import errors")
    def test_multitask_command(self):      self._assert_skips("/multitask - run 3 tasks")
    def test_amplihack_command(self):      self._assert_skips("/amplihack:ddd:1-plan")

    # Empty/whitespace
    def test_empty(self):                  self._assert_skips("")
    def test_whitespace_slash(self):
        # Only actual slash prefix skips; whitespace-then-text injects
        ok, _ = should_auto_route("   hello")
        self.assertTrue(ok)  # Not a slash command, gets injection


class TestEnvVarDisable(unittest.TestCase):
    """AMPLIHACK_AUTO_DEV=false/0/no/off should disable all injection."""

    def tearDown(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)

    def _assert_disabled(self, value: str):
        os.environ["AMPLIHACK_AUTO_DEV"] = value
        ok, ctx = should_auto_route("fix the login bug")
        self.assertFalse(ok, f"AMPLIHACK_AUTO_DEV={value} should disable routing")
        self.assertEqual(ctx, "")

    def test_false(self):     self._assert_disabled("false")
    def test_False(self):     self._assert_disabled("False")
    def test_FALSE(self):     self._assert_disabled("FALSE")
    def test_zero(self):      self._assert_disabled("0")
    def test_no(self):        self._assert_disabled("no")
    def test_off(self):       self._assert_disabled("off")

    def test_enabled_by_default(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        ok, ctx = should_auto_route("fix the login bug")
        self.assertTrue(ok)

    def test_true_enables(self):
        os.environ["AMPLIHACK_AUTO_DEV"] = "true"
        ok, ctx = should_auto_route("fix the login bug")
        self.assertTrue(ok)


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

    def test_prompt_is_concise(self):
        """The routing prompt should not be excessively long."""
        self.assertLess(len(_ROUTING_PROMPT), 1500,
            "Routing prompt should be concise to minimize token overhead")


if __name__ == "__main__":
    unittest.main(verbosity=2)
