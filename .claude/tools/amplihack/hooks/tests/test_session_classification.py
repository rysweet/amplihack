#!/usr/bin/env python3
"""
Failing tests for Power Steering Session Classification (Issue #1492).

Tests session type detection and selective consideration application
to prevent false positives for non-development sessions.

Session Types:
1. DEVELOPMENT - Full workflow (PR, CI/CD, testing, reviews)
2. INFORMATIONAL - Q&A, help, capability queries
3. MAINTENANCE - Cleanup, docs, config updates
4. INVESTIGATION - Research, exploration, analysis

Test-Driven Development:
- All tests written to FAIL initially
- Tests define expected behavior
- Implementation will make tests pass
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


class TestSessionClassification(unittest.TestCase):
    """Tests for session type classification."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create directory structure
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True, exist_ok=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )

        # Create default config
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {
            "enabled": True,
            "version": "2.1.0",
            "phase": 2,
        }
        config_path.write_text(json.dumps(config, indent=2))

        # Initialize checker
        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    # ========================================================================
    # Session Type Detection Tests
    # ========================================================================

    def test_detect_development_session_with_pr_and_ci(self):
        """DEVELOPMENT: PR creation + code changes + tests + CI checks."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Add authentication feature to the API"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "src/auth.py"},
                        },
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "pytest tests/test_auth.py"},
                        },
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "gh pr create --title 'Add auth'"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "DEVELOPMENT")

    def test_detect_informational_session_qa_only(self):
        """INFORMATIONAL: Q&A with no tool usage."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "What skills do you have available?"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "I have the following skills: analyzer, builder...",
                        },
                    ]
                },
            },
            {
                "type": "user",
                "message": {"content": "What slash commands are available?"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Available commands: /ultrathink, /analyze...",
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INFORMATIONAL")

    def test_detect_maintenance_session_docs_and_config(self):
        """MAINTENANCE: Documentation and configuration updates only."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Update README with new installation instructions"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Edit", "input": {"file_path": "README.md"}},
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": ".github/workflows/ci.yml"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "MAINTENANCE")

    def test_detect_investigation_session_read_only(self):
        """INVESTIGATION: Read-only exploration with analysis."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Investigate why authentication is failing"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "src/auth.py"}},
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Grep", "input": {"pattern": "auth_token"}},
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "git log --grep='auth' -5"},
                        },
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Analysis complete: The issue is in token validation...",
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_detect_development_session_without_pr(self):
        """DEVELOPMENT: Code changes and tests but no PR yet."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Fix the login bug"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": "src/login.py"},
                        },
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "pytest tests/test_login.py"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "DEVELOPMENT")

    def test_detect_informational_session_with_read_tools(self):
        """INFORMATIONAL: Q&A with Read tools but no modifications."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "What does the auth module do?"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "src/auth.py"}},
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "The auth module provides JWT token validation...",
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INFORMATIONAL")

    # ========================================================================
    # Selective Consideration Application Tests
    # ========================================================================

    def test_informational_session_skips_pr_checks(self):
        """INFORMATIONAL: Should skip all PR-related considerations."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Explain how this works"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Here's how it works..."},
                    ]
                },
            },
        ]

        # Save transcript
        transcript_path = self.project_root / "transcript.jsonl"
        with open(transcript_path, "w") as f:
            for msg in transcript:
                f.write(json.dumps(msg) + "\n")

        result = self.checker.check(transcript_path, "test_session")

        # Should approve without checking PR considerations
        self.assertEqual(result.decision, "approve")

        # Verify PR checks were not applied
        analysis = self.checker._analyze_considerations(transcript, "test_session")
        pr_checks = [
            "unrelated_changes",
            "root_pollution",
            "pr_description",
            "review_responses",
        ]

        for check_id in pr_checks:
            if check_id in analysis.results:
                # If checked, should be satisfied (not blocking)
                self.assertTrue(analysis.results[check_id].satisfied)

    def test_informational_session_skips_ci_checks(self):
        """INFORMATIONAL: Should skip CI/CD considerations."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "What's the current project status?"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Current status: 5 open issues..."},
                    ]
                },
            },
        ]

        transcript_path = self.project_root / "transcript.jsonl"
        with open(transcript_path, "w") as f:
            for msg in transcript:
                f.write(json.dumps(msg) + "\n")

        result = self.checker.check(transcript_path, "test_session")

        # Should approve without CI checks
        self.assertEqual(result.decision, "approve")

        analysis = self.checker._analyze_considerations(transcript, "test_session")
        ci_checks = ["ci_status", "branch_rebase", "ci_precommit_mismatch"]

        for check_id in ci_checks:
            if check_id in analysis.results:
                self.assertTrue(analysis.results[check_id].satisfied)

    def test_informational_session_skips_testing_checks(self):
        """INFORMATIONAL: Should skip testing considerations."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Show me the test coverage"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Current test coverage is 85%..."},
                    ]
                },
            },
        ]

        transcript_path = self.project_root / "transcript.jsonl"
        with open(transcript_path, "w") as f:
            for msg in transcript:
                f.write(json.dumps(msg) + "\n")

        result = self.checker.check(transcript_path, "test_session")
        self.assertEqual(result.decision, "approve")

        analysis = self.checker._analyze_considerations(transcript, "test_session")
        test_checks = ["local_testing", "interactive_testing"]

        for check_id in test_checks:
            if check_id in analysis.results:
                self.assertTrue(analysis.results[check_id].satisfied)

    def test_development_session_applies_all_checks(self):
        """DEVELOPMENT: Should apply full workflow checks."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Add feature X"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Write", "input": {"file_path": "src/new.py"}},
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "TodoWrite",
                            "input": {
                                "todos": [
                                    {
                                        "content": "Implement X",
                                        "status": "pending",
                                        "activeForm": "...",
                                    },
                                ]
                            },
                        },
                    ]
                },
            },
        ]

        transcript_path = self.project_root / "transcript.jsonl"
        with open(transcript_path, "w") as f:
            for msg in transcript:
                f.write(json.dumps(msg) + "\n")

        result = self.checker.check(transcript_path, "test_session")

        # Should block because TODOs incomplete and tests missing
        self.assertEqual(result.decision, "block")
        self.assertIn("todos_complete", result.reasons)

    def test_maintenance_session_applies_minimal_checks(self):
        """MAINTENANCE: Should apply documentation and organization checks only."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Update the README"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Edit", "input": {"file_path": "README.md"}},
                    ]
                },
            },
        ]

        transcript_path = self.project_root / "transcript.jsonl"
        with open(transcript_path, "w") as f:
            for msg in transcript:
                f.write(json.dumps(msg) + "\n")

        result = self.checker.check(transcript_path, "test_session")

        # Should approve (documentation updated, minimal checks)
        self.assertEqual(result.decision, "approve")

    def test_investigation_session_applies_documentation_checks(self):
        """INVESTIGATION: Should require investigation docs but skip workflow."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Investigate the performance issue"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "src/main.py"}},
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Analysis: The bottleneck is in database queries...",
                        },
                    ]
                },
            },
        ]

        transcript_path = self.project_root / "transcript.jsonl"
        with open(transcript_path, "w") as f:
            for msg in transcript:
                f.write(json.dumps(msg) + "\n")

        _ = self.checker.check(transcript_path, "test_session")

        # Should block if investigation not documented
        analysis = self.checker._analyze_considerations(transcript, "test_session")
        if "investigation_docs" in analysis.results:
            # This check should be applied for INVESTIGATION sessions
            self.assertIsNotNone(analysis.results["investigation_docs"])

    # ========================================================================
    # Edge Cases and Boundary Tests
    # ========================================================================

    def test_mixed_session_prioritizes_development(self):
        """Mixed session with Q&A and development should be DEVELOPMENT."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "What does this function do?"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "This function validates..."},
                    ]
                },
            },
            {
                "type": "user",
                "message": {"content": "Fix the bug in it"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Edit", "input": {"file_path": "src/code.py"}},
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "DEVELOPMENT")

    def test_empty_transcript_defaults_to_informational(self):
        """Empty transcript should default to INFORMATIONAL (fail-open)."""
        transcript = []

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INFORMATIONAL")

    def test_single_read_tool_is_informational(self):
        """Single Read tool with no follow-up is INFORMATIONAL."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Show me the config"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "config.json"}},
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INFORMATIONAL")

    def test_multiple_reads_with_analysis_is_investigation(self):
        """Multiple Read/Grep tools with analysis is INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Find all uses of deprecated API"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Grep", "input": {"pattern": "old_api"}},
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "file1.py"}},
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Read", "input": {"file_path": "file2.py"}},
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_git_commit_cleanup_is_maintenance(self):
        """Git commits for cleanup without code changes is MAINTENANCE."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Commit the pending changes"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "git add . && git commit -m 'Cleanup'"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "MAINTENANCE")

    # ========================================================================
    # Environment Override Tests
    # ========================================================================

    def test_environment_override_session_type(self):
        """AMPLIHACK_SESSION_TYPE env var overrides detection."""
        import os

        transcript = [
            {
                "type": "user",
                "message": {"content": "Add feature"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Write", "input": {"file_path": "src/new.py"}},
                    ]
                },
            },
        ]

        # Set environment override
        os.environ["AMPLIHACK_SESSION_TYPE"] = "INFORMATIONAL"

        try:
            session_type = self.checker.detect_session_type(transcript)
            self.assertEqual(session_type, "INFORMATIONAL")
        finally:
            del os.environ["AMPLIHACK_SESSION_TYPE"]

    def test_invalid_environment_override_ignored(self):
        """Invalid session type in env var should be ignored."""
        import os

        transcript = [
            {
                "type": "user",
                "message": {"content": "Show me the docs"},
            },
        ]

        os.environ["AMPLIHACK_SESSION_TYPE"] = "INVALID_TYPE"

        try:
            session_type = self.checker.detect_session_type(transcript)
            # Should fall back to detection
            self.assertEqual(session_type, "INFORMATIONAL")
        finally:
            del os.environ["AMPLIHACK_SESSION_TYPE"]

    # ========================================================================
    # Backward Compatibility Tests
    # ========================================================================

    def test_backward_compatibility_no_session_type_method(self):
        """Old code without detect_session_type should still work."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Test"},
            },
        ]

        transcript_path = self.project_root / "transcript.jsonl"
        with open(transcript_path, "w") as f:
            for msg in transcript:
                f.write(json.dumps(msg) + "\n")

        # Should not crash if detect_session_type doesn't exist
        result = self.checker.check(transcript_path, "test_session")
        self.assertIn(result.decision, ["approve", "block"])

    def test_existing_qa_detection_still_works(self):
        """Existing _is_qa_session method should still function."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "What is this?"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "This is..."},
                    ]
                },
            },
        ]

        is_qa = self.checker._is_qa_session(transcript)
        self.assertTrue(is_qa)

    # ========================================================================
    # Session Type Heuristics Tests
    # ========================================================================

    def test_development_indicators_code_file_extensions(self):
        """Code file modifications indicate DEVELOPMENT."""
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "src/module.py"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "DEVELOPMENT")

    def test_maintenance_indicators_doc_files_only(self):
        """Only .md and .txt modifications indicate MAINTENANCE."""
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": "docs/guide.md"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "MAINTENANCE")

    def test_investigation_indicators_grep_patterns(self):
        """Multiple Grep/search operations indicate INVESTIGATION."""
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Grep", "input": {"pattern": "error"}},
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "tool_use", "name": "Grep", "input": {"pattern": "exception"}},
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_informational_indicators_question_marks(self):
        """High question density indicates INFORMATIONAL.

        Note: Questions like "How does X work?" are now classified as INVESTIGATION
        per issue #1604. This test uses truly informational questions about
        capabilities and features rather than system internals.
        """
        transcript = [
            {
                "type": "user",
                # Use informational questions (capabilities/features) not investigation questions
                "message": {
                    "content": "What commands are available? Can you help me? What's the format?"
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Available commands are... Yes I can help... The format is...",
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INFORMATIONAL")


class TestConsiderationMapping(unittest.TestCase):
    """Tests for consideration-to-session-type mapping."""

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
        config = {"enabled": True, "version": "2.1.0", "phase": 2}
        config_path.write_text(json.dumps(config, indent=2))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_get_applicable_considerations_for_development(self):
        """DEVELOPMENT sessions should get all considerations."""
        applicable = self.checker.get_applicable_considerations("DEVELOPMENT")

        # Should include all categories
        consideration_ids = {c["id"] for c in applicable}
        self.assertIn("todos_complete", consideration_ids)
        self.assertIn("ci_status", consideration_ids)
        self.assertIn("local_testing", consideration_ids)
        self.assertIn("pr_description", consideration_ids)

    def test_get_applicable_considerations_for_informational(self):
        """INFORMATIONAL sessions should get minimal considerations."""
        applicable = self.checker.get_applicable_considerations("INFORMATIONAL")

        # Should NOT include PR/CI/testing checks
        consideration_ids = {c["id"] for c in applicable}
        self.assertNotIn("ci_status", consideration_ids)
        self.assertNotIn("local_testing", consideration_ids)
        self.assertNotIn("pr_description", consideration_ids)

        # Should NOT include objective_completion for simple Q&A (Issue #2023)
        self.assertNotIn("objective_completion", consideration_ids)

    def test_get_applicable_considerations_for_maintenance(self):
        """MAINTENANCE sessions should get doc and organization checks."""
        applicable = self.checker.get_applicable_considerations("MAINTENANCE")

        consideration_ids = {c["id"] for c in applicable}

        # Should include doc checks
        self.assertIn("documentation_updates", consideration_ids)
        self.assertIn("docs_organization", consideration_ids)

        # Should NOT include testing/CI
        self.assertNotIn("local_testing", consideration_ids)
        self.assertNotIn("ci_status", consideration_ids)

    def test_get_applicable_considerations_for_investigation(self):
        """INVESTIGATION sessions should get investigation docs check."""
        applicable = self.checker.get_applicable_considerations("INVESTIGATION")

        consideration_ids = {c["id"] for c in applicable}

        # Should require investigation docs
        self.assertIn("investigation_docs", consideration_ids)

        # Should NOT include workflow checks
        self.assertNotIn("dev_workflow_complete", consideration_ids)
        self.assertNotIn("ci_status", consideration_ids)


class TestPerformance(unittest.TestCase):
    """Performance tests for session classification."""

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
        config = {"enabled": True, "version": "2.1.0", "phase": 2}
        config_path.write_text(json.dumps(config, indent=2))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_classification_performance_under_500ms(self):
        """Session type classification should complete in under 500ms."""
        import time

        # Create a realistic transcript with mixed operations
        transcript = []

        # Add 50 messages (realistic session size)
        for i in range(50):
            # User messages
            transcript.append(
                {
                    "type": "user",
                    "message": {"content": f"Please implement feature {i}"},
                }
            )

            # Assistant responses with tool usage
            transcript.append(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Write",
                                "input": {"file_path": f"src/module{i}.py"},
                            },
                        ]
                    },
                }
            )

            transcript.append(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Read",
                                "input": {"file_path": f"src/other{i}.py"},
                            },
                        ]
                    },
                }
            )

        # Measure classification time
        start_time = time.time()
        session_type = self.checker.detect_session_type(transcript)
        elapsed_ms = (time.time() - start_time) * 1000

        # Verify it completed in under 500ms
        self.assertLess(
            elapsed_ms, 500, f"Classification took {elapsed_ms:.2f}ms, should be < 500ms"
        )

        # Verify correct classification
        self.assertEqual(session_type, "DEVELOPMENT")

    def test_classification_performance_large_transcript(self):
        """Classification should handle large transcripts efficiently."""
        import time

        # Create a large transcript (200 messages)
        transcript = []
        for i in range(200):
            transcript.append(
                {
                    "type": "user",
                    "message": {"content": f"Request {i}"},
                }
            )
            transcript.append(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Read",
                                "input": {"file_path": f"file{i}.py"},
                            },
                        ]
                    },
                }
            )

        # Measure classification time
        start_time = time.time()
        _ = self.checker.detect_session_type(
            transcript
        )  # Result not used, just measuring performance
        elapsed_ms = (time.time() - start_time) * 1000

        # Should still complete in reasonable time (under 1 second for large transcript)
        self.assertLess(
            elapsed_ms,
            1000,
            f"Large transcript classification took {elapsed_ms:.2f}ms, should be < 1000ms",
        )


class TestInvestigationKeywordDetection(unittest.TestCase):
    """Tests for investigation keyword detection (Issue #1604).

    These tests verify that investigation/troubleshooting sessions are correctly
    classified based on keywords in user messages, even when tool usage patterns
    would suggest a different classification.
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
        config = {"enabled": True, "version": "2.1.0", "phase": 2}
        config_path.write_text(json.dumps(config, indent=2))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_investigate_keyword_triggers_investigation(self):
        """'Investigate' keyword should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Investigate why the SSH connection is failing"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "ssh user@host"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_troubleshoot_keyword_triggers_investigation(self):
        """'Troubleshoot' keyword should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Troubleshoot the deployment failure"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "docker logs app"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_diagnose_keyword_triggers_investigation(self):
        """'Diagnose' keyword should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Diagnose the memory leak issue"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "ps aux | grep python"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_debug_keyword_triggers_investigation(self):
        """'Debug' keyword should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Debug the authentication error"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Read",
                            "input": {"file_path": "logs/auth.log"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_figure_out_phrase_triggers_investigation(self):
        """'Figure out' phrase should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Figure out why the tests are failing"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_why_does_phrase_triggers_investigation(self):
        """'Why does' phrase should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Why does the API return 500 errors?"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_root_cause_phrase_triggers_investigation(self):
        """'Root cause' phrase should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Find the root cause of the crash"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_keyword_takes_priority_over_doc_updates(self):
        """Investigation keyword should take priority even with doc updates.

        This is the core issue from #1604 - troubleshooting sessions that
        update DISCOVERIES.md should still be classified as INVESTIGATION.
        """
        transcript = [
            {
                "type": "user",
                "message": {"content": "Troubleshoot the SSH connection issue"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "ssh user@host"},
                        },
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": ".claude/context/DISCOVERIES.md"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(
            session_type,
            "INVESTIGATION",
            "Troubleshooting session with doc updates should still be INVESTIGATION",
        )

    def test_keyword_takes_priority_over_git_operations(self):
        """Investigation keyword should take priority even with git operations."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Investigate why the VM connection fails"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "ssh azureuser@vm.example.com"},
                        },
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "git commit -m 'Fix: update SSH key'"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(
            session_type,
            "INVESTIGATION",
            "Investigation session with git commit should still be INVESTIGATION",
        )

    def test_keyword_detection_case_insensitive(self):
        """Keyword detection should be case-insensitive."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "INVESTIGATE the connection failure"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_has_investigation_keywords_helper(self):
        """Test the _has_investigation_keywords helper method directly."""
        # With keyword
        transcript_with_keyword = [
            {
                "type": "user",
                "message": {"content": "Investigate the issue"},
            },
        ]
        self.assertTrue(self.checker._has_investigation_keywords(transcript_with_keyword))

        # Without keyword
        transcript_without_keyword = [
            {
                "type": "user",
                "message": {"content": "Add a new feature"},
            },
        ]
        self.assertFalse(self.checker._has_investigation_keywords(transcript_without_keyword))

    def test_keyword_detection_checks_first_5_messages(self):
        """Keyword detection should only check first 5 user messages."""
        # Keyword in 6th message should not trigger
        transcript = []
        for i in range(6):
            transcript.append(
                {
                    "type": "user",
                    "message": {"content": f"Do something {i}"},
                }
            )

        # Add investigation keyword in 6th user message
        transcript[5]["message"]["content"] = "Investigate the issue"

        # Should NOT detect as investigation because keyword is in 6th message
        self.assertFalse(self.checker._has_investigation_keywords(transcript))

    def test_analyze_keyword_triggers_investigation(self):
        """'Analyze' keyword should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Analyze the performance metrics"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_research_keyword_triggers_investigation(self):
        """'Research' keyword should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Research how authentication works"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_explore_keyword_triggers_investigation(self):
        """'Explore' keyword should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Explore the codebase structure"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_understand_keyword_triggers_investigation(self):
        """'Understand' keyword should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Help me understand how the API works"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_explain_keyword_triggers_investigation(self):
        """'Explain' keyword should classify as INVESTIGATION."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Explain why this test is failing"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_how_does_phrase_triggers_investigation(self):
        """'How does X work?' phrase should classify as INVESTIGATION.

        This test was added per review feedback to explicitly verify that
        questions about how things work are classified as INVESTIGATION.
        """
        transcript = [
            {
                "type": "user",
                "message": {"content": "How does this authentication module work?"},
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "INVESTIGATION")

    def test_no_false_positive_for_development_task(self):
        """Development tasks without keywords should still be DEVELOPMENT."""
        transcript = [
            {
                "type": "user",
                "message": {"content": "Add JWT authentication to the API"},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "src/auth.py"},
                        },
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "pytest tests/test_auth.py"},
                        },
                    ]
                },
            },
        ]

        session_type = self.checker.detect_session_type(transcript)
        self.assertEqual(session_type, "DEVELOPMENT")


if __name__ == "__main__":
    unittest.main()
