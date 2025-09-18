#!/usr/bin/env python3
"""
Developer setup script - Run this after cloning the repository.
Ensures pre-commit hooks are installed and environment is ready.
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: "list[str]", check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def check_git_hooks_installed() -> bool:
    """Check if pre-commit hooks are installed."""
    git_hooks_path = Path(".git/hooks/pre-commit")
    if not git_hooks_path.exists():
        return False

    # Check if it's the pre-commit hook (not just the sample)
    with open(git_hooks_path) as f:
        content = f.read()
        return "pre-commit" in content and "pre_commit" in content


def main():
    """Set up developer environment."""
    print("🚀 Setting up developer environment...")

    # Check if we're in the right directory
    if not Path(".git").exists():
        print("❌ Error: Not in a git repository root. Please run from the project root.")
        sys.exit(1)

    # Check if pre-commit is installed
    result = run_command(["which", "pre-commit"], check=False)
    if result.returncode != 0:
        print("📦 Installing pre-commit...")
        run_command([sys.executable, "-m", "pip", "install", "pre-commit"])
    else:
        print("✅ pre-commit is already installed")

    # Check if hooks are installed
    if check_git_hooks_installed():
        print("✅ Git hooks are already installed")
    else:
        print("🔧 Installing git hooks...")
        run_command(["pre-commit", "install"])
        print("✅ Git hooks installed successfully")

    # Run pre-commit on all files to verify setup
    print("\n🔍 Running pre-commit checks to verify setup...")
    result = run_command(["pre-commit", "run", "--all-files"], check=False)

    if result.returncode == 0:
        print("✅ All pre-commit checks passed!")
    else:
        print("⚠️  Some files need formatting. This is normal for first setup.")
        print("   The hooks will auto-fix these issues on your first commit.")

    print("\n✨ Setup complete! You're ready to develop.")
    print("📝 Remember: Pre-commit hooks will now run automatically on every commit.")


if __name__ == "__main__":
    main()
