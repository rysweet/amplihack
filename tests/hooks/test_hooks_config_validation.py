"""Test hooks.json configuration validation for Issue #2336.

This test verifies that hooks.json uses correct directory paths instead
of ${CLAUDE_PLUGIN_ROOT} variable references.

EXPECTED BEHAVIOR: These tests SHOULD FAIL before the fix is applied.
"""

import json
from pathlib import Path


def test_hooks_json_is_valid_json():
    """Verify hooks.json is syntactically valid JSON."""
    # Test the project file (what's in the PR), not the installed file
    hooks_json_path = (
        Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks/hooks.json"
    )

    if not hooks_json_path.exists():
        # Fallback to installed location if project file doesn't exist
        hooks_json_path = Path.home() / ".amplihack/.claude/tools/amplihack/hooks/hooks.json"

    assert hooks_json_path.exists(), f"hooks.json not found at {hooks_json_path}"

    with open(hooks_json_path) as f:
        data = json.load(f)  # Should not raise JSONDecodeError

    assert isinstance(data, dict), "hooks.json should be a JSON object"
    print("✅ hooks.json is valid JSON")


def test_hooks_json_has_no_plugin_root_references():
    """Verify no ${CLAUDE_PLUGIN_ROOT} variable references remain.

    EXPECTED TO FAIL: Before fix, this will find 7 occurrences of ${CLAUDE_PLUGIN_ROOT}
    """
    # Test the project file (what's in the PR), not the installed file
    hooks_json_path = (
        Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks/hooks.json"
    )

    if not hooks_json_path.exists():
        hooks_json_path = Path.home() / ".amplihack/.claude/tools/amplihack/hooks/hooks.json"

    with open(hooks_json_path) as f:
        content = f.read()

    plugin_root_count = content.count("${CLAUDE_PLUGIN_ROOT}")

    # THIS SHOULD FAIL before fix is applied
    assert plugin_root_count == 0, (
        f"Found {plugin_root_count} references to ${{CLAUDE_PLUGIN_ROOT}}. "
        f"All paths should use ~/.amplihack/.claude instead."
    )

    print("✅ No ${CLAUDE_PLUGIN_ROOT} references found")


def test_hooks_json_uses_correct_directory_paths():
    """Verify all hook paths use ~/.amplihack/.claude/tools/amplihack/hooks/.

    EXPECTED TO FAIL: Before fix, paths use ${CLAUDE_PLUGIN_ROOT} instead
    """
    # Test the project file (what's in the PR), not the installed file
    hooks_json_path = (
        Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks/hooks.json"
    )

    if not hooks_json_path.exists():
        hooks_json_path = Path.home() / ".amplihack/.claude/tools/amplihack/hooks/hooks.json"

    with open(hooks_json_path) as f:
        data = json.load(f)

    expected_prefix = "~/.amplihack/.claude/tools/amplihack/hooks/"
    hook_paths = []

    # Extract all hook paths from the JSON structure
    for event_name, event_configs in data.items():
        for config in event_configs:
            for hook in config.get("hooks", []):
                command = hook.get("command")
                if command:
                    hook_paths.append((event_name, command))

    # Verify we found the expected 7 hook paths
    assert len(hook_paths) == 7, f"Expected 7 hook paths, found {len(hook_paths)}"

    # Verify each path uses correct directory
    failed_paths = []
    for event_name, path in hook_paths:
        if not path.startswith(expected_prefix):
            failed_paths.append((event_name, path))

    # THIS SHOULD FAIL before fix is applied
    assert len(failed_paths) == 0, (
        f"Found {len(failed_paths)} hook paths NOT using correct directory:\n"
        + "\n".join(f"  {event}: {path}" for event, path in failed_paths)
    )

    print(f"✅ All {len(hook_paths)} hook paths use correct directory")


def test_hooks_json_hook_count():
    """Verify hooks.json contains exactly 7 hook definitions."""
    # Test the project file (what's in the PR), not the installed file
    hooks_json_path = (
        Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks/hooks.json"
    )

    if not hooks_json_path.exists():
        hooks_json_path = Path.home() / ".amplihack/.claude/tools/amplihack/hooks/hooks.json"

    with open(hooks_json_path) as f:
        data = json.load(f)

    # Count all hooks across all events
    hook_count = 0
    for event_configs in data.values():
        for config in event_configs:
            hook_count += len(config.get("hooks", []))

    assert hook_count == 7, (
        f"Expected 7 hook definitions, found {hook_count}. "
        f"Hook count mismatch may indicate structural issues."
    )

    print("✅ Found exactly 7 hook definitions")


def test_hooks_json_critical_hooks_present():
    """Verify critical hooks are present in hooks.json."""
    # Test the project file (what's in the PR), not the installed file
    hooks_json_path = (
        Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks/hooks.json"
    )

    if not hooks_json_path.exists():
        hooks_json_path = Path.home() / ".amplihack/.claude/tools/amplihack/hooks/hooks.json"

    with open(hooks_json_path) as f:
        data = json.load(f)

    # Expected hook events
    expected_events = [
        "SessionStart",
        "Stop",
        "PreToolUse",
        "PostToolUse",
        "UserPromptSubmit",
        "PreCompact",
    ]

    for event in expected_events:
        assert event in data, f"Critical hook event '{event}' missing from hooks.json"

    print(f"✅ All {len(expected_events)} critical hook events present")


if __name__ == "__main__":
    print("🧪 Running Hooks Configuration Validation Tests (Issue #2336)\n")
    print("⚠️  These tests SHOULD FAIL before the fix is applied\n")

    tests = [
        ("Valid JSON syntax", test_hooks_json_is_valid_json),
        ("No ${CLAUDE_PLUGIN_ROOT} references", test_hooks_json_has_no_plugin_root_references),
        ("Correct directory paths", test_hooks_json_uses_correct_directory_paths),
        ("Hook count validation", test_hooks_json_hook_count),
        ("Critical hooks present", test_hooks_json_critical_hooks_present),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Test: {test_name}")
        print(f"{'=' * 60}")
        try:
            test_func()
            print("✅ PASSED")
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED (EXPECTED): {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
            import traceback

            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {passed} passed, {failed} failed")
    if failed > 0:
        print("⚠️  Failures are EXPECTED before fix implementation")
    print(f"{'=' * 60}")
