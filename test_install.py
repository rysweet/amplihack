#!/usr/bin/env python3
"""Test the installation from outside the repository directory."""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path to import amplihack
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_external_install():
    """Test installation as if running from uvx or pip."""
    # Get the repo root
    repo_root = os.path.dirname(os.path.abspath(__file__))

    # Create a temporary directory to simulate running from elsewhere
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory (simulating uvx environment)
        original_cwd = os.getcwd()
        os.chdir(tmpdir)

        print(f"Testing from temporary directory: {tmpdir}")
        print(f"Repository root: {repo_root}")

        try:
            # Import and run the install
            from amplihack import _local_install

            # This should install from the repo_root even though we're in tmpdir
            _local_install(repo_root)

            # Verify installation
            claude_dir = Path.home() / ".claude"

            required_dirs = [
                claude_dir / "agents" / "amplihack",
                claude_dir / "commands" / "amplihack",
                claude_dir / "tools" / "amplihack",
                claude_dir / "context",
                claude_dir / "workflow",
                claude_dir / "runtime",
                claude_dir / "runtime" / "logs",
            ]

            print("\nVerifying installation:")
            all_good = True
            for dir_path in required_dirs:
                if dir_path.exists():
                    print(f"  ✅ {dir_path.relative_to(Path.home())}")
                else:
                    print(f"  ❌ {dir_path.relative_to(Path.home())} MISSING")
                    all_good = False

            # Check settings.json
            settings_path = claude_dir / "settings.json"
            if settings_path.exists():
                import json

                with open(settings_path) as f:
                    settings = json.load(f)

                # Verify hooks have absolute paths
                hook_count = 0
                for hook_type in ["SessionStart", "Stop", "PostToolUse", "PreCompact"]:
                    if hook_type in settings.get("hooks", {}):
                        for config in settings["hooks"][hook_type]:
                            for hook in config.get("hooks", []):
                                if "command" in hook:
                                    cmd = hook["command"]
                                    if cmd.startswith("/"):
                                        hook_count += 1
                                    else:
                                        print(
                                            f"  ⚠️  {hook_type} hook not using absolute path: {cmd}"
                                        )

                if hook_count >= 4:
                    print(f"  ✅ All {hook_count} hooks using absolute paths")
                else:
                    print(f"  ⚠️  Only {hook_count}/4 hooks configured with absolute paths")
            else:
                print("  ❌ settings.json MISSING")
                all_good = False

            if all_good:
                print("\n✅ Installation test PASSED - all components installed correctly")
            else:
                print("\n❌ Installation test FAILED - some components missing")

            return all_good

        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    success = test_external_install()
    sys.exit(0 if success else 1)
