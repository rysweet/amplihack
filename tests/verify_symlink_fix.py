#!/usr/bin/env python
"""
Standalone verification script for symlink path traversal fix.

This script tests that the FilesystemPackager correctly rejects
symlink-based path traversal attacks.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.amplihack.bundle_generator.filesystem_packager import FilesystemPackager
from src.amplihack.bundle_generator.exceptions import PackagingError


def test_symlink_to_etc():
    """Test that symlink to /etc is rejected."""
    print("Test 1: Symlink to /etc should be rejected...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        symlink_path = tmpdir_path / "evil"
        symlink_path.symlink_to(Path("/etc"))

        try:
            FilesystemPackager(symlink_path)
            print("  FAIL: Expected PackagingError but none was raised")
            return False
        except PackagingError as e:
            if "symlink" in str(e).lower():
                print(f"  PASS: Rejected with message: {e}")
                return True
            else:
                print(f"  FAIL: Wrong error message: {e}")
                return False


def test_symlink_to_usr():
    """Test that symlink to /usr is rejected."""
    print("Test 2: Symlink to /usr should be rejected...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        symlink_path = tmpdir_path / "malicious"
        symlink_path.symlink_to(Path("/usr"))

        try:
            FilesystemPackager(symlink_path)
            print("  FAIL: Expected PackagingError but none was raised")
            return False
        except PackagingError as e:
            if "symlink" in str(e).lower():
                print(f"  PASS: Rejected with message: {e}")
                return True
            else:
                print(f"  FAIL: Wrong error message: {e}")
                return False


def test_symlink_to_bin():
    """Test that symlink to /bin is rejected."""
    print("Test 3: Symlink to /bin should be rejected...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        symlink_path = tmpdir_path / "attack"
        symlink_path.symlink_to(Path("/bin"))

        try:
            FilesystemPackager(symlink_path)
            print("  FAIL: Expected PackagingError but none was raised")
            return False
        except PackagingError as e:
            if "symlink" in str(e).lower():
                print(f"  PASS: Rejected with message: {e}")
                return True
            else:
                print(f"  FAIL: Wrong error message: {e}")
                return False


def test_regular_directory():
    """Test that regular directories are accepted."""
    print("Test 4: Regular directory should be accepted...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        regular_dir = tmpdir_path / "regular"
        regular_dir.mkdir()

        try:
            packager = FilesystemPackager(regular_dir)
            print(f"  PASS: Regular directory accepted")
            return True
        except Exception as e:
            print(f"  FAIL: Unexpected error: {e}")
            return False


def test_nonexistent_path():
    """Test that nonexistent regular paths are accepted."""
    print("Test 5: Nonexistent regular path should be accepted...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        nonexistent = tmpdir_path / "will_be_created"

        try:
            packager = FilesystemPackager(nonexistent)
            print(f"  PASS: Nonexistent path accepted")
            return True
        except Exception as e:
            print(f"  FAIL: Unexpected error: {e}")
            return False


def test_symlink_chain():
    """Test that symlink chains are rejected."""
    print("Test 6: Symlink chain should be rejected...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        link1 = tmpdir_path / "link1"
        link2 = tmpdir_path / "link2"

        link2.symlink_to(Path("/etc"))
        link1.symlink_to(link2)

        try:
            FilesystemPackager(link1)
            print("  FAIL: Expected PackagingError but none was raised")
            return False
        except PackagingError as e:
            if "symlink" in str(e).lower():
                print(f"  PASS: Rejected with message: {e}")
                return True
            else:
                print(f"  FAIL: Wrong error message: {e}")
                return False


def test_symlink_to_root():
    """Test that symlink to / is rejected."""
    print("Test 7: Symlink to / should be rejected...")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        symlink_path = tmpdir_path / "root_link"
        symlink_path.symlink_to(Path("/"))

        try:
            FilesystemPackager(symlink_path)
            print("  FAIL: Expected PackagingError but none was raised")
            return False
        except PackagingError as e:
            if "symlink" in str(e).lower():
                print(f"  PASS: Rejected with message: {e}")
                return True
            else:
                print(f"  FAIL: Wrong error message: {e}")
                return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Path Traversal Symlink Fix Verification")
    print("=" * 70 + "\n")

    tests = [
        test_symlink_to_etc,
        test_symlink_to_usr,
        test_symlink_to_bin,
        test_regular_directory,
        test_nonexistent_path,
        test_symlink_chain,
        test_symlink_to_root,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append(False)
        print()

    # Summary
    passed = sum(results)
    total = len(results)
    print("=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)

    if passed == total:
        print("SUCCESS: All tests passed! Symlink path traversal is fixed.")
        return 0
    else:
        print("FAILURE: Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
