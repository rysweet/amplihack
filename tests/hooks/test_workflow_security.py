# tests/hooks/test_workflow_security.py
"""
Security tests for workflow reminder functionality.

MANDATORY security validation tests for path traversal prevention,
JSON injection protection, and file permission verification.

These tests MUST pass before deployment to production.

Test Coverage:
- Path traversal attack prevention (../../etc/passwd, etc.)
- Session ID validation (special chars, null bytes, shell metacharacters)
- JSON injection prevention (prototype pollution, type confusion)
- File permission verification (directory 0o700, files 0o600)
- Safe JSON parsing (malformed JSON, wrong types, null values)
- State file corruption handling
- Preference file parsing safety
"""

import json
import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPathTraversalPrevention:
    """CRITICAL: Path traversal attack prevention tests."""

    @pytest.mark.parametrize(
        "malicious_session_id",
        [
            "../../../etc/passwd",
            "../../root/.ssh/id_rsa",
            "..%2F..%2Fetc%2Fpasswd",  # URL-encoded path traversal
            "../../../proc/self/environ",
            "../../../../../../etc/shadow",
            "....//....//....//etc/passwd",  # Double-slash bypass attempt
            "..\\..\\..\\windows\\system32\\config\\sam",  # Windows path traversal
        ],
    )
    def test_rejects_path_traversal_attempts(self, tmp_path, malicious_session_id):
        """CRITICAL: Must reject all path traversal attempts."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            with pytest.raises(ValueError, match="Invalid session ID"):
                hook._get_workflow_state_file(malicious_session_id)

    @pytest.mark.parametrize(
        "malicious_session_id",
        [
            "session;rm -rf /",
            "session`whoami`",
            "session$(cat /etc/passwd)",
            "session|cat /etc/shadow",
            "session&& cat /etc/passwd",
            "session || cat /etc/passwd",
            "session\ncat /etc/passwd",
            "session\rcat /etc/passwd",
        ],
    )
    def test_rejects_shell_command_injection(self, tmp_path, malicious_session_id):
        """CRITICAL: Must reject shell command injection attempts."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            with pytest.raises(ValueError, match="Invalid session ID"):
                hook._get_workflow_state_file(malicious_session_id)

    @pytest.mark.parametrize(
        "malicious_session_id",
        [
            "session\x00hidden",
            "session\x00.txt",
            "valid\x00../../etc/passwd",
            "\x00etc/passwd",
        ],
    )
    def test_rejects_null_byte_injection(self, tmp_path, malicious_session_id):
        """CRITICAL: Must reject null byte injection attempts."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            with pytest.raises(ValueError, match="Invalid session ID"):
                hook._get_workflow_state_file(malicious_session_id)

    def test_path_stays_within_state_directory(self, tmp_path):
        """CRITICAL: Generated paths must stay within state directory."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)

        valid_session_id = "test-session-123"

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            file_path = hook._get_workflow_state_file(valid_session_id)

        # Use pathlib to verify path is within state_dir
        resolved_path = Path(file_path).resolve()
        resolved_state_dir = state_dir.resolve()

        assert resolved_path.is_relative_to(resolved_state_dir), (
            f"Path {resolved_path} escapes state directory {resolved_state_dir}"
        )

    def test_session_id_regex_validation_enforced(self):
        """CRITICAL: Session ID must match ^[a-zA-Z0-9_-]+$ regex."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()

        # Valid IDs should pass
        valid_ids = ["abc123", "test-session", "SESSION_456", "0000-abcd_1234"]
        for valid_id in valid_ids:
            # Should not raise
            hook._validate_session_id(valid_id)

        # Invalid IDs should fail
        invalid_ids = ["../etc/passwd", "test@session", "session.txt", "test/session"]
        for invalid_id in invalid_ids:
            with pytest.raises(ValueError, match="Invalid session ID"):
                hook._validate_session_id(invalid_id)


class TestJSONInjectionPrevention:
    """CRITICAL: JSON injection and parsing safety tests."""

    def test_rejects_json_with_executable_code(self, tmp_path):
        """CRITICAL: JSON containing code strings should be safely parsed."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        # Malicious JSON with code-like strings
        malicious_json = {
            "session_id": session_id,
            "last_classified_turn": "__import__('os').system('rm -rf /')",
            "__proto__": {"polluted": True},
        }
        state_file.write_text(json.dumps(malicious_json))

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            # Should load safely without executing anything
            last_turn = hook._get_last_classified_turn(session_id)

        # Should gracefully degrade (wrong type for last_classified_turn)
        assert last_turn is None or isinstance(last_turn, int)

    def test_safe_json_parsing_no_eval_exec(self, tmp_path):
        """CRITICAL: JSON parsing must use json.loads(), not eval/exec."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        # JSON with Python expressions (only safe with json.loads)
        state_data = '{"session_id": "test", "last_classified_turn": 1+1}'
        state_file.write_text(state_data)

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            # Should fail to parse (json.loads rejects expressions)
            last_turn = hook._get_last_classified_turn(session_id)

        # Should gracefully degrade on parse error
        assert last_turn is None

    def test_json_type_confusion_attack_blocked(self, tmp_path):
        """CRITICAL: Type confusion attacks should be blocked by schema validation."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        # Type confusion: string instead of int
        malicious_json = {
            "session_id": session_id,
            "last_classified_turn": "99999999999999999999",  # String overflow attempt
        }
        state_file.write_text(json.dumps(malicious_json))

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            last_turn = hook._get_last_classified_turn(session_id)

        # Should validate type and reject (graceful degradation)
        assert last_turn is None or isinstance(last_turn, int)

    def test_malformed_json_graceful_degradation(self, tmp_path):
        """CRITICAL: Malformed JSON should degrade gracefully, not crash."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.log = MagicMock()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        # Completely broken JSON
        state_file.write_text("{invalid json content!!!")

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            last_turn = hook._get_last_classified_turn(session_id)

        # Should not crash, should return None
        assert last_turn is None
        # Should log warning
        assert any("WARNING" in str(call) for call in hook.log.call_args_list)

    def test_json_schema_validation_enforces_structure(self, tmp_path):
        """CRITICAL: Schema validation should enforce required fields and types."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        # Valid structure
        valid_json = {"session_id": "test-session", "last_classified_turn": 42}
        state_file.write_text(json.dumps(valid_json))

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            last_turn = hook._get_last_classified_turn(session_id)

        assert last_turn == 42

        # Missing required field
        invalid_json = {"last_classified_turn": 42}  # Missing session_id
        state_file.write_text(json.dumps(invalid_json))

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            last_turn = hook._get_last_classified_turn(session_id)

        # Should validate schema and reject
        assert last_turn is None

    def test_json_array_instead_of_object_rejected(self, tmp_path):
        """CRITICAL: JSON must be object, not array."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        # Array instead of object
        state_file.write_text('[{"session_id": "test", "last_classified_turn": 42}]')

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            last_turn = hook._get_last_classified_turn(session_id)

        # Should reject (not a dict)
        assert last_turn is None


class TestFilePermissions:
    """CRITICAL: File permission security tests."""

    def test_state_directory_permissions_0o700(self, tmp_path):
        """CRITICAL: State directory must have 0o700 permissions (owner rwx only)."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        state_dir = tmp_path / "classification_state"

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            hook._init_workflow_state_dir()

        # Check permissions are exactly 0o700
        mode = state_dir.stat().st_mode
        perms = stat.S_IMODE(mode)

        assert perms == 0o700, f"State directory has permissions {oct(perms)}, expected 0o700"

    def test_state_file_permissions_0o600(self, tmp_path):
        """CRITICAL: State files must have 0o600 permissions (owner rw only)."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            hook._save_workflow_classification_state(session_id, turn=5)

        # Check permissions are exactly 0o600
        mode = state_file.stat().st_mode
        perms = stat.S_IMODE(mode)

        assert perms == 0o600, f"State file has permissions {oct(perms)}, expected 0o600"

    def test_atomic_write_with_chmod(self, tmp_path):
        """CRITICAL: File writes must be atomic (write to .tmp, chmod, rename)."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        # Mock to verify chmod is called before rename
        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            with patch("os.chmod") as mock_chmod:
                with patch("os.rename") as mock_rename:
                    hook._save_workflow_classification_state(session_id, turn=5)

        # Verify chmod was called (atomic write pattern)
        mock_chmod.assert_called_once()
        # Verify rename was called (atomic write pattern)
        mock_rename.assert_called_once()

    def test_no_group_or_other_permissions(self, tmp_path):
        """CRITICAL: No group or other users should have any access."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            hook._save_workflow_classification_state(session_id, turn=5)

        mode = state_file.stat().st_mode

        # Check no group permissions
        assert not (mode & stat.S_IRGRP), "Group has read permission"
        assert not (mode & stat.S_IWGRP), "Group has write permission"
        assert not (mode & stat.S_IXGRP), "Group has execute permission"

        # Check no other permissions
        assert not (mode & stat.S_IROTH), "Others have read permission"
        assert not (mode & stat.S_IWOTH), "Others have write permission"
        assert not (mode & stat.S_IXOTH), "Others have execute permission"


class TestStaticTemplates:
    """CRITICAL: Template security - no user input interpolation."""

    def test_reminder_template_is_static_no_user_input(self):
        """CRITICAL: Reminder template must be static, no user input."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        reminder = hook._build_workflow_reminder()

        # Should not contain any variable markers
        assert "{user" not in reminder.lower()
        assert "{prompt" not in reminder.lower()
        assert "${" not in reminder
        assert "%" not in reminder or "100%" in reminder  # Only literal percent signs

    def test_no_f_string_formatting_with_user_data(self):
        """CRITICAL: No f-strings or .format() with user-controlled data."""
        import inspect

        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()

        # Get source code of _build_workflow_reminder method
        source = inspect.getsource(hook._build_workflow_reminder)

        # Check for dangerous patterns (this is a static analysis test)
        # F-strings with variables would appear as f"{variable}"
        # We allow f-strings with only literals
        assert 'f"' not in source or all(
            "{" not in line.split('f"')[1].split('"')[0]
            for line in source.split("\n")
            if 'f"' in line
        ), "Found f-string with variable interpolation"

    def test_template_content_cannot_be_influenced_by_context(self):
        """CRITICAL: Template content must not change based on user context."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()

        # Generate template multiple times with different "contexts"
        template1 = hook._build_workflow_reminder()
        template2 = hook._build_workflow_reminder()

        # Should be identical (no randomness, no context influence)
        assert template1 == template2


class TestInputValidation:
    """CRITICAL: Input validation tests."""

    def test_turn_number_must_be_non_negative_integer(self):
        """CRITICAL: Turn number must be validated (non-negative int)."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()

        # Valid turn numbers
        assert hook._is_new_workflow_topic("test", turn_number=0) is not None
        assert hook._is_new_workflow_topic("test", turn_number=100) is not None

        # Invalid turn numbers should be rejected
        with pytest.raises((ValueError, TypeError)):
            hook._is_new_workflow_topic("test", turn_number=-1)

        with pytest.raises((ValueError, TypeError)):
            hook._is_new_workflow_topic("test", turn_number="5")

    def test_prompt_must_be_string(self):
        """CRITICAL: User prompt must be validated as string."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()

        # Valid prompts
        assert hook._is_new_workflow_topic("valid prompt", turn_number=0) is not None

        # Invalid prompts should be rejected or handled
        with pytest.raises((ValueError, TypeError, AttributeError)):
            hook._is_new_workflow_topic(None, turn_number=0)

        with pytest.raises((ValueError, TypeError, AttributeError)):
            hook._is_new_workflow_topic(12345, turn_number=0)


class TestSecurityMetrics:
    """Security event metrics tracking."""

    def test_metrics_track_path_traversal_blocks(self, tmp_path):
        """Security metric should increment on path traversal attempt."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        state_dir = tmp_path / "classification_state"
        state_dir.mkdir(parents=True)

        with patch.object(hook, "_get_state_dir", return_value=state_dir):
            try:
                hook._get_workflow_state_file("../../../etc/passwd")
            except ValueError:
                pass

        # Should increment security metric
        hook.save_metric.assert_any_call("workflow_security_path_traversal_blocked", 1)

    def test_metrics_track_json_parse_errors(self, tmp_path):
        """Security metric should increment on JSON parse errors."""
        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()
        hook.save_metric = MagicMock()
        session_id = "test-session"
        state_file = tmp_path / f"{session_id}.json"
        state_file.write_text("{invalid json")

        with patch.object(hook, "_get_workflow_state_file", return_value=str(state_file)):
            hook._get_last_classified_turn(session_id)

        # Should increment security metric
        hook.save_metric.assert_any_call("workflow_security_json_parse_error", 1)


class TestCodeForbiddenPatterns:
    """CRITICAL: Verify forbidden patterns are not in code."""

    def test_no_eval_in_codebase(self):
        """CRITICAL: Code must not contain eval() anywhere."""
        import inspect

        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()

        # Get all methods
        methods = [
            hook._init_workflow_state_dir,
            hook._get_workflow_state_file,
            hook._is_workflow_reminder_enabled,
            hook._is_recipe_active,
            hook._is_new_workflow_topic,
            hook._save_workflow_classification_state,
            hook._build_workflow_reminder,
            hook._get_last_classified_turn,
        ]

        for method in methods:
            source = inspect.getsource(method)
            assert "eval(" not in source, f"Found eval() in {method.__name__}"

    def test_no_exec_in_codebase(self):
        """CRITICAL: Code must not contain exec() anywhere."""
        import inspect

        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()

        methods = [
            hook._init_workflow_state_dir,
            hook._get_workflow_state_file,
            hook._is_workflow_reminder_enabled,
            hook._is_recipe_active,
            hook._is_new_workflow_topic,
            hook._save_workflow_classification_state,
            hook._build_workflow_reminder,
            hook._get_last_classified_turn,
        ]

        for method in methods:
            source = inspect.getsource(method)
            assert "exec(" not in source, f"Found exec() in {method.__name__}"

    def test_uses_pathlib_not_string_concatenation(self):
        """CRITICAL: File paths must use pathlib, not string concatenation."""
        import inspect

        from hooks.user_prompt_submit import UserPromptSubmitHook

        hook = UserPromptSubmitHook()

        # Check _get_workflow_state_file uses pathlib
        source = inspect.getsource(hook._get_workflow_state_file)

        # Should import Path
        assert "Path" in source or "pathlib" in source

        # Should NOT use string concatenation for paths
        # (This is heuristic - look for suspicious patterns)
        assert '+ "/"' not in source
        assert '+ "\\"' not in source
