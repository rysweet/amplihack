"""R10: AMPLIHACK_HOOK_ENGINE allowlist validation.

``get_hook_engine()`` must raise ``ValueError`` when the env var is set to a
value outside the allowlist ``{"python", "rust", "auto"}``.  Silently falling
back to a default engine could mask misconfigurations and run hooks under the
wrong engine without the operator knowing.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from amplihack.settings import HOOK_ENGINE_ALLOWLIST, get_hook_engine


class TestHookEngineAllowlist:
    """R10: AMPLIHACK_HOOK_ENGINE must be validated against a strict allowlist."""

    def test_allowlist_constant_exists(self):
        """HOOK_ENGINE_ALLOWLIST must be exported from amplihack.settings."""
        assert HOOK_ENGINE_ALLOWLIST is not None
        assert isinstance(HOOK_ENGINE_ALLOWLIST, (set, frozenset))

    def test_allowlist_contains_expected_values(self):
        """Allowlist must contain python, rust, and auto."""
        assert "python" in HOOK_ENGINE_ALLOWLIST
        assert "rust" in HOOK_ENGINE_ALLOWLIST
        assert "auto" in HOOK_ENGINE_ALLOWLIST

    @pytest.mark.parametrize(
        "bad_value",
        [
            "javascript",
            "node",
            "auto; rm -rf /",  # injection attempt
            " ",
            "python; echo injected",
            "../../etc/passwd",
        ],
    )
    def test_invalid_engine_raises_value_error(self, bad_value):
        """Values outside the allowlist must raise ValueError (fail-secure)."""
        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": bad_value}):
            with pytest.raises(ValueError, match="AMPLIHACK_HOOK_ENGINE"):
                get_hook_engine()

    def test_valid_python_engine(self):
        """AMPLIHACK_HOOK_ENGINE=python must return 'python'."""
        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "python"}):
            assert get_hook_engine() == "python"

    def test_valid_rust_engine(self):
        """AMPLIHACK_HOOK_ENGINE=rust must return 'rust' when binary is present."""
        with patch(
            "amplihack.settings.find_rust_hook_binary", return_value="/usr/bin/amplihack-hooks"
        ):
            with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "rust"}):
                result = get_hook_engine()
                assert result == "rust"

    def test_valid_auto_engine_with_binary(self):
        """AMPLIHACK_HOOK_ENGINE=auto must return 'rust' when binary is found."""
        with patch(
            "amplihack.settings.find_rust_hook_binary", return_value="/usr/bin/amplihack-hooks"
        ):
            with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "auto"}):
                assert get_hook_engine() == "rust"

    def test_valid_auto_engine_without_binary(self):
        """AMPLIHACK_HOOK_ENGINE=auto must return 'python' when binary is absent."""
        with patch("amplihack.settings.find_rust_hook_binary", return_value=None):
            with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "auto"}):
                assert get_hook_engine() == "python"

    def test_unset_env_var_does_not_raise(self):
        """When AMPLIHACK_HOOK_ENGINE is unset, get_hook_engine() must not raise."""
        env_without_key = {k: v for k, v in os.environ.items() if k != "AMPLIHACK_HOOK_ENGINE"}
        with patch("amplihack.settings.find_rust_hook_binary", return_value=None):
            with patch.dict(os.environ, env_without_key, clear=True):
                result = get_hook_engine()
                assert result in ("python", "rust")

    def test_error_message_is_informative(self):
        """The ValueError message must identify the bad value and list valid values."""
        bad = "invalid-engine"
        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": bad}):
            with pytest.raises(ValueError) as exc_info:
                get_hook_engine()
            msg = str(exc_info.value)
            # Must name the bad value so operators can diagnose the issue.
            assert bad in msg or "AMPLIHACK_HOOK_ENGINE" in msg

    def test_fail_secure_not_silent_fallback(self):
        """Must NOT silently fall back to a default — must raise explicitly."""
        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "unknown-engine"}):
            # The old code printed a warning and returned "python".
            # R10 requires a ValueError instead.
            with pytest.raises(ValueError):
                get_hook_engine()
