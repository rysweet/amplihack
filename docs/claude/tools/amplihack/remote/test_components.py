#!/usr/bin/env python3
"""
Component-level tests for remote execution feature.

Tests individual components without requiring Azure VM provisioning.
These tests validate the feature logic works correctly.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

# Add parent directories to path to handle imports
remote_dir = Path(__file__).parent
tools_dir = remote_dir.parent
sys.path.insert(0, str(tools_dir))

from remote.context_packager import ContextPackager


def test_secret_detection():
    """Test that secret scanning detects various patterns."""
    print("\n" + "=" * 60)
    print("TEST 1: SECRET DETECTION")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "test_repo"
        repo_path.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )

        # Create .claude directory
        claude_dir = repo_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "runtime" / "logs").mkdir(parents=True)

        # Test 1: No secrets - should pass
        print("\n[Test 1a] Clean repository (no secrets)...")
        clean_file = repo_path / "clean.py"
        clean_file.write_text("import os\nprint('Hello world')\n")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "clean"], cwd=repo_path, check=True, capture_output=True
        )

        with ContextPackager(repo_path) as packager:
            secrets = packager.scan_secrets()
            if not secrets:
                print("  ✓ No secrets detected (correct)")
            else:
                print(f"  ✗ False positive: {len(secrets)} secrets detected")
                return False

        # Test 2: API key in code - should detect
        print("\n[Test 1b] API key in Python file...")
        secret_file = repo_path / "config.py"
        secret_file.write_text('ANTHROPIC_API_KEY = "sk-ant-1234567890abcdef"\n')
        subprocess.run(["git", "add", "config.py"], cwd=repo_path, check=True, capture_output=True)

        with ContextPackager(repo_path) as packager:
            secrets = packager.scan_secrets()
            if secrets:
                print(f"  ✓ Secret detected: {secrets[0].pattern_name} in {secrets[0].file_path}")
            else:
                print("  ✗ Failed to detect API key")
                return False

        # Test 3: Token in environment file - should detect
        print("\n[Test 1c] Token in .env file...")
        env_file = repo_path / ".env"
        env_file.write_text("GITHUB_TOKEN=ghp_1234567890123456789012345678901234\n")

        with ContextPackager(repo_path) as packager:
            secrets = packager.scan_secrets()
            # Should find both the API key and the token
            if len(secrets) >= 2:
                print(f"  ✓ {len(secrets)} secrets detected")
            else:
                print(f"  ✗ Only {len(secrets)} secrets detected (expected 2)")
                return False

        # Test 4: Password pattern - should detect
        print("\n[Test 1d] Password in config...")
        pwd_file = repo_path / "database.conf"
        pwd_file.write_text('password = "mysecretpassword123"\n')

        with ContextPackager(repo_path) as packager:
            secrets = packager.scan_secrets()
            if len(secrets) >= 3:
                print(f"  ✓ {len(secrets)} secrets detected total")
            else:
                print(f"  ✗ Only {len(secrets)} secrets detected")
                return False

    print("\n✓ SECRET DETECTION: ALL TESTS PASSED")
    return True


def test_context_packaging():
    """Test that context packaging works correctly."""
    print("\n" + "=" * 60)
    print("TEST 2: CONTEXT PACKAGING")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "test_repo"
        repo_path.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )

        # Create .claude directory structure
        claude_dir = repo_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "runtime" / "logs").mkdir(parents=True)
        (claude_dir / "context").mkdir()

        # Add some files
        (repo_path / "README.md").write_text("# Test Repo\n")
        (repo_path / "src").mkdir(parents=True)
        (repo_path / "src" / "main.py").write_text("print('test')\n")
        (claude_dir / "context" / "PROJECT.md").write_text("# Project Context\n")

        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"], cwd=repo_path, check=True, capture_output=True
        )

        # Test packaging
        print("\n[Test 2a] Creating context archive...")
        with ContextPackager(repo_path) as packager:
            archive_path = packager.package()

            if archive_path.exists():
                size_kb = archive_path.stat().st_size / 1024
                print(f"  ✓ Archive created: {archive_path.name} ({size_kb:.1f} KB)")
            else:
                print("  ✗ Archive not created")
                return False

            # Verify archive contains expected files
            print("\n[Test 2b] Verifying archive contents...")
            import tarfile

            with tarfile.open(archive_path, "r:gz") as tar:
                names = tar.getnames()

                if "repo.bundle" in names:
                    print("  ✓ Git bundle present")
                else:
                    print("  ✗ Git bundle missing")
                    return False

                if any(".claude" in name for name in names):
                    print("  ✓ .claude directory present")
                else:
                    print("  ✗ .claude directory missing")
                    return False

    print("\n✓ CONTEXT PACKAGING: ALL TESTS PASSED")
    return True


def test_exclusion_patterns():
    """Test that sensitive files are excluded."""
    print("\n" + "=" * 60)
    print("TEST 3: FILE EXCLUSION")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "test_repo"
        repo_path.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )

        # Create .claude
        claude_dir = repo_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "runtime" / "logs").mkdir(parents=True)

        # Create files that should be excluded
        (repo_path / ".env").write_text("SECRET=value\n")
        (repo_path / "credentials.json").write_text('{"key": "value"}\n')
        (repo_path / "test.pem").write_text("-----BEGIN PRIVATE KEY-----\n")

        # Create regular files
        (repo_path / "README.md").write_text("# Test\n")

        subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"], cwd=repo_path, check=True, capture_output=True
        )

        print("\n[Test 3a] Checking exclusion patterns...")
        with ContextPackager(repo_path) as packager:
            # Test individual file exclusions
            tests = [
                (".env", True, "Environment file"),
                ("credentials.json", True, "Credentials file"),
                ("test.pem", True, "Private key"),
                ("README.md", False, "Regular file"),
            ]

            all_passed = True
            for filename, should_exclude, description in tests:
                # Pass filename as string, not Path object
                is_excluded = packager._is_excluded(filename)

                if is_excluded == should_exclude:
                    status = "✓"
                else:
                    status = "✗"
                    all_passed = False

                print(f"  {status} {description}: {filename} (excluded={is_excluded})")

            if not all_passed:
                return False

    print("\n✓ FILE EXCLUSION: ALL TESTS PASSED")
    return True


def main():
    """Run all component tests."""
    print("=" * 60)
    print("REMOTE EXECUTION COMPONENT TESTS")
    print("=" * 60)
    print("\nThese tests validate the feature logic without requiring")
    print("Azure VM provisioning (which requires interactive prompts).")
    print("=" * 60)

    results = []

    # Test 1: Secret Detection
    try:
        results.append(("Secret Detection", test_secret_detection()))
    except Exception as e:
        print(f"\n✗ Secret detection test failed: {e}")
        import traceback

        traceback.print_exc()
        results.append(("Secret Detection", False))

    # Test 2: Context Packaging
    try:
        results.append(("Context Packaging", test_context_packaging()))
    except Exception as e:
        print(f"\n✗ Context packaging test failed: {e}")
        import traceback

        traceback.print_exc()
        results.append(("Context Packaging", False))

    # Test 3: Exclusion Patterns
    try:
        results.append(("File Exclusion", test_exclusion_patterns()))
    except Exception as e:
        print(f"\n✗ Exclusion patterns test failed: {e}")
        import traceback

        traceback.print_exc()
        results.append(("File Exclusion", False))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)

    return all(result for _, result in results)


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
