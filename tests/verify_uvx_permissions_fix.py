#!/usr/bin/env python3
"""Verification script for UVX permissions fix.

This script demonstrates that the UVX permissions issue #138 has been resolved.
It simulates a fresh UVX installation and verifies that bypass permissions
are properly configured without user intervention.
"""

import json
import tempfile
from pathlib import Path

from src.amplihack.utils.uvx_models import UVXConfiguration
from src.amplihack.utils.uvx_settings_manager import uvx_settings_manager
from src.amplihack.utils.uvx_staging_v2 import UVXStager


def simulate_fresh_uvx_installation():
    """Simulate a fresh UVX installation process."""
    print("🚀 Simulating fresh UVX installation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Simulate UVX framework source (what gets staged)
        source_dir = temp_path / "uvx_source"
        source_claude = source_dir / ".claude"
        source_claude.mkdir(parents=True)

        # Create project settings.json (current repo version)
        project_settings = {
            "permissions": {
                "allow": ["Bash", "TodoWrite", "WebSearch", "WebFetch"],
                "deny": [],
                "defaultMode": "bypassPermissions",
                "additionalDirectories": [".claude", "Specs"],
            },
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": ".claude/tools/amplihack/hooks/session_start.py",
                            }
                        ]
                    }
                ]
            },
        }

        with open(source_claude / "settings.json", "w") as f:
            json.dump(project_settings, f, indent=2)

        # Create some other framework files
        tools_dir = source_claude / "tools" / "amplihack" / "hooks"
        tools_dir.mkdir(parents=True)
        (tools_dir / "session_start.py").write_text(
            "#!/usr/bin/env python3\nprint('Hook executed')"
        )

        # Simulate target directory (user's working directory)
        target_dir = temp_path / "user_project"
        target_dir.mkdir()

        print("📁 Created simulation environment")
        print(f"   Source: {source_dir}")
        print(f"   Target: {target_dir}")

        # Stage the framework (this is what UVX does)
        print("\n📦 Staging UVX framework...")
        stager = UVXStager(UVXConfiguration(overwrite_existing=True))
        result = stager._stage_claude_directory(source_claude, target_dir / ".claude")

        if not result:
            print("❌ Staging failed!")
            return False

        print("✅ Staging completed successfully")

        # Verify the results
        settings_path = target_dir / ".claude" / "settings.json"
        if not settings_path.exists():
            print("❌ settings.json was not created!")
            return False

        with open(settings_path) as f:
            final_settings = json.load(f)

        print("\n🔍 Verifying UVX permissions configuration...")

        # Check bypass permissions
        default_mode = final_settings.get("permissions", {}).get("defaultMode", "askPermissions")
        if default_mode != "bypassPermissions":
            print(f"❌ Default mode is '{default_mode}', expected 'bypassPermissions'")
            return False
        print("✅ Bypass permissions enabled")

        # Check comprehensive tool allowlist
        allow_list = final_settings.get("permissions", {}).get("allow", [])
        required_tools = [
            "Bash",
            "TodoWrite",
            "WebFetch",
            "WebSearch",
            "Grep",
            "Glob",
            "Read",
            "Edit",
            "MultiEdit",
        ]

        missing_tools = [tool for tool in required_tools if tool not in allow_list]
        if missing_tools:
            print(f"❌ Missing tools in allow list: {missing_tools}")
            return False
        print(f"✅ Comprehensive tool allowlist ({len(allow_list)} tools pre-approved)")

        # Check hooks configuration
        hooks = final_settings.get("hooks", {})
        required_hooks = ["SessionStart", "Stop", "PostToolUse", "PreCompact"]
        missing_hooks = [hook for hook in required_hooks if hook not in hooks]
        if missing_hooks:
            print(f"❌ Missing hooks: {missing_hooks}")
            return False
        print("✅ All amplihack hooks configured")

        # Display final configuration summary
        print("\n📋 Final UVX Configuration Summary:")
        print(f"   Default Mode: {default_mode}")
        print(f"   Pre-approved Tools: {len(allow_list)}")
        print(f"   Configured Hooks: {len(hooks)}")
        print(
            f"   Additional Directories: {len(final_settings.get('permissions', {}).get('additionalDirectories', []))}"
        )

        return True


def demonstrate_existing_settings_preservation():
    """Demonstrate that existing user settings are preserved."""
    print("\n🔧 Demonstrating existing settings preservation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create existing user settings
        target_dir = temp_path / "existing_project"
        target_claude = target_dir / ".claude"
        target_claude.mkdir(parents=True)

        existing_settings = {
            "permissions": {
                "allow": ["UserTool", "CustomTool"],
                "deny": ["DangerousTool"],
                "defaultMode": "askPermissions",  # User prefers to be asked
                "additionalDirectories": ["user-specific"],
            },
            "userCustomization": "important-value",
            "hooks": {"UserHook": [{"type": "command", "command": "user_script.py"}]},
        }

        settings_path = target_claude / "settings.json"
        with open(settings_path, "w") as f:
            json.dump(existing_settings, f, indent=2)

        print("👤 Created existing user settings with custom configuration")

        # Test the merge functionality
        success = uvx_settings_manager.merge_with_existing_settings(
            settings_path, existing_settings
        )

        if not success:
            print("❌ Failed to merge existing settings")
            return False

        # Verify preservation
        with open(settings_path) as f:
            merged_settings = json.load(f)

        # Should preserve user customizations
        if merged_settings.get("userCustomization") != "important-value":
            print("❌ User customization was not preserved")
            return False
        print("✅ User customizations preserved")

        # Should have UVX bypass permissions for smooth operation
        if merged_settings.get("permissions", {}).get("defaultMode") != "bypassPermissions":
            print("❌ Bypass permissions not applied during merge")
            return False
        print("✅ Bypass permissions enabled for UVX operation")

        # Should merge tool allowlists
        allow_list = merged_settings.get("permissions", {}).get("allow", [])
        if "UserTool" not in allow_list or "Bash" not in allow_list:
            print("❌ Tool allowlists not properly merged")
            return False
        print("✅ Tool allowlists merged (user tools + UVX tools)")

        # Should merge hooks
        hooks = merged_settings.get("hooks", {})
        if "UserHook" not in hooks or "SessionStart" not in hooks:
            print("❌ Hooks not properly merged")
            return False
        print("✅ Hooks merged (user hooks + amplihack hooks)")

        print("\n📋 Merged Configuration Summary:")
        print("   User Tools Preserved: ✅")
        print("   UVX Tools Added: ✅")
        print("   Bypass Permissions: ✅")
        print("   Custom Properties: ✅")

        return True


def validate_permission_coverage():
    """Validate that all essential tools are covered by UVX template."""
    print("\n🛡️  Validating comprehensive permission coverage...")

    template = uvx_settings_manager.get_template_settings()
    if not template:
        print("❌ Could not load UVX template")
        return False

    allow_list = template.get("permissions", {}).get("allow", [])

    # Essential tool categories
    tool_categories = {
        "System Execution": ["Bash", "BashOutput", "KillShell"],
        "Task Management": ["TodoWrite", "SlashCommand"],
        "Web Access": ["WebFetch", "WebSearch"],
        "File Operations": ["Read", "Edit", "MultiEdit", "Write", "Glob", "Grep"],
        "Jupyter Support": ["NotebookEdit"],
        "IDE Integration": ["mcp__ide__getDiagnostics", "mcp__ide__executeCode"],
    }

    all_covered = True
    for category, tools in tool_categories.items():
        missing = [tool for tool in tools if tool not in allow_list]
        if missing:
            print(f"❌ {category}: Missing {missing}")
            all_covered = False
        else:
            print(f"✅ {category}: All tools covered ({len(tools)} tools)")

    if all_covered:
        print(
            f"\n🎯 All {len([tool for tools in tool_categories.values() for tool in tools])} essential tools are pre-approved"
        )
        return True
    print("\n❌ Some essential tools are missing from the allowlist")
    return False


def main():
    """Run complete verification of UVX permissions fix."""
    print("=" * 70)
    print("🔧 UVX Permissions Fix Verification (Issue #138)")
    print("=" * 70)

    all_tests_passed = True

    # Test 1: Fresh installation
    print("\n" + "=" * 50)
    print("TEST 1: Fresh UVX Installation")
    print("=" * 50)
    if not simulate_fresh_uvx_installation():
        all_tests_passed = False
        print("❌ Fresh installation test FAILED")
    else:
        print("✅ Fresh installation test PASSED")

    # Test 2: Existing settings preservation
    print("\n" + "=" * 50)
    print("TEST 2: Existing Settings Preservation")
    print("=" * 50)
    if not demonstrate_existing_settings_preservation():
        all_tests_passed = False
        print("❌ Settings preservation test FAILED")
    else:
        print("✅ Settings preservation test PASSED")

    # Test 3: Permission coverage validation
    print("\n" + "=" * 50)
    print("TEST 3: Permission Coverage Validation")
    print("=" * 50)
    if not validate_permission_coverage():
        all_tests_passed = False
        print("❌ Permission coverage test FAILED")
    else:
        print("✅ Permission coverage test PASSED")

    # Final result
    print("\n" + "=" * 70)
    if all_tests_passed:
        print("🎉 ALL TESTS PASSED - UVX Permissions Fix Verified!")
        print("=" * 70)
        print("\n✅ Issue #138 Resolution Summary:")
        print("   • Fresh UVX installations now have bypass permissions enabled by default")
        print("   • Comprehensive tool allowlist eliminates permission dialogs")
        print("   • Existing user settings are preserved and enhanced")
        print("   • All essential tools are pre-approved for seamless operation")
        print("   • Amplihack hooks are automatically configured")
        print("\n🚀 UVX users will now have a smooth, permission-dialog-free experience!")
        return 0
    print("❌ SOME TESTS FAILED - Fix needs more work")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
