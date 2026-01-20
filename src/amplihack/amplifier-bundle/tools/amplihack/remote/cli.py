"""CLI entry point for remote execution.

This module provides the command-line interface for executing
amplihack commands on remote Azure VMs. Supports both synchronous
execution and detached session management.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

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
from .session import SessionManager, SessionStatus
from .vm_pool import VMPoolManager, VMSize


@click.group(name="remote")
def remote_cli():
    """Remote execution and session management commands."""


# ====================================================================
# SYNCHRONOUS EXECUTION (Original Command)
# ====================================================================


@remote_cli.command(name="exec")
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
    vm_name: str | None,
    keep_vm: bool,
    no_reuse: bool,
    timeout: int,
    region: str | None,
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


# ====================================================================
# SESSION MANAGEMENT COMMANDS
# ====================================================================


@remote_cli.command(name="list")
@click.option(
    "--status",
    type=click.Choice(["pending", "running", "completed", "failed", "killed"]),
    default=None,
    help="Filter by session status",
)
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def cmd_list(status: str | None, output_json: bool):
    """List all remote sessions.

    Usage: amplihack remote list [--status <status>] [--json]

    Examples:
        amplihack remote list
        amplihack remote list --status running
        amplihack remote list --json
    """
    try:
        # Create session manager
        session_mgr = SessionManager()

        # Filter by status if specified
        filter_status = SessionStatus(status) if status else None
        sessions = session_mgr.list_sessions(status=filter_status)

        if output_json:
            # JSON output
            output = [s.to_dict() for s in sessions]
            click.echo(json.dumps(output, indent=2))
            return

        # Table output
        if not sessions:
            click.echo("No remote sessions found.")
            return

        # Calculate age for each session
        now = datetime.now()

        # Header
        click.echo(f"{'SESSION':<30} {'VM':<32} {'STATUS':<10} {'AGE':<8} {'PROMPT'}")
        click.echo("-" * 120)

        # Rows
        for session in sessions:
            age_delta = now - session.created_at
            age_minutes = int(age_delta.total_seconds() / 60)

            if age_minutes < 60:
                age_str = f"{age_minutes}m"
            else:
                age_hours = age_minutes // 60
                age_str = f"{age_hours}h"

            # Truncate prompt to fit
            prompt_display = (
                session.prompt[:50] + "..." if len(session.prompt) > 50 else session.prompt
            )

            click.echo(
                f"{session.session_id:<30} {session.vm_name:<32} "
                f"{session.status.value:<10} {age_str:<8} {prompt_display}"
            )

        click.echo(f"\nTotal: {len(sessions)} session(s)")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@remote_cli.command(name="start")
@click.argument("prompts", nargs=-1, required=True)
@click.option(
    "--command",
    default="auto",
    type=click.Choice(["auto", "ultrathink", "analyze", "fix"]),
    help="Claude command mode (default: auto)",
)
@click.option("--max-turns", default=10, type=int, help="Maximum turns (default: 10)")
@click.option(
    "--size",
    default="l",
    type=click.Choice(["s", "m", "l", "xl"]),
    help="VM size tier (s=1, m=2, l=4, xl=8 sessions) [default: l]",
)
@click.option("--region", default=None, help="Azure region")
def cmd_start(prompts: tuple, command: str, max_turns: int, size: str, region: str | None):
    """Start one or more detached remote sessions.

    Usage: amplihack remote start [options] "<prompt1>" "<prompt2>" ...

    Options:
        --command: Claude command mode (auto, ultrathink, etc.) [default: auto]
        --max-turns: Maximum turns [default: 10]
        --size: VM size (s/m/l/xl) [default: l]
        --region: Azure region [optional]

    Examples:
        amplihack remote start "implement user auth"
        amplihack remote start --command ultrathink "fix bug #123"
        amplihack remote start --size xl "task1" "task2" "task3"
    """
    try:
        # Validate arguments
        if not prompts:
            click.echo("Error: At least one prompt is required", err=True)
            sys.exit(1)

        # Convert size to VMSize enum
        vm_size = VMSize[size.upper()]

        # Get repository path
        repo_path = Path.cwd()

        # Get default region from environment or use eastus
        if not region:
            region = os.getenv("AZURE_REGION", "eastus")

        # Get API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            click.echo(
                "Error: ANTHROPIC_API_KEY not found. Set it in environment or ~/.claude.json",
                err=True,
            )
            sys.exit(1)

        # Initialize managers
        session_mgr = SessionManager()
        vm_pool_mgr = VMPoolManager()

        click.echo(f"\n🚀 Starting {len(prompts)} remote session(s)...")
        click.echo(f"   Command: {command}")
        click.echo(f"   VM Size: {size.upper()} ({vm_size.value} concurrent sessions)")
        click.echo(f"   Region: {region}\n")

        started_sessions = []

        for i, prompt in enumerate(prompts, 1):
            click.echo(f"[{i}/{len(prompts)}] Starting session: {prompt[:60]}...")

            try:
                # Step 1: Package context
                click.echo("  → Packaging context...")
                with ContextPackager(repo_path) as packager:
                    # Scan for secrets
                    secrets = packager.scan_secrets()
                    if secrets:
                        click.echo(
                            f"  ✗ Found {len(secrets)} potential secret(s). Remove them and retry.",
                            err=True,
                        )
                        continue

                    # Create package
                    archive_path = packager.package()
                    archive_size_mb = archive_path.stat().st_size / 1024 / 1024
                    click.echo(f"  ✓ Context packaged: {archive_size_mb:.1f} MB")

                    # Step 2: Allocate VM
                    click.echo("  → Allocating VM...")

                    # Create temporary session ID for allocation
                    temp_session = session_mgr.create_session(
                        vm_name="pending",
                        prompt=prompt,
                        command=command,
                        max_turns=max_turns,
                    )

                    vm = vm_pool_mgr.allocate_vm(
                        session_id=temp_session.session_id,
                        size=vm_size,
                        region=region,
                    )

                    # Update session with actual VM name
                    temp_session.vm_name = vm.name
                    session_mgr._save_state()

                    click.echo(f"  ✓ VM allocated: {vm.name}")

                    # Step 3: Transfer context
                    click.echo("  → Transferring context...")
                    executor = Executor(vm)
                    executor.transfer_context(archive_path)
                    click.echo("  ✓ Context transferred")

                # Step 4: Launch in tmux
                click.echo("  → Launching tmux session...")
                executor.execute_remote_tmux(
                    session_id=temp_session.session_id,
                    command=command,
                    prompt=prompt,
                    max_turns=max_turns,
                    api_key=api_key,
                )

                # Step 5: Mark session as RUNNING
                session_mgr.start_session(temp_session.session_id, archive_path)

                click.echo(f"  ✓ Session started: {temp_session.session_id}\n")
                started_sessions.append(temp_session.session_id)

            except Exception as e:
                click.echo(f"  ✗ Failed to start session: {e}", err=True)
                continue

        # Summary
        if started_sessions:
            click.echo(f"\n✓ Successfully started {len(started_sessions)} session(s):")
            for session_id in started_sessions:
                click.echo(f"  - {session_id}")
            click.echo("\nUse 'amplihack remote output <session-id>' to view progress")
        else:
            click.echo("\n✗ No sessions were started successfully", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@remote_cli.command(name="output")
@click.argument("session_id")
@click.option("--lines", default=100, type=int, help="Number of lines to capture (default: 100)")
@click.option("--follow", is_flag=True, help="Poll for updates every 5s (like tail -f)")
def cmd_output(session_id: str, lines: int, follow: bool):
    """View session output via tmux capture.

    Usage: amplihack remote output <session-id> [--lines N] [--follow]

    Options:
        --lines: Number of lines to capture [default: 100]
        --follow: Poll for updates every 5s (like tail -f)

    Examples:
        amplihack remote output sess-20251202-123456-abc
        amplihack remote output sess-20251202-123456-abc --lines 200
        amplihack remote output sess-20251202-123456-abc --follow
    """
    try:
        # Initialize session manager
        session_mgr = SessionManager()

        # Get session
        session = session_mgr.get_session(session_id)
        if not session:
            click.echo(f"Error: Session '{session_id}' not found.", err=True)
            click.echo("Use 'amplihack remote list' to see available sessions.", err=True)
            sys.exit(3)

        # Capture output
        def capture_and_display():
            output = session_mgr.capture_output(session_id, lines=lines)

            # Clear screen if following
            if follow:
                click.clear()

            click.echo(f"=== Session: {session_id} ===")
            click.echo(f"Status: {session.status.value}")
            click.echo(f"VM: {session.vm_name}")
            click.echo(f"Prompt: {session.prompt}")
            click.echo("=" * 80)
            click.echo(output)

            if follow:
                click.echo("\n[Following output... Press Ctrl+C to stop]")

        # Initial capture
        capture_and_display()

        # Follow mode
        if follow:
            try:
                while True:
                    time.sleep(5)
                    capture_and_display()
            except KeyboardInterrupt:
                click.echo("\n\nStopped following output.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@remote_cli.command(name="kill")
@click.argument("session_id")
@click.option("--force", is_flag=True, help="Force kill even if session is in unknown state")
def cmd_kill(session_id: str, force: bool):
    """Terminate a running session.

    Usage: amplihack remote kill <session-id> [--force]

    Examples:
        amplihack remote kill sess-20251202-123456-abc
        amplihack remote kill sess-20251202-123456-abc --force
    """
    try:
        # Initialize managers
        session_mgr = SessionManager()
        vm_pool_mgr = VMPoolManager()

        # Get session
        session = session_mgr.get_session(session_id)
        if not session:
            click.echo(f"Error: Session '{session_id}' not found.", err=True)
            click.echo("Use 'amplihack remote list' to see available sessions.", err=True)
            sys.exit(3)

        click.echo(f"Killing session: {session_id}")

        # Kill tmux session on VM
        try:
            kill_cmd = f"tmux kill-session -t {session_id}"
            result = subprocess.run(
                ["azlin", "connect", session.vm_name, kill_cmd],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )

            if result.returncode == 0:
                click.echo(f"  ✓ Tmux session terminated on {session.vm_name}")
            else:
                if force:
                    click.echo(
                        "  ! Warning: Could not kill tmux session (force=True, continuing...)"
                    )
                else:
                    click.echo(f"  ✗ Failed to kill tmux session: {result.stderr}", err=True)
                    sys.exit(1)

        except subprocess.TimeoutExpired:
            click.echo("  ! Warning: Kill command timed out")
        except Exception as e:
            if not force:
                click.echo(f"  ✗ Error killing tmux session: {e}", err=True)
                sys.exit(1)

        # Update session state
        session_mgr.kill_session(session_id, force=force)
        click.echo("  ✓ Session marked as KILLED")

        # Release VM capacity
        vm_pool_mgr.release_session(session_id)
        click.echo("  ✓ VM capacity released")

        click.echo(f"\n✓ Session '{session_id}' has been terminated.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@remote_cli.command(name="status")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def cmd_status(output_json: bool):
    """Show pool status (VMs + sessions).

    Usage: amplihack remote status [--json]

    Examples:
        amplihack remote status
        amplihack remote status --json
    """
    try:
        # Initialize managers
        vm_pool_mgr = VMPoolManager()
        session_mgr = SessionManager()

        # Get pool status
        pool_status = vm_pool_mgr.get_pool_status()

        # Get session counts
        all_sessions = session_mgr.list_sessions()
        session_counts = {
            "running": len([s for s in all_sessions if s.status == SessionStatus.RUNNING]),
            "completed": len([s for s in all_sessions if s.status == SessionStatus.COMPLETED]),
            "failed": len([s for s in all_sessions if s.status == SessionStatus.FAILED]),
            "killed": len([s for s in all_sessions if s.status == SessionStatus.KILLED]),
            "pending": len([s for s in all_sessions if s.status == SessionStatus.PENDING]),
        }

        if output_json:
            # JSON output
            output = {
                "pool": pool_status,
                "sessions": session_counts,
                "total_sessions": len(all_sessions),
            }
            click.echo(json.dumps(output, indent=2))
            return

        # Human-readable output
        click.echo("\n=== Remote Session Pool Status ===\n")

        # VM Pool
        click.echo(f"VMs: {pool_status['total_vms']} total")
        if pool_status["total_vms"] > 0:
            for vm_info in pool_status["vms"]:
                capacity_pct = (
                    (vm_info["active_sessions"] / vm_info["capacity"] * 100)
                    if vm_info["capacity"] > 0
                    else 0
                )
                click.echo(f"  {vm_info['name']} ({vm_info['size']}, {vm_info['region']})")
                click.echo(
                    f"    Sessions: {vm_info['active_sessions']}/{vm_info['capacity']} "
                    f"({capacity_pct:.0f}% capacity)"
                )

                # Show sessions on this VM
                vm_sessions = [s for s in all_sessions if s.vm_name == vm_info["name"]]
                for session in vm_sessions:
                    click.echo(f"      - {session.session_id} ({session.status.value})")
        else:
            click.echo("  (No VMs in pool)")

        # Session Summary
        click.echo(f"\nSessions: {len(all_sessions)} total")
        if len(all_sessions) > 0:
            click.echo(f"  Running: {session_counts['running']}")
            click.echo(f"  Completed: {session_counts['completed']}")
            click.echo(f"  Failed: {session_counts['failed']}")
            click.echo(f"  Killed: {session_counts['killed']}")
            click.echo(f"  Pending: {session_counts['pending']}")
        else:
            click.echo("  (No sessions)")

        click.echo()

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def main():
    """Entry point for CLI."""
    remote_cli()


if __name__ == "__main__":
    main()
