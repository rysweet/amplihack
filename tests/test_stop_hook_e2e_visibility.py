#!/usr/bin/env python3
"""
End-to-End tests for Stop hook output visibility.

Tests Suite 6: E2E visibility validation
These tests verify that the Stop hook actually produces visible output
that Claude Code will display to the user.

CRITICAL: These tests validate the user-facing behavior.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add project paths
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack" / "hooks"))
sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack"))

from stop import StopHook


class TestStopHookE2EVisibility(unittest.TestCase):
    """
    E2E Test Suite 6: End-to-end visibility validation.

    Tests that Stop hook produces output visible to users.
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.hook = self._create_hook_with_mocked_paths()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_hook_with_mocked_paths(self):
        """Helper to create hook with mocked paths."""
        hook = StopHook()
        hook.project_root = Path(self.temp_dir)
        hook.log_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        hook.metrics_dir = Path(self.temp_dir) / ".claude" / "runtime" / "metrics"
        hook.analysis_dir = Path(self.temp_dir) / ".claude" / "runtime" / "analysis"
        hook.log_dir.mkdir(parents=True, exist_ok=True)
        hook.metrics_dir.mkdir(parents=True, exist_ok=True)
        hook.analysis_dir.mkdir(parents=True, exist_ok=True)
        hook.session_id = hook.get_session_id()
        hook.session_dir = hook.log_dir / hook.session_id
        hook.session_dir.mkdir(parents=True, exist_ok=True)
        return hook

    def _create_decisions_file(self, session_id: str, content: str):
        """Helper to create DECISIONS.md file."""
        session_dir = self.hook.log_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        decisions_file = session_dir / "DECISIONS.md"
        decisions_file.write_text(content, encoding="utf-8")
        return decisions_file

    def test_e2e_decision_records_are_visible_in_output(self):
        """
        E2E TEST: Decision records must appear in hook output.

        Simulates real user scenario:
        1. User has session with decisions
        2. User stops session
        3. Stop hook runs
        4. User sees decision records summary
        """
        # Step 1: Create session with decisions
        decisions_content = """# Session Decisions

## Decision: Implement user authentication
**What**: Add JWT-based authentication
**Why**: Secure API endpoints
**Alternatives**: OAuth, Session cookies

## Decision: Use Redis for caching
**What**: Implement Redis caching layer
**Why**: Improve response times
**Alternatives**: Memcached, In-memory cache
"""
        self._create_decisions_file(self.hook.session_id, decisions_content)

        # Step 2 & 3: Stop hook runs
        with patch.object(self.hook, "extract_learnings", return_value=[]):
            with patch.object(self.hook, "save_session_analysis"):
                input_data = {
                    "messages": [{"role": "user", "content": "session messages"}],
                    "session_id": self.hook.session_id,
                }

                result = self.hook.process(input_data)

        # Step 4: Verify user sees decision records
        self.assertIn("message", result, "Output must have message field for visibility")

        message = result["message"]
        self.assertIsInstance(message, str, "Message must be string")
        self.assertGreater(len(message), 0, "Message must not be empty")

        # Verify decision content is visible
        self.assertIn("Decision Records Summary", message, "Summary header must be visible")
        self.assertIn("Total Decisions: 2", message, "Decision count must be visible")
        self.assertIn("user authentication", message, "Decision preview must be visible")

    def test_e2e_output_displays_when_stopping_session(self):
        """
        E2E TEST: Output is properly formatted for display at session stop.

        Verifies output structure matches Claude Code's expectations.
        """
        decisions_content = "## Decision: Critical decision\n"
        self._create_decisions_file(self.hook.session_id, decisions_content)

        with patch.object(self.hook, "extract_learnings", return_value=[]):
            with patch.object(self.hook, "save_session_analysis"):
                input_data = {
                    "messages": [{"role": "user", "content": "test"}],
                    "session_id": self.hook.session_id,
                }

                result = self.hook.process(input_data)

        # Claude Code expects dict output with "message" field
        self.assertIsInstance(result, dict, "Output must be dict")
        self.assertIn("message", result, "Output must have 'message' field")

        # Message should be ready for display (non-empty string)
        self.assertIsInstance(result["message"], str)
        self.assertGreater(len(result["message"]), 0)

    def test_e2e_hook_output_serializes_to_json_for_stdout(self):
        """
        E2E TEST: Hook output must serialize to JSON for stdout.

        Claude Code hooks communicate via JSON on stdout.
        """
        decisions_content = "## Decision: Test\n"
        self._create_decisions_file(self.hook.session_id, decisions_content)

        with patch.object(self.hook, "extract_learnings", return_value=[]):
            with patch.object(self.hook, "save_session_analysis"):
                input_data = {
                    "messages": [{"role": "user", "content": "test"}],
                    "session_id": self.hook.session_id,
                }

                result = self.hook.process(input_data)

        # Should serialize to JSON without error
        try:
            json_output = json.dumps(result)
            self.assertIsInstance(json_output, str)

            # Should be parseable back to dict
            parsed = json.loads(json_output)
            self.assertEqual(parsed, result)
        except (TypeError, ValueError) as e:
            self.fail(f"Hook output failed JSON serialization: {e}")

    def test_e2e_decision_file_link_is_clickable(self):
        """
        E2E TEST: Decision file link should be formatted as file:// URL.

        Users should be able to click the link to open the file.
        """
        decisions_content = "## Decision: Check this out\n"
        decisions_file = self._create_decisions_file(self.hook.session_id, decisions_content)

        summary = self.hook.display_decision_summary(self.hook.session_id)

        # Should contain file:// URL
        expected_url = f"file://{decisions_file.resolve()}"
        self.assertIn(expected_url, summary, "Summary should contain clickable file:// URL")

    def test_e2e_no_output_when_no_content_to_display(self):
        """
        E2E TEST: Hook should return empty dict when nothing to display.

        Avoids cluttering output with empty messages.
        """
        # No decisions file, no learnings
        with patch.object(self.hook, "extract_learnings", return_value=[]):
            with patch.object(self.hook, "save_session_analysis"):
                input_data = {
                    "messages": [{"role": "user", "content": "test"}],
                    "session_id": self.hook.session_id,
                }

                result = self.hook.process(input_data)

        # When nothing to display, should return empty dict
        self.assertEqual(result, {}, "Should return empty dict when no content")


class TestStopHookE2EMultipleScenarios(unittest.TestCase):
    """
    E2E tests for various real-world scenarios.
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.hook = self._create_hook_with_mocked_paths()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_hook_with_mocked_paths(self):
        """Helper to create hook with mocked paths."""
        hook = StopHook()
        hook.project_root = Path(self.temp_dir)
        hook.log_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        hook.metrics_dir = Path(self.temp_dir) / ".claude" / "runtime" / "metrics"
        hook.analysis_dir = Path(self.temp_dir) / ".claude" / "runtime" / "analysis"
        hook.log_dir.mkdir(parents=True, exist_ok=True)
        hook.metrics_dir.mkdir(parents=True, exist_ok=True)
        hook.analysis_dir.mkdir(parents=True, exist_ok=True)
        hook.session_id = hook.get_session_id()
        hook.session_dir = hook.log_dir / hook.session_id
        hook.session_dir.mkdir(parents=True, exist_ok=True)
        return hook

    def _create_decisions_file(self, session_id: str, content: str):
        """Helper to create DECISIONS.md file."""
        session_dir = self.hook.log_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        decisions_file = session_dir / "DECISIONS.md"
        decisions_file.write_text(content, encoding="utf-8")
        return decisions_file

    def test_e2e_scenario_developer_makes_decisions_during_session(self):
        """
        E2E SCENARIO: Developer makes architectural decisions during coding.

        Real workflow:
        1. Developer discusses architecture with Claude
        2. Decisions are recorded in DECISIONS.md
        3. Session ends
        4. Developer sees summary of decisions made
        """
        # Simulate decisions made during session
        decisions_content = """# Session Decisions

## Decision: Split monolith into microservices
**What**: Decompose monolithic app into separate services
**Why**: Improve scalability and maintainability
**Alternatives**: Keep monolith, Use modular monolith

## Decision: Use Kubernetes for orchestration
**What**: Deploy services on Kubernetes cluster
**Why**: Better container orchestration and scaling
**Alternatives**: Docker Swarm, ECS

## Decision: Implement event-driven architecture
**What**: Use message queue for service communication
**Why**: Loose coupling and better resilience
**Alternatives**: REST APIs, gRPC
"""
        self._create_decisions_file(self.hook.session_id, decisions_content)

        # Session ends
        with patch.object(self.hook, "extract_learnings", return_value=[]):
            with patch.object(self.hook, "save_session_analysis"):
                input_data = {
                    "messages": [
                        {"role": "user", "content": "Let's discuss architecture"},
                        {"role": "assistant", "content": "I suggest microservices..."},
                    ],
                    "session_id": self.hook.session_id,
                }

                result = self.hook.process(input_data)

        # Developer sees summary
        self.assertIn("message", result)
        message = result["message"]

        # Verify all 3 decisions are visible
        self.assertIn("Total Decisions: 3", message)
        self.assertIn("microservices", message)
        self.assertIn("Kubernetes", message)
        self.assertIn("event-driven", message)

    @unittest.skip("Test requires extract_learnings and learnings display - reflection disabled")
    def test_e2e_scenario_no_decisions_but_has_learnings(self):
        """
        E2E SCENARIO: Session has learnings but no explicit decisions.

        Should display learnings recommendations, no decision summary.
        """
        # No decisions file created

        mock_learnings = [
            {
                "type": "error_handling",
                "priority": "high",
                "suggestion": "Add try-catch blocks around API calls",
            },
            {"type": "performance", "priority": "medium", "suggestion": "Cache database queries"},
        ]

        with patch.object(self.hook, "extract_learnings", return_value=mock_learnings):
            with patch.object(self.hook, "save_session_analysis"):
                input_data = {
                    "messages": [{"role": "user", "content": "found some issues"}],
                    "session_id": self.hook.session_id,
                }

                result = self.hook.process(input_data)

        # Should have message with learnings
        self.assertIn("message", result)
        message = result["message"]

        # Should contain learning recommendations
        self.assertIn("Improvement Recommendations", message)
        self.assertIn("error_handling", message)

        # Should NOT contain decision summary (no decisions)
        self.assertNotIn("Decision Records Summary", message)

    def test_e2e_scenario_empty_session_no_content(self):
        """
        E2E SCENARIO: Short session with no meaningful content.

        Should not clutter output with empty summaries.
        """
        # No decisions, no learnings, minimal messages
        with patch.object(self.hook, "extract_learnings", return_value=[]):
            with patch.object(self.hook, "save_session_analysis"):
                input_data = {
                    "messages": [{"role": "user", "content": "hello"}],
                    "session_id": self.hook.session_id,
                }

                result = self.hook.process(input_data)

        # Should return empty dict (nothing to display)
        self.assertEqual(result, {})


class TestStopHookE2ERegressionPrevention(unittest.TestCase):
    """
    E2E regression tests for the specific bugs we fixed.

    These tests MUST continue to pass to prevent regression.
    """

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.hook = self._create_hook_with_mocked_paths()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_hook_with_mocked_paths(self):
        """Helper to create hook with mocked paths."""
        hook = StopHook()
        hook.project_root = Path(self.temp_dir)
        hook.log_dir = Path(self.temp_dir) / ".claude" / "runtime" / "logs"
        hook.metrics_dir = Path(self.temp_dir) / ".claude" / "runtime" / "metrics"
        hook.analysis_dir = Path(self.temp_dir) / ".claude" / "runtime" / "analysis"
        hook.log_dir.mkdir(parents=True, exist_ok=True)
        hook.metrics_dir.mkdir(parents=True, exist_ok=True)
        hook.analysis_dir.mkdir(parents=True, exist_ok=True)
        hook.session_id = hook.get_session_id()
        hook.session_dir = hook.log_dir / hook.session_id
        hook.session_dir.mkdir(parents=True, exist_ok=True)
        return hook

    def _create_decisions_file(self, session_id: str, content: str):
        """Helper to create DECISIONS.md file."""
        session_dir = self.hook.log_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        decisions_file = session_dir / "DECISIONS.md"
        decisions_file.write_text(content, encoding="utf-8")
        return decisions_file

    def test_regression_bug_decision_summary_unreachable_when_learnings_empty(self):
        """
        REGRESSION TEST: Bug where decision_summary was unreachable.

        Before fix (lines 664-704):
        ```python
        if learnings:
            output = {...}
            # ... recommendations code ...
            decision_summary = self.display_decision_summary(session_id)  # LINE 709
            # UNREACHABLE when learnings is empty!
        ```

        After fix (lines 706-715):
        ```python
        # CRITICAL FIX: Display decision summary OUTSIDE learnings block
        decision_summary = self.display_decision_summary(session_id)
        if decision_summary:
            output["message"] = existing_msg + decision_summary
        ```

        This test MUST pass to prevent regression.
        """
        # Setup: Create decisions, ensure learnings is empty
        decisions_content = "## Decision: Regression test decision\n"
        self._create_decisions_file(self.hook.session_id, decisions_content)

        # Execute: Run with empty learnings
        with patch.object(self.hook, "extract_learnings", return_value=[]):
            with patch.object(self.hook, "save_session_analysis"):
                input_data = {
                    "messages": [{"role": "user", "content": "test"}],
                    "session_id": self.hook.session_id,
                }

                result = self.hook.process(input_data)

        # Verify: Decision summary is visible (bug was: returned empty dict)
        self.assertNotEqual(result, {}, "BUG REGRESSION: Returned empty dict")
        self.assertIn("message", result, "BUG REGRESSION: No message field")
        self.assertIn(
            "Regression test decision", result["message"], "BUG REGRESSION: Decision not visible"
        )

    def test_regression_bug_reflection_import_error(self):
        """
        REGRESSION TEST: Bug where reflection module imports failed.

        Before fix:
        - reflection/__init__.py imported non-existent functions
        - Caused ImportError when stop.py tried to import

        After fix:
        - Only imports functions that actually exist
        - No ImportError

        This test MUST pass to prevent regression.
        """
        # This should not raise ImportError
        try:
            # Simulate stop.py's import pattern
            sys.path.insert(0, str(project_root / ".claude" / "tools" / "amplihack" / "reflection"))
            from reflection import analyze_session_patterns  # noqa: F401
        except ImportError as e:
            self.fail(f"BUG REGRESSION: ImportError in reflection module: {e}")

    def test_regression_bug_output_dict_not_initialized(self):
        """
        REGRESSION TEST: Bug where output dict not initialized before use.

        Before fix:
        - output dict only created inside "if learnings:" block
        - Accessing output["message"] raised KeyError when learnings empty

        After fix:
        - output dict initialized early
        - Can safely access output["message"]

        This test MUST pass to prevent regression.
        """
        decisions_content = "## Decision: Test\n"
        self._create_decisions_file(self.hook.session_id, decisions_content)

        with patch.object(self.hook, "extract_learnings", return_value=[]):
            with patch.object(self.hook, "save_session_analysis"):
                input_data = {
                    "messages": [{"role": "user", "content": "test"}],
                    "session_id": self.hook.session_id,
                }

                # Should not raise KeyError or AttributeError
                try:
                    result = self.hook.process(input_data)
                except (KeyError, AttributeError) as e:
                    self.fail(f"BUG REGRESSION: {type(e).__name__}: {e}")

                # Verify result is valid
                self.assertIsInstance(result, dict)
                self.assertIn("message", result)


if __name__ == "__main__":
    unittest.main()
