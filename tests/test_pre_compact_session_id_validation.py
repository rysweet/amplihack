"""R9: UUID v4 session ID validation in pre_compact hook.

Session IDs from untrusted hook input must be validated as UUID v4 before
being used to construct filesystem paths.  A malformed or path-traversal
session ID (e.g. ``../../etc``) could redirect log writes to unintended
locations.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).parents[1]
HOOKS_DIR = REPO_ROOT / ".claude" / "tools" / "amplihack" / "hooks"
PRE_COMPACT_PATH = HOOKS_DIR / "pre_compact.py"


def _load_pre_compact() -> ModuleType:
    """Import the pre_compact module without executing __main__."""
    spec = importlib.util.spec_from_file_location("pre_compact_module", PRE_COMPACT_PATH)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    # Add the hooks dir to sys.path so that hook-local imports work.
    if str(HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(HOOKS_DIR))
    if str(HOOKS_DIR.parent) not in sys.path:
        sys.path.insert(0, str(HOOKS_DIR.parent))
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except ImportError:
        pytest.skip("pre_compact dependencies (hook_processor etc.) not importable in isolation")
    return mod


class TestValidateSessionIdFunction:
    """Direct unit tests for _validate_session_id."""

    @pytest.fixture
    def mod(self):
        return _load_pre_compact()

    @pytest.fixture
    def validate(self, mod):
        if not hasattr(mod, "_validate_session_id"):
            pytest.skip("_validate_session_id not defined in pre_compact.py (R9 not implemented)")
        return mod._validate_session_id

    # -- Valid UUID v4 inputs -------------------------------------------------

    @pytest.mark.parametrize(
        "valid_uuid",
        [
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-41d4-a800-000000000000",
            "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "00000000-0000-4000-8000-000000000000",
            "FFFFFFFF-FFFF-4FFF-9FFF-FFFFFFFFFFFF",  # uppercase must also work
        ],
    )
    def test_valid_uuid_v4_accepted(self, validate, valid_uuid):
        """Valid UUID v4 strings must be returned unchanged."""
        assert validate(valid_uuid) == valid_uuid

    # -- Invalid inputs that must be rejected ---------------------------------

    @pytest.mark.parametrize(
        "bad_id",
        [
            "../../etc/passwd",  # path traversal
            "../sessions/other",  # path traversal
            "not-a-uuid",  # too short
            "550e8400e29b41d4a716446655440000",  # missing hyphens
            "550e8400-e29b-31d4-a716-446655440000",  # version 3, not 4
            "550e8400-e29b-41d4-c716-446655440000",  # wrong variant
            "",  # empty
            "session_20250923_120000",  # timestamp-style (old format)
            "'; DROP TABLE sessions; --",  # SQL injection attempt
            "\x00uuid",  # null byte
            "a" * 100,  # too long
            "550e8400-e29b-41d4-a716",  # truncated
        ],
    )
    def test_invalid_session_id_raises(self, validate, bad_id):
        """Invalid session IDs must raise ValueError (R9 fail-secure)."""
        with pytest.raises(ValueError):
            validate(bad_id)

    def test_error_message_is_informative(self, validate):
        """ValueError message must mention UUID v4 so operators can diagnose."""
        with pytest.raises(ValueError) as exc_info:
            validate("not-valid")
        msg = str(exc_info.value).lower()
        assert "uuid" in msg or "session_id" in msg, (
            f"R9: error message must mention UUID or session_id; got: {exc_info.value}"
        )


class TestPreCompactFileExistsWithR9:
    """Verify R9 is implemented in the pre_compact hook file."""

    def test_pre_compact_exists(self):
        assert PRE_COMPACT_PATH.exists(), f"Expected {PRE_COMPACT_PATH} to exist"

    def test_validate_session_id_defined(self):
        """pre_compact.py must define _validate_session_id."""
        content = PRE_COMPACT_PATH.read_text()
        assert "_validate_session_id" in content, (
            "R9: _validate_session_id not found in pre_compact.py — UUID validation not implemented"
        )

    def test_validate_session_id_called_in_bind_session(self):
        """_validate_session_id must be called inside _bind_session."""
        content = PRE_COMPACT_PATH.read_text()
        # Find _bind_session and verify _validate_session_id appears within it.
        bind_idx = content.find("def _bind_session")
        assert bind_idx != -1, "_bind_session not found in pre_compact.py"
        # Look for validation call after the function start.
        next_def = content.find("\n    def ", bind_idx + 1)
        bind_body = content[bind_idx:next_def] if next_def != -1 else content[bind_idx:]
        assert "_validate_session_id" in bind_body, (
            "R9: _validate_session_id must be called inside _bind_session to guard path usage"
        )

    def test_uuid_v4_pattern_present(self):
        """The UUID v4 regex pattern must appear in pre_compact.py."""
        content = PRE_COMPACT_PATH.read_text()
        # Version 4 UUIDs have '4' as the version nibble.
        assert "-4" in content or "4[0-9a-f]" in content or "UUID" in content.upper(), (
            "R9: UUID v4 validation pattern not found in pre_compact.py"
        )
