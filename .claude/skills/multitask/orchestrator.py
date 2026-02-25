#!/usr/bin/env python3
"""Parallel Workstream Orchestrator with Recipe Runner support.

Executes multiple independent development tasks in parallel using subprocess
isolation. Each workstream runs in a clean /tmp clone with its own execution
context.

Two execution modes:
  - recipe (default): Uses Recipe Runner for code-enforced step ordering
  - classic: Uses single Claude session with prompt-based workflow

Usage:
    python orchestrator.py workstreams.json
    python orchestrator.py workstreams.json --mode classic
    python orchestrator.py workstreams.json --recipe investigation-workflow
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Workstream:
    """A parallel workstream executing in a subprocess."""

    issue: int
    branch: str
    description: str
    task: str
    recipe: str = "default-workflow"
    work_dir: Path = field(default_factory=Path)
    log_file: Path = field(default_factory=Path)
    pid: int | None = None
    start_time: float | None = None
    end_time: float | None = None
    exit_code: int | None = None

    @property
    def is_running(self) -> bool:
        if self.pid is None:
            return False
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    @property
    def runtime_seconds(self) -> float | None:
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return end - self.start_time


class ParallelOrchestrator:
    """Orchestrates parallel workstream execution with Recipe Runner support."""

    def __init__(
        self,
        repo_url: str,
        tmp_base: str = "/tmp/amplihack-workstreams",
        mode: str = "recipe",
    ):
        self.repo_url = repo_url
        self.tmp_base = Path(tmp_base)
        self.mode = mode
        self.workstreams: list[Workstream] = []
        self._processes: dict[int, subprocess.Popen] = {}

    def setup(self) -> None:
        """Create clean temporary directory for workstreams and check disk space."""
        if self.tmp_base.exists():
            shutil.rmtree(self.tmp_base)
        self.tmp_base.mkdir(parents=True)

        # Check disk space and warn if low
        self._check_disk_space()

    def add(
        self,
        issue: int | str,
        branch: str,
        description: str,
        task: str,
        recipe: str = "default-workflow",
    ) -> Workstream:
        """Add a workstream. Clones from main and prepares execution files.

        If issue is "TBD", auto-creates a GitHub issue using gh CLI.
        """
        # Auto-create issue if TBD
        if str(issue).upper() == "TBD":
            print(f"[TBD] Creating GitHub issue for: {description}...")
            result = subprocess.run(
                ["gh", "issue", "create", "--title", description, "--body", task],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                # Extract issue number from URL like https://github.com/.../issues/123
                url = result.stdout.strip()
                issue = int(url.rstrip("/").split("/")[-1])
                print(f"[{issue}] Created issue: {url}")
            else:
                # Fallback: use timestamp-based ID
                issue = int(time.time()) % 100000
                print(f"[{issue}] Could not create issue, using fallback ID")

        ws = Workstream(
            issue=issue,
            branch=branch,
            description=description,
            task=task,
            recipe=recipe,
        )
        ws.work_dir = self.tmp_base / f"ws-{issue}"
        ws.log_file = self.tmp_base / f"log-{issue}.txt"

        # Clean up stale work dir from previous runs
        if ws.work_dir.exists():
            import shutil

            shutil.rmtree(ws.work_dir)

        print(f"[{issue}] Cloning from main (workflow will create {branch})...")
        subprocess.run(
            [
                "git",
                "clone",
                "--depth=1",
                "--branch=main",
                self.repo_url,
                str(ws.work_dir),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
        # Note: The workflow Step 4 will create the feature branch

        # Write execution files based on mode
        if self.mode == "recipe":
            self._write_recipe_launcher(ws)
        else:
            self._write_classic_launcher(ws)

        self.workstreams.append(ws)
        return ws

    def _write_recipe_launcher(self, ws: Workstream) -> None:
        """Write launcher files for recipe-based execution.

        Creates a Python script that uses run_recipe_by_name() with
        CLISubprocessAdapter, and a shell wrapper that unsets CLAUDECODE.
        """
        # Python launcher that uses Recipe Runner directly
        launcher_py = ws.work_dir / "launcher.py"
        # Use json.dumps for proper escaping of all special characters
        import json

        safe_task = json.dumps(ws.task)
        launcher_py.write_text(
            textwrap.dedent(f"""\
            #!/usr/bin/env python3
            \"\"\"Workstream launcher - recipe runner execution.\"\"\"
            import sys
            import logging

            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            )

            try:
                from amplihack.recipes import run_recipe_by_name
                from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter
            except ImportError:
                print("ERROR: amplihack package not importable. Falling back to classic mode.")
                sys.exit(2)

            adapter = CLISubprocessAdapter(cli="claude", working_dir=".")
            result = run_recipe_by_name(
                "{ws.recipe}",
                adapter=adapter,
                user_context={{
                    "task_description": {safe_task},
                    "repo_path": ".",
                }},
            )

            print()
            print("=" * 60)
            print("RECIPE EXECUTION RESULTS")
            print("=" * 60)
            for sr in result.step_results:
                print(f"  [{{sr.status.value:>9}}] {{sr.step_id}}")
            print(f"\\nOverall: {{'SUCCESS' if result.success else 'FAILED'}}")
            sys.exit(0 if result.success else 1)
            """)
        )
        launcher_py.chmod(0o755)

        # Shell wrapper that handles CLAUDECODE env var
        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text(
            textwrap.dedent(f"""\
            #!/bin/bash
            cd "{ws.work_dir}"
            unset CLAUDECODE  # Allow nested Claude sessions
            exec python3 launcher.py
            """)
        )
        run_sh.chmod(0o755)

    def _write_classic_launcher(self, ws: Workstream) -> None:
        """Write launcher for classic single-session execution."""
        # Task file
        task_md = ws.work_dir / "TASK.md"
        task_md.write_text(
            f"# Issue #{ws.issue}\n\n{ws.task}\n\n"
            f"Follow DEFAULT_WORKFLOW.md autonomously. "
            f"NO QUESTIONS. Work through Steps 0-22. Create PR when complete."
        )

        # Shell launcher
        run_sh = ws.work_dir / "run.sh"
        run_sh.write_text(
            textwrap.dedent(f"""\
            #!/bin/bash
            cd "{ws.work_dir}"
            unset CLAUDECODE
            amplihack claude -- -p "@TASK.md

            Execute task autonomously following DEFAULT_WORKFLOW.md.
            NO QUESTIONS. Work through all steps. Create PR when complete."
            """)
        )
        run_sh.chmod(0o755)

    def launch(self, ws: Workstream) -> None:
        """Launch a single workstream subprocess."""
        log_handle = ws.log_file.open("w")
        proc = subprocess.Popen(
            [str(ws.work_dir / "run.sh")],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=ws.work_dir,
        )
        ws.pid = proc.pid
        ws.start_time = time.time()
        self._processes[ws.issue] = proc
        print(f"[{ws.issue}] Launched PID {ws.pid} ({self.mode} mode)")

    def launch_all(self) -> None:
        """Launch all workstreams in parallel."""
        for ws in self.workstreams:
            self.launch(ws)
        print(f"\n{len(self.workstreams)} workstreams launched in parallel ({self.mode} mode)")

    def get_status(self) -> dict[str, list[int]]:
        """Get current status of all workstreams."""
        status: dict[str, list[int]] = {"running": [], "completed": [], "failed": []}

        for ws in self.workstreams:
            proc = self._processes.get(ws.issue)
            if proc and proc.poll() is None:
                status["running"].append(ws.issue)
            elif proc:
                ws.exit_code = proc.returncode
                if ws.end_time is None:
                    ws.end_time = time.time()
                if ws.exit_code == 0:
                    status["completed"].append(ws.issue)
                else:
                    status["failed"].append(ws.issue)
            else:
                status["failed"].append(ws.issue)

        return status

    def monitor(self, check_interval: int = 60, max_runtime: int = 7200) -> None:
        """Monitor all workstreams until complete or timeout."""
        start = time.time()

        while time.time() - start < max_runtime:
            status = self.get_status()

            now = datetime.now().strftime("%H:%M:%S")
            elapsed = int(time.time() - start)
            print(f"\n[{now}] Status (elapsed: {elapsed}s):")
            print(f"  Running:   {len(status['running'])} {status['running']}")
            print(f"  Completed: {len(status['completed'])} {status['completed']}")
            print(f"  Failed:    {len(status['failed'])} {status['failed']}")

            if not status["running"]:
                break

            time.sleep(check_interval)

        # Mark any still-running as timed out
        for ws in self.workstreams:
            proc = self._processes.get(ws.issue)
            if proc and proc.poll() is None:
                print(f"[{ws.issue}] Timed out after {max_runtime}s, terminating...")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                ws.exit_code = -1
                ws.end_time = time.time()

    def report(self) -> str:
        """Generate final report."""
        lines = [
            "",
            "=" * 70,
            "PARALLEL WORKSTREAM REPORT",
            f"Mode: {self.mode}",
            "=" * 70,
        ]

        succeeded = 0
        failed = 0

        for ws in self.workstreams:
            runtime = f"{ws.runtime_seconds:.0f}s" if ws.runtime_seconds else "N/A"
            status = "OK" if ws.exit_code == 0 else f"FAILED (exit {ws.exit_code})"
            if ws.exit_code == 0:
                succeeded += 1
            else:
                failed += 1

            lines.extend(
                [
                    f"\n[{ws.issue}] {ws.description}",
                    f"  Branch:  {ws.branch}",
                    f"  Status:  {status}",
                    f"  Runtime: {runtime}",
                    f"  Log:     {ws.log_file}",
                ]
            )

        # Calculate disk usage
        disk_usage_gb, ws_count = self._calculate_disk_usage()

        lines.extend(
            [
                "",
                "-" * 70,
                f"Total: {len(self.workstreams)} | Succeeded: {succeeded} | Failed: {failed}",
                "",
                "DISK USAGE:",
                f"  Workstream directories: {ws_count}",
                f"  Total disk used: {disk_usage_gb:.2f}GB",
                f"  Location: {self.tmp_base}",
                "",
                "CLEANUP:",
                "  After merging PRs, run:",
                f"    python {__file__} --cleanup <config.json>",
                "=" * 70,
            ]
        )

        report_text = "\n".join(lines)
        print(report_text)

        # Write report to file
        report_file = self.tmp_base / "REPORT.md"
        report_file.write_text(report_text)
        print(f"\nReport saved to: {report_file}")

        return report_text

    def _check_disk_space(self, min_free_gb: float = 10.0) -> None:
        """Check available disk space and warn if low."""
        usage = shutil.disk_usage(self.tmp_base)
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        used_percent = (usage.used / usage.total) * 100

        print("\nDisk Space Check:")
        print(f"  Location: {self.tmp_base}")
        print(f"  Free: {free_gb:.1f}GB / {total_gb:.1f}GB ({100 - used_percent:.1f}% available)")

        if free_gb < min_free_gb:
            print(f"\n⚠️  WARNING: Only {free_gb:.1f}GB free (threshold: {min_free_gb}GB)")
            print("Each workstream requires ~1.5GB. Consider cleaning up old workstreams:")
            print(f"  rm -rf {self.tmp_base}/ws-*")
            print()
            try:
                response = input("Continue anyway? (y/N): ").strip().lower()
                if response != "y":
                    print("Aborted by user.")
                    sys.exit(0)
            except (EOFError, KeyboardInterrupt):
                print("\nAborted.")
                sys.exit(0)

    def _calculate_disk_usage(self) -> tuple[float, int]:
        """Calculate total disk usage of all workstream directories.

        Returns:
            (total_size_gb, workstream_count)
        """
        total_bytes = 0
        ws_count = 0

        if not self.tmp_base.exists():
            return (0.0, 0)

        for item in self.tmp_base.iterdir():
            if item.is_dir() and item.name.startswith("ws-"):
                ws_count += 1
                for dirpath, _dirnames, filenames in os.walk(item):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_bytes += os.path.getsize(filepath)
                        except OSError:
                            pass  # File disappeared or inaccessible

        total_gb = total_bytes / (1024**3)
        return (total_gb, ws_count)

    def cleanup_running(self) -> None:
        """Terminate all running workstreams."""
        for ws in self.workstreams:
            proc = self._processes.get(ws.issue)
            if proc and proc.poll() is None:
                print(f"[{ws.issue}] Terminating PID {ws.pid}...")
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

    def cleanup_merged(self, config_path: str, dry_run: bool = False) -> None:
        """Clean up workstreams whose PRs have been merged.

        Args:
            config_path: Path to original workstreams config file
            dry_run: If True, only show what would be deleted without deleting
        """
        config = json.loads(Path(config_path).read_text())
        deleted_count = 0
        freed_gb = 0.0

        print("\nChecking PR status for workstream cleanup...")

        for item in config:
            issue = item["issue"]
            if str(issue).upper() == "TBD":
                continue

            # Check PR status using gh CLI
            try:
                result = subprocess.run(
                    ["gh", "pr", "list", "--search", f"#{issue}", "--json", "number,state,merged"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    prs = json.loads(result.stdout)
                    pr_merged = any(pr.get("merged") or pr.get("state") == "MERGED" for pr in prs)

                    if pr_merged:
                        ws_dir = self.tmp_base / f"ws-{issue}"
                        if ws_dir.exists():
                            # Calculate size before deleting
                            dir_size = 0
                            for dirpath, _dirs, files in os.walk(ws_dir):
                                for f in files:
                                    fp = os.path.join(dirpath, f)
                                    try:
                                        dir_size += os.path.getsize(fp)
                                    except OSError:
                                        pass
                            size_gb = dir_size / (1024**3)

                            if dry_run:
                                print(f"  [DRY RUN] Would delete ws-{issue} ({size_gb:.2f}GB)")
                            else:
                                shutil.rmtree(ws_dir)
                                print(f"  ✓ Deleted ws-{issue} (PR merged, freed {size_gb:.2f}GB)")
                                deleted_count += 1
                                freed_gb += size_gb
                    else:
                        print(f"  [SKIP] ws-{issue} (PR not merged yet)")
                else:
                    print(f"  [ERROR] Could not check PR status for #{issue}")
            except Exception as e:
                print(f"  [ERROR] Failed to process #{issue}: {e}")

        print(f"\n{'DRY RUN ' if dry_run else ''}Summary:")
        print(f"  Workstreams {'would be ' if dry_run else ''}deleted: {deleted_count}")
        print(f"  Disk space {'would be ' if dry_run else ''}freed: {freed_gb:.2f}GB")

        if dry_run and deleted_count > 0:
            print("\nRun without --dry-run to actually delete these workstreams.")


def run(config_path: str, mode: str = "recipe", recipe: str = "default-workflow") -> str:
    """Main entry point for the orchestrator.

    Args:
        config_path: Path to JSON config file with workstream definitions.
        mode: Execution mode - "recipe" (default) or "classic".
        recipe: Recipe name for recipe mode (default: "default-workflow").

    Returns:
        Report text.
    """
    config = json.loads(Path(config_path).read_text())

    # Detect repo URL from git remote
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    repo_url = result.stdout.strip() if result.returncode == 0 else ""
    if not repo_url:
        print("ERROR: Could not determine repo URL from git remote.")
        sys.exit(1)

    orchestrator = ParallelOrchestrator(repo_url=repo_url, mode=mode)
    orchestrator.setup()

    for item in config:
        orchestrator.add(
            issue=item["issue"],
            branch=item["branch"],
            description=item.get("description", f"Issue #{item['issue']}"),
            task=item["task"],
            recipe=item.get("recipe", recipe),
        )

    # Handle SIGINT gracefully
    def signal_handler(sig, frame):
        print("\nInterrupted! Cleaning up workstreams...")
        orchestrator.cleanup_running()
        sys.exit(130)

    signal.signal(signal.SIGINT, signal_handler)

    orchestrator.launch_all()
    orchestrator.monitor()
    return orchestrator.report()


def cleanup(config_path: str, dry_run: bool = False) -> None:
    """Clean up workstreams with merged PRs.

    Args:
        config_path: Path to JSON config file with workstream definitions
        dry_run: If True, show what would be deleted without deleting
    """
    # Detect repo URL
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    repo_url = result.stdout.strip() if result.returncode == 0 else ""

    orchestrator = ParallelOrchestrator(repo_url=repo_url)
    orchestrator.cleanup_merged(config_path, dry_run=dry_run)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parallel Workstream Orchestrator")
    parser.add_argument("config", help="Path to workstreams JSON config file")
    parser.add_argument(
        "--mode",
        choices=["recipe", "classic"],
        default="recipe",
        help="Execution mode (default: recipe)",
    )
    parser.add_argument(
        "--recipe",
        default="default-workflow",
        help="Recipe name for recipe mode (default: default-workflow)",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up workstreams with merged PRs instead of running tasks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting (use with --cleanup)",
    )
    args = parser.parse_args()

    if args.cleanup:
        cleanup(args.config, dry_run=args.dry_run)
    else:
        if args.dry_run:
            print("WARNING: --dry-run only works with --cleanup, ignoring")
        run(args.config, mode=args.mode, recipe=args.recipe)
