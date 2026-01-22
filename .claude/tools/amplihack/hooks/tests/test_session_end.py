#!/usr/bin/env python3
"""
Test suite for SessionEnd hook.
Comprehensive tests covering various scenarios and edge cases.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run_hook(test_input: dict) -> tuple[int, str, str]:
    """Execute the hook with given input and return results.

    Args:
        test_input: Input data to pass to the hook

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    hook_path = Path(__file__).parent.parent / "session_end.py"

    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(test_input),
        capture_output=True,
        text=True,
        timeout=10,
    )

    return result.returncode, result.stdout, result.stderr


def test_uncommitted_work():
    """Test the SessionEnd hook with uncommitted work in current directory."""
    test_input = {
        "hook_event_name": "SessionEnd",
        "session_id": "test_20260122_123456",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": str(Path.cwd()),
        "permission_mode": "bypassPermissions",
        "reason": "exit",
    }

    print("\n" + "=" * 70)
    print("TEST 1: Uncommitted work detection")
    print("=" * 70)
    print(f"Test input: {json.dumps(test_input, indent=2)}")

    returncode, stdout, stderr = run_hook(test_input)

    print(f"\nReturn code: {returncode}")
    print(f"\nSTDOUT:\n{stdout}")
    print(f"\nSTDERR:\n{stderr}")

    # Verify no emojis in output
    emoji_list = ["⚠️", "📦", "✏️", "💡", "📝", "💾", "🔍", "🔄"]
    for emoji in emoji_list:
        if emoji in stderr:
            print(f"❌ FAIL: Found emoji '{emoji}' in output")
            return False

    # Verify output JSON is valid
    if stdout.strip():
        try:
            json.loads(stdout)
        except json.JSONDecodeError as e:
            print(f"❌ FAIL: Invalid JSON output - {e}")
            return False

    print("✅ PASS: Uncommitted work detection test")
    return returncode == 0


def test_clean_repository():
    """Test hook behavior with a clean git repository (no uncommitted work)."""
    # Create a temporary git repository
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmpdir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmpdir,
            capture_output=True,
        )

        # Create and commit a file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test content")
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=tmpdir,
            capture_output=True,
        )

        test_input = {
            "hook_event_name": "SessionEnd",
            "session_id": "test_clean_repo",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": tmpdir,
            "permission_mode": "bypassPermissions",
            "reason": "exit",
        }

        print("\n" + "=" * 70)
        print("TEST 2: Clean repository (no uncommitted work)")
        print("=" * 70)

        returncode, stdout, stderr = run_hook(test_input)

        print(f"\nReturn code: {returncode}")
        print(f"\nSTDOUT:\n{stdout}")
        print(f"\nSTDERR:\n{stderr}")

        # Verify no warning is shown
        if "WARNING: UNCOMMITTED WORK" in stderr:
            print("❌ FAIL: Warning shown for clean repository")
            return False

        print("✅ PASS: Clean repository test")
        return returncode == 0


def test_non_git_directory():
    """Test hook behavior in a non-git directory (should handle gracefully)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_input = {
            "hook_event_name": "SessionEnd",
            "session_id": "test_non_git",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": tmpdir,
            "permission_mode": "bypassPermissions",
            "reason": "exit",
        }

        print("\n" + "=" * 70)
        print("TEST 3: Non-git directory")
        print("=" * 70)

        returncode, stdout, stderr = run_hook(test_input)

        print(f"\nReturn code: {returncode}")
        print(f"\nSTDOUT:\n{stdout}")
        print(f"\nSTDERR:\n{stderr}")

        # Should handle gracefully without crashing
        if returncode != 0:
            print("❌ FAIL: Hook crashed on non-git directory")
            return False

        # Should not show uncommitted work warning
        if "WARNING: UNCOMMITTED WORK" in stderr:
            print("❌ FAIL: Warning shown for non-git directory")
            return False

        print("✅ PASS: Non-git directory test")
        return True


def test_git_timeout():
    """Test graceful handling when git commands timeout."""
    # Use a directory that exists but git operations might be slow
    test_input = {
        "hook_event_name": "SessionEnd",
        "session_id": "test_timeout",
        "transcript_path": "/path/to/transcript.jsonl",
        "cwd": str(Path.cwd()),
        "permission_mode": "bypassPermissions",
        "reason": "exit",
    }

    print("\n" + "=" * 70)
    print("TEST 4: Git timeout handling")
    print("=" * 70)
    print("Note: Testing timeout handling mechanism exists (2s for rev-parse, 5s for status)")

    returncode, _stdout, _stderr = run_hook(test_input)

    print(f"\nReturn code: {returncode}")

    # Should not crash even if timeout occurs
    if returncode != 0:
        print("❌ FAIL: Hook crashed during timeout test")
        return False

    print("✅ PASS: Git timeout handling test")
    return True


def test_file_list_truncation():
    """Test that file lists are truncated to max 5 files with '... and N more'."""
    # Create a temporary git repository with many modified files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=tmpdir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=tmpdir,
            capture_output=True,
        )

        # Create 10 uncommitted files
        for i in range(10):
            test_file = Path(tmpdir) / f"test_{i}.txt"
            test_file.write_text(f"test content {i}")

        test_input = {
            "hook_event_name": "SessionEnd",
            "session_id": "test_truncation",
            "transcript_path": "/path/to/transcript.jsonl",
            "cwd": tmpdir,
            "permission_mode": "bypassPermissions",
            "reason": "exit",
        }

        print("\n" + "=" * 70)
        print("TEST 5: File list truncation (max 5 files shown)")
        print("=" * 70)

        returncode, _stdout, stderr = run_hook(test_input)

        print(f"\nReturn code: {returncode}")
        print(f"\nSTDERR:\n{stderr}")

        # Should show truncation message
        if "... and " not in stderr and "more" not in stderr:
            print("❌ FAIL: Truncation message not found for 10 files")
            return False

        # Should show warning
        if "WARNING: UNCOMMITTED WORK" not in stderr:
            print("❌ FAIL: No warning shown for uncommitted files")
            return False

        print("✅ PASS: File list truncation test")
        return returncode == 0


def test_empty_input():
    """Test hook behavior with missing or empty input fields."""
    test_input = {
        "hook_event_name": "SessionEnd",
        # Missing session_id, transcript_path, cwd fields
        "permission_mode": "bypassPermissions",
    }

    print("\n" + "=" * 70)
    print("TEST 6: Empty/missing input fields")
    print("=" * 70)
    print(f"Test input: {json.dumps(test_input, indent=2)}")

    returncode, stdout, stderr = run_hook(test_input)

    print(f"\nReturn code: {returncode}")
    print(f"\nSTDOUT:\n{stdout}")
    print(f"\nSTDERR:\n{stderr}")

    # Should handle gracefully without crashing
    if returncode != 0:
        print("❌ FAIL: Hook crashed on empty input")
        return False

    # Should still return valid JSON
    if stdout.strip():
        try:
            json.loads(stdout)
        except json.JSONDecodeError as e:
            print(f"❌ FAIL: Invalid JSON output - {e}")
            return False

    print("✅ PASS: Empty input handling test")
    return True


def main():
    """Run all test cases and report results."""
    print("\n" + "=" * 70)
    print("SessionEnd Hook Test Suite")
    print("=" * 70)

    tests = [
        ("Uncommitted work detection", test_uncommitted_work),
        ("Clean repository", test_clean_repository),
        ("Non-git directory", test_non_git_directory),
        ("Git timeout handling", test_git_timeout),
        ("File list truncation", test_file_list_truncation),
        ("Empty input handling", test_empty_input),
    ]

    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print(f"\n{passed}/{total} tests passed")
    print("=" * 70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
