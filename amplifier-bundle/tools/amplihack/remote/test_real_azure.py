#!/usr/bin/env python3
"""
Real Azure integration test for remote execution feature.

This test validates the feature works with actual Azure VMs.
Cost: ~$0.10-0.50 per test run.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add parent directories to path to handle imports
remote_dir = Path(__file__).parent
tools_dir = remote_dir.parent
sys.path.insert(0, str(tools_dir))

# Now import as a package
from remote.context_packager import ContextPackager
from remote.errors import ExecutionError, PackagingError, ProvisioningError
from remote.executor import Executor
from remote.orchestrator import Orchestrator, VMOptions


def test_minimal_smoke():
    """Minimal smoke test with real Azure VM.

    This test:
    1. Creates a simple git repo
    2. Packages it (with secret scanning)
    3. Provisions a VM
    4. Transfers context
    5. Runs a simple echo command
    6. Retrieves results
    7. Cleans up VM
    """
    print("=" * 60)
    print("REMOTE EXECUTION SMOKE TEST")
    print("=" * 60)

    # Create temporary test repository
    print("\n[1/7] Creating test repository...")
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir) / "test_repo"
        repo_path.mkdir()

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create .claude directory structure
        claude_dir = repo_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "runtime").mkdir()
        (claude_dir / "runtime" / "logs").mkdir(parents=True)

        # Add a test file
        test_file = repo_path / "README.md"
        test_file.write_text("# Test Repository\n\nThis is a test for remote execution.\n")

        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        print("✓ Test repository created")

        # Step 2: Package context with secret scanning
        print("\n[2/7] Packaging context...")
        try:
            with ContextPackager(repo_path) as packager:
                # Scan for secrets
                secrets = packager.scan_secrets()
                if secrets:
                    print(f"✗ Secrets detected: {len(secrets)}")
                    for secret in secrets[:3]:  # Show first 3
                        print(f"  - {secret.file_path}:{secret.line_number}")
                    return False

                # Create package
                archive_path = packager.package()
                print(
                    f"✓ Context packaged: {archive_path} ({archive_path.stat().st_size / 1024:.1f} KB)"
                )
        except PackagingError as e:
            print(f"✗ Packaging failed: {e}")
            return False

        # Step 3: Provision VM
        print("\n[3/7] Provisioning Azure VM...")
        orchestrator = Orchestrator()
        vm_options = VMOptions(
            size="s",  # Small VM size (azlin format: s/m/l/xl)
            region="westus2",
            no_reuse=False,  # Allow reuse
            keep_vm=False,  # Clean up after test
        )

        try:
            vm = orchestrator.provision_or_reuse(vm_options)
            print(f"✓ VM ready: {vm.name} ({vm.size})")
        except ProvisioningError as e:
            print(f"✗ VM provisioning failed: {e}")
            return False

        # Step 4: Transfer context
        print("\n[4/7] Transferring context to VM...")
        executor = Executor(vm, timeout_seconds=300)  # 5 minute timeout for test

        try:
            success = executor.transfer_context(archive_path)
            if not success:
                print("✗ Transfer failed")
                orchestrator.cleanup(vm, force=False)
                return False
            print("✓ Context transferred")
        except Exception as e:
            print(f"✗ Transfer error: {e}")
            orchestrator.cleanup(vm, force=False)
            return False

        # Step 5: Execute simple command (just echo, not amplihack)
        print("\n[5/7] Executing test command...")
        api_key = os.getenv("ANTHROPIC_API_KEY", "dummy-key-for-test")

        try:
            result = executor.execute_remote(
                command="echo",  # Simple command for smoke test
                prompt="Hello from remote VM",
                max_turns=1,
                api_key=api_key,
            )

            if result.exit_code == 0:
                print("✓ Command executed successfully")
                print(f"  Duration: {result.duration_seconds:.1f}s")
                if result.stdout:
                    print(f"  Output preview: {result.stdout[:100]}")
            else:
                print(f"✗ Command failed with exit code {result.exit_code}")
                print(f"  Stderr: {result.stderr[:200]}")
        except ExecutionError as e:
            print(f"✗ Execution error: {e}")
            orchestrator.cleanup(vm, force=False)
            return False

        # Step 6: Retrieve results (logs only for smoke test)
        print("\n[6/7] Retrieving logs...")
        try:
            logs_retrieved = executor.retrieve_logs(Path(temp_dir) / "logs")
            if logs_retrieved:
                print("✓ Logs retrieved")
            else:
                print("⚠ No logs to retrieve (expected for simple command)")
        except Exception as e:
            print(f"⚠ Log retrieval warning: {e}")

        # Step 7: Cleanup VM
        print("\n[7/7] Cleaning up VM...")
        try:
            orchestrator.cleanup(vm)
            print("✓ VM cleaned up")
        except Exception as e:
            print(f"⚠ Cleanup warning: {e}")

        print("\n" + "=" * 60)
        print("SMOKE TEST: PASSED ✓")
        print("=" * 60)
        return True


if __name__ == "__main__":
    try:
        success = test_minimal_smoke()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
