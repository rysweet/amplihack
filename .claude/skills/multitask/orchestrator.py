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
        """Create clean temporary directory for workstreams."""
        if self.tmp_base.exists():
            import shutil

            shutil.rmtree(self.tmp_base)
        self.tmp_base.mkdir(parents=True)

    def add(
        self,
        issue: int,
        branch: str,
        description: str,
        task: str,
        recipe: str = "default-workflow",
    ) -> Workstream:
        """Add a workstream. Clones the branch and prepares execution files."""
        ws = Workstream(
            issue=issue,
            branch=branch,
            description=description,
            task=task,
            recipe=recipe,
        )
        ws.work_dir = self.tmp_base / f"ws-{issue}"
        ws.log_file = self.tmp_base / f"log-{issue}.txt"

        print(f"[{issue}] Cloning {branch}...")
        subprocess.run(
            [
                "git",
                "clone",
                "--depth=1",
                f"--branch={branch}",
                self.repo_url,
                str(ws.work_dir),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )

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
        # Escape task text for safe embedding in Python string
        safe_task = ws.task.replace("\\", "\\\\").replace("'", "\\'")
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
                    "task_description": '{safe_task}',
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

        lines.extend(
            [
                "",
                "-" * 70,
                f"Total: {len(self.workstreams)} | Succeeded: {succeeded} | Failed: {failed}",
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
    args = parser.parse_args()

    run(args.config, mode=args.mode, recipe=args.recipe)
