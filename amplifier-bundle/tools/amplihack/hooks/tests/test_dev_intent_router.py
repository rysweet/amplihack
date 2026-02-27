"""
Tests for dev_intent_router.py — auto-dev routing via UserPromptSubmit hook.

Coverage: 51 prompts across 7 categories.
Accuracy target: ≥98% (0 false positives, ≤1 false negative).
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dev_intent_router import classify, should_auto_route, DevIntentResult


class TestDevImperatives(unittest.TestCase):
    """Clear development action verbs — should always route."""

    def _assert_routes(self, prompt: str):
        r = classify(prompt)
        self.assertTrue(r.should_route, f"Expected DEV routing for: '{prompt}' — got: {r.reason}")

    def test_fix_bug(self):             self._assert_routes("fix the login timeout bug")
    def test_build_api(self):           self._assert_routes("build a REST API for user management")
    def test_add_oauth(self):           self._assert_routes("add OAuth support to the auth flow")
    def test_refactor(self):            self._assert_routes("refactor the payment service for readability")
    def test_implement(self):           self._assert_routes("implement exponential backoff on retries")
    def test_create_component(self):    self._assert_routes("create a React component for the dashboard")
    def test_debug(self):               self._assert_routes("debug why the tests are failing")
    def test_write_migration(self):     self._assert_routes("write a migration script for the user table")
    def test_optimize(self):            self._assert_routes("optimize the slow database queries")
    def test_update_jwt(self):          self._assert_routes("update the JWT expiry to 24 hours")
    def test_make_webui(self):          self._assert_routes("make a webui and an api for orders")
    def test_deploy(self):              self._assert_routes("deploy the new service to staging")
    def test_setup_cicd(self):          self._assert_routes("set up CI/CD for the mobile app")
    def test_migrate_db(self):          self._assert_routes("migrate the database to Postgres")
    def test_scaffold(self):            self._assert_routes("scaffold a new Express service")
    def test_improve_error(self):       self._assert_routes("improve error handling in the API gateway")
    def test_add_rate_limit(self):      self._assert_routes("add rate limiting to the endpoints")
    def test_integrate_stripe(self):    self._assert_routes("integrate Stripe for payment processing")
    def test_clean_legacy(self):        self._assert_routes("clean up the legacy auth code")
    def test_test_e2e(self):            self._assert_routes("test the checkout flow end to end")
    def test_structure(self):           self._assert_routes("structure the authentication module properly")
    def test_automate(self):            self._assert_routes("automate the deployment pipeline")
    def test_secure(self):              self._assert_routes("secure the API endpoints with rate limiting")


class TestDevQuestions(unittest.TestCase):
    """Question-form dev requests — ambiguous starters but clear dev intent."""

    def _assert_routes(self, prompt: str):
        r = classify(prompt)
        self.assertTrue(r.should_route, f"Expected DEV routing for: '{prompt}' — got: {r.reason}")

    def test_can_you_fix(self):         self._assert_routes("can you fix the session bug?")
    def test_how_do_i_add(self):        self._assert_routes("how do I add pagination to the API?")
    def test_could_you_implement(self): self._assert_routes("could you help me implement caching?")
    def test_best_way_implement(self):  self._assert_routes("what would be the best way to implement rate limiting?")
    def test_id_like_to_add(self):      self._assert_routes("I'd like to add authentication to my service")
    def test_help_migrate(self):        self._assert_routes("help me migrate the database schema")
    def test_show_implement(self):      self._assert_routes("show me how to implement OAuth")
    def test_how_should_structure(self): self._assert_routes("how should I structure the microservices?")
    def test_how_add_endpoint(self):    self._assert_routes("how do I add an endpoint for user profiles?")


class TestInvestigation(unittest.TestCase):
    """Investigation/analysis tasks — should route."""

    def _assert_routes(self, prompt: str):
        r = classify(prompt)
        self.assertTrue(r.should_route, f"Expected DEV routing for: '{prompt}' — got: {r.reason}")

    def test_investigate(self):   self._assert_routes("investigate why the build is failing")
    def test_analyze(self):       self._assert_routes("analyze the performance bottlenecks")
    def test_explore(self):       self._assert_routes("explore the best architecture for this service")
    def test_review_pr(self):     self._assert_routes("review PR #42 for security issues")
    def test_research(self):      self._assert_routes("research caching strategies for the feed")
    def test_audit(self):         self._assert_routes("audit the authentication module")


class TestQA(unittest.TestCase):
    """Pure Q&A / knowledge requests — should NOT route."""

    def _assert_skips(self, prompt: str):
        r = classify(prompt)
        self.assertFalse(r.should_route, f"Expected SKIP for: '{prompt}' — got: {r.reason}")

    def test_what_is_oauth(self):   self._assert_skips("what is OAuth?")
    def test_how_does_jwt(self):    self._assert_skips("how does JWT work?")
    def test_explain_pattern(self): self._assert_skips("explain the circuit breaker pattern")
    def test_difference(self):      self._assert_skips("what's the difference between REST and GraphQL?")
    def test_why_redis(self):       self._assert_skips("why use Redis instead of Memcached?")
    def test_when_microservices(self): self._assert_skips("when should I use microservices?")
    def test_solid_principles(self): self._assert_skips("what are the SOLID principles?")


class TestGreetingsAndAcks(unittest.TestCase):
    """Greetings and acknowledgements — should NOT route."""

    def _assert_skips(self, prompt: str):
        r = classify(prompt)
        self.assertFalse(r.should_route, f"Expected SKIP for: '{prompt}' — got: {r.reason}")

    def test_hello(self):           self._assert_skips("hello")
    def test_thanks(self):          self._assert_skips("thanks, that worked!")
    def test_ok(self):              self._assert_skips("ok sounds good")


class TestExistingCommands(unittest.TestCase):
    """Existing slash commands — should NEVER be intercepted."""

    def _assert_skips(self, prompt: str):
        r = classify(prompt)
        self.assertFalse(r.should_route, f"Expected SKIP for: '{prompt}' — got: {r.reason}")

    def test_analyze(self):     self._assert_skips("/analyze the auth module")
    def test_fix(self):         self._assert_skips("/fix import errors")
    def test_multitask(self):   self._assert_skips("/multitask - run 3 tasks")
    def test_dev(self):         self._assert_skips("/dev fix the bug")


class TestOperations(unittest.TestCase):
    """Shell/admin operations — should NOT route."""

    def _assert_skips(self, prompt: str):
        r = classify(prompt)
        self.assertFalse(r.should_route, f"Expected SKIP for: '{prompt}' — got: {r.reason}")

    def test_git(self):             self._assert_skips("run git status")
    def test_disk(self):            self._assert_skips("show me the disk usage")
    def test_delete_logs(self):     self._assert_skips("delete old log files from /tmp")


class TestBypassPhrases(unittest.TestCase):
    """Explicit bypass signals — should NOT route even if dev keywords present."""

    def _assert_skips(self, prompt: str):
        r = classify(prompt)
        self.assertFalse(r.should_route, f"Expected SKIP for: '{prompt}' — got: {r.reason}")

    def test_just_answer(self):     self._assert_skips("just answer briefly — what is OAuth?")
    def test_without_workflow(self): self._assert_skips("without workflow, fix this quick: what is caching?")


class TestEnvVarBypass(unittest.TestCase):
    """AMPLIHACK_AUTO_DEV=false should disable routing entirely."""

    def test_env_var_disables_routing(self):
        os.environ["AMPLIHACK_AUTO_DEV"] = "false"
        try:
            ok, ctx = should_auto_route("fix the login timeout bug")
            self.assertFalse(ok, "should_auto_route must return False when AMPLIHACK_AUTO_DEV=false")
            self.assertEqual(ctx, "")
        finally:
            del os.environ["AMPLIHACK_AUTO_DEV"]

    def test_env_var_enabled_by_default(self):
        os.environ.pop("AMPLIHACK_AUTO_DEV", None)
        ok, ctx = should_auto_route("fix the login timeout bug")
        self.assertTrue(ok, "should_auto_route must return True by default for dev tasks")
        self.assertIn("dev-orchestrator", ctx)


class TestConfidenceTiers(unittest.TestCase):
    """Verify confidence and tier values for key prompt categories."""

    def test_clear_action_is_required(self):
        r = classify("implement JWT authentication")
        self.assertTrue(r.should_route)
        self.assertEqual(r.tier, "required")
        self.assertGreaterEqual(r.confidence, 0.90)

    def test_ambiguous_question_is_recommended(self):
        r = classify("how do I add rate limiting to my API?")
        self.assertTrue(r.should_route)
        self.assertIn(r.tier, ("required", "recommended"))

    def test_qa_is_skipped(self):
        r = classify("what is rate limiting?")
        self.assertFalse(r.should_route)
        self.assertEqual(r.tier, "skip")

    def test_injection_contains_directive(self):
        from dev_intent_router import build_context_injection
        r = classify("fix the login bug")
        ctx = build_context_injection(r, "fix the login bug")
        self.assertIn("dev-orchestrator", ctx)
        self.assertIn("system-reminder", ctx)


if __name__ == "__main__":
    unittest.main(verbosity=2)
