#!/usr/bin/env python3
"""
TDD Failing Tests for Power-Steering Merge Preference Awareness.

Tests the feature that makes power-steering respect the user preference:
"NEVER Merge PRs Without Permission"

This test suite follows TDD methodology - all tests are designed to FAIL initially
until the implementation is complete.

Feature Requirements:
- Detect user preference in USER_PREFERENCES.md via regex pattern
- Modify CI status check behavior when preference is detected
- Fail-open design: errors/missing files preserve existing behavior
- No merge requirement when preference is active

Architecture:
- _user_prefers_no_auto_merge() - preference detection (fail-open)
- _check_ci_status_no_auto_merge() - CI validation without merge check
- _check_ci_status() - delegates based on preference
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


class TestPowerSteeringMergePreference(unittest.TestCase):
    """TDD Tests for merge preference awareness feature."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        # Create directory structure
        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(
            parents=True, exist_ok=True
        )
        (self.project_root / ".claude" / "context").mkdir(parents=True, exist_ok=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )

        # Create default config
        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {
            "enabled": True,
            "version": "1.0.0",
            "phase": 1,
            "checkers_enabled": {
                "ci_status": True,
            },
        }
        config_path.write_text(json.dumps(config, indent=2))

        # Store preferences path for tests
        self.preferences_path = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    # ========================================================================
    # Test Group 1: Preference Detection Tests
    # ========================================================================

    def test_user_prefers_no_auto_merge_detected(self):
        """Test preference detection when explicit "never merge without permission" exists.

        Expected behavior:
        - Method _user_prefers_no_auto_merge() exists
        - Returns True when preference is present in USER_PREFERENCES.md
        - Matches various phrasings (case-insensitive):
          - "never merge without permission"
          - "must not merge without approval"
          - "do not merge without explicit permission"
          - "don't merge PRs without permission"
        """
        # Create preferences file with merge permission requirement
        self.preferences_path.write_text(
            """# User Preferences

## Pull Request Workflow

**CRITICAL**: NEVER merge PRs without explicit permission from me.
Always wait for approval before merging.

## Other preferences
Some other content here.
"""
        )

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until _user_prefers_no_auto_merge() is implemented
        result = checker._user_prefers_no_auto_merge()

        self.assertTrue(
            result,
            "Should detect 'never merge without permission' preference",
        )

    def test_user_prefers_no_auto_merge_variations(self):
        """Test preference detection handles various phrasings.

        Tests multiple valid preference phrasings to ensure regex is robust.
        """
        test_cases = [
            "Never merge PRs without permission",
            "Must not merge without my approval",
            "Do not merge without explicit permission",
            "Don't merge PRs without approval",
            "NEVER MERGE WITHOUT PERMISSION",  # case insensitive
            "You must not merge any PR without my explicit approval",
        ]

        for preference_text in test_cases:
            with self.subTest(preference=preference_text):
                # Write preference
                self.preferences_path.write_text(
                    f"""# User Preferences

## Pull Requests

{preference_text}

## Other stuff
More content.
"""
                )

                checker = PowerSteeringChecker(self.project_root)

                # This test WILL FAIL until implementation is complete
                result = checker._user_prefers_no_auto_merge()

                self.assertTrue(
                    result,
                    f"Should detect preference: '{preference_text}'",
                )

    def test_user_prefers_no_auto_merge_not_detected(self):
        """Test preference detection returns False when preference absent.

        Expected behavior:
        - Returns False when USER_PREFERENCES.md exists but has no merge restriction
        - Does not false-positive on similar but different text
        """
        # Create preferences file WITHOUT merge restriction
        self.preferences_path.write_text(
            """# User Preferences

## Pull Request Workflow

Feel free to merge PRs when CI passes and code looks good.
Use your judgment on when to merge.

## Other preferences
Some other content here.
"""
        )

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until _user_prefers_no_auto_merge() is implemented
        result = checker._user_prefers_no_auto_merge()

        self.assertFalse(
            result,
            "Should NOT detect preference when not present",
        )

    def test_user_prefers_no_auto_merge_false_positives(self):
        """Test that similar but different text doesn't trigger false positives."""
        false_positive_cases = [
            "Never forget to merge PRs",  # wrong verb
            "Merge without hesitation",  # missing "never"
            "Always get permission before deleting branches",  # wrong action
            "Never push without testing",  # wrong action
        ]

        for text in false_positive_cases:
            with self.subTest(text=text):
                self.preferences_path.write_text(
                    f"""# User Preferences

{text}

## Other stuff
More content.
"""
                )

                checker = PowerSteeringChecker(self.project_root)

                # This test WILL FAIL until implementation is complete
                result = checker._user_prefers_no_auto_merge()

                self.assertFalse(
                    result,
                    f"Should NOT trigger on false positive: '{text}'",
                )

    def test_user_prefers_no_auto_merge_file_missing(self):
        """Test fail-open behavior when USER_PREFERENCES.md doesn't exist.

        Expected behavior:
        - Returns False (fail-open) when file is missing
        - Does not raise exception
        - Preserves existing power-steering behavior
        """
        # Do NOT create preferences file - test missing file scenario
        # (self.preferences_path does not exist)

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until _user_prefers_no_auto_merge() is implemented
        result = checker._user_prefers_no_auto_merge()

        self.assertFalse(
            result,
            "Should return False (fail-open) when preferences file missing",
        )

    def test_user_prefers_no_auto_merge_file_unreadable(self):
        """Test fail-open behavior when USER_PREFERENCES.md cannot be read.

        Expected behavior:
        - Returns False (fail-open) on read errors
        - Does not raise exception
        - Logs error but continues
        """
        # Create file but make it unreadable
        self.preferences_path.write_text("Some content")
        self.preferences_path.chmod(0o000)  # Remove all permissions

        try:
            checker = PowerSteeringChecker(self.project_root)

            # This test WILL FAIL until _user_prefers_no_auto_merge() is implemented
            result = checker._user_prefers_no_auto_merge()

            self.assertFalse(
                result,
                "Should return False (fail-open) when file unreadable",
            )
        finally:
            # Restore permissions for cleanup
            self.preferences_path.chmod(0o644)

    def test_user_prefers_no_auto_merge_empty_file(self):
        """Test handling of empty USER_PREFERENCES.md file."""
        # Create empty preferences file
        self.preferences_path.write_text("")

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until _user_prefers_no_auto_merge() is implemented
        result = checker._user_prefers_no_auto_merge()

        self.assertFalse(
            result,
            "Should return False for empty preferences file",
        )

    # ========================================================================
    # Test Group 2: CI Status Check with Preference Tests
    # ========================================================================

    def test_check_ci_status_no_auto_merge_exists(self):
        """Test that _check_ci_status_no_auto_merge method exists.

        This is the alternative CI checker that validates PR is ready
        without requiring merge indicators.
        """
        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until _check_ci_status_no_auto_merge() is implemented
        self.assertTrue(
            hasattr(checker, "_check_ci_status_no_auto_merge"),
            "Method _check_ci_status_no_auto_merge() should exist",
        )

    def test_ci_status_with_preference_pr_ready_passes(self):
        """Test CI check passes when preference is set and PR is ready.

        Expected behavior:
        - When _user_prefers_no_auto_merge() returns True
        - AND PR shows "ready for review" or similar indicators
        - AND CI is passing
        - Then _check_ci_status() returns True
        - WITHOUT requiring merge/mergeable indicators
        """
        # Setup: Create preference
        self.preferences_path.write_text(
            """# User Preferences

**CRITICAL**: Never merge PRs without explicit permission.
"""
        )

        # Create transcript showing PR ready + CI passing (but NOT mergeable)
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "PR #123 is ready for review. CI checks are passing.",
                        }
                    ]
                },
            }
        ]

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until implementation is complete
        result = checker._check_ci_status(transcript, "test_session")

        self.assertTrue(
            result,
            "Should pass when preference set, PR ready, and CI passing",
        )

    def test_ci_status_with_preference_ci_failing_blocks(self):
        """Test CI check fails when preference is set but CI is failing.

        Expected behavior:
        - When _user_prefers_no_auto_merge() returns True
        - AND PR shows "ready for review"
        - BUT CI is failing
        - Then _check_ci_status() returns False
        """
        # Setup: Create preference
        self.preferences_path.write_text(
            """# User Preferences

Do not merge without permission.
"""
        )

        # Create transcript showing PR ready but CI failing
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "PR #123 is ready for review. However, CI checks are failing.",
                        }
                    ]
                },
            }
        ]

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until implementation is complete
        result = checker._check_ci_status(transcript, "test_session")

        self.assertFalse(
            result,
            "Should fail when CI is failing even with preference",
        )

    def test_ci_status_with_preference_pr_not_ready_blocks(self):
        """Test CI check fails when preference is set but PR not ready.

        Expected behavior:
        - When _user_prefers_no_auto_merge() returns True
        - BUT PR is draft or not ready
        - Then _check_ci_status() returns False
        """
        # Setup: Create preference
        self.preferences_path.write_text(
            """# User Preferences

Never merge without approval.
"""
        )

        # Create transcript showing draft PR
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Created draft PR #123. CI is running.",
                        }
                    ]
                },
            }
        ]

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until implementation is complete
        result = checker._check_ci_status(transcript, "test_session")

        self.assertFalse(
            result,
            "Should fail when PR is draft even with preference",
        )

    def test_ci_status_without_preference_unchanged(self):
        """Test existing CI check behavior preserved when preference NOT set.

        Expected behavior:
        - When _user_prefers_no_auto_merge() returns False
        - Existing _check_ci_status() behavior is unchanged
        - Still requires "mergeable" or "passing" indicators
        - This ensures backward compatibility
        """
        # Setup: NO preference in file
        self.preferences_path.write_text(
            """# User Preferences

## Some other settings
Regular preferences here.
"""
        )

        # Create transcript showing PR ready but NOT mergeable
        # (this would fail old behavior)
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "PR #123 is ready for review. CI checks passing.",
                        }
                    ]
                },
            }
        ]

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until implementation is complete
        result = checker._check_ci_status(transcript, "test_session")

        # Without preference, should follow OLD behavior:
        # - Needs "mergeable" or similar to pass
        # - "ready for review" alone is not enough
        self.assertFalse(
            result,
            "Should preserve old behavior when preference not set",
        )

    def test_ci_status_without_preference_mergeable_passes(self):
        """Test that mergeable PRs still pass when preference NOT set.

        Ensures we don't break existing behavior.
        """
        # Setup: NO preference
        self.preferences_path.write_text("# User Preferences\n\nSome settings.")

        # Create transcript showing mergeable PR
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "PR #123 is mergeable. CI passing.",
                        }
                    ]
                },
            }
        ]

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until implementation is complete
        result = checker._check_ci_status(transcript, "test_session")

        self.assertTrue(
            result,
            "Should pass for mergeable PR when no preference (old behavior)",
        )

    # ========================================================================
    # Test Group 3: Integration Tests - State Verification
    # ========================================================================

    def test_state_verification_with_preference_accepts_ready_pr(self):
        """Integration test: Verify complete flow accepts ready PR with preference.

        This tests the full integration:
        1. Preference is detected
        2. Alternative CI checker is used
        3. Ready PR + passing CI = satisfied
        4. No merge required
        """
        # Setup: Create preference
        self.preferences_path.write_text(
            """# User Preferences

**CRITICAL**: Never merge PRs without explicit permission from me.
"""
        )

        # Create realistic transcript
        transcript = [
            {
                "type": "user",
                "message": {"content": [{"type": "text", "text": "Create PR"}]},
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "Created PR #456. Waiting for CI checks to complete.",
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "CI checks are now passing. PR is ready for your review and approval.",
                        }
                    ]
                },
            },
        ]

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until implementation is complete
        result = checker._check_ci_status(transcript, "test_session")

        self.assertTrue(
            result,
            "Integration test: Should accept ready PR with preference set",
        )

    def test_state_verification_without_preference_requires_merge(self):
        """Integration test: Verify complete flow requires merge without preference.

        This tests backward compatibility:
        1. No preference detected
        2. Standard CI checker is used
        3. Ready PR without "mergeable" = unsatisfied
        4. Merge indicator required
        """
        # Setup: NO preference
        self.preferences_path.write_text("# User Preferences\n")

        # Create transcript with ready PR but no merge indicator
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "PR is ready for review. CI passing.",
                        }
                    ]
                },
            }
        ]

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until implementation is complete
        result = checker._check_ci_status(transcript, "test_session")

        self.assertFalse(
            result,
            "Integration test: Should require merge indicator without preference",
        )

    # ========================================================================
    # Test Group 4: Edge Cases and Error Handling
    # ========================================================================

    def test_preference_detection_called_on_each_check(self):
        """Test that preference detection is lazy (called during check, not init).

        Expected behavior:
        - Preference is checked during _check_ci_status() call
        - Not cached at initialization
        - Allows preference to change during session (though unlikely)
        """
        # Setup: Start with no preference
        self.preferences_path.write_text("# User Preferences\n")

        checker = PowerSteeringChecker(self.project_root)

        # First check - no preference
        transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "PR ready, CI passing",
                        }
                    ]
                },
            }
        ]

        # This test WILL FAIL until implementation is complete
        result1 = checker._check_ci_status(transcript, "test_session")
        self.assertFalse(result1, "Should fail without preference")

        # Now add preference
        self.preferences_path.write_text(
            """# User Preferences

Never merge without permission.
"""
        )

        # Second check - preference now exists
        # This test WILL FAIL until implementation is complete
        result2 = checker._check_ci_status(transcript, "test_session")
        self.assertTrue(result2, "Should pass with preference added")

    def test_malformed_preferences_file_fails_open(self):
        """Test handling of malformed USER_PREFERENCES.md content."""
        # Create malformed file (invalid characters, etc)
        self.preferences_path.write_bytes(b"\xff\xfe\x00\x00Invalid UTF-8")

        checker = PowerSteeringChecker(self.project_root)

        # This test WILL FAIL until implementation is complete
        # Should not raise exception
        result = checker._user_prefers_no_auto_merge()

        self.assertFalse(
            result,
            "Should fail-open on malformed file",
        )

    def test_check_ci_status_no_auto_merge_matches_standard_ci_checks(self):
        """Test that alternative checker validates CI status correctly.

        The _check_ci_status_no_auto_merge() method should:
        - Check for CI passing indicators
        - Check for CI failing indicators
        - Check for PR ready state
        - NOT check for mergeable/merge indicators
        """
        self.preferences_path.write_text("# User Preferences\n")

        checker = PowerSteeringChecker(self.project_root)

        # Test CI passing detection
        passing_transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "CI checks are passing. PR is ready.",
                        }
                    ]
                },
            }
        ]

        # This test WILL FAIL until implementation is complete
        result = checker._check_ci_status_no_auto_merge(passing_transcript)
        self.assertTrue(result, "Should detect CI passing")

        # Test CI failing detection
        failing_transcript = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "CI checks failed. Please fix the errors.",
                        }
                    ]
                },
            }
        ]

        # This test WILL FAIL until implementation is complete
        result = checker._check_ci_status_no_auto_merge(failing_transcript)
        self.assertFalse(result, "Should detect CI failing")


class TestPreferenceRegexPattern(unittest.TestCase):
    """Detailed tests for the preference detection regex pattern.

    Pattern should match:
    (?i)(never|must not|do not|don't).*merge.*without.*(permission|approval|explicit)
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)

        (self.project_root / ".claude" / "tools" / "amplihack").mkdir(
            parents=True, exist_ok=True
        )
        (self.project_root / ".claude" / "context").mkdir(parents=True, exist_ok=True)
        (self.project_root / ".claude" / "runtime" / "power-steering").mkdir(
            parents=True, exist_ok=True
        )

        config_path = (
            self.project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        config = {"enabled": True, "version": "1.0.0"}
        config_path.write_text(json.dumps(config))

        self.preferences_path = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"

    def tearDown(self):
        """Clean up."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_regex_matches_all_valid_patterns(self):
        """Test regex matches all documented valid patterns."""
        valid_patterns = [
            "never merge without permission",
            "must not merge without approval",
            "do not merge without explicit permission",
            "don't merge PRs without permission",
            "NEVER MERGE WITHOUT PERMISSION",  # case insensitive
            "Never merge any PR without my explicit approval",
            "You must not merge without getting permission first",
            "Do not merge pull requests without approval",
            "Don't ever merge without my explicit permission",
        ]

        for pattern in valid_patterns:
            with self.subTest(pattern=pattern):
                self.preferences_path.write_text(f"# Preferences\n\n{pattern}\n")
                checker = PowerSteeringChecker(self.project_root)

                # This test WILL FAIL until implementation is complete
                result = checker._user_prefers_no_auto_merge()
                self.assertTrue(result, f"Should match: {pattern}")

    def test_regex_rejects_invalid_patterns(self):
        """Test regex does NOT match invalid patterns."""
        invalid_patterns = [
            "always merge when ready",  # missing "never"
            "never push without testing",  # wrong action
            "merge without hesitation",  # missing "never"
            "never delete without permission",  # wrong action
            "must not commit without testing",  # wrong action
            "never merge",  # missing "without permission"
            "without permission merge never",  # wrong order
        ]

        for pattern in invalid_patterns:
            with self.subTest(pattern=pattern):
                self.preferences_path.write_text(f"# Preferences\n\n{pattern}\n")
                checker = PowerSteeringChecker(self.project_root)

                # This test WILL FAIL until implementation is complete
                result = checker._user_prefers_no_auto_merge()
                self.assertFalse(result, f"Should NOT match: {pattern}")


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
