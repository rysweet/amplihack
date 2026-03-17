"""Tests for HOOK_CONFIGS / RUST_HOOK_MAP validation against hooks.json.

Bug #3234: HOOK_CONFIGS and RUST_HOOK_MAP are duplicated sources of truth
with no validation against hooks.json. These tests verify that the new
validate_hook_configs_against_json() function catches every divergence type.
"""

import json
import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hooks_json_path():
    """Return the path to the canonical hooks.json used in the repo."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / ".claude" / "tools" / "amplihack" / "hooks" / "hooks.json"


def _load_hooks_json():
    path = _hooks_json_path()
    assert path.exists(), f"hooks.json not found at {path}"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Unit tests — validate_hook_configs_against_json with real data
# ---------------------------------------------------------------------------

class TestValidateHookConfigsReal:
    """Validate the ACTUAL HOOK_CONFIGS / RUST_HOOK_MAP against hooks.json."""

    def test_current_configs_are_valid(self):
        """HOOK_CONFIGS and RUST_HOOK_MAP must match hooks.json right now."""
        from amplihack import validate_hook_configs_against_json

        is_valid, errors = validate_hook_configs_against_json(
            hooks_json_path=_hooks_json_path()
        )
        assert is_valid, (
            "HOOK_CONFIGS/RUST_HOOK_MAP diverged from hooks.json:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    def test_hooks_json_event_types_match_hook_configs(self):
        """Every event type in hooks.json must appear in HOOK_CONFIGS['amplihack']."""
        from amplihack import HOOK_CONFIGS

        hooks_json = _load_hooks_json()
        json_events = set(hooks_json.keys())
        config_events = {h["type"] for h in HOOK_CONFIGS["amplihack"]}

        assert json_events == config_events, (
            f"Event type mismatch.\n"
            f"  In hooks.json only: {json_events - config_events}\n"
            f"  In HOOK_CONFIGS only: {config_events - json_events}"
        )

    def test_rust_hook_map_covers_all_non_python_only_hooks(self):
        """RUST_HOOK_MAP must have an entry for every amplihack hook
        except the documented Python-only ones."""
        from amplihack import HOOK_CONFIGS, RUST_HOOK_MAP

        python_only = {"workflow_classification_reminder.py"}
        all_files = {h["file"] for h in HOOK_CONFIGS["amplihack"]}

        missing = (all_files - python_only) - set(RUST_HOOK_MAP.keys())
        assert not missing, f"RUST_HOOK_MAP missing entries for: {missing}"


# ---------------------------------------------------------------------------
# Unit tests — validate_hook_configs_against_json with synthetic data
# ---------------------------------------------------------------------------

class TestValidateHookConfigsSynthetic:
    """Use crafted hooks.json files to prove every divergence type is caught."""

    def _write_hooks_json(self, tmp_path, data):
        p = tmp_path / "hooks.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    def test_missing_hooks_json_reports_error(self, tmp_path):
        from amplihack import validate_hook_configs_against_json

        is_valid, errors = validate_hook_configs_against_json(
            hooks_json_path=tmp_path / "nonexistent.json"
        )
        assert not is_valid
        assert any("Failed to read" in e or "not found" in e for e in errors)

    def test_invalid_json_reports_error(self, tmp_path):
        from amplihack import validate_hook_configs_against_json

        bad = tmp_path / "hooks.json"
        bad.write_text("{invalid json", encoding="utf-8")

        is_valid, errors = validate_hook_configs_against_json(hooks_json_path=bad)
        assert not is_valid
        assert any("Failed to read" in e for e in errors)

    def test_extra_event_in_json_caught(self, tmp_path):
        """hooks.json has an event type not in HOOK_CONFIGS."""
        from amplihack import HOOK_CONFIGS, validate_hook_configs_against_json

        # Build a hooks.json that matches current HOOK_CONFIGS + one extra
        hooks_json = _load_hooks_json()
        hooks_json["NotifyUser"] = [
            {"hooks": [{"type": "command", "command": "notify.py"}]}
        ]
        p = self._write_hooks_json(tmp_path, hooks_json)

        is_valid, errors = validate_hook_configs_against_json(hooks_json_path=p)
        assert not is_valid
        assert any("missing event type 'NotifyUser'" in e for e in errors)

    def test_extra_event_in_config_caught(self, tmp_path):
        """HOOK_CONFIGS has an event type not in hooks.json."""
        from amplihack import validate_hook_configs_against_json

        # Remove an event from hooks.json
        hooks_json = _load_hooks_json()
        del hooks_json["PreCompact"]
        p = self._write_hooks_json(tmp_path, hooks_json)

        is_valid, errors = validate_hook_configs_against_json(hooks_json_path=p)
        assert not is_valid
        assert any("'PreCompact'" in e and "not present in hooks.json" in e for e in errors)

    def test_file_mismatch_within_event_caught(self, tmp_path):
        """Same event type but different hook files."""
        from amplihack import validate_hook_configs_against_json

        hooks_json = _load_hooks_json()
        # Replace a hook file in SessionStart
        for config in hooks_json["SessionStart"]:
            for hook in config.get("hooks", []):
                hook["command"] = "~/.amplihack/.claude/tools/amplihack/hooks/wrong_hook.py"
        p = self._write_hooks_json(tmp_path, hooks_json)

        is_valid, errors = validate_hook_configs_against_json(hooks_json_path=p)
        assert not is_valid
        assert any("SessionStart" in e for e in errors)

    def test_valid_hooks_json_passes(self, tmp_path):
        """Current hooks.json should pass validation (sanity check)."""
        from amplihack import validate_hook_configs_against_json

        is_valid, errors = validate_hook_configs_against_json(
            hooks_json_path=_hooks_json_path()
        )
        assert is_valid
        assert errors == []


# ---------------------------------------------------------------------------
# Integration test — startup warning
# ---------------------------------------------------------------------------

class TestStartupValidation:
    """Verify _validate_hooks_on_startup emits warnings on divergence."""

    def test_startup_warns_on_divergence(self, capsys):
        from amplihack import _validate_hooks_on_startup

        # Patch to force a divergence
        with patch(
            "amplihack.validate_hook_configs_against_json",
            return_value=(False, ["fake divergence error"]),
        ):
            _validate_hooks_on_startup()

        captured = capsys.readouterr()
        assert "diverged from hooks.json" in captured.err
        assert "fake divergence error" in captured.err

    def test_startup_silent_when_valid(self, capsys):
        from amplihack import _validate_hooks_on_startup

        with patch(
            "amplihack.validate_hook_configs_against_json",
            return_value=(True, []),
        ):
            _validate_hooks_on_startup()

        captured = capsys.readouterr()
        assert "diverged" not in captured.err
