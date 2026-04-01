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
