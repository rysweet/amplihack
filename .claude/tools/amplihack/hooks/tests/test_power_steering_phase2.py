#!/usr/bin/env python3
"""
Unit tests for PowerSteeringChecker Phase 2 functionality.

Tests:
- YAML loading and validation
- All 16 new checker methods
- Generic analyzer
- User customization
- Backward compatibility with Phase 1
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


class TestYAMLLoading(unittest.TestCase):
    """Tests for YAML loading and validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create directory structure
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )

        # Create default config
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {"enabled": True, "version": "1.0.0", "phase": 2}
        config_path.write_text(json.dumps(config, indent=2))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_yaml_loading_valid(self):
        """Test YAML loading with valid file."""
        # Create valid YAML file
        yaml_path = self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        yaml_content = """
- id: test_consideration
  category: Test Category
  question: Is this a test?
  description: Test consideration
  severity: blocker
  checker: _check_todos_complete
  enabled: true
"""
        yaml_path.write_text(yaml_content)

        checker = PowerSteeringChecker(self.project_root)

        # Should load YAML successfully
        self.assertEqual(len(checker.considerations), 1)
        self.assertEqual(checker.considerations[0]["id"], "test_consideration")

    def test_yaml_loading_missing_file(self):
        """Test YAML loading falls back to Phase 1 when file missing."""
        # No YAML file created
        checker = PowerSteeringChecker(self.project_root)

        # Should fall back to Phase 1 (5 considerations)
        self.assertEqual(len(checker.considerations), 5)
        self.assertEqual(checker.considerations[0]["id"], "todos_complete")

    def test_yaml_loading_invalid_format(self):
        """Test YAML loading with invalid format."""
        # Create invalid YAML (not a list)
        yaml_path = self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        yaml_content = """
invalid_format: not_a_list
"""
        yaml_path.write_text(yaml_content)

        checker = PowerSteeringChecker(self.project_root)

        # Should fall back to Phase 1
        self.assertEqual(len(checker.considerations), 5)

    def test_yaml_loading_malformed(self):
        """Test YAML loading with malformed syntax."""
        # Create malformed YAML
        yaml_path = self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        yaml_content = """
- id: test
  missing_colon after key
  invalid syntax
"""
        yaml_path.write_text(yaml_content)

        checker = PowerSteeringChecker(self.project_root)

        # Should fall back to Phase 1 on parse error
        self.assertEqual(len(checker.considerations), 5)

    def test_yaml_loading_partial_valid(self):
        """Test YAML loading with mix of valid and invalid considerations."""
        # Create YAML with one valid, one invalid
        yaml_path = self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        yaml_content = """
- id: valid_consideration
  category: Test
  question: Valid?
  description: Valid test
  severity: blocker
  checker: _check_todos_complete
  enabled: true

- id: invalid_consideration
  # Missing required fields
  question: Invalid?
"""
        yaml_path.write_text(yaml_content)

        checker = PowerSteeringChecker(self.project_root)

        # Should load only valid consideration
        self.assertEqual(len(checker.considerations), 1)
        self.assertEqual(checker.considerations[0]["id"], "valid_consideration")


class TestYAMLValidation(unittest.TestCase):
    """Tests for YAML schema validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config_path.write_text(json.dumps({"enabled": True}))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_validate_consideration_valid(self):
        """Test validation of valid consideration."""
        consideration = {
            "id": "test",
            "category": "Test",
            "question": "Test?",
            "description": "Test desc",
            "severity": "blocker",
            "checker": "test_checker",
            "enabled": True,
        }

        result = self.checker._validate_consideration_schema(consideration)
        self.assertTrue(result)

    def test_validate_consideration_missing_fields(self):
        """Test validation with missing required fields."""
        consideration = {
            "id": "test",
            # Missing other required fields
        }

        result = self.checker._validate_consideration_schema(consideration)
        self.assertFalse(result)

    def test_validate_consideration_invalid_severity(self):
        """Test validation with invalid severity."""
        consideration = {
            "id": "test",
            "category": "Test",
            "question": "Test?",
            "description": "Test desc",
            "severity": "invalid_severity",  # Invalid
            "checker": "test_checker",
            "enabled": True,
        }

        result = self.checker._validate_consideration_schema(consideration)
        self.assertFalse(result)

    def test_validate_consideration_invalid_enabled(self):
        """Test validation with invalid enabled type."""
        consideration = {
            "id": "test",
            "category": "Test",
            "question": "Test?",
            "description": "Test desc",
            "severity": "blocker",
            "checker": "test_checker",
            "enabled": "yes",  # Should be boolean
        }

        result = self.checker._validate_consideration_schema(consideration)
        self.assertFalse(result)

    def test_validate_consideration_not_dict(self):
        """Test validation with non-dictionary input."""
        result = self.checker._validate_consideration_schema("not a dict")
        self.assertFalse(result)


class TestGenericAnalyzer(unittest.TestCase):
    """Tests for generic analyzer."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config_path.write_text(json.dumps({"enabled": True}))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_generic_analyzer_basic(self):
        """Test generic analyzer with basic consideration."""
        transcript = [
            {"type": "user", "message": {"content": "Test question"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Answer"}]}},
        ]

        consideration = {
            "id": "test",
            "question": "Is this a test?",
            "category": "Test",
            "severity": "warning",
        }

        # Generic analyzer should default to satisfied (fail-open)
        result = self.checker._generic_analyzer(transcript, "test_session", consideration)
        self.assertTrue(result)

    def test_generic_analyzer_with_keywords(self):
        """Test generic analyzer extracts keywords from question."""
        transcript = [
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "security scan completed"}]},
            }
        ]

        consideration = {
            "id": "security_scan",
            "question": "Were security scans performed?",
            "category": "Security",
            "severity": "blocker",
        }

        # Should extract "security" and "scan" as keywords
        result = self.checker._generic_analyzer(transcript, "test_session", consideration)
        # Phase 2: Always satisfied (fail-open)
        self.assertTrue(result)

    def test_generic_analyzer_empty_question(self):
        """Test generic analyzer with empty question."""
        transcript = []
        consideration = {"id": "empty", "question": "", "category": "Test", "severity": "warning"}

        result = self.checker._generic_analyzer(transcript, "test_session", consideration)
        self.assertTrue(result)  # Should default to satisfied


class TestNewCheckers(unittest.TestCase):
    """Tests for the 16 new checker methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config_path.write_text(json.dumps({"enabled": True}))

        self.checker = PowerSteeringChecker(self.project_root)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_check_agent_unnecessary_questions(self):
        """Test _check_agent_unnecessary_questions."""
        # Transcript with many questions
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Question 1? Question 2? Question 3? Question 4?"}
                    ]
                },
            }
        ]

        result = self.checker._check_agent_unnecessary_questions(transcript, "test_session")
        self.assertFalse(result)  # Too many questions

        # Transcript with few questions
        transcript_good = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}}
        ]

        result = self.checker._check_agent_unnecessary_questions(transcript_good, "test_session")
        self.assertTrue(result)

    def test_check_objective_completion(self):
        """Test _check_objective_completion."""
        # Transcript with completion indicators
        transcript = [
            {"type": "user", "message": {"content": "Implement feature X"}},
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Implementation complete"}]},
            },
        ]

        result = self.checker._check_objective_completion(transcript, "test_session")
        self.assertTrue(result)

        # Transcript without completion
        transcript_incomplete = [
            {"type": "user", "message": {"content": "Implement feature X"}},
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Working on it"}]},
            },
        ]

        result = self.checker._check_objective_completion(transcript_incomplete, "test_session")
        self.assertFalse(result)

    def test_check_documentation_updates(self):
        """Test _check_documentation_updates."""
        # Code changes with doc updates
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/test.py", "content": "code"},
                        },
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/README.md", "content": "docs"},
                        },
                    ]
                },
            }
        ]

        result = self.checker._check_documentation_updates(transcript, "test_session")
        self.assertTrue(result)

        # Code changes without doc updates
        transcript_no_docs = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/test.py", "content": "code"},
                        }
                    ]
                },
            }
        ]

        result = self.checker._check_documentation_updates(transcript_no_docs, "test_session")
        self.assertFalse(result)

    def test_check_tutorial_needed(self):
        """Test _check_tutorial_needed."""
        # New feature with tutorial
        transcript = [
            {"type": "user", "message": {"content": "Add new feature X"}},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/examples/tutorial.md", "content": "guide"},
                        }
                    ]
                },
            },
        ]

        result = self.checker._check_tutorial_needed(transcript, "test_session")
        self.assertTrue(result)

        # New feature without tutorial
        transcript_no_tutorial = [
            {"type": "user", "message": {"content": "Add new feature X"}},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/src/feature.py", "content": "code"},
                        }
                    ]
                },
            },
        ]

        result = self.checker._check_tutorial_needed(transcript_no_tutorial, "test_session")
        self.assertFalse(result)

    def test_check_presentation_needed(self):
        """Test _check_presentation_needed."""
        # Always returns True (low priority check)
        transcript = []
        result = self.checker._check_presentation_needed(transcript, "test_session")
        self.assertTrue(result)

    def test_check_next_steps(self):
        """Test _check_next_steps."""
        # Transcript with next steps mentioned
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Next steps: implement feature Y"}]
                },
            }
        ]

        result = self.checker._check_next_steps(transcript, "test_session")
        self.assertTrue(result)

        # Transcript without next steps
        transcript_no_steps = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done"}]}}
        ]

        result = self.checker._check_next_steps(transcript_no_steps, "test_session")
        self.assertFalse(result)

    def test_check_docs_organization(self):
        """Test _check_docs_organization."""
        # Docs in correct location
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {
                                "file_path": "/.claude/runtime/investigation.md",
                                "content": "findings",
                            },
                        }
                    ]
                },
            }
        ]

        result = self.checker._check_docs_organization(transcript, "test_session")
        self.assertTrue(result)

        # Docs in wrong location
        transcript_wrong = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {
                                "file_path": "/investigation.md",  # Should be in .claude/
                                "content": "findings",
                            },
                        }
                    ]
                },
            }
        ]

        result = self.checker._check_docs_organization(transcript_wrong, "test_session")
        self.assertFalse(result)

    def test_check_investigation_docs(self):
        """Test _check_investigation_docs."""
        # Investigation with documentation
        transcript = [
            {"type": "user", "message": {"content": "Investigation into bug X"}},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/findings.md", "content": "results"},
                        }
                    ]
                },
            },
        ]

        result = self.checker._check_investigation_docs(transcript, "test_session")
        self.assertTrue(result)

        # Investigation without documentation
        transcript_no_docs = [
            {"type": "user", "message": {"content": "Investigation into bug X"}},
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Found issues"}]},
            },
        ]

        result = self.checker._check_investigation_docs(transcript_no_docs, "test_session")
        self.assertFalse(result)

    def test_check_shortcuts(self):
        """Test _check_shortcuts."""
        # Code with shortcut indicators
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {
                                "file_path": "/test.py",
                                "content": "def foo():\n    pass  # TODO: fix later",
                            },
                        }
                    ]
                },
            }
        ]

        result = self.checker._check_shortcuts(transcript, "test_session")
        self.assertFalse(result)

        # Clean code
        transcript_clean = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {
                                "file_path": "/test.py",
                                "content": "def foo():\n    return 42",
                            },
                        }
                    ]
                },
            }
        ]

        result = self.checker._check_shortcuts(transcript_clean, "test_session")
        self.assertTrue(result)

    def test_check_interactive_testing(self):
        """Test _check_interactive_testing."""
        # Transcript with interactive testing mention
        transcript = [
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Manually tested the feature"}]},
            }
        ]

        result = self.checker._check_interactive_testing(transcript, "test_session")
        self.assertTrue(result)

        # Only automated tests
        transcript_automated = [
            {
                "type": "tool_result",
                "message": {"content": "Tests: 5 passed"},
            }
        ]

        result = self.checker._check_interactive_testing(transcript_automated, "test_session")
        self.assertFalse(result)  # Not enough tests

    def test_check_unrelated_changes(self):
        """Test _check_unrelated_changes."""
        # Few files modified
        transcript = [
            {"type": "user", "message": {"content": "Fix bug in auth"}},
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/auth.py", "content": "fix"},
                        }
                    ]
                },
            },
        ]

        result = self.checker._check_unrelated_changes(transcript, "test_session")
        self.assertTrue(result)

        # Many files modified (scope creep)
        transcript_many = [
            {"type": "user", "message": {"content": "Fix bug in auth"}},
        ]
        # Add 25 file modifications
        for i in range(25):
            transcript_many.append(
                {
                    "type": "assistant",
                    "message": {
                        "content": [
                            {
                                "type": "tool_use",
                                "name": "Write",
                                "input": {"file_path": f"/file{i}.py", "content": "code"},
                            }
                        ]
                    },
                }
            )

        result = self.checker._check_unrelated_changes(transcript_many, "test_session")
        self.assertFalse(result)

    def test_check_root_pollution(self):
        """Test _check_root_pollution."""
        # Acceptable root file
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/README.md", "content": "docs"},
                        }
                    ]
                },
            }
        ]

        result = self.checker._check_root_pollution(transcript, "test_session")
        self.assertTrue(result)

        # Unacceptable root file
        transcript_pollution = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/random_file.txt", "content": "stuff"},
                        }
                    ]
                },
            }
        ]

        result = self.checker._check_root_pollution(transcript_pollution, "test_session")
        self.assertFalse(result)

    def test_check_pr_description(self):
        """Test _check_pr_description."""
        # PR with good description
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {
                                "command": 'gh pr create --title "Fix" --body "Summary: fix\nTest plan: tested"'
                            },
                        }
                    ]
                },
            }
        ]

        result = self.checker._check_pr_description(transcript, "test_session")
        self.assertTrue(result)

        # PR with poor description
        transcript_bad = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": 'gh pr create --title "Fix" --body "Quick fix"'},
                        }
                    ]
                },
            }
        ]

        result = self.checker._check_pr_description(transcript_bad, "test_session")
        self.assertFalse(result)

    def test_check_review_responses(self):
        """Test _check_review_responses."""
        # Review feedback addressed
        transcript = [
            {"type": "user", "message": {"content": "Please address the review comments"}},
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Addressed all feedback"}]},
            },
        ]

        result = self.checker._check_review_responses(transcript, "test_session")
        self.assertTrue(result)

        # Review feedback not addressed
        transcript_not_addressed = [
            {"type": "user", "message": {"content": "Please address the review comments"}},
            {
                "type": "assistant",
                "message": {"content": [{"type": "text", "text": "Working on it"}]},
            },
        ]

        result = self.checker._check_review_responses(transcript_not_addressed, "test_session")
        self.assertFalse(result)

    def test_check_branch_rebase(self):
        """Test _check_branch_rebase."""
        # Branch up to date
        transcript = [
            {"type": "tool_result", "message": {"content": "Your branch is up to date with main"}}
        ]

        result = self.checker._check_branch_rebase(transcript, "test_session")
        self.assertTrue(result)

        # Branch behind
        transcript_behind = [
            {
                "type": "tool_result",
                "message": {"content": "Your branch is behind main by 5 commits"},
            }
        ]

        result = self.checker._check_branch_rebase(transcript_behind, "test_session")
        self.assertFalse(result)

    def test_check_ci_precommit_mismatch(self):
        """Test _check_ci_precommit_mismatch."""
        # No mismatch
        transcript = [
            {"type": "tool_result", "message": {"content": "pre-commit passed"}},
            {"type": "tool_result", "message": {"content": "CI checks passed"}},
        ]

        result = self.checker._check_ci_precommit_mismatch(transcript, "test_session")
        self.assertTrue(result)

        # Mismatch detected
        transcript_mismatch = [
            {"type": "tool_result", "message": {"content": "pre-commit passed"}},
            {"type": "tool_result", "message": {"content": "CI checks failed"}},
        ]

        result = self.checker._check_ci_precommit_mismatch(transcript_mismatch, "test_session")
        self.assertFalse(result)


class TestUserCustomization(unittest.TestCase):
    """Tests for user customization features."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config_path.write_text(json.dumps({"enabled": True}))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_custom_consideration_loaded(self):
        """Test custom considerations are loaded from YAML."""
        # Create YAML with custom consideration
        yaml_path = self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        yaml_content = """
- id: custom_security_check
  category: Security
  question: Was security audit performed?
  description: Custom security consideration
  severity: blocker
  checker: generic
  enabled: true
"""
        yaml_path.write_text(yaml_content)

        checker = PowerSteeringChecker(self.project_root)

        # Should load custom consideration
        self.assertEqual(len(checker.considerations), 1)
        self.assertEqual(checker.considerations[0]["id"], "custom_security_check")

    def test_consideration_disabled(self):
        """Test disabled considerations are not checked."""
        yaml_path = self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        yaml_content = """
- id: enabled_check
  category: Test
  question: Enabled?
  description: Enabled consideration
  severity: blocker
  checker: generic
  enabled: true

- id: disabled_check
  category: Test
  question: Disabled?
  description: Disabled consideration
  severity: blocker
  checker: generic
  enabled: false
"""
        yaml_path.write_text(yaml_content)

        checker = PowerSteeringChecker(self.project_root)

        # Create test transcript
        transcript = []
        analysis = checker._analyze_considerations(transcript, "test_session")

        # Only enabled consideration should be in results
        self.assertIn("enabled_check", analysis.results)
        self.assertNotIn("disabled_check", analysis.results)

    def test_custom_consideration_with_generic_checker(self):
        """Test custom considerations work with generic checker."""
        yaml_path = self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        yaml_content = """
- id: custom_check
  category: Custom
  question: Is custom requirement met?
  description: Custom check
  severity: warning
  checker: generic
  enabled: true
"""
        yaml_path.write_text(yaml_content)

        checker = PowerSteeringChecker(self.project_root)
        transcript = [
            {"type": "user", "message": {"content": "Test"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done"}]}},
        ]

        analysis = checker._analyze_considerations(transcript, "test_session")

        # Should have result for custom check
        self.assertIn("custom_check", analysis.results)
        # Generic analyzer defaults to satisfied (fail-open)
        self.assertTrue(analysis.results["custom_check"].satisfied)


class TestBackwardCompatibility(unittest.TestCase):
    """Tests for backward compatibility with Phase 1."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {
            "enabled": True,
            "checkers_enabled": {
                "todos_complete": True,
                "dev_workflow_complete": True,
                "philosophy_compliance": True,
                "local_testing": True,
                "ci_status": True,
            },
        }
        config_path.write_text(json.dumps(config, indent=2))

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_phase1_checkers_still_work(self):
        """Test Phase 1 checkers still function with Phase 2 code."""
        # No YAML file - should use Phase 1 fallback
        checker = PowerSteeringChecker(self.project_root)

        # Should have Phase 1 considerations
        self.assertEqual(len(checker.considerations), 5)

        # Test a Phase 1 checker still works
        transcript = [
            {"type": "user", "message": {"content": "Test"}},
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
                                        "content": "Task 1",
                                        "status": "completed",
                                        "activeForm": "Completing",
                                    }
                                ]
                            },
                        }
                    ]
                },
            },
        ]

        result = checker._check_todos_complete(transcript, "test_session")
        self.assertTrue(result)

    def test_config_checkers_enabled_respected(self):
        """Test Phase 1 config checkers_enabled still works."""
        # Disable a checker in config
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = json.loads(config_path.read_text())
        config["checkers_enabled"]["todos_complete"] = False
        config_path.write_text(json.dumps(config))

        checker = PowerSteeringChecker(self.project_root)
        transcript = []

        analysis = checker._analyze_considerations(transcript, "test_session")

        # todos_complete should not be in results (disabled in config)
        self.assertNotIn("todos_complete", analysis.results)


if __name__ == "__main__":
    unittest.main()
