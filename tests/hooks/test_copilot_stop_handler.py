"""Tests for the collection-safe copilot stop-handler shims."""

from __future__ import annotations

import json
import os
import stat

import copilot_stop_handler as top_level
from amplihack.hooks import copilot_stop_handler as package_level


def test_top_level_and_package_exports_match():
    """Both compatibility import paths should expose the same shared implementation."""
    assert top_level.get_copilot_continuation is package_level.get_copilot_continuation
    assert top_level.disable_lock_files is package_level.disable_lock_files
    assert top_level._log_decision is package_level._log_decision


def test_log_decision_sanitizes_fields_and_secures_permissions(tmp_path):
    """Decision logging should redact secrets and use owner-only permissions."""
    fake_github_token = "ghp_FAKE_TOKEN_FOR_TESTING_ONLY_DO_NOT_USE"  # pragma: allowlist secret

    top_level._log_decision(
        project_root=tmp_path,
        goal="Investigate key sk-1234567890abcdefghij",  # pragma: allowlist secret
        action="send_input",
        confidence=0.85,
        reasoning=f"Use token {fake_github_token}",
        input_text="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",  # pragma: allowlist secret
        progress_pct=60,
    )

    log_dir = tmp_path / ".claude" / "runtime" / "copilot-decisions"
    log_file = log_dir / "decisions.jsonl"

    entry = json.loads(log_file.read_text(encoding="utf-8").strip())
    serialized = json.dumps(entry)

    assert "sk-1234567890abcdefghij" not in serialized  # pragma: allowlist secret
    assert fake_github_token not in serialized
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in serialized  # pragma: allowlist secret
    assert "sk-***" in entry["goal"]
    assert "ghp_***" in entry["reasoning"]
    assert "***" in entry["input_text"]

    log_dir_mode = stat.S_IMODE(os.stat(log_dir).st_mode)
    log_file_mode = stat.S_IMODE(os.stat(log_file).st_mode)
    assert log_dir_mode == 0o700, f"Expected 0700, got {oct(log_dir_mode)}"
    assert log_file_mode == 0o600, f"Expected 0600, got {oct(log_file_mode)}"


def test_disable_lock_files_removes_related_lock_state(tmp_path):
    """Auto-disable should clear prompt/message companions, not just the lock bit."""
    lock_dir = tmp_path / ".claude" / "runtime" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    for name in (".lock_active", ".lock_goal", ".lock_message", ".continuation_prompt"):
        (lock_dir / name).write_text("x", encoding="utf-8")

    top_level.disable_lock_files(tmp_path)

    for name in (".lock_active", ".lock_goal", ".lock_message", ".continuation_prompt"):
        assert not (lock_dir / name).exists()


# ===========================================================================
# TDD: session_id sanitization mirror in _copilot_stop_handler_impl.py (#3960)
# Tests FAIL until sanitization is applied in the mirror module.
# ===========================================================================


def test_sanitize_session_id_accessible_from_impl():
    """_copilot_stop_handler_impl must export _sanitize_session_id or delegate to lock_tool."""
    import importlib.util
    from pathlib import Path

    # Import the implementation module directly
    impl_path = (
        Path(__file__).resolve().parent.parent.parent
        / "src" / "amplihack" / "hooks" / "_copilot_stop_handler_impl.py"
    )
    spec = importlib.util.spec_from_file_location("_csh_impl_test", impl_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    # Either the impl exposes _sanitize_session_id directly, or it imports it
    # from lock_tool and re-exports it.  Either way, calling it must work.
    assert hasattr(module, "_sanitize_session_id"), (
        "_sanitize_session_id not found in _copilot_stop_handler_impl.py — "
        "mirror the function from lock_tool.py or re-export it"
    )


def test_sanitize_session_id_impl_matches_lock_tool_behavior():
    """Both modules must produce identical sanitization results."""
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent

    # Load lock_tool
    spec_lt = importlib.util.spec_from_file_location(
        "lock_tool_csh_mirror",
        root / ".claude" / "tools" / "amplihack" / "lock_tool.py",
    )
    lt = importlib.util.module_from_spec(spec_lt)
    assert spec_lt.loader is not None
    spec_lt.loader.exec_module(lt)

    # Load impl
    spec_impl = importlib.util.spec_from_file_location(
        "_csh_impl_mirror",
        root / "src" / "amplihack" / "hooks" / "_copilot_stop_handler_impl.py",
    )
    impl = importlib.util.module_from_spec(spec_impl)
    assert spec_impl.loader is not None
    spec_impl.loader.exec_module(impl)

    for test_input in ["../../etc/passwd", "session\ninjected", "session-123", "", "   "]:
        lt_result = lt._sanitize_session_id(test_input)
        impl_result = impl._sanitize_session_id(test_input)
        assert lt_result == impl_result, (
            f"Sanitization mismatch for {test_input!r}: "
            f"lock_tool={lt_result!r}, impl={impl_result!r}"
        )
