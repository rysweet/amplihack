"""Background worker mixin and project/session management for FleetDashboardApp.

Contains @work(thread=True) methods that perform I/O in background threads,
plus the UI-side project management and new-session creation methods that
are closely coupled to those workers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from textual import work
from textual.widgets import DataTable, Input, Select
from textual.worker import get_current_worker

from amplihack.fleet._validation import (
    validate_session_name,
    validate_vm_name,
)
from amplihack.fleet.fleet_session_reasoner import (
    AnthropicBackend,
    SessionDecision,
    SessionReasoner,
)

logger = logging.getLogger(__name__)


class _WorkersMixin:
    """Background workers, project management, and session creation."""

    # ------------------------------------------------------------------
    # Background workers
    # ------------------------------------------------------------------

    @work(thread=True)
    def _adopt_session_bg(self, vm_name: str, session_name: str) -> None:
        """Run SessionAdopter in a background thread."""
        worker = get_current_worker()
        try:
            from amplihack.fleet.fleet_adopt import SessionAdopter
            from amplihack.fleet.fleet_tasks import TaskQueue

            queue_path = Path.home() / ".amplihack" / "fleet" / "task_queue.json"
            adopter = SessionAdopter(azlin_path=self._fleet.azlin_path)
            queue = TaskQueue(persist_path=queue_path)
            adopted = adopter.adopt_sessions(vm_name, queue, sessions=[session_name])
            msg = f"Adopted {len(adopted)} session(s) on {vm_name}"
            severity = "information"
        except Exception as exc:
            msg = f"Adopt failed: {exc}"
            severity = "error"
        if worker.is_cancelled:
            return
        self.call_from_thread(self.notify, msg, severity=severity)
        self.call_from_thread(self._schedule_refresh)

    @work(thread=True)
    def _fetch_tmux_capture(self, vm_name: str, session_name: str) -> None:
        """Fetch full tmux capture from a session in background."""
        import shlex
        import subprocess

        validate_vm_name(vm_name)
        validate_session_name(session_name)
        worker = get_current_worker()
        key = f"{vm_name}/{session_name}"

        cmd = f"tmux capture-pane -t {shlex.quote(session_name)} -p -S -60"
        capture_text = ""
        try:
            result = subprocess.run(
                [self._fleet.azlin_path, "connect", vm_name, "--no-tmux", "--", cmd],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                capture_text = result.stdout
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            capture_text = "(failed to capture tmux output)"
        if worker.is_cancelled:
            return
        entry = self._cache.get(key)
        if entry:
            entry.tmux_capture = capture_text
        self.call_from_thread(self._show_tmux_capture, capture_text)

    @work(thread=True)
    def _run_reasoning(self, vm_name: str, session_name: str) -> None:
        """Call SessionReasoner in a background thread."""
        worker = get_current_worker()
        key = f"{vm_name}/{session_name}"
        try:
            reasoner = SessionReasoner(
                azlin_path=self._fleet.azlin_path, backend=AnthropicBackend(), dry_run=True,
            )
            decision = reasoner.reason_about_session(vm_name=vm_name, session_name=session_name)
        except Exception as exc:
            decision = SessionDecision(
                session_name=session_name, vm_name=vm_name,
                action="escalate", reasoning=f"Reasoning failed: {exc}", confidence=0.0,
            )
        if worker.is_cancelled:
            return
        entry = self._cache.get(key)
        if entry:
            entry.proposal = decision
        self.call_from_thread(self._show_proposal, decision)

    @work(thread=True)
    def _create_session_bg(self, vm_name: str, agent_type: str) -> None:
        """Create a new tmux session on a VM in background."""
        import shlex
        import subprocess

        validate_vm_name(vm_name)
        worker = get_current_worker()
        agent_commands = {
            "claude": "amplihack claude",
            "copilot": "amplihack copilot",
            "amplifier": "amplihack amplifier",
        }
        launch_cmd = agent_commands.get(agent_type)
        if launch_cmd is None:
            self.call_from_thread(
                self.notify,
                f"Unknown agent type: {agent_type!r}. Must be one of: {', '.join(agent_commands)}",
                severity="error",
            )
            return
        session_name = f"{agent_type}-{int(__import__('time').time()) % 10000}"
        remote_cmd = f"tmux new-session -d -s {shlex.quote(session_name)} {shlex.quote(launch_cmd)}"
        try:
            result = subprocess.run(
                [self._fleet.azlin_path, "connect", vm_name, "--no-tmux", "--", remote_cmd],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                msg = f"Created session '{session_name}' on {vm_name} running {agent_type}"
                severity = "information"
            else:
                msg = f"Failed to create session: {result.stderr.strip()}"
                severity = "error"
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            msg = f"Failed to create session: {exc}"
            severity = "error"
        if worker.is_cancelled:
            return
        self.call_from_thread(self.notify, msg, severity=severity)
        self.call_from_thread(self._schedule_refresh)

    @work(thread=True)
    def _execute_decision_bg(self, decision: SessionDecision) -> None:
        """Execute a decision via SessionReasoner in background."""
        worker = get_current_worker()
        try:
            reasoner = SessionReasoner(
                azlin_path=self._fleet.azlin_path, backend=AnthropicBackend(), dry_run=False,
            )
            reasoner.execute_decision(decision)
            msg = f"Applied: {decision.action}"
            severity = "information"
        except Exception as exc:
            msg = f"Failed to apply: {exc}"
            severity = "error"
        if worker.is_cancelled:
            return
        self.call_from_thread(self.notify, msg, severity=severity)

    # ------------------------------------------------------------------
    # Project management (UI-thread)
    # ------------------------------------------------------------------

    def _add_project_from_input(self) -> None:
        """Add a project from the repo Input widget."""
        repo_input = self.query_one("#project-repo-input", Input)
        repo_url = repo_input.value.strip()
        if not repo_url:
            self.notify("Enter a repo URL first", severity="warning")
            return
        dash = self._get_dashboard()
        if dash.get_project(repo_url):
            self.notify(f"Project already exists: {repo_url}", severity="warning")
            return
        dash.add_project(repo_url=repo_url)
        repo_input.value = ""
        self._refresh_projects_table()
        self.notify(f"Added project: {repo_url}")

    def _remove_selected_project(self) -> None:
        """Remove the currently selected project from the table."""
        proj_table = self.query_one("#project-table", DataTable)
        if proj_table.cursor_row is None:
            self.notify("Select a project first", severity="warning")
            return
        row_key = proj_table.get_row_at(proj_table.cursor_row)
        if not row_key:
            return
        cursor_key = proj_table.coordinate_to_cell_key(proj_table.cursor_coordinate).row_key
        project_name = str(cursor_key.value) if cursor_key else ""
        if not project_name:
            self.notify("Could not determine project name", severity="warning")
            return
        dash = self._get_dashboard()
        if dash.remove_project(project_name):
            self._refresh_projects_table()
            self.notify(f"Removed project: {project_name}")
        else:
            self.notify(f"Project not found: {project_name}", severity="warning")

    # ------------------------------------------------------------------
    # New session creation (UI-thread)
    # ------------------------------------------------------------------

    def _populate_vm_select(self) -> None:
        """Fill the VM select dropdown with running VMs from cache."""
        all_vms: set[str] = set()
        for key, entry in self._cache.items():
            if entry.view.vm_name and entry.view.status != "empty":
                all_vms.add(entry.view.vm_name)
        for key, entry in self._all_cache.items():
            if entry.view.vm_name:
                all_vms.add(entry.view.vm_name)
        vm_select = self.query_one("#vm-select", Select)
        vm_select.set_options([(name, name) for name in sorted(all_vms)])

    def _create_new_session(self) -> None:
        """Create a new agent session on the selected VM."""
        vm_select = self.query_one("#vm-select", Select)
        agent_select = self.query_one("#agent-select", Select)
        vm_name = str(vm_select.value) if vm_select.value is not Select.BLANK else ""
        agent_type = str(agent_select.value) if agent_select.value is not Select.BLANK else "claude"
        if not vm_name:
            self.notify("Select a VM first", severity="warning")
            return
        self.notify(f"Creating {agent_type} session on {vm_name}...")
        self._create_session_bg(vm_name, agent_type)
