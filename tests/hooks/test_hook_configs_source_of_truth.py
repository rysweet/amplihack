"""Tests for bug #3234: validate HOOK_CONFIGS and RUST_HOOK_MAP against hooks.json.

Ensures the three sources of truth (HOOK_CONFIGS, RUST_HOOK_MAP, hooks.json)
never silently diverge.
"""

import json
import os
import tempfile

import pytest


def _hooks_json_path():
    """Return the path to hooks.json in the repo."""
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        ".claude", "tools", "amplihack", "hooks", "hooks.json",
    )


# ---------------------------------------------------------------------------
# Test: current codebase is internally consistent
# ---------------------------------------------------------------------------

def test_current_configs_match_hooks_json():
    """HOOK_CONFIGS and RUST_HOOK_MAP must match hooks.json as-is."""
    from amplihack import validate_hook_configs_against_json

    path = _hooks_json_path()
    if not os.path.isfile(path):
        pytest.skip("hooks.json not found in repo tree")

    valid, errors = validate_hook_configs_against_json(hooks_json_path=path)
    assert valid, "HOOK_CONFIGS/RUST_HOOK_MAP diverge from hooks.json:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Test: validation catches a hook added to hooks.json but not HOOK_CONFIGS
# ---------------------------------------------------------------------------

def test_detects_hook_in_json_not_in_configs(tmp_path):
    """Adding a hook to hooks.json without updating HOOK_CONFIGS is caught."""
    from amplihack import validate_hook_configs_against_json

    path = _hooks_json_path()
    if not os.path.isfile(path):
        pytest.skip("hooks.json not found in repo tree")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Inject an extra hook that HOOK_CONFIGS does not know about
    data["NotifyAdmin"] = [
        {"hooks": [{"type": "command", "command": "~/.amplihack/.claude/tools/amplihack/hooks/notify_admin.py", "timeout": 5}]}
    ]

    modified = tmp_path / "hooks.json"
    modified.write_text(json.dumps(data, indent=2))

    valid, errors = validate_hook_configs_against_json(hooks_json_path=str(modified))
    assert not valid, "Should detect hook in hooks.json missing from HOOK_CONFIGS"
    assert any("notify_admin.py" in e for e in errors)


# ---------------------------------------------------------------------------
# Test: validation catches a hook in HOOK_CONFIGS but removed from hooks.json
# ---------------------------------------------------------------------------

def test_detects_hook_in_configs_not_in_json(tmp_path):
    """Removing a hook from hooks.json without updating HOOK_CONFIGS is caught."""
    from amplihack import validate_hook_configs_against_json

    path = _hooks_json_path()
    if not os.path.isfile(path):
        pytest.skip("hooks.json not found in repo tree")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Remove PreCompact from hooks.json
    data.pop("PreCompact", None)

    modified = tmp_path / "hooks.json"
    modified.write_text(json.dumps(data, indent=2))

    valid, errors = validate_hook_configs_against_json(hooks_json_path=str(modified))
    assert not valid, "Should detect hook in HOOK_CONFIGS missing from hooks.json"
    assert any("pre_compact.py" in e for e in errors)


# ---------------------------------------------------------------------------
# Test: validation catches timeout mismatch
# ---------------------------------------------------------------------------

def test_detects_timeout_mismatch(tmp_path):
    """Changing a timeout in hooks.json without updating HOOK_CONFIGS is caught."""
    from amplihack import validate_hook_configs_against_json

    path = _hooks_json_path()
    if not os.path.isfile(path):
        pytest.skip("hooks.json not found in repo tree")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Alter the SessionStart timeout from 10 to 999
    for config in data.get("SessionStart", []):
        for hook in config.get("hooks", []):
            hook["timeout"] = 999

    modified = tmp_path / "hooks.json"
    modified.write_text(json.dumps(data, indent=2))

    valid, errors = validate_hook_configs_against_json(hooks_json_path=str(modified))
    assert not valid, "Should detect timeout mismatch"
    assert any("timeout mismatch" in e for e in errors)


# ---------------------------------------------------------------------------
# Test: validation catches RUST_HOOK_MAP entry not in HOOK_CONFIGS or JSON
# ---------------------------------------------------------------------------

def test_detects_orphan_rust_hook_map_entry(tmp_path, monkeypatch):
    """RUST_HOOK_MAP entry that is in neither HOOK_CONFIGS nor hooks.json is caught."""
    import amplihack

    path = _hooks_json_path()
    if not os.path.isfile(path):
        pytest.skip("hooks.json not found in repo tree")

    # Temporarily add a bogus entry to RUST_HOOK_MAP
    original = dict(amplihack.RUST_HOOK_MAP)
    amplihack.RUST_HOOK_MAP["phantom_hook.py"] = "phantom-hook"
    try:
        valid, errors = amplihack.validate_hook_configs_against_json(hooks_json_path=path)
        assert not valid, "Should detect orphan RUST_HOOK_MAP entry"
        assert any("phantom_hook.py" in e for e in errors)
    finally:
        amplihack.RUST_HOOK_MAP.clear()
        amplihack.RUST_HOOK_MAP.update(original)


# ---------------------------------------------------------------------------
# Test: missing hooks.json is gracefully skipped
# ---------------------------------------------------------------------------

def test_missing_hooks_json_is_not_an_error():
    """When hooks.json is absent the validation should pass (not crash)."""
    from amplihack import validate_hook_configs_against_json

    valid, errors = validate_hook_configs_against_json(hooks_json_path="/nonexistent/hooks.json")
    # A non-existent explicit path should report an error (can't read it)
    assert not valid


def test_auto_resolve_missing_gracefully(monkeypatch):
    """When hooks.json cannot be auto-resolved, validation is skipped (pass)."""
    import amplihack
    monkeypatch.setattr(amplihack, "_resolve_hooks_json_path", lambda: None)
    valid, errors = amplihack.validate_hook_configs_against_json()
    assert valid
    assert errors == []
