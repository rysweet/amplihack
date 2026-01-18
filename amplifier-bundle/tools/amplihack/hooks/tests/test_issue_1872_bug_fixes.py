#!/usr/bin/env python3
"""
Failing tests for Issue #1872 power steering bug fixes.

These tests verify the four bug fixes:
1. Math Display Bug - Summary shows correct count format
2. SDK Error Visibility - SDK exceptions logged to stderr
3. Failure Reason Extraction - analyze_consideration returns tuple with reason
4. Final Guidance Generation - generate_final_guidance() function works

All tests MUST fail before implementation.
"""

import asyncio
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import (
    CheckerResult,
    ConsiderationAnalysis,
    PowerSteeringChecker,
)


class TestBug1MathDisplay(unittest.TestCase):
    """Tests for Bug #1: Math display in summary.

    Bug: Summary says "(0 passed, 0 failed)" when skipped checks exist.
    Fix: Summary should be "(X passed, Y failed, Z skipped)" where X+Y+Z=total.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create directory structure
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )

        # Create minimal config
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {
            "enabled": True,
            "version": "1.0.0",
            "phase": 1,
        }
        config_path.write_text(json.dumps(config, indent=2))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_summary_includes_skipped_count(self):
        """Test that summary includes skipped count in format (X passed, Y failed, Z skipped)."""
        # Create analysis with mixed results
        analysis = ConsiderationAnalysis()

        # 2 passed
        analysis.add_result(
            CheckerResult(
                consideration_id="check_0",
                satisfied=True,
                reason="Passed",
                severity="blocker",
            )
        )
        analysis.add_result(
            CheckerResult(
                consideration_id="check_1",
                satisfied=True,
                reason="Passed",
                severity="blocker",
            )
        )

        # 1 failed
        analysis.add_result(
            CheckerResult(
                consideration_id="check_2",
                satisfied=False,
                reason="Failed",
                severity="blocker",
            )
        )

        # Simulate 22 total considerations (2 passed + 1 failed + 19 skipped)
        self.checker.considerations = [{"id": f"check_{i}", "category": "Test"} for i in range(22)]

        # Generate summary
        results_text = self.checker._format_results_text(analysis, "DEVELOPMENT")

        # Verify format includes all three counts
        self.assertIn("2 passed", results_text, "Should show passed count")
        self.assertIn("1 failed", results_text, "Should show failed count")
        self.assertIn("19 skipped", results_text, "Should show skipped count")

    def test_summary_math_totals_correctly(self):
        """Test that X + Y + Z = total considerations."""
        # Create analysis with known counts
        analysis = ConsiderationAnalysis()

        # 5 passed (use first 5 consideration IDs)
        for i in range(5):
            analysis.add_result(
                CheckerResult(
                    consideration_id=f"consideration_{i}",
                    satisfied=True,
                    reason="Passed",
                    severity="blocker",
                )
            )

        # 3 failed (use next 3 consideration IDs)
        for i in range(5, 8):
            analysis.add_result(
                CheckerResult(
                    consideration_id=f"consideration_{i}",
                    satisfied=False,
                    reason="Failed",
                    severity="blocker",
                )
            )

        # 22 total considerations (5 + 3 + 14 skipped)
        self.checker.considerations = [
            {"id": f"consideration_{i}", "category": "Test"} for i in range(22)
        ]

        results_text = self.checker._format_results_text(analysis, "DEVELOPMENT")

        # Extract counts from text
        import re

        passed_match = re.search(r"(\d+)\s+passed", results_text)
        failed_match = re.search(r"(\d+)\s+failed", results_text)
        skipped_match = re.search(r"(\d+)\s+skipped", results_text)

        self.assertIsNotNone(passed_match, "Should show passed count")
        self.assertIsNotNone(failed_match, "Should show failed count")
        self.assertIsNotNone(skipped_match, "Should show skipped count")

        passed = int(passed_match.group(1))
        failed = int(failed_match.group(1))
        skipped = int(skipped_match.group(1))

        # Verify math: X + Y + Z = 22
        self.assertEqual(passed + failed + skipped, 22, "Sum should equal total considerations")
        self.assertEqual(passed, 5, "Should have 5 passed")
        self.assertEqual(failed, 3, "Should have 3 failed")
        self.assertEqual(skipped, 14, "Should have 14 skipped")

    def test_summary_format_with_parentheses(self):
        """Test that summary uses format (X passed, Y failed, Z skipped) with parentheses."""
        analysis = ConsiderationAnalysis()

        # 1 passed, 1 failed
        analysis.add_result(
            CheckerResult(
                consideration_id="c0",
                satisfied=True,
                reason="Passed",
                severity="blocker",
            )
        )
        analysis.add_result(
            CheckerResult(
                consideration_id="c1",
                satisfied=False,
                reason="Failed",
                severity="blocker",
            )
        )

        # 22 total (1 + 1 + 20 skipped)
        self.checker.considerations = [{"id": f"c{i}", "category": "T"} for i in range(22)]

        results_text = self.checker._format_results_text(analysis, "DEVELOPMENT")

        # Should contain format: (1 passed, 1 failed, 20 skipped)

        pattern = r"\(\s*1\s+passed\s*,\s*1\s+failed\s*,\s*20\s+skipped\s*\)"
        self.assertRegex(
            results_text,
            pattern,
            "Should have format (X passed, Y failed, Z skipped)",
        )


class TestBug2SDKErrorVisibility(unittest.TestCase):
    """Tests for Bug #2: SDK error visibility.

    Bug: SDK exceptions swallowed silently, hard to debug.
    Fix: Log SDK errors to stderr with consideration ID and fail-open behavior.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create directory structure
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )

        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {"enabled": True, "version": "1.0.0", "phase": 1}
        config_path.write_text(json.dumps(config, indent=2))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("power_steering_checker.SDK_AVAILABLE", True)
    @patch("power_steering_checker.analyze_consideration")
    def test_sdk_exception_logged_to_stderr(self, mock_analyze, mock_stderr):
        """Test that SDK exceptions are logged to stderr with consideration ID."""

        # Make SDK raise exception
        async def failing_analyze(*args, **kwargs):
            raise RuntimeError("SDK connection timeout")

        mock_analyze.side_effect = failing_analyze

        checker = PowerSteeringChecker(self.project_root)

        consideration = {
            "id": "test_check",
            "question": "Test question?",
            "category": "Test",
            "severity": "blocker",
        }

        transcript = [
            {"type": "user", "message": {"content": "test"}},
        ]

        # Run checker (should log error but not crash)
        try:
            asyncio.run(
                checker._check_single_consideration_async(consideration, transcript, "test_session")
            )
        except Exception:
            pass  # Expected to fail-open

        stderr_output = mock_stderr.getvalue()

        # Verify error was logged to stderr
        self.assertIn("[Power Steering SDK Error]", stderr_output, "Should have error prefix")
        self.assertIn("test_check", stderr_output, "Should include consideration ID")
        self.assertIn("SDK connection timeout", stderr_output, "Should include error message")

    @patch("sys.stderr", new_callable=io.StringIO)
    @patch("power_steering_checker.SDK_AVAILABLE", True)
    @patch("power_steering_checker.analyze_consideration")
    def test_sdk_error_log_format(self, mock_analyze, mock_stderr):
        """Test that SDK error log has correct format: [Power Steering SDK Error] {id}: {error}."""

        async def failing_analyze(*args, **kwargs):
            raise ValueError("Invalid consideration format")

        mock_analyze.side_effect = failing_analyze

        checker = PowerSteeringChecker(self.project_root)

        consideration = {
            "id": "philosophy_check",
            "question": "Philosophy compliance?",
            "category": "Quality",
            "severity": "warning",
        }

        transcript = []

        try:
            asyncio.run(
                checker._check_single_consideration_async(consideration, transcript, "session_123")
            )
        except Exception:
            pass

        stderr_output = mock_stderr.getvalue()

        # Verify format
        self.assertRegex(
            stderr_output,
            r"\[Power Steering SDK Error\]\s+philosophy_check:",
            "Should match format: [Power Steering SDK Error] {id}:",
        )

    @patch("power_steering_checker.SDK_AVAILABLE", True)
    @patch("power_steering_checker.analyze_consideration")
    def test_sdk_error_fails_open_returns_true(self, mock_analyze):
        """Test that SDK errors fail-open (return True/satisfied)."""

        async def failing_analyze(*args, **kwargs):
            raise Exception("Network error")

        mock_analyze.side_effect = failing_analyze

        checker = PowerSteeringChecker(self.project_root)

        consideration = {
            "id": "test_check",
            "question": "Test?",
            "category": "Test",
            "severity": "blocker",
        }

        transcript = []

        # Should not raise, should return satisfied=True
        result = asyncio.run(
            checker._check_single_consideration_async(consideration, transcript, "test_session")
        )

        self.assertIsNotNone(result, "Should return a result")
        self.assertTrue(result.satisfied, "Should fail-open with satisfied=True")


class TestBug3FailureReasonExtraction(unittest.TestCase):
    """Tests for Bug #3: Failure reason extraction.

    Bug: analyze_consideration() returns bool, no reason string.
    Fix: Return Tuple[bool, Optional[str]] with reason when check fails.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", True)
    @patch("claude_power_steering.query")
    def test_analyze_consideration_returns_tuple(self, mock_query):
        """Test that analyze_consideration returns Tuple[bool, Optional[str]]."""
        # Import here to get patched version
        from claude_power_steering import analyze_consideration

        # Mock SDK response with NOT SATISFIED
        async def mock_response(*args, **kwargs):
            class MockMessage:
                def __init__(self, text):
                    self.text = text

            yield MockMessage("NOT SATISFIED: Missing tests")

        mock_query.return_value = mock_response()

        consideration = {
            "id": "test_check",
            "question": "Were tests run?",
            "description": "Check for test execution",
            "category": "Testing",
        }

        conversation = [{"type": "user", "message": {"content": "Fix the bug"}}]

        # Run async function
        result = asyncio.run(analyze_consideration(conversation, consideration, self.project_root))

        # Verify return type is tuple
        self.assertIsInstance(result, tuple, "Should return tuple")
        self.assertEqual(len(result), 2, "Should return 2-element tuple")

        satisfied, reason = result
        self.assertIsInstance(satisfied, bool, "First element should be bool")
        self.assertIsInstance(reason, (str, type(None)), "Second element should be str or None")

    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", True)
    @patch("claude_power_steering.query")
    def test_reason_extracted_when_check_fails(self, mock_query):
        """Test that reason is extracted when check fails."""
        from claude_power_steering import analyze_consideration

        async def mock_response(*args, **kwargs):
            class MockMessage:
                text = "NOT SATISFIED: TodoWrite shows 3 incomplete tasks"

            yield MockMessage()

        mock_query.return_value = mock_response()

        consideration = {
            "id": "todos_complete",
            "question": "Were all TODOs completed?",
            "description": "Check TodoWrite",
            "category": "Completion",
        }

        conversation = []

        satisfied, reason = asyncio.run(
            analyze_consideration(conversation, consideration, self.project_root)
        )

        self.assertFalse(satisfied, "Should be not satisfied")
        self.assertIsNotNone(reason, "Reason should not be None when check fails")
        self.assertIn("incomplete", reason.lower(), "Reason should mention incomplete tasks")

    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", True)
    @patch("claude_power_steering.query")
    def test_reason_truncated_to_200_chars(self, mock_query):
        """Test that reason is truncated to 200 characters."""
        from claude_power_steering import analyze_consideration

        long_reason = "NOT SATISFIED: " + ("A" * 300)  # 313 chars total

        async def mock_response(*args, **kwargs):
            class MockMessage:
                text = long_reason

            yield MockMessage()

        mock_query.return_value = mock_response()

        consideration = {
            "id": "test_check",
            "question": "Test?",
            "category": "Test",
        }

        conversation = []

        satisfied, reason = asyncio.run(
            analyze_consideration(conversation, consideration, self.project_root)
        )

        self.assertFalse(satisfied)
        self.assertIsNotNone(reason)
        self.assertLessEqual(len(reason), 200, "Reason should be truncated to 200 chars")

    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", True)
    @patch("claude_power_steering.query")
    def test_reason_none_when_check_passes(self, mock_query):
        """Test that reason is None when check passes."""
        from claude_power_steering import analyze_consideration

        async def mock_response(*args, **kwargs):
            class MockMessage:
                text = "SATISFIED: All tests passed successfully"

            yield MockMessage()

        mock_query.return_value = mock_response()

        consideration = {
            "id": "local_testing",
            "question": "Were tests run?",
            "category": "Testing",
        }

        conversation = []

        satisfied, reason = asyncio.run(
            analyze_consideration(conversation, consideration, self.project_root)
        )

        self.assertTrue(satisfied, "Should be satisfied")
        self.assertIsNone(reason, "Reason should be None when check passes")


class TestBug4FinalGuidanceGeneration(unittest.TestCase):
    """Tests for Bug #4: Final guidance generation.

    Bug: No function to generate final guidance using SDK.
    Fix: Add generate_final_guidance() function with SDK integration.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_generate_final_guidance_function_exists(self):
        """Test that generate_final_guidance() function exists in claude_power_steering."""
        try:
            from claude_power_steering import generate_final_guidance

            self.assertTrue(callable(generate_final_guidance), "Should be callable")
        except ImportError:
            self.fail("generate_final_guidance function should exist")

    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", True)
    @patch("claude_power_steering.query")
    def test_generate_final_guidance_calls_sdk(self, mock_query):
        """Test that generate_final_guidance calls SDK with failed checks and reasons."""
        from claude_power_steering import generate_final_guidance

        # Mock SDK response
        async def mock_response(*args, **kwargs):
            class MockMessage:
                text = "Complete the remaining TODOs and run tests locally."

            yield MockMessage()

        mock_query.return_value = mock_response()

        failed_checks = [
            ("todos_complete", "3 tasks remain incomplete"),
            ("local_testing", "No test execution found"),
        ]

        conversation = []

        guidance = asyncio.run(
            generate_final_guidance(failed_checks, conversation, self.project_root)
        )

        # Verify SDK was called
        self.assertTrue(mock_query.called, "SDK query should be called")
        self.assertIsInstance(guidance, str, "Should return string")
        self.assertGreater(len(guidance), 0, "Guidance should not be empty")

    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", True)
    @patch("claude_power_steering.query")
    def test_generate_final_guidance_includes_failure_context(self, mock_query):
        """Test that generate_final_guidance includes actual failure context in prompt."""
        from claude_power_steering import generate_final_guidance

        async def mock_response(*args, **kwargs):
            class MockMessage:
                text = "Fix the failing checks"

            yield MockMessage()

        mock_query.return_value = mock_response()

        failed_checks = [
            ("ci_status", "CI checks failing on test_module.py"),
        ]

        conversation = []

        asyncio.run(generate_final_guidance(failed_checks, conversation, self.project_root))

        # Verify the prompt passed to SDK includes the failure info
        call_args = mock_query.call_args
        prompt = call_args[1]["prompt"]  # Get keyword argument 'prompt'

        self.assertIn("ci_status", prompt, "Prompt should include check ID")
        self.assertIn("failing", prompt.lower(), "Prompt should include failure reason")

    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", False)
    def test_generate_final_guidance_fallback_when_sdk_unavailable(self):
        """Test that generate_final_guidance uses template fallback when SDK unavailable."""
        from claude_power_steering import generate_final_guidance

        failed_checks = [
            ("todos_complete", "2 tasks incomplete"),
            ("local_testing", "No tests run"),
        ]

        conversation = []

        guidance = asyncio.run(
            generate_final_guidance(failed_checks, conversation, self.project_root)
        )

        # Should still return guidance (template-based)
        self.assertIsInstance(guidance, str, "Should return string even without SDK")
        self.assertGreater(len(guidance), 0, "Should have fallback guidance")

        # Template should mention the checks
        self.assertIn("todos_complete", guidance, "Should mention failed check")
        self.assertIn("local_testing", guidance, "Should mention failed check")

    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", True)
    @patch("claude_power_steering.query")
    def test_generate_final_guidance_is_specific_not_generic(self, mock_query):
        """Test that guidance is specific to actual failures, not generic advice."""
        from claude_power_steering import generate_final_guidance

        async def mock_response(*args, **kwargs):
            class MockMessage:
                text = "You need to complete the 3 incomplete TODOs and run pytest locally."

            yield MockMessage()

        mock_query.return_value = mock_response()

        failed_checks = [
            ("todos_complete", "3 incomplete tasks"),
            ("local_testing", "pytest not run"),
        ]

        conversation = []

        guidance = asyncio.run(
            generate_final_guidance(failed_checks, conversation, self.project_root)
        )

        # Guidance should be specific, not generic
        self.assertIn("3", guidance, "Should mention specific number from failure reason")
        self.assertIn("pytest", guidance.lower(), "Should mention specific tool from reason")

    @patch("claude_power_steering.CLAUDE_SDK_AVAILABLE", True)
    @patch("claude_power_steering.query")
    def test_generate_final_guidance_sdk_failure_uses_template(self, mock_query):
        """Test that SDK failure falls back to template guidance."""
        from claude_power_steering import generate_final_guidance

        # Make SDK raise exception
        async def failing_response(*args, **kwargs):
            raise RuntimeError("SDK timeout")

        mock_query.side_effect = failing_response

        failed_checks = [
            ("ci_status", "CI failing"),
        ]

        conversation = []

        guidance = asyncio.run(
            generate_final_guidance(failed_checks, conversation, self.project_root)
        )

        # Should fall back to template
        self.assertIsInstance(guidance, str, "Should return string")
        self.assertGreater(len(guidance), 0, "Should have fallback guidance")
        self.assertIn("ci_status", guidance, "Template should mention failed check")


class TestBug3Integration(unittest.TestCase):
    """Integration tests for Bug #3: Failure reason extraction at call site.

    Tests the single call site update at line 2037 in power_steering_checker.py.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )

        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {"enabled": True, "version": "1.0.0", "phase": 1}
        config_path.write_text(json.dumps(config, indent=2))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    @patch("power_steering_checker.SDK_AVAILABLE", True)
    @patch("power_steering_checker.analyze_consideration")
    def test_call_site_unpacks_tuple_correctly(self, mock_analyze):
        """Test that call site at line 2037 correctly unpacks (bool, str) tuple."""

        # Mock SDK to return tuple
        async def mock_analyze_tuple(*args, **kwargs):
            return (False, "Tests were not executed")

        mock_analyze.side_effect = mock_analyze_tuple

        checker = PowerSteeringChecker(self.project_root)

        consideration = {
            "id": "local_testing",
            "question": "Were tests run?",
            "category": "Testing",
            "severity": "blocker",
        }

        transcript = []

        # Should not crash when unpacking tuple
        result = asyncio.run(
            checker._check_single_consideration_async(consideration, transcript, "test_session")
        )

        self.assertIsNotNone(result, "Should return result")
        self.assertFalse(result.satisfied, "Should capture satisfied=False")
        self.assertIn("not executed", result.reason, "Should capture reason string")

    @patch("power_steering_checker.SDK_AVAILABLE", True)
    @patch("power_steering_checker.analyze_consideration")
    def test_call_site_handles_none_reason(self, mock_analyze):
        """Test that call site handles None reason when check passes."""

        async def mock_analyze_tuple(*args, **kwargs):
            return (True, None)

        mock_analyze.side_effect = mock_analyze_tuple

        checker = PowerSteeringChecker(self.project_root)

        consideration = {
            "id": "ci_status",
            "question": "Is CI passing?",
            "category": "CI",
            "severity": "blocker",
        }

        transcript = []

        result = asyncio.run(
            checker._check_single_consideration_async(consideration, transcript, "test_session")
        )

        self.assertTrue(result.satisfied, "Should be satisfied")
        # Reason should use default when None returned
        self.assertIsInstance(result.reason, str, "Should have string reason even when None")


if __name__ == "__main__":
    unittest.main()
