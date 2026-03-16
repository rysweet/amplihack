"""Outside-in tests for the send_input allow-list security feature (#2903).

Tests verify the feature from a user's perspective:
- Safe patterns (y, n, Enter, quit, exit) are accepted without confirmation
- Arbitrary / potentially dangerous patterns are rejected by default
- --confirm (confirm=True) bypasses the allow-list for explicit overrides
- Custom patterns can be loaded from an external JSON config file
- Scenario-level validation works on parsed YAML dictionaries

Usage:
    uv run pytest tests/outside_in/test_safe_send_input_allowlist.py -v
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from amplihack.testing.send_input_allowlist import (
    ALLOWLIST_ENV_VAR,
    DEFAULT_SAFE_PATTERNS,
    UnsafeInputError,
    get_safe_patterns,
    is_safe_pattern,
    validate_scenario_send_inputs,
    validate_send_input,
)

# --------------------------------------------------------------------------- #
# Default safe patterns
# --------------------------------------------------------------------------- #


class TestDefaultSafePatterns:
    """The built-in allow-list covers common interactive responses."""

    @pytest.mark.parametrize(
        "value",
        [
            "y",
            "Y",
            "y\n",
            "Y\n",
            "yes",
            "YES",
            "yes\n",
            "n",
            "N",
            "n\n",
            "no",
            "no\n",
            "\n",
            "",
            "q",
            "q\n",
            "quit",
            "quit\n",
            "exit",
            "exit\n",
        ],
    )
    def test_common_confirmation_patterns_are_safe(self, value: str):
        """Common interactive responses must be accepted without confirmation."""
        assert is_safe_pattern(value), f"Expected {value!r} to be safe"

    @pytest.mark.parametrize(
        "value",
        [
            "rm -rf /",
            "sudo reboot",
            "DROP TABLE users;",
            "import os; os.system('id')",
            "cat /etc/passwd",
            "some arbitrary command",
            "not a safe pattern",
            "1234",
        ],
    )
    def test_arbitrary_values_are_not_safe(self, value: str):
        """Arbitrary / dangerous values must not match the allow-list."""
        assert not is_safe_pattern(value), f"Expected {value!r} to be unsafe"


# --------------------------------------------------------------------------- #
# validate_send_input
# --------------------------------------------------------------------------- #


class TestValidateSendInput:
    """validate_send_input enforces the allow-list or accepts --confirm."""

    def test_safe_value_passes_without_confirm(self):
        """Safe patterns must not raise."""
        validate_send_input("y")  # should not raise
        validate_send_input("\n")  # should not raise
        validate_send_input("exit\n")  # should not raise

    def test_unsafe_value_raises_without_confirm(self):
        """Unsafe patterns raise UnsafeInputError when confirm=False."""
        with pytest.raises(UnsafeInputError) as exc_info:
            validate_send_input("rm -rf /")
        assert "rm -rf /" in str(exc_info.value)
        assert "--confirm" in str(exc_info.value)

    def test_unsafe_value_allowed_with_confirm(self):
        """confirm=True must bypass the allow-list check."""
        validate_send_input("rm -rf /", confirm=True)  # no exception

    def test_unsafe_error_exposes_value(self):
        """UnsafeInputError.value must be set to the rejected input."""
        with pytest.raises(UnsafeInputError) as exc_info:
            validate_send_input("dangerous payload")
        assert exc_info.value.value == "dangerous payload"

    def test_confirm_true_is_explicit_override(self):
        """Passing confirm=True on any value must always succeed."""
        for dangerous in ["sudo rm -rf /", "DROP TABLE;", "passwd root"]:
            validate_send_input(dangerous, confirm=True)


# --------------------------------------------------------------------------- #
# Configurable allow-list via env var
# --------------------------------------------------------------------------- #


class TestConfigurableAllowlist:
    """Users can extend the allow-list via an external JSON file."""

    def test_extra_patterns_loaded_from_env_file(self, tmp_path: Path):
        """Patterns from an env-var-referenced JSON file extend the default list."""
        custom = tmp_path / "allowlist.json"
        custom.write_text(json.dumps(["proceed\n", "ok\n"]), encoding="utf-8")

        with _set_env(ALLOWLIST_ENV_VAR, str(custom)):
            assert is_safe_pattern("proceed\n"), "Custom pattern should be safe"
            assert is_safe_pattern("ok\n"), "Custom pattern should be safe"

    def test_default_patterns_unchanged_with_extras(self, tmp_path: Path):
        """Default patterns must still work when extra config is present."""
        custom = tmp_path / "allowlist.json"
        custom.write_text(json.dumps(["proceed\n"]), encoding="utf-8")

        with _set_env(ALLOWLIST_ENV_VAR, str(custom)):
            assert is_safe_pattern("y"), "Default 'y' must still be safe"
            assert is_safe_pattern("\n"), "Default '\\n' must still be safe"

    def test_missing_env_file_does_not_raise(self):
        """A non-existent file path in the env var must be silently ignored."""
        with _set_env(ALLOWLIST_ENV_VAR, "/nonexistent/path/allowlist.json"):
            patterns = get_safe_patterns()
        assert DEFAULT_SAFE_PATTERNS.issubset(patterns)

    def test_invalid_json_in_env_file_does_not_raise(self, tmp_path: Path):
        """A malformed JSON file must be silently ignored."""
        bad = tmp_path / "bad.json"
        bad.write_text("not valid json", encoding="utf-8")

        with _set_env(ALLOWLIST_ENV_VAR, str(bad)):
            patterns = get_safe_patterns()
        assert DEFAULT_SAFE_PATTERNS.issubset(patterns)

    def test_non_array_json_in_env_file_does_not_raise(self, tmp_path: Path):
        """A JSON object (not array) in the config file must be silently ignored."""
        bad = tmp_path / "obj.json"
        bad.write_text(json.dumps({"proceed": True}), encoding="utf-8")

        with _set_env(ALLOWLIST_ENV_VAR, str(bad)):
            patterns = get_safe_patterns()
        assert DEFAULT_SAFE_PATTERNS.issubset(patterns)


# --------------------------------------------------------------------------- #
# Scenario-level validation
# --------------------------------------------------------------------------- #


class TestValidateScenarioSendInputs:
    """validate_scenario_send_inputs checks an entire YAML scenario dict."""

    def _make_scenario(self, *send_input_values: str) -> dict:
        """Build a minimal scenario dict with the given send_input values."""
        steps = []
        for v in send_input_values:
            steps.append({"action": "send_input", "value": v})
        return {"name": "test", "steps": steps}

    def test_all_safe_inputs_returns_empty_list(self):
        """A scenario with only safe inputs must return an empty list."""
        scenario = self._make_scenario("y\n", "\n", "exit\n")
        unsafe = validate_scenario_send_inputs(scenario)
        assert unsafe == []

    def test_unsafe_input_raises_by_default(self):
        """A scenario with an unsafe value must raise UnsafeInputError."""
        scenario = self._make_scenario("y\n", "rm -rf /", "\n")
        with pytest.raises(UnsafeInputError) as exc_info:
            validate_scenario_send_inputs(scenario)
        assert "rm -rf /" in str(exc_info.value)

    def test_confirm_collects_all_unsafe(self):
        """With confirm=True, all unsafe values are collected rather than raising."""
        scenario = self._make_scenario("y\n", "cmd1", "cmd2", "n\n")
        unsafe = validate_scenario_send_inputs(scenario, confirm=True)
        assert "cmd1" in unsafe
        assert "cmd2" in unsafe
        assert len(unsafe) == 2

    def test_non_send_input_steps_ignored(self):
        """Steps with actions other than send_input must not be validated."""
        scenario = {
            "steps": [
                {"action": "launch", "target": "./app"},
                {"action": "verify_output", "contains": "ready"},
                {"action": "send_input", "value": "y\n"},
            ]
        }
        unsafe = validate_scenario_send_inputs(scenario)
        assert unsafe == []

    def test_empty_steps_returns_empty_list(self):
        """A scenario with no steps must return an empty list."""
        unsafe = validate_scenario_send_inputs({"steps": []})
        assert unsafe == []

    def test_missing_steps_key_returns_empty_list(self):
        """A scenario dict without 'steps' must return an empty list."""
        unsafe = validate_scenario_send_inputs({})
        assert unsafe == []

    def test_numeric_value_coerced_to_string(self):
        """send_input values that are not strings must be coerced and validated."""
        scenario = {"steps": [{"action": "send_input", "value": 1}]}
        # "1" is not on the safe list
        with pytest.raises(UnsafeInputError):
            validate_scenario_send_inputs(scenario)


# --------------------------------------------------------------------------- #
# get_safe_patterns
# --------------------------------------------------------------------------- #


class TestGetSafePatterns:
    """get_safe_patterns returns an immutable-safe frozenset."""

    def test_returns_frozenset(self):
        """get_safe_patterns must return a frozenset."""
        assert isinstance(get_safe_patterns(), frozenset)

    def test_includes_all_defaults(self):
        """Default patterns must all appear in the returned set."""
        patterns = get_safe_patterns()
        assert DEFAULT_SAFE_PATTERNS.issubset(patterns)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


class _set_env:
    """Context manager that temporarily sets an environment variable."""

    def __init__(self, key: str, value: str) -> None:
        self._key = key
        self._value = value
        self._old: str | None = None

    def __enter__(self) -> _set_env:
        self._old = os.environ.get(self._key)
        os.environ[self._key] = self._value
        return self

    def __exit__(self, *_) -> None:
        if self._old is None:
            os.environ.pop(self._key, None)
        else:
            os.environ[self._key] = self._old
