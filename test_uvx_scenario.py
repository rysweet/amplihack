#!/usr/bin/env python3
"""Test amplihack installation in a simulated UVX environment."""

import subprocess
import sys
import tempfile
from pathlib import Path


def test_uvx_scenario():
    """Simulate a UVX installation scenario."""
    print("=" * 60)
    print("TESTING UVX INSTALLATION SCENARIO")
    print("=" * 60)

    # Get repo root
    repo_root = Path(__file__).parent.absolute()

    # Create a temporary "uvx" environment
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        print("\n📦 Setting up simulated UVX environment in:")
        print(f"   {tmpdir}")

        # Copy the amplihack package to simulate pip/uvx install
        venv_site_packages = tmpdir / "site-packages"
        venv_site_packages.mkdir(parents=True)

        # Copy src/amplihack to the "installed" location
        import shutil

        src_amplihack = repo_root / "src" / "amplihack"
        dest_amplihack = venv_site_packages / "amplihack"
        shutil.copytree(src_amplihack, dest_amplihack)
        print("\n📋 Copied amplihack package to site-packages")

        # Also need to copy the .claude directory to amplihack package
        # (This simulates what would be in the wheel/package)
        src_claude = repo_root / ".claude"
        dest_claude = dest_amplihack / ".claude"
        shutil.copytree(src_claude, dest_claude)
        print("📋 Copied .claude directory to package")

        # Create a test script that simulates running amplihack from uvx
        test_script = tmpdir / "run_install.py"
        test_script.write_text(f"""
import sys
import os

# Add the simulated site-packages to path
sys.path.insert(0, r'{venv_site_packages}')

# Change to a different directory (simulating user's home)
import tempfile
with tempfile.TemporaryDirectory() as user_dir:
    os.chdir(user_dir)
    print(f"\\n📍 Running from: {{os.getcwd()}}")

    # Now import and run amplihack install
    from amplihack import _local_install

    # The package directory is where amplihack is installed
    package_dir = r'{dest_amplihack}'
    print(f"📦 Package directory: {{package_dir}}")

    # Install from the package directory (which has .claude)
    _local_install(package_dir)

    # Verify installation
    import json
    from pathlib import Path

    claude_dir = Path.home() / '.claude'

    print("\\n🔍 Verifying installation:")
    checks = {{
        "agents/amplihack": claude_dir / 'agents' / 'amplihack',
        "commands/amplihack": claude_dir / 'commands' / 'amplihack',
        "tools/amplihack": claude_dir / 'tools' / 'amplihack',
        "context": claude_dir / 'context',
        "workflow": claude_dir / 'workflow',
        "settings.json": claude_dir / 'settings.json',
    }}

    all_good = True
    for name, path in checks.items():
        if path.exists():
            print(f"  ✅ {{name}}")
        else:
            print(f"  ❌ {{name}} MISSING")
            all_good = False

    # Check hook paths
    settings_path = claude_dir / 'settings.json'
    if settings_path.exists():
        with open(settings_path) as f:
            settings = json.load(f)

        abs_hooks = 0
        for hook_type in ['SessionStart', 'Stop', 'PostToolUse', 'PreCompact']:
            if hook_type in settings.get('hooks', {{}}):
                for config in settings['hooks'][hook_type]:
                    for hook in config.get('hooks', []):
                        if 'command' in hook and hook['command'].startswith('/'):
                            abs_hooks += 1

        if abs_hooks >= 4:
            print(f"  ✅ All {{abs_hooks}} hooks using absolute paths")
        else:
            print(f"  ⚠️  Only {{abs_hooks}}/4 hooks with absolute paths")

    if all_good:
        print("\\n✅ UVX-style installation completed successfully!")
        sys.exit(0)
    else:
        print("\\n❌ UVX-style installation had issues")
        sys.exit(1)
""")

        # Run the test script
        print("\n🚀 Running simulated UVX installation...")
        result = subprocess.run([sys.executable, str(test_script)], capture_output=True, text=True)

        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)

        return result.returncode == 0


if __name__ == "__main__":
    success = test_uvx_scenario()
    if success:
        print("\n🎉 UVX scenario test PASSED!")
        sys.exit(0)
    else:
        print("\n❌ UVX scenario test FAILED")
        sys.exit(1)
