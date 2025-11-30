"""CLI entry point for remote execution.

This module provides the command-line interface for executing
amplihack commands on remote Azure VMs.
"""

import sys
import tempfile
from pathlib import Path
from typing import Optional

import click

from .context_packager import ContextPackager
from .errors import (
    CleanupError,
    ExecutionError,
    IntegrationError,
    PackagingError,
    ProvisioningError,
    RemoteExecutionError,
    TransferError,
)
from .executor import Executor
from .integrator import Integrator
from .orchestrator import Orchestrator, VMOptions


@click.command(name="remote", context_settings={"ignore_unknown_options": True})
@click.argument("command", type=click.Choice(["auto", "ultrathink", "analyze", "fix"]))
@click.argument("prompt")
@click.option("--max-turns", default=10, type=int, help="Maximum turns for auto mode")
@click.option("--vm-size", default="Standard_D2s_v3", help="Azure VM size")
@click.option("--vm-name", default=None, help="Specific VM to reuse")
@click.option("--keep-vm", is_flag=True, help="Don't cleanup VM after execution")
@click.option("--no-reuse", is_flag=True, help="Always provision fresh VM")
@click.option("--timeout", default=120, type=int, help="Max execution time in minutes")
@click.option("--region", default=None, help="Azure region")
@click.argument("azlin_args", nargs=-1, type=click.UNPROCESSED)
def remote_execute(
    command: str,
    prompt: str,
    max_turns: int,
    vm_size: str,
    vm_name: Optional[str],
    keep_vm: bool,
    no_reuse: bool,
    timeout: int,
    region: Optional[str],
    azlin_args: tuple,
):
    """Execute amplihack command on remote Azure VM.

    COMMAND: Amplihack command to execute (auto, ultrathink, analyze, fix)
    PROMPT: Task prompt for the command

    Examples:

      amplihack remote auto "implement user authentication"

      amplihack remote --max-turns 20 auto "refactor API module"

      amplihack remote --keep-vm ultrathink "read issue #24 and submit PR"
    """
    # Validate arguments
    if not prompt.strip():
        click.echo("Error: Prompt cannot be empty", err=True)
        sys.exit(1)

    if max_turns < 1 or max_turns > 50:
        click.echo("Error: max-turns must be between 1 and 50", err=True)
        sys.exit(1)

    if timeout < 5 or timeout > 480:
        click.echo("Error: timeout must be between 5 and 480 minutes", err=True)
        sys.exit(1)

    # Get repository path (current directory)
    repo_path = Path.cwd()

    # Create VM options (include any extra azlin arguments)
    vm_options = VMOptions(
        size=vm_size,
        region=region,
        vm_name=vm_name,
        no_reuse=no_reuse,
        keep_vm=keep_vm,
        azlin_extra_args=list(azlin_args) if azlin_args else None,
    )

    # Execute with progress reporting
    try:
        execute_remote_workflow(
            repo_path=repo_path,
            command=command,
            prompt=prompt,
            max_turns=max_turns,
            vm_options=vm_options,
            timeout=timeout,
        )
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except RemoteExecutionError as e:
        click.echo(f"\nError: {e}", err=True)
        if e.context:
            click.echo(f"Context: {e.context}", err=True)
        sys.exit(1)


def execute_remote_workflow(
    repo_path: Path,
    command: str,
    prompt: str,
    max_turns: int,
    vm_options: VMOptions,
    timeout: int,
    skip_secret_scan: bool = False,
):
    """Execute the complete remote workflow.

    Args:
        repo_path: Local repository path
        command: Amplihack command
        prompt: Task prompt
        max_turns: Maximum turns
        vm_options: VM configuration
        timeout: Timeout in minutes
        skip_secret_scan: Skip secret scanning (for development with ephemeral VMs)
    """
    vm = None
    results_dir = None

    try:
        # Step 1: Validate environment
        click.echo("\n[1/7] Validating environment...")
        click.echo("  \u2713 Repository found")
        click.echo("  \u2713 Starting remote execution workflow")

        # Step 2: Package context
        click.echo("\n[2/7] Packaging context...")

        with ContextPackager(repo_path) as packager:
            # Scan for secrets (unless skipped)
            if not skip_secret_scan:
                click.echo("  \u2192 Scanning for secrets...")
                secrets = packager.scan_secrets()
                if secrets:
                    raise PackagingError(
                        f"Found {len(secrets)} potential secret(s). Please remove them and retry."
                    )
                click.echo("  \u2713 No secrets detected")
            else:
                click.echo("  \u26a0  Secret scanning skipped (--skip-secret-scan)")

            # Create package
            click.echo("  \u2192 Creating context archive...")
            archive_path = packager.package(skip_secret_scan=skip_secret_scan)
            archive_size_mb = archive_path.stat().st_size / 1024 / 1024
            click.echo(f"  \u2713 Context package created: {archive_size_mb:.1f} MB")

            # Step 3: Provision VM
            click.echo("\n[3/7] Provisioning VM...")
            orchestrator = Orchestrator()
            vm = orchestrator.provision_or_reuse(vm_options)
            click.echo(f"  \u2713 VM ready: {vm.name} ({vm.size})")

            # Step 4: Transfer context
            click.echo("\n[4/7] Transferring context...")
            executor = Executor(vm, timeout_minutes=timeout)
            executor.transfer_context(archive_path)
            click.echo("  \u2713 Context transferred")

        # Package cleanup happens here (context manager exit)

        # Step 5: Execute remote command
        click.echo("\n[5/7] Executing remote command...")
        click.echo(f"  \u2192 Running: amplihack {command} --max-turns {max_turns}")
        click.echo(
            f"  \u2192 Prompt: {prompt[:80]}..."
            if len(prompt) > 80
            else f"  \u2192 Prompt: {prompt}"
        )

        result = executor.execute_remote(command=command, prompt=prompt, max_turns=max_turns)

        if result.timed_out:
            click.echo(f"  ! Execution timed out after {result.duration_seconds / 60:.1f} minutes")
        elif result.exit_code == 0:
            click.echo(f"  \u2713 Execution complete ({result.duration_seconds / 60:.1f} minutes)")
        else:
            click.echo(f"  ! Execution failed with exit code {result.exit_code}")
            click.echo(f"\nStderr:\n{result.stderr}")

        # Step 6: Retrieve results
        click.echo("\n[6/7] Retrieving results...")

        # Create temporary directory for results
        results_dir = Path(tempfile.mkdtemp(prefix="amplihack-results-"))

        # Retrieve logs
        try:
            executor.retrieve_logs(results_dir)
            click.echo("  \u2713 Logs retrieved")
        except TransferError as e:
            click.echo(f"  ! Log retrieval failed: {e}")

        # Retrieve git state
        try:
            executor.retrieve_git_state(results_dir)
            click.echo("  \u2713 Git state retrieved")
        except TransferError as e:
            click.echo(f"  ! Git state retrieval failed: {e}")

        # Integrate results
        integrator = Integrator(repo_path)
        summary = integrator.integrate(results_dir)

        click.echo(f"  \u2713 Branches: {len(summary.branches)}")
        click.echo(f"  \u2713 Commits: {summary.commits_count}")
        click.echo(f"  \u2713 Files changed: {summary.files_changed}")

        if summary.has_conflicts:
            click.echo("  ! Conflicts detected (manual merge required)")

        # Step 7: Cleanup
        click.echo("\n[7/7] Cleaning up...")

        # Cleanup VM unless keep-vm flag set or execution failed critically
        should_cleanup = not vm_options.keep_vm
        if result.exit_code != 0 and not result.timed_out:
            # Preserve VM on non-timeout failures for debugging
            click.echo(f"  \u2192 Preserving VM for debugging: {vm.name}")
            should_cleanup = False

        if should_cleanup:
            try:
                orchestrator.cleanup(vm, force=True)
                click.echo(f"  \u2713 VM cleaned up: {vm.name}")
            except CleanupError as e:
                click.echo(f"  ! Cleanup failed: {e}")
                click.echo(f"  \u2192 Manual cleanup: azlin kill {vm.name}")
        else:
            click.echo(f"  \u2192 VM preserved: {vm.name}")

        # Display summary
        click.echo(integrator.create_summary_report(summary))

        # Exit with appropriate code
        if result.exit_code != 0:
            sys.exit(result.exit_code)

    except PackagingError as e:
        click.echo(f"\nPackaging Error: {e}", err=True)
        sys.exit(1)

    except ProvisioningError as e:
        click.echo(f"\nProvisioning Error: {e}", err=True)
        click.echo("\nTroubleshooting:", err=True)
        click.echo("  - Verify azlin is installed: pip install azlin", err=True)
        click.echo("  - Verify azlin is configured: azlin configure", err=True)
        click.echo("  - Check Azure subscription status", err=True)
        sys.exit(1)

    except TransferError as e:
        click.echo(f"\nTransfer Error: {e}", err=True)
        if vm:
            click.echo(f"\nVM preserved for inspection: {vm.name}", err=True)
            click.echo(f"Manual access: azlin connect {vm.name}", err=True)
        sys.exit(1)

    except ExecutionError as e:
        click.echo(f"\nExecution Error: {e}", err=True)
        if vm:
            click.echo(f"\nVM preserved for inspection: {vm.name}", err=True)
        sys.exit(1)

    except IntegrationError as e:
        click.echo(f"\nIntegration Error: {e}", err=True)
        if results_dir:
            click.echo(f"\nResults archived at: {results_dir}", err=True)
        sys.exit(1)

    finally:
        # Cleanup temporary results directory
        if results_dir and results_dir.exists():
            import shutil

            try:
                shutil.rmtree(results_dir)
            except (OSError, PermissionError) as e:
                # Non-fatal: log but continue
                click.echo(f"Warning: Could not cleanup temp directory: {e}", err=True)


def main():
    """Entry point for CLI."""
    remote_execute()


if __name__ == "__main__":
    main()
