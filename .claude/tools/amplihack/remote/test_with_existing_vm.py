#!/usr/bin/env python3
"""
E2E test using an existing VM (no provisioning needed).

This bypasses azlin's bastion prompt bug by using a pre-existing VM.
"""

import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add parent directories to path
remote_dir = Path(__file__).parent
tools_dir = remote_dir.parent
sys.path.insert(0, str(tools_dir))

from remote.context_packager import ContextPackager
from remote.errors import ExecutionError, PackagingError
from remote.executor import Executor
from remote.orchestrator import VM


def test_with_existing_vm(vm_name: str):
    """Test remote execution using an existing VM.

    Args:
        vm_name: Name of existing azlin VM to use
    """
    print("=" * 70)
    print(f"E2E TEST WITH EXISTING VM: {vm_name}")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Step 1: Create test repository
        print("\n[1/5] Creating test repository...")
        repo_path = Path(temp_dir) / "test_repo"
        repo_path.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@amplihack.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )

        # Create .claude directory
        claude_dir = repo_path / ".claude"
        (claude_dir / "runtime" / "logs").mkdir(parents=True)

        # Add test file
        (repo_path / "test.txt").write_text("Hello from test repository\n")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "test"], cwd=repo_path, check=True, capture_output=True
        )

        print("✓ Test repository created")

        # Step 2: Package context
        print("\n[2/5] Packaging context...")
        packager = None
        try:
            packager = ContextPackager(repo_path)
            packager.__enter__()  # Start context

            secrets = packager.scan_secrets()
            if secrets:
                print(f"✗ Secrets found: {len(secrets)}")
                packager.__exit__(None, None, None)
                return False

            archive_path = packager.package()
            size_kb = archive_path.stat().st_size / 1024
            print(f"✓ Context packaged: {size_kb:.1f} KB")

            # Copy to safe location before cleanup
            safe_archive = Path(temp_dir) / "context-safe.tar.gz"
            import shutil

            shutil.copy2(archive_path, safe_archive)
            archive_path = safe_archive

            # Now cleanup packager
            packager.__exit__(None, None, None)
            packager = None

        except PackagingError as e:
            print(f"✗ Packaging failed: {e}")
            if packager:
                packager.__exit__(None, None, None)
            return False

        # Step 3: Create VM object (using existing VM)
        print(f"\n[3/5] Using existing VM: {vm_name}...")
        vm = VM(
            name=vm_name,
            size="m",  # Assuming medium
            region="westus2",
            created_at=datetime.now(),
        )
        print("✓ VM object created")

        # Step 4: Test transfer
        print("\n[4/5] Testing file transfer...")
        executor = Executor(vm, timeout_minutes=5)  # 5 minute timeout for test

        try:
            # Transfer context (this will use azlin cp)
            print(f"  Transferring {size_kb:.1f} KB to {vm_name}:/tmp/...")
            success = executor.transfer_context(archive_path)

            if success:
                print("  ✓ Transfer successful")
            else:
                print("  ✗ Transfer failed")
                return False

        except Exception as e:
            print(f"  ✗ Transfer error: {e}")
            return False

        # Step 5: Test simple remote command
        print("\n[5/5] Testing remote execution...")
        api_key = os.getenv("ANTHROPIC_API_KEY", "dummy-for-test")

        try:
            # Run simple echo command (not full amplihack to keep test quick)
            result = executor.execute_remote(
                command="echo", prompt="Testing remote execution", max_turns=1, api_key=api_key
            )

            print(f"  Exit code: {result.exit_code}")
            print(f"  Duration: {result.duration_seconds:.1f}s")

            if result.exit_code == 0:
                print("  ✓ Remote execution successful")
                if result.stdout:
                    print(f"  Output preview: {result.stdout[:150]}")
            else:
                print("  ✗ Command failed")
                print(f"  Stderr: {result.stderr[:200]}")
                return False

        except ExecutionError as e:
            print(f"  ✗ Execution error: {e}")
            return False

        print("\n" + "=" * 70)
        print("E2E TEST: PASSED ✓")
        print("=" * 70)
        print("\nValidated:")
        print("  ✓ Context packaging works")
        print("  ✓ Secret scanning works")
        print("  ✓ File transfer to VM works (azlin cp)")
        print("  ✓ Remote command execution works (azlin connect)")
        print(f"  ✓ Integration with existing VM: {vm_name}")
        return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_with_existing_vm.py <vm-name>")
        print("\nExample: python test_with_existing_vm.py azlin-vm-1762653587")
        sys.exit(1)

    vm_name = sys.argv[1]

    try:
        success = test_with_existing_vm(vm_name)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
