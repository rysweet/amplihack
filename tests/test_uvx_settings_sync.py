"""Tests for UVX settings template synchronization."""

import json
from pathlib import Path

import pytest

from amplihack.utils.sync_validator import (
    compare_hooks,
    normalize_hook_path,
    normalize_hooks_dict,
    validate_hooks_sync,
)


@pytest.fixture
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def settings_path(project_root):
    """Get path to authoritative settings.json."""
    return project_root / ".claude" / "settings.json"


@pytest.fixture
def template_path(project_root):
    """Get path to UVX settings template."""
    return project_root / "src" / "amplihack" / "utils" / "uvx_settings_template.json"


def test_normalize_hook_path():
    """Test hook path normalization."""
    # Test with $CLAUDE_PROJECT_DIR prefix
    assert normalize_hook_path("$CLAUDE_PROJECT_DIR/.claude/tools/hook.py") == ".claude/tools/hook.py"

    # Test without prefix
    assert normalize_hook_path(".claude/tools/hook.py") == ".claude/tools/hook.py"

    # Test empty string
    assert normalize_hook_path("") == ""


def test_settings_files_exist(settings_path, template_path):
    """Verify required settings files exist."""
    assert settings_path.exists(), f"Settings file not found: {settings_path}"
    assert template_path.exists(), f"Template file not found: {template_path}"


def test_settings_files_valid_json(settings_path, template_path):
    """Verify settings files contain valid JSON."""
    with open(settings_path) as f:
        settings_data = json.load(f)
    assert isinstance(settings_data, dict)
    assert "hooks" in settings_data

    with open(template_path) as f:
        template_data = json.load(f)
    assert isinstance(template_data, dict)
    assert "hooks" in template_data


def test_hooks_are_synchronized(settings_path, template_path):
    """Ensure template hooks match authoritative settings.

    This is the critical test that prevents the UserPromptSubmit bug from recurring.
    """
    is_valid, errors = validate_hooks_sync(settings_path, template_path)

    if not is_valid:
        error_msg = "Hooks are out of sync:\n" + "\n".join(f"  • {e}" for e in errors)
        error_msg += "\n\nTo fix, run: python scripts/sync_hooks.py"
        pytest.fail(error_msg)


def test_normalize_hooks_dict_preserves_structure():
    """Test that normalization preserves hook structure."""
    test_hooks = {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "$CLAUDE_PROJECT_DIR/.claude/tools/hook.py",
                        "timeout": 10000
                    }
                ]
            }
        ]
    }

    normalized = normalize_hooks_dict(test_hooks)

    assert "SessionStart" in normalized
    assert len(normalized["SessionStart"]) == 1
    assert "hooks" in normalized["SessionStart"][0]
    assert normalized["SessionStart"][0]["hooks"][0]["command"] == ".claude/tools/hook.py"
    assert normalized["SessionStart"][0]["hooks"][0]["timeout"] == 10000


def test_compare_hooks_detects_missing():
    """Test that compare_hooks detects missing hooks."""
    source = {
        "SessionStart": [],
        "UserPromptSubmit": []
    }
    template = {
        "SessionStart": []
    }

    errors = compare_hooks(source, template)
    assert len(errors) > 0
    assert any("UserPromptSubmit" in error for error in errors)


def test_compare_hooks_detects_extra():
    """Test that compare_hooks detects unexpected hooks."""
    source = {
        "SessionStart": []
    }
    template = {
        "SessionStart": [],
        "UnknownHook": []
    }

    errors = compare_hooks(source, template)
    assert len(errors) > 0
    assert any("UnknownHook" in error for error in errors)


def test_all_required_hooks_present(settings_path, template_path):
    """Verify all required hooks are present in both files."""
    with open(settings_path) as f:
        settings_data = json.load(f)
    with open(template_path) as f:
        template_data = json.load(f)

    required_hooks = {"SessionStart", "Stop", "PostToolUse", "PreCompact", "UserPromptSubmit"}

    settings_hooks = set(settings_data.get("hooks", {}).keys())
    template_hooks = set(template_data.get("hooks", {}).keys())

    # All required hooks must be in settings
    missing_in_settings = required_hooks - settings_hooks
    assert not missing_in_settings, f"Missing hooks in settings.json: {missing_in_settings}"

    # All required hooks must be in template
    missing_in_template = required_hooks - template_hooks
    assert not missing_in_template, f"Missing hooks in template: {missing_in_template}"
