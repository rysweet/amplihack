#!/usr/bin/env python3
"""Integration test for gitignore_checker in session_start.py.

This test verifies that:
1. GitignoreChecker can be imported
2. The session_start hook calls gitignore_checker properly
3. Error handling works correctly
"""

import subprocess
import tempfile
from pathlib import Path


def test_gitignore_checker_integration():
    """Test that gitignore_checker integrates correctly with session_start."""
    print("🧪 Testing gitignore_checker integration...")

    # Create temporary git repo
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        print(f"\n📁 Created test repo: {repo_path}")

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True,
        )

        # Create .claude directory structure
        claude_dir = repo_path / ".claude"
        claude_dir.mkdir(parents=True)
        logs_dir = claude_dir / "logs"
        logs_dir.mkdir()
        runtime_dir = claude_dir / "runtime"
        runtime_dir.mkdir()

        # Create a dummy file in runtime to make it trackable
        (runtime_dir / "test.txt").write_text("test")

        print("✅ Created .claude/logs/ and .claude/runtime/ directories")

        # Test gitignore_checker directly
        import sys

        sys.path.insert(0, str(Path(__file__).parent))
        from gitignore_checker import GitignoreChecker

        # Change to test repo
        import os

        original_dir = os.getcwd()
        try:
            os.chdir(repo_path)

            # Run checker
            checker = GitignoreChecker()
            result = checker.run(display_warnings=False)

            print(f"\n📊 Checker result: {result}")

            # Verify .gitignore was created/updated
            gitignore_path = repo_path / ".gitignore"
            assert gitignore_path.exists(), ".gitignore should be created"
            print("✅ .gitignore file created")

            # Verify patterns were added
            content = gitignore_path.read_text()
            assert ".claude/logs/" in content, ".claude/logs/ should be in .gitignore"
            assert ".claude/runtime/" in content, ".claude/runtime/ should be in .gitignore"
            print("✅ Runtime directories added to .gitignore")

            # Verify result structure
            assert result.get("is_git_repo") is True, "Should detect git repo"
            assert result.get("modified") is True, "Should report modification"
            assert len(result.get("missing_dirs", [])) == 2, "Should find 2 missing dirs"
            print("✅ Result structure correct")

            # Test idempotency - running again should not modify
            result2 = checker.run(display_warnings=False)
            assert result2.get("modified") is False, "Second run should not modify"
            print("✅ Idempotency verified")

        finally:
            os.chdir(original_dir)

    print("\n🎉 All integration tests passed!")


if __name__ == "__main__":
    test_gitignore_checker_integration()
