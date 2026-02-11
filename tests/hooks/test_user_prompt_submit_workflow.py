# tests/hooks/test_user_prompt_submit_workflow.py
"""
Unit tests for workflow reminder functionality in user_prompt_submit.py hook.

These tests define the contract for workflow classification reminder integration.
All tests should FAIL initially until implementation is complete.

Test Coverage:
- State directory initialization
- State file path generation
- Preference parsing (enabled/disabled/missing/malformed)
- Recipe detection (env vars, lock files, fail-safe)
- Keyword detection (all trigger phrases, case-insensitive)
- First message detection (turn 0)
- Caching behavior (3-turn gap enforcement)
- State save/load round-trip
- Error handling (non-fatal degradation)
- Reminder template generation
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Add hook location to path
hook_path = Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
sys.path.insert(0, str(hook_path))

from user_prompt_submit import UserPromptSubmitHook


class TestWorkflowStateDirectoryInitialization:
    """Test state directory creation with proper permissions."""

    def test_init_creates_state_directory_if_not_exists(self, tmp_path):
        """State directory should be created on first initialization."""

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / ".claude" / "runtime" / "logs" / "classification_state"

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            hook._init_workflow_state_dir()

        assert state_dir.exists()
        assert state_dir.is_dir()

    def test_init_sets_directory_permissions_0o700(self, tmp_path):
        """State directory should have restrictive permissions (0o700)."""

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / ".claude" / "runtime" / "logs" / "classification_state"

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            hook._init_workflow_state_dir()

        # Check permissions are 0o700 (owner rwx, no group/other access)
        assert oct(state_dir.stat().st_mode)[-3:] == "700"

    def test_init_is_idempotent_no_error_if_exists(self, tmp_path):
        """Calling init multiple times should not raise errors."""

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / ".claude" / "runtime" / "logs" / "classification_state"
        state_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            # Should not raise
            hook._init_workflow_state_dir()
            hook._init_workflow_state_dir()


class TestStateFilePathGeneration:
    """Test state file path generation with validation."""

    @pytest.mark.parametrize(
        "session_id",
        [
            "abc123",
            "test-session-123",
            "SESSION_456",
            "a1b2c3d4e5f6",
            "0000000000000000-ab8c1f0343fb4726_amplihack-tester",
        ],
    )
    def test_get_workflow_state_file_valid_session_ids(self, tmp_path, session_id):
        """Valid session IDs should generate correct file paths."""

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            file_path = hook._get_workflow_state_file(session_id)

        expected_path = state_dir / f"{session_id}.json"
        assert file_path == str(expected_path)

    @pytest.mark.parametrize(
        "malicious_id",
        [
            "../../../etc/passwd",
            "../../root/.ssh/id_rsa",
            "..%2F..%2Fetc%2Fpasswd",
            "session;rm -rf /",
            "session`whoami`",
            "session$(cat /etc/passwd)",
            "session\x00hidden",
            "session|cat /etc/shadow",
        ],
    )
    def test_get_workflow_state_file_rejects_path_traversal(self, tmp_path, malicious_id):
        """Malicious session IDs should be rejected (raise ValueError)."""

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            with pytest.raises(ValueError, match="Invalid session ID"):
                hook._get_workflow_state_file(malicious_id)


class TestPreferencesParsing:
    """Test workflow reminder preference parsing from USER_PREFERENCES.md."""

    @pytest.mark.parametrize(
        "pref_value,expected",
        [
            ("enabled", True),
            ("yes", True),
            ("on", True),
            ("true", True),
            ("ENABLED", True),  # case insensitive
            ("Yes", True),
            ("disabled", False),
            ("no", False),
            ("off", False),
            ("false", False),
            ("DISABLED", False),  # case insensitive
            ("No", False),
        ],
    )
    def test_is_workflow_reminder_enabled_valid_values(self, pref_value, expected):
        """Preference values should be parsed correctly (case-insensitive)."""

        hook = UserPromptSubmitHook()

        mock_preferences = f"""
## Workflow Preferences

Workflow Reminders: {pref_value}
"""

        with patch("builtins.open", mock_open(read_data=mock_preferences)):
            result = hook._is_workflow_reminder_enabled()

        assert result == expected

    def test_is_workflow_reminder_enabled_default_when_missing(self):
        """Missing preference should default to enabled (opt-out pattern)."""

        hook = UserPromptSubmitHook()

        mock_preferences = """
## Workflow Preferences

Some other setting: value
"""

        with patch("builtins.open", mock_open(read_data=mock_preferences)):
            result = hook._is_workflow_reminder_enabled()

        assert result is True  # Default to enabled

    def test_is_workflow_reminder_enabled_default_when_file_missing(self):
        """Missing USER_PREFERENCES.md should default to enabled."""

        hook = UserPromptSubmitHook()

        with patch("builtins.open", side_effect=FileNotFoundError):
            result = hook._is_workflow_reminder_enabled()

        assert result is True  # Default to enabled

    def test_is_workflow_reminder_enabled_malformed_value_defaults_enabled(self):
        """Malformed preference values should default to enabled (fail-safe)."""

        hook = UserPromptSubmitHook()

        mock_preferences = """
## Workflow Preferences

Workflow Reminders: maybe-sometimes-yes
"""

        with patch("builtins.open", mock_open(read_data=mock_preferences)):
            result = hook._is_workflow_reminder_enabled()

        assert result is True  # Default to enabled on parse error


class TestRecipeDetection:
    """Test active recipe detection with multi-tier hierarchy."""

    def test_is_recipe_active_detects_env_var_AMPLIFIER_RECIPE_ACTIVE(self):
        """AMPLIFIER_RECIPE_ACTIVE=1 should indicate active recipe."""

        hook = UserPromptSubmitHook()

        with patch.dict(os.environ, {"AMPLIFIER_RECIPE_ACTIVE": "1"}):
            assert hook._is_recipe_active() is True

    def test_is_recipe_active_detects_env_var_RECIPE_SESSION(self):
        """RECIPE_SESSION=<value> should indicate active recipe."""

        hook = UserPromptSubmitHook()

        with patch.dict(os.environ, {"RECIPE_SESSION": "recipe_20251118_143022"}):
            assert hook._is_recipe_active() is True

    def test_is_recipe_active_detects_lock_file(self, tmp_path):
        """Lock file existence should indicate active recipe."""

        hook = UserPromptSubmitHook()
        session_id = "test-session-123"
        lock_file = tmp_path / ".amplifier" / "runtime" / "recipe_locks" / f"{session_id}.lock"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.touch()

        with patch.object(hook, "_get_session_id", return_value=session_id):
            with patch.object(hook, "_get_lock_file_path", return_value=lock_file):
                assert hook._is_recipe_active() is True

    def test_is_recipe_active_fail_safe_default_false(self):
        """No detection should default to NOT active (fail-safe to inject)."""

        hook = UserPromptSubmitHook()

        with patch.dict(os.environ, {}, clear=True):  # No env vars
            with patch.object(hook, "_get_lock_file_path", return_value="/nonexistent/path"):
                assert hook._is_recipe_active() is False


class TestKeywordDetection:
    """Test new topic keyword detection (direction change and implementation)."""

    @pytest.mark.parametrize(
        "prompt",
        [
            "Now let's implement the authentication system",
            "now let's move on to the next feature",
            "NOW LET'S refactor this code",  # case insensitive
            "Next, we should add error handling",
            "next we need to update the docs",
            "NEXT step is testing",
            "Different topic - let's discuss CI/CD",
            "different topic now",
            "Moving on to the deployment phase",
            "moving on to security",
            "Switching to the database layer",
            "switching to frontend work",
        ],
    )
    def test_is_new_workflow_topic_direction_change_keywords(self, prompt):
        """Direction change keywords should trigger new topic detection."""

        hook = UserPromptSubmitHook()
        turn_number = 10  # Not first message

        # Mock state: last classified at turn 5 (gap > 3)
        with patch.object(hook, "_get_last_classified_turn", return_value=5):
            assert hook._is_new_workflow_topic(prompt, turn_number) is True

    @pytest.mark.parametrize(
        "prompt",
        [
            "Implement the user authentication module",
            "implement error logging",
            "IMPLEMENT the retry logic",  # case insensitive
            "Build a caching layer for the API",
            "build the frontend components",
            "Create a feature for notifications",
            "create the database schema",
            "Add support for OAuth2",
            "add pagination to the endpoint",
            "Develop a new reporting dashboard",
            "develop the admin panel",
            "Write code for the payment gateway",
            "write code to handle webhooks",
        ],
    )
    def test_is_new_workflow_topic_implementation_keywords(self, prompt):
        """Implementation keywords should trigger new topic detection."""

        hook = UserPromptSubmitHook()
        turn_number = 10  # Not first message

        # Mock state: last classified at turn 5 (gap > 3)
        with patch.object(hook, "_get_last_classified_turn", return_value=5):
            assert hook._is_new_workflow_topic(prompt, turn_number) is True

    def test_is_new_workflow_topic_no_keywords_returns_false(self):
        """Prompts without keywords should not trigger detection."""

        hook = UserPromptSubmitHook()
        prompt = "Can you explain how this works?"
        turn_number = 10

        with patch.object(hook, "_get_last_classified_turn", return_value=5):
            assert hook._is_new_workflow_topic(prompt, turn_number) is False


class TestFirstMessageDetection:
    """Test first message detection (turn 0)."""

    def test_is_new_workflow_topic_turn_0_is_first_message(self):
        """Turn 0 should always be considered first message."""

        hook = UserPromptSubmitHook()
        prompt = "Hello, let's start working"
        turn_number = 0

        assert hook._is_new_workflow_topic(prompt, turn_number) is True

    def test_is_new_workflow_topic_turn_1_not_first_message(self):
        """Turn 1 should NOT be considered first message (0-indexed)."""

        hook = UserPromptSubmitHook()
        prompt = "Continue with the same task"
        turn_number = 1

        with patch.object(hook, "_get_last_classified_turn", return_value=0):
            # Should require keywords or gap
            assert hook._is_new_workflow_topic(prompt, turn_number) is False


class TestCachingBehavior:
    """Test 3-turn gap caching enforcement."""

    def test_caching_blocks_injection_within_3_turns(self):
        """Keyword detection within 3 turns of last classification should be blocked."""

        hook = UserPromptSubmitHook()
        prompt = "Now let's implement this feature"  # Has keyword

        # Last classified at turn 10, current turn 12 (gap = 2, < 3)
        with patch.object(hook, "_get_last_classified_turn", return_value=10):
            assert hook._is_new_workflow_topic(prompt, turn_number=12) is False

    def test_caching_allows_injection_after_3_turns(self):
        """Keyword detection after 3+ turns should be allowed."""

        hook = UserPromptSubmitHook()
        prompt = "Now let's implement this feature"  # Has keyword

        # Last classified at turn 10, current turn 14 (gap = 4, >= 3)
        with patch.object(hook, "_get_last_classified_turn", return_value=10):
            assert hook._is_new_workflow_topic(prompt, turn_number=14) is True

    def test_caching_turn_gap_exactly_3_allows_injection(self):
        """Exactly 3 turn gap should allow injection (boundary condition)."""

        hook = UserPromptSubmitHook()
        prompt = "Now let's implement this feature"  # Has keyword

        # Last classified at turn 10, current turn 13 (gap = 3, >= 3)
        with patch.object(hook, "_get_last_classified_turn", return_value=10):
            assert hook._is_new_workflow_topic(prompt, turn_number=13) is True


class TestStateSaveLoad:
    """Test state persistence round-trip."""

    def test_save_workflow_classification_state_creates_file(self, tmp_path):
        """Saving state should create JSON file with correct structure."""

        hook = UserPromptSubmitHook()
        session_id = "test-session-123"
        turn_number = 5
        state_file = tmp_path / f"{session_id}.json"

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            hook._save_workflow_classification_state(session_id, turn_number)

        assert state_file.exists()

        with open(state_file, "r") as f:
            data = json.load(f)

        assert data["session_id"] == session_id
        assert data["last_classified_turn"] == turn_number

    def test_save_workflow_classification_state_sets_permissions_0o600(self, tmp_path):
        """State files should have restrictive permissions (0o600)."""

        hook = UserPromptSubmitHook()
        session_id = "test-session-123"
        state_file = tmp_path / f"{session_id}.json"

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            hook._save_workflow_classification_state(session_id, turn_number=5)

        # Check permissions are 0o600 (owner rw, no group/other access)
        assert oct(state_file.stat().st_mode)[-3:] == "600"

    def test_get_last_classified_turn_loads_from_state_file(self, tmp_path):
        """Loading state should return last_classified_turn from JSON."""

        hook = UserPromptSubmitHook()
        session_id = "test-session-123"
        state_file = tmp_path / f"{session_id}.json"

        # Create state file manually
        state_data = {"session_id": session_id, "last_classified_turn": 42}
        state_file.write_text(json.dumps(state_data))

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            last_turn = hook._get_last_classified_turn(session_id)

        assert last_turn == 42

    def test_get_last_classified_turn_returns_none_if_no_state(self, tmp_path):
        """Missing state file should return None (new session)."""

        hook = UserPromptSubmitHook()
        session_id = "new-session"
        state_file = tmp_path / f"{session_id}.json"  # Doesn't exist

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            last_turn = hook._get_last_classified_turn(session_id)

        assert last_turn is None


class TestErrorHandling:
    """Test non-fatal error handling and graceful degradation."""

    def test_workflow_reminder_injection_continues_on_state_error(self):
        """State file errors should not crash the hook (log warning, continue)."""

        hook = UserPromptSubmitHook()
        hook.log = MagicMock()

        # Simulate state file read error
        with patch.object(hook, "_get_last_classified_turn", side_effect=IOError("Disk error")):
            # Should not raise, should log warning
            try:
                result = hook._is_new_workflow_topic("implement feature", turn_number=5)
                # Should degrade gracefully (assume no cache)
                assert result is True  # Keyword detected, no cache blocks it
                hook.log.assert_any_call("Workflow state error (non-fatal)", "WARNING")
            except Exception:
                pytest.fail("Error handling failed - exception not caught")

    def test_workflow_reminder_injection_continues_on_preference_error(self):
        """Preference file errors should default to enabled (fail-safe)."""

        hook = UserPromptSubmitHook()
        hook.log = MagicMock()

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = hook._is_workflow_reminder_enabled()

        assert result is True  # Default to enabled
        hook.log.assert_any_call("Preference read error (non-fatal)", "WARNING")

    def test_workflow_reminder_injection_continues_on_json_parse_error(self, tmp_path):
        """Corrupted JSON state should degrade gracefully."""

        hook = UserPromptSubmitHook()
        hook.log = MagicMock()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        # Create corrupted JSON file
        state_file.write_text("{invalid json content")

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            last_turn = hook._get_last_classified_turn(session_id)

        assert last_turn is None  # Graceful degradation
        hook.log.assert_any_call("JSON parse error (non-fatal)", "WARNING")


class TestReminderTemplateGeneration:
    """Test workflow reminder template content."""

    def test_build_workflow_reminder_returns_correct_template(self):
        """Reminder should match the ~110 token template specification."""

        hook = UserPromptSubmitHook()
        reminder = hook._build_workflow_reminder()

        # Check emoji header
        assert "⚙️" in reminder
        assert "Workflow Classification Reminder" in reminder

        # Check key content
        assert "structured workflows" in reminder
        assert "default-workflow.yaml" in reminder
        assert "recipes" in reminder

        # Check concrete invocation example
        assert "recipes(operation=" in reminder or "How to use" in reminder

        # Token count should be ~110 (rough check: 80-150 tokens)
        # Approximate: 1 token ≈ 4 characters
        assert 320 <= len(reminder) <= 600, f"Template size unexpected: {len(reminder)} chars"

    def test_build_workflow_reminder_no_user_input_interpolation(self):
        """Template should be static (no user input, no f-strings)."""

        hook = UserPromptSubmitHook()
        reminder = hook._build_workflow_reminder()

        # Should not contain any placeholders or variable markers
        assert "{" not in reminder or "recipes(" in reminder  # Only code example braces allowed
        assert "$" not in reminder
        assert "%" not in reminder  # No printf-style formatting


class TestIntegrationWithUserPromptSubmitHook:
    """Test integration into existing user_prompt_submit.py hook."""

    def test_workflow_reminder_added_as_section_4(self):
        """Reminder should be appended after Section 3 (AMPLIHACK.md)."""

        hook = UserPromptSubmitHook()
        hook.log = MagicMock()
        hook.save_metric = MagicMock()

        context = {
            "session_id": "test-session",
            "turn_number": 0,  # First message
            "user_prompt": "implement new feature",
        }

        with patch.object(hook, "_is_workflow_reminder_enabled", return_value=True):
            with patch.object(hook, "_is_recipe_active", return_value=False):
                result = hook.run(context)

        # Should have additionalContext with workflow reminder
        assert "additionalContext" in result
        additional_context = result["additionalContext"]

        # Should contain workflow reminder
        assert "⚙️" in additional_context or "Workflow Classification Reminder" in additional_context

    def test_workflow_reminder_not_added_when_disabled(self):
        """Reminder should not be added if user preference is disabled."""

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()

        context = {
            "session_id": "test-session",
            "turn_number": 0,
            "user_prompt": "implement feature",
        }

        with patch.object(hook, "_is_workflow_reminder_enabled", return_value=False):
            hook.run(context)

        # Metric should be incremented
        hook.save_metric.assert_any_call("workflow_reminder_disabled", 1)

    def test_workflow_reminder_not_added_during_active_recipe(self):
        """Reminder should not be added if recipe is active."""

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()

        context = {
            "session_id": "test-session",
            "turn_number": 0,
            "user_prompt": "implement feature",
        }

        with patch.object(hook, "_is_workflow_reminder_enabled", return_value=True):
            with patch.object(hook, "_is_recipe_active", return_value=True):
                hook.run(context)

        # Metric should be incremented
        hook.save_metric.assert_any_call("workflow_reminder_skipped_recipe", 1)
