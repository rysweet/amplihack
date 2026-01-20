#!/usr/bin/env python3
"""
Example demonstrating UVX staging functionality.

This example shows how the UVX staging mechanism works when AmplifyHack
is run via UVX instead of local installation.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.utils.paths import FrameworkPathResolver
from amplihack.utils.uvx_staging import is_uvx_deployment, stage_uvx_framework


def main():
    """Demonstrate UVX staging workflow."""
    print("🚀 AmplifyHack UVX Staging Example")
    print("=" * 50)

    # Check deployment type
    print(f"🔍 UVX Deployment Detected: {is_uvx_deployment()}")

    # Show current working directory
    print(f"📁 Working Directory: {Path.cwd()}")

    # Check for local framework files
    local_claude = Path.cwd() / ".claude"
    print(f"📂 Local .claude exists: {local_claude.exists()}")

    # Try to find framework root using the resolver
    framework_root = FrameworkPathResolver.find_framework_root()
    print(f"🎯 Framework Root Found: {framework_root}")

    if framework_root:
        print(f"   📍 Location: {framework_root}")

        # List some framework files
        claude_dir = framework_root / ".claude"
        if claude_dir.exists():
            print("   📋 Framework files found:")
            for item in sorted(claude_dir.rglob("*"))[:10]:  # First 10 items
                relative_path = item.relative_to(framework_root)
                print(f"      - {relative_path}")

    # Check specific framework files
    print("\n🔧 Framework File Resolution:")
    test_files = [
        ".claude/context/USER_PREFERENCES.md",
        ".claude/workflow/DEFAULT_WORKFLOW.md",
        "CLAUDE.md",
        "DISCOVERIES.md",
    ]

    for file_path in test_files:
        resolved = FrameworkPathResolver.resolve_framework_file(file_path)
        status = "✅ Found" if resolved else "❌ Missing"
        location = f" at {resolved}" if resolved else ""
        print(f"   {status} {file_path}{location}")

    # If UVX deployment, show staging information
    if is_uvx_deployment():
        print("\n🎭 UVX Staging Status:")
        print("   - Framework files will be staged to working directory")
        print("   - @ imports in CLAUDE.md will work correctly")
        print("   - Automatic cleanup on session end")

        # Try staging manually
        print("\n🎬 Manual Staging Demo:")
        success = stage_uvx_framework()
        print(f"   Staging Result: {'✅ Success' if success else '❌ Failed'}")

        if success:
            # Show what was staged
            from amplihack.utils.uvx_staging import _uvx_stager

            staged_files = _uvx_stager._staged_files
            if staged_files:
                print(f"   📦 Staged {len(staged_files)} items:")
                for staged_file in sorted(staged_files):
                    print(f"      - {staged_file.name}")

            # Note: Cleanup removed in simplified implementation
            print("\n🧹 Cleanup Demo:")
            print("   ✅ Files remain staged (persistent by default in simplified version)")

    print("\n" + "=" * 50)
    print("🎉 Demo Complete!")


if __name__ == "__main__":
    main()
