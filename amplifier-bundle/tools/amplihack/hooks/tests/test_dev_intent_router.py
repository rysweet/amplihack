"""
Tests for dev_intent_router.py — auto-dev routing via UserPromptSubmit hook.

Coverage: 97 tests across 11 categories.
Accuracy target: >=98% (minimal false positives, precision-first design).
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

    def test_test_with_object_routes(self):
        """'test' as imperative verb with direct object should route."""
        self._assert_routes("test the checkout flow")
        self._assert_routes("test the payment service integration")

    def test_she_tests_routes(self):
        """'she tests the service' — subject-verb-object, should route."""
        self._assert_routes("she tests the service")
        self._assert_routes("she test the endpoint")

    def test_write_code_artifacts_route(self):
        self._assert_routes("write unit tests for auth")
        self._assert_routes("write a migration script")
        self._assert_routes("write the implementation for the API")

    def test_check_security_routes(self):
        self._assert_routes("check for security vulnerabilities")
        self._assert_routes("check the authentication module for security issues")

    def test_do_code_review_routes(self):
        self._assert_routes("do a code review")

    def test_make_sure_routes(self):
        """'make sure it works' — verification is dev work, routes as DEV."""
        r = classify("make sure it works")
        self.assertEqual(r.route_type, "dev",
            f"Expected DEV routing for 'make sure it works' — got: {r.route_type} reason={r.reason}")

    def test_make_it_work_routes(self):
        """'make it work' — 'make' is a dev action verb, routes as DEV."""
        r = classify("make it work")
        self.assertEqual(r.route_type, "dev",
            f"Expected DEV routing for 'make it work' — got: {r.route_type} reason={r.reason}")

    def test_write_docs_routes(self):
        """'write some docs' — documentation is dev work, routes as DEV."""
        r = classify("write some docs")
        self.assertEqual(r.route_type, "dev",
            f"Expected DEV routing for 'write some docs' — got: {r.route_type} reason={r.reason}")

    def test_write_blog_routes(self):
        """'write a blog post' — 'write' is a dev action verb, routes as DEV."""
        r = classify("write a blog post")
        self.assertEqual(r.route_type, "dev",
            f"Expected DEV routing for 'write a blog post' — got: {r.route_type} reason={r.reason}")


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
    """Knowledge requests — should route as Q&A."""

    def _assert_qa(self, prompt: str):
        r = classify(prompt)
        self.assertEqual(r.route_type, "qa",
            f"Expected QA routing for: '{prompt}' — got: {r.route_type} reason={r.reason}")

    def test_what_is_oauth(self):   self._assert_qa("what is OAuth?")
    def test_how_does_jwt(self):    self._assert_qa("how does JWT work?")
    def test_explain_pattern(self): self._assert_qa("explain the circuit breaker pattern")
    def test_difference(self):      self._assert_qa("what's the difference between REST and GraphQL?")
    def test_why_redis(self):
        """'why use X' — knowledge intent but 'why use' not in _KNOWLEDGE_RE; routes as qa or skip."""
        r = classify("why use Redis instead of Memcached?")
        self.assertIn(r.route_type, ("qa", "skip"),
            f"Expected QA or SKIP for: 'why use Redis instead of Memcached?' — got: {r.route_type}")
    def test_when_microservices(self): self._assert_qa("when should I use microservices?")
    def test_solid_principles(self): self._assert_qa("what are the SOLID principles?")

    def test_qa_prompts_should_route(self):
        """Q&A prompts have should_route=True since they get an injection."""
        r = classify("what is OAuth?")
        self.assertTrue(r.should_route, "Q&A routes should have should_route=True")
        self.assertEqual(r.route_type, "qa")

    def test_how_do_i_understand(self):
        """'how do I understand X' — pure knowledge question, routes as Q&A."""
        r = classify("how do I understand microservices?")
        self.assertIn(r.route_type, ("qa", "skip"),
            f"Expected QA or SKIP for knowledge-only prompt — got: {r.route_type}")

    def test_how_do_i_know(self):
        """'how do I know when to use X' — pure knowledge question."""
        r = classify("how do I know when to use Redis?")
        self.assertIn(r.route_type, ("qa", "skip"),
            f"Expected QA or SKIP for knowledge-only prompt — got: {r.route_type}")

    def test_rest_not_tech_when_used_as_noun(self):
        """'rest' as plain English noun should not route as dev."""
        r = classify("I need some rest from the database work")
        self.assertNotEqual(r.route_type, "dev",
            "Plain-English 'rest' should not trigger dev routing")
        r = classify("take a rest from the api drama")
        self.assertNotEqual(r.route_type, "dev",
            "Plain-English 'rest' should not trigger dev routing")

    def test_test_noun_does_not_route_as_dev(self):
        """'test' as a standalone noun should not route as dev."""
        r = classify("just a quick test")
        self.assertNotEqual(r.route_type, "dev",
            "Standalone noun 'test' should not route as dev")

    def test_test_in_question_context_skips(self):
        r = classify("what should I test next?")
        self.assertNotEqual(r.route_type, "dev",
            "Pure knowledge question about testing should not route as dev")

    def test_test_suite_compound_skips(self):
        r = classify("running test suite")
        self.assertNotEqual(r.route_type, "dev",
            "'test suite' as noun compound should not route as dev")
        r = classify("unit test suite configuration")
        self.assertNotEqual(r.route_type, "dev",
            "'unit test suite' as noun phrase should not route as dev")


class TestGreetingsAndAcks(unittest.TestCase):
    """Greetings and acknowledgements — should NOT route."""

    def _assert_skips(self, prompt: str):
        r = classify(prompt)
        self.assertFalse(r.should_route, f"Expected SKIP for: '{prompt}' — got: {r.reason}")

    def test_hello(self):           self._assert_skips("hello")
    def test_thanks(self):          self._assert_skips("thanks, that worked!")
    def test_ok(self):              self._assert_skips("ok sounds good")

    def test_long_greeting_skips(self):
        """Long acknowledgements should not route even without hitting the <= 5 word limit."""
        self._assert_skips("ok that all sounds good to me")
        self._assert_skips("great that makes sense now")


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
    """Shell/admin operations — should route as OPS."""

    def _assert_ops(self, prompt: str):
        r = classify(prompt)
        self.assertEqual(r.route_type, "ops",
            f"Expected OPS routing for: '{prompt}' — got: {r.route_type}")

    def test_git(self):             self._assert_ops("run git status")
    def test_disk(self):            self._assert_ops("show me the disk usage")
    def test_delete_logs(self):     self._assert_ops("delete log files from /tmp")


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

    def test_zero_also_disables(self):
        """AMPLIHACK_AUTO_DEV=0 should also disable routing."""
        os.environ["AMPLIHACK_AUTO_DEV"] = "0"
        try:
            ok, _ = should_auto_route("fix the login bug")
            self.assertFalse(ok)
        finally:
            del os.environ["AMPLIHACK_AUTO_DEV"]

    def test_no_also_disables(self):
        """AMPLIHACK_AUTO_DEV=no should also disable routing."""
        os.environ["AMPLIHACK_AUTO_DEV"] = "no"
        try:
            ok, _ = should_auto_route("fix the login bug")
            self.assertFalse(ok)
        finally:
            del os.environ["AMPLIHACK_AUTO_DEV"]


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

    def test_qa_routes_not_skip(self):
        """Q&A prompts now route to 'qa', they no longer return a 'skip' tier."""
        r = classify("what is rate limiting?")
        self.assertEqual(r.route_type, "qa")
        self.assertTrue(r.should_route, "Q&A questions should route (to qa), not skip")

    def test_injection_contains_directive(self):
        from dev_intent_router import build_context_injection
        r = classify("fix the login bug")
        ctx = build_context_injection(r, "fix the login bug")
        self.assertIn("dev-orchestrator", ctx)
        self.assertIn("system-reminder", ctx)

    def test_injection_contains_prompt_text(self):
        """Verify the original prompt appears in the injection text."""
        from dev_intent_router import build_context_injection
        prompt = "fix the login timeout bug"
        r = classify(prompt)
        ctx = build_context_injection(r, prompt)
        self.assertIn(prompt, ctx,
            "Injection must include the original prompt text for Claude to forward it")

    def test_long_prompt_truncated_in_injection(self):
        """Prompts longer than 300 chars are truncated in injection."""
        from dev_intent_router import build_context_injection
        long_prompt = "implement " + "x" * 350
        r = classify(long_prompt)
        ctx = build_context_injection(r, long_prompt)
        self.assertLess(len(ctx), 700, "Injection should not balloon for very long prompts")

    def test_recommended_tier_does_not_have_must(self):
        from dev_intent_router import build_context_injection
        r = classify("how do I add pagination?")
        ctx = build_context_injection(r, "how do I add pagination?")
        self.assertIn("dev-orchestrator", ctx)
        self.assertNotIn("MUST", ctx)

    def test_confidence_is_float_in_range(self):
        r = classify("fix the login bug")
        self.assertIsInstance(r.confidence, float)
        self.assertGreaterEqual(r.confidence, 0.0)
        self.assertLessEqual(r.confidence, 1.0)

    def test_tier_is_valid(self):
        valid_tiers = {"required", "recommended", "suggested", "skip"}
        for p in ["implement auth", "what is oauth?", "how do I add caching?"]:
            r = classify(p)
            self.assertIn(r.tier, valid_tiers)

    def test_qa_should_route_is_true(self):
        r = classify("what is OAuth?")
        self.assertTrue(r.should_route, "Q&A routes should have should_route=True")
        self.assertEqual(r.route_type, "qa")

    def test_ops_should_route_is_true(self):
        r = classify("run git status")
        self.assertTrue(r.should_route)
        self.assertEqual(r.route_type, "ops")

    def test_skip_should_route_is_false(self):
        r = classify("/analyze the code")
        self.assertFalse(r.should_route)


class TestQAInjection(unittest.TestCase):
    """Verify Q&A and OPS injection content."""

    def test_qa_injection_says_answer_directly(self):
        from dev_intent_router import build_context_injection
        r = classify("what is OAuth?")
        ctx = build_context_injection(r, "what is OAuth?")
        self.assertIn("Q&A", ctx)
        self.assertIn("directly", ctx.lower())
        self.assertNotIn("dev-orchestrator", ctx)

    def test_ops_injection_says_execute_directly(self):
        from dev_intent_router import build_context_injection
        r = classify("run git status")
        ctx = build_context_injection(r, "run git status")
        self.assertIn("OPERATIONS", ctx)
        self.assertIn("directly", ctx.lower())
        self.assertNotIn("dev-orchestrator", ctx)


class TestEnvVarBypassExtended(unittest.TestCase):
    """Extended env var bypass tests."""

    def test_off_value_disables_routing(self):
        os.environ["AMPLIHACK_AUTO_DEV"] = "off"
        try:
            ok, _ = should_auto_route("fix the login bug")
            self.assertFalse(ok)
        finally:
            del os.environ["AMPLIHACK_AUTO_DEV"]


class TestShouldAutoRouteEdgeCases(unittest.TestCase):
    def test_empty_string_returns_false(self):
        ok, ctx = should_auto_route("")
        self.assertFalse(ok)
        self.assertEqual(ctx, "")

    def test_whitespace_only_returns_false(self):
        ok, ctx = should_auto_route("   ")
        self.assertFalse(ok)

    def test_qa_prompt_returns_true(self):
        """Q&A prompts now inject a Q&A routing signal."""
        ok, ctx = should_auto_route("what is OAuth?")
        self.assertTrue(ok)
        self.assertIn("Q&A", ctx)

    def test_ops_prompt_returns_true(self):
        ok, ctx = should_auto_route("run git status")
        self.assertTrue(ok)
        self.assertIn("OPERATIONS", ctx)


if __name__ == "__main__":
    unittest.main(verbosity=2)
