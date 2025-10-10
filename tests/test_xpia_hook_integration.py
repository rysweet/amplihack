#!/usr/bin/env python3
"""
Test Suite for XPIA Hook Integration

Tests the complete XPIA security hook integration system including:
- Hook merge utility functionality
- XPIA health checking
- Hook execution simulation
- Edge case handling

Addresses Issue #137: XPIA hooks not configured during installation
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Add source paths for imports
project_root = Path(__file__).parents[1]
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "Specs"))

# Imports after path modification
from amplihack.security.xpia_health import check_xpia_health  # noqa: E402
from amplihack.utils.hook_merge_utility import (  # noqa: E402
    HookMergeUtility,
    get_required_xpia_hooks,
)


class TestXPIAHookMergeUtility(unittest.TestCase):
    """Test the hook merge utility functionality"""

    def setUp(self):
        """Set up test environment with temporary settings file"""
        self.temp_dir = tempfile.mkdtemp()
        self.settings_path = Path(self.temp_dir) / "settings.json"
        self.utility = HookMergeUtility(self.settings_path)

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fresh_installation_merge(self):
        """Test merging XPIA hooks into fresh installation (no settings.json)"""
        # Ensure settings file doesn't exist
        self.assertFalse(self.settings_path.exists())

        # Get XPIA hooks and merge
        xpia_hooks = get_required_xpia_hooks()

        # Run merge (async function needs to be tested differently)
        import asyncio

        result = asyncio.run(self.utility.merge_hooks(xpia_hooks))

        # Verify result
        self.assertTrue(result.success, f"Merge failed: {result.error_message}")
        self.assertEqual(result.hooks_added, 3)
        self.assertEqual(result.hooks_updated, 0)

        # Verify settings file was created
        self.assertTrue(self.settings_path.exists())

        # Verify content
        with open(self.settings_path) as f:
            settings = json.load(f)

        self.assertIn("hooks", settings)
        self.assertIn("SessionStart", settings["hooks"])
        self.assertIn("PostToolUse", settings["hooks"])
        self.assertIn("PreToolUse", settings["hooks"])

    def test_existing_settings_merge(self):
        """Test merging XPIA hooks into existing settings with other hooks"""
        # Create existing settings with amplihack hooks
        existing_settings = {
            "permissions": {
                "allow": ["Bash", "TodoWrite"],
                "deny": [],
                "defaultMode": "bypassPermissions",
            },
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "~/.claude/tools/amplihack/hooks/session_start.py",
                                "timeout": 10000,
                            }
                        ]
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "~/.claude/tools/amplihack/hooks/post_tool_use.py",
                            }
                        ],
                    }
                ],
            },
        }

        # Write existing settings
        with open(self.settings_path, "w") as f:
            json.dump(existing_settings, f, indent=2)

        # Get XPIA hooks and merge
        xpia_hooks = get_required_xpia_hooks()

        import asyncio

        result = asyncio.run(self.utility.merge_hooks(xpia_hooks))

        # Verify result
        self.assertTrue(result.success, f"Merge failed: {result.error_message}")
        self.assertEqual(result.hooks_added, 3)  # 3 new XPIA hooks
        self.assertEqual(result.hooks_updated, 0)

        # Verify settings preservation and addition
        with open(self.settings_path) as f:
            updated_settings = json.load(f)

        # Original amplihack hooks should still be there
        self.assertIn("SessionStart", updated_settings["hooks"])
        self.assertIn("PostToolUse", updated_settings["hooks"])
        self.assertIn("PreToolUse", updated_settings["hooks"])  # New from XPIA

        # Should have both amplihack and XPIA hooks in SessionStart
        session_hooks = updated_settings["hooks"]["SessionStart"]
        self.assertEqual(len(session_hooks), 2)  # Original + XPIA

        # Verify XPIA hook is present
        xpia_session_hook = None
        for hook_entry in session_hooks:
            for hook in hook_entry.get("hooks", []):
                if "xpia" in hook.get("command", ""):
                    xpia_session_hook = hook
                    break

        self.assertIsNotNone(xpia_session_hook, "XPIA session hook not found")

    def test_duplicate_xpia_hooks_update(self):
        """Test updating existing XPIA hooks rather than duplicating"""
        # Create settings with existing XPIA hooks
        existing_settings = {
            "permissions": {"allow": ["Bash"]},
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/Users/test/.claude/tools/xpia/hooks/session_start.py",
                                "timeout": 5000,  # Different timeout
                            }
                        ]
                    }
                ]
            },
        }

        # Write existing settings
        with open(self.settings_path, "w") as f:
            json.dump(existing_settings, f, indent=2)

        # Get XPIA hooks and merge
        xpia_hooks = get_required_xpia_hooks()

        import asyncio

        result = asyncio.run(self.utility.merge_hooks(xpia_hooks))

        # Verify result - should update existing and add new
        self.assertTrue(result.success, f"Merge failed: {result.error_message}")
        self.assertEqual(result.hooks_updated, 1)  # Updated SessionStart
        self.assertEqual(result.hooks_added, 2)  # Added PostToolUse, PreToolUse

    def test_malformed_json_handling(self):
        """Test handling of malformed JSON in settings file"""
        # Write malformed JSON
        with open(self.settings_path, "w") as f:
            f.write('{"hooks": malformed json}')

        # Get XPIA hooks and merge
        xpia_hooks = get_required_xpia_hooks()

        import asyncio

        result = asyncio.run(self.utility.merge_hooks(xpia_hooks))

        # Should succeed by creating new settings
        self.assertTrue(
            result.success, f"Merge should handle malformed JSON: {result.error_message}"
        )
        self.assertEqual(result.hooks_added, 3)

        # Verify backup was created
        self.assertIsNotNone(result.backup_path)
        self.assertTrue(Path(result.backup_path).exists())

    def test_backup_and_rollback(self):
        """Test backup creation and rollback functionality"""
        # Create initial settings
        initial_settings = {"hooks": {"test": "value"}}
        with open(self.settings_path, "w") as f:
            json.dump(initial_settings, f)

        # Force a failure by mocking the save function to fail
        with mock.patch.object(
            self.utility, "_save_settings", side_effect=Exception("Mock failure")
        ):
            xpia_hooks = get_required_xpia_hooks()

            import asyncio

            result = asyncio.run(self.utility.merge_hooks(xpia_hooks))

        # Should have failed and rolled back
        self.assertFalse(result.success)
        self.assertTrue(result.rollback_performed)

        # Original settings should be restored
        with open(self.settings_path) as f:
            restored_settings = json.load(f)
        self.assertEqual(restored_settings, initial_settings)


class TestXPIAHealthCheck(unittest.TestCase):
    """Test XPIA health check functionality"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.settings_path = Path(self.temp_dir) / "settings.json"

    def tearDown(self):
        """Clean up temporary files"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_health_check_no_settings(self):
        """Test health check with no settings file"""
        result = check_xpia_health(self.settings_path)

        self.assertEqual(result["overall_status"], "unhealthy")
        self.assertEqual(result["components"]["settings_hooks"]["status"], "no_settings")

    def test_health_check_with_xpia_hooks(self):
        """Test health check with properly configured XPIA hooks"""
        # Create settings with XPIA hooks
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/Users/test/.claude/tools/xpia/hooks/session_start.py",
                                "timeout": 10000,
                            }
                        ]
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "*",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/Users/test/.claude/tools/xpia/hooks/post_tool_use.py",
                                "timeout": 3000,
                            }
                        ],
                    }
                ],
                "PreToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/Users/test/.claude/tools/xpia/hooks/pre_tool_use.py",
                                "timeout": 5000,
                            }
                        ],
                    }
                ],
            }
        }

        # Write settings
        with open(self.settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        # Check health
        result = check_xpia_health(self.settings_path)

        # Settings hooks should be OK (3 of 3 found)
        settings_component = result["components"]["settings_hooks"]
        self.assertEqual(settings_component["status"], "ok")
        self.assertEqual(settings_component["total_found"], 3)
        self.assertEqual(settings_component["expected_count"], 3)

    def test_health_check_missing_hooks(self):
        """Test health check with missing XPIA hooks"""
        # Create settings with only some XPIA hooks
        settings = {
            "hooks": {
                "SessionStart": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/Users/test/.claude/tools/xpia/hooks/session_start.py",
                                "timeout": 10000,
                            }
                        ]
                    }
                ]
                # Missing PostToolUse and PreToolUse
            }
        }

        # Write settings
        with open(self.settings_path, "w") as f:
            json.dump(settings, f, indent=2)

        # Check health
        result = check_xpia_health(self.settings_path)

        # Settings hooks should indicate missing hooks
        settings_component = result["components"]["settings_hooks"]
        self.assertEqual(settings_component["status"], "missing_hooks")
        self.assertEqual(settings_component["total_found"], 1)
        self.assertEqual(settings_component["expected_count"], 3)


class TestXPIAHookExecution(unittest.TestCase):
    """Test XPIA hook execution (simulation)"""

    def setUp(self):
        """Set up test environment"""
        self.project_root = Path(__file__).parents[1]

    def test_session_start_hook(self):
        """Test XPIA session start hook execution"""
        hook_path = self.project_root / ".claude" / "tools" / "xpia" / "hooks" / "session_start.py"

        if not hook_path.exists():
            self.skipTest(f"Session start hook not found: {hook_path}")

        # Run the hook
        try:
            result = subprocess.run(
                [sys.executable, str(hook_path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should exit successfully
            self.assertEqual(result.returncode, 0, f"Hook failed: {result.stderr}")

            # Should produce JSON output
            output = result.stdout.strip()
            self.assertTrue(output, "Hook produced no output")

            # Parse JSON output
            hook_result = json.loads(output)
            self.assertIn("status", hook_result)

        except subprocess.TimeoutExpired:
            self.fail("Session start hook timed out")

    def test_pre_tool_use_hook_safe_command(self):
        """Test pre-tool-use hook with safe command"""
        hook_path = self.project_root / ".claude" / "tools" / "xpia" / "hooks" / "pre_tool_use.py"

        if not hook_path.exists():
            self.skipTest(f"Pre-tool-use hook not found: {hook_path}")

        # Test input: safe command
        test_input = {"tool": "Bash", "parameters": {"command": "ls -la"}}

        # Run the hook
        try:
            result = subprocess.run(
                [sys.executable, str(hook_path)],
                check=False,
                input=json.dumps(test_input),
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should exit successfully (allow command)
            self.assertEqual(result.returncode, 0, f"Hook failed: {result.stderr}")

            # Parse result
            hook_result = json.loads(result.stdout.strip())
            self.assertEqual(hook_result["action"], "allow")

        except subprocess.TimeoutExpired:
            self.fail("Pre-tool-use hook timed out")

    def test_pre_tool_use_hook_dangerous_command(self):
        """Test pre-tool-use hook with dangerous command"""
        hook_path = self.project_root / ".claude" / "tools" / "xpia" / "hooks" / "pre_tool_use.py"

        if not hook_path.exists():
            self.skipTest(f"Pre-tool-use hook not found: {hook_path}")

        # Test input: dangerous command
        test_input = {"tool": "Bash", "parameters": {"command": "rm -rf /"}}

        # Run the hook
        try:
            result = subprocess.run(
                [sys.executable, str(hook_path)],
                check=False,
                input=json.dumps(test_input),
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Should exit with error code (block command)
            self.assertEqual(result.returncode, 1, "Hook should block dangerous command")

            # Parse result
            hook_result = json.loads(result.stdout.strip())
            self.assertEqual(hook_result["action"], "deny")
            self.assertIn("blocked", hook_result["message"].lower())

        except subprocess.TimeoutExpired:
            self.fail("Pre-tool-use hook timed out")


class TestXPIAIntegrationEndToEnd(unittest.TestCase):
    """End-to-end integration tests"""

    def test_complete_installation_simulation(self):
        """Simulate complete XPIA installation process"""
        # Create temporary directory for installation test
        temp_dir = tempfile.mkdtemp()
        settings_path = Path(temp_dir) / "settings.json"

        try:
            # Step 1: Start with existing amplihack settings
            existing_settings = {
                "permissions": {
                    "allow": ["Bash", "TodoWrite", "WebSearch", "WebFetch"],
                    "deny": [],
                    "defaultMode": "bypassPermissions",
                },
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "~/.claude/tools/amplihack/hooks/session_start.py",
                                    "timeout": 10000,
                                }
                            ]
                        }
                    ]
                },
            }

            with open(settings_path, "w") as f:
                json.dump(existing_settings, f, indent=2)

            # Step 2: Run hook merge utility
            utility = HookMergeUtility(settings_path)
            xpia_hooks = get_required_xpia_hooks()

            import asyncio

            merge_result = asyncio.run(utility.merge_hooks(xpia_hooks))

            # Verify merge succeeded
            self.assertTrue(merge_result.success, f"Merge failed: {merge_result.error_message}")
            self.assertEqual(merge_result.hooks_added, 3)

            # Step 3: Run health check
            health_result = check_xpia_health(settings_path)

            # Verify XPIA hooks are properly configured
            self.assertEqual(health_result["components"]["settings_hooks"]["status"], "ok")
            self.assertEqual(health_result["components"]["settings_hooks"]["total_found"], 3)

            # Step 4: Verify final settings structure
            with open(settings_path) as f:
                final_settings = json.load(f)

            # Should have all hook types
            self.assertIn("SessionStart", final_settings["hooks"])
            self.assertIn("PostToolUse", final_settings["hooks"])
            self.assertIn("PreToolUse", final_settings["hooks"])

            # SessionStart should have both amplihack and XPIA hooks
            session_hooks = final_settings["hooks"]["SessionStart"]
            self.assertEqual(len(session_hooks), 2)

            print("✅ End-to-end XPIA integration test passed")

        finally:
            # Clean up
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all XPIA integration tests"""
    # Set up logging for tests
    import logging

    logging.basicConfig(level=logging.WARNING)  # Reduce noise during tests

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        TestXPIAHookMergeUtility,
        TestXPIAHealthCheck,
        TestXPIAHookExecution,
        TestXPIAIntegrationEndToEnd,
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return appropriate exit code
    if result.wasSuccessful():
        print("\n🎉 All XPIA integration tests passed!")
        return 0
    print(f"\n❌ {len(result.failures)} test(s) failed, {len(result.errors)} error(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
