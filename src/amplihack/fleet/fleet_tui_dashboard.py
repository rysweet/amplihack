"""Fleet TUI Dashboard v2 -- interactive Textual-based fleet cockpit.

Navigate VMs and sessions, view live tmux captures, see director proposals,
edit and apply actions.  Auto-refreshes via background workers.

Usage:
    fleet tui2                # Launch interactive dashboard
    fleet tui2 --interval 30  # Custom refresh interval

Public API:
    FleetDashboardApp: The Textual application
    run_dashboard: Entry-point function
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    LoadingIndicator,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)
from textual.worker import get_current_worker

from amplihack.fleet._validation import (
    DANGEROUS_PATTERNS,
    is_dangerous_input,
    validate_session_name,
    validate_vm_name,
)
from amplihack.fleet.fleet_session_reasoner import (
    AnthropicBackend,
    SessionDecision,
    SessionReasoner,
)
from amplihack.fleet.fleet_tui import FleetTUI, SessionView, VMView

__all__ = ["FleetDashboardApp", "run_dashboard"]

# ---------------------------------------------------------------------------
# Pirate ship ASCII logo
# ---------------------------------------------------------------------------
PIRATE_LOGO = """\
[bold white]              _~
             /~   \\
            |  ☠  |
             \\_~_/[/bold white]
[cyan]        |    |    |
       )_)  )_)  )_)
      )___))___))___)\\
     )____)____)_____)\\\\
   _____|____|____|____\\\\\\__
---\\                   /------
    \\_________________/[/cyan]
  [bold green]~~~  A M P L I H A C K   F L E E T  ~~~[/bold green]"""

# ---------------------------------------------------------------------------
# Status icon mapping (Rich-compatible markup)
# ---------------------------------------------------------------------------
STATUS_STYLES: dict[str, tuple[str, str]] = {
    "thinking": ("\u25c9", "green"),
    "working": ("\u25c9", "green"),
    "running": ("\u25c9", "green"),
    "waiting_input": ("\u25c9", "green"),
    "idle": ("\u25cf", "yellow"),
    "shell": ("\u25cb", "dim"),
    "empty": ("\u25cb", "dim"),
    "no_session": ("\u25cb", "dim"),
    "unknown": ("\u25cb", "dim"),
    "error": ("\u2717", "red"),
    "completed": ("\u2713", "dodger_blue1"),
}

ACTION_CHOICES: list[tuple[str, str]] = [
    ("send_input", "send_input"),
    ("wait", "wait"),
    ("escalate", "escalate"),
    ("mark_complete", "mark_complete"),
    ("restart", "restart"),
]


@dataclass
class _CachedSession:
    """Internal cache entry for a polled session."""

    view: SessionView
    tmux_capture: str = ""
    proposal: SessionDecision | None = None


# ---------------------------------------------------------------------------
# Textual App
# ---------------------------------------------------------------------------


class FleetDashboardApp(App):
    """Interactive fleet management dashboard built on Textual."""

    TITLE = "Fleet Dashboard"
    SUB_TITLE = "Autonomous Coding Agent Fleet Management"

    CSS = """
Screen {
    layout: vertical;
    background: $surface;
}

/* ---- Pirate Logo ---- */
#pirate-logo {
    height: auto;
    max-height: 10;
    padding: 0 2;
    content-align: center middle;
    text-align: center;
    background: $surface;
}
#pirate-logo.hidden {
    display: none;
}

/* ---- Fleet Overview Tab ---- */
#fleet-tab Horizontal {
    height: 1fr;
}
#session-table {
    width: 62%;
    border: tall $primary-background;
    scrollbar-size: 1 1;
}
#session-table > .datatable--cursor {
    background: $accent 40%;
    color: $text;
}
#preview-pane {
    width: 38%;
    border: tall $accent;
    padding: 0 1;
    background: $panel;
    color: $text-muted;
}
#all-session-table {
    width: 62%;
    border: tall $primary-background;
    scrollbar-size: 1 1;
}
#all-session-table > .datatable--cursor {
    background: $accent 40%;
    color: $text;
}
#all-preview-pane {
    width: 38%;
    border: tall $accent;
    padding: 0 1;
    background: $panel;
    color: $text-muted;
}
#fleet-summary {
    height: 3;
    dock: bottom;
    padding: 0 2;
    background: $primary-background;
    color: $text;
    text-style: bold;
}

/* ---- Session Detail Tab ---- */
#detail-header {
    height: auto;
    max-height: 6;
    padding: 1 2;
    background: $primary-background;
    color: $text;
    text-style: bold;
    border-bottom: heavy $accent;
}
#tmux-capture {
    height: 1fr;
    min-height: 10;
    border: tall $primary;
    padding: 0 1;
    background: #1a1a2e;
    color: #eaeaea;
}
#proposal-section {
    height: auto;
    max-height: 16;
    border: tall $warning;
    padding: 1 2;
    background: $panel;
}

/* ---- Action Editor Tab ---- */
#editor-reasoning {
    height: auto;
    max-height: 8;
    padding: 1 2;
    background: $panel;
    border: tall $accent;
    color: $text-muted;
}
#input-editor {
    height: 10;
    border: tall $success;
}
#action-select {
    margin: 1 2;
    width: 40;
}

/* ---- Projects Tab ---- */
#project-add-bar {
    height: auto;
    layout: horizontal;
    padding: 1 1;
    background: $primary-background;
}
#project-repo-input {
    width: 1fr;
    margin: 0 1 0 0;
}
#project-table {
    height: 1fr;
    border: tall $primary-background;
    scrollbar-size: 1 1;
}
#project-table > .datatable--cursor {
    background: $accent 40%;
    color: $text;
}

/* ---- New Session Tab ---- */
#new-session-header {
    padding: 1 2;
    background: $primary-background;
    color: $text;
}
#new-session-form {
    height: auto;
    padding: 1 2;
    align: left middle;
}
#new-session-form Select {
    width: 30;
    margin: 0 1;
}

/* ---- Shared ---- */
Button {
    margin: 0 1;
    min-width: 14;
}
.button-row {
    height: 5;
    layout: horizontal;
    align: center middle;
    padding: 1 0;
}
#loading-overlay {
    display: none;
    dock: top;
    height: 3;
    content-align: center middle;
    background: $warning 30%;
}
.active-loading #loading-overlay {
    display: block;
}

/* ---- Tab styling ---- */
TabbedContent {
    height: 1fr;
}
TabPane {
    padding: 0;
}
"""

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True, priority=True),
        Binding("r", "force_refresh", "Refresh", show=True, priority=True),
        Binding("enter", "open_detail", "Detail", show=True, priority=True),
        Binding("escape", "back_to_fleet", "Back", show=True, priority=True),
        Binding("e", "edit_proposal", "Edit", show=True),
        Binding("A", "adopt_session", "Adopt", show=True),
        Binding("a", "apply_proposal", "Apply", show=True),
        Binding("d", "dry_run_session", "Dry-run", show=True),
        Binding("l", "toggle_logo", "Logo", show=True),
        Binding("n", "new_session", "New Session", show=True),
        # Tab navigation — always works regardless of focus
        Binding("1", "tab_fleet", "Fleet", show=True, priority=True),
        Binding("2", "tab_detail", "Detail", show=True, priority=True),
        Binding("3", "tab_editor", "Editor", show=True, priority=True),
        Binding("4", "tab_projects", "Projects", show=True, priority=True),
    ]

    def __init__(
        self,
        refresh_interval: int = 30,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._refresh_interval = refresh_interval
        self._fleet = FleetTUI()
        self._cache: dict[str, _CachedSession] = {}
        self._all_cache: dict[str, _CachedSession] = {}
        self._managed_vm_names: set[str] = set()
        self._selected_key: str = ""
        self._refreshing = False
        self._refresh_generation: int = 0

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(PIRATE_LOGO, id="pirate-logo", markup=True)
        with TabbedContent(id="tabs"):
            # --- Tab 1: Fleet Overview ---
            with TabPane("Fleet Overview", id="fleet-tab"):
                with TabbedContent(id="fleet-subtabs"):
                    with TabPane("Managed", id="managed-subtab"):
                        with Horizontal():
                            yield DataTable(id="session-table", cursor_type="row")
                            yield RichLog(id="preview-pane", wrap=True, markup=True)
                    with TabPane("All Sessions", id="all-subtab"):
                        with Horizontal():
                            yield DataTable(id="all-session-table", cursor_type="row")
                            yield RichLog(id="all-preview-pane", wrap=True, markup=True)
                yield Static("Loading fleet data...", id="fleet-summary")

            # --- Tab 2: Session Detail ---
            with TabPane("Session Detail", id="detail-tab"):
                yield Static(
                    "Select a session from Fleet Overview and press Enter.", id="detail-header"
                )
                yield RichLog(id="tmux-capture", wrap=True, markup=True)
                with Vertical(id="proposal-section"):
                    yield Static("Proposal will appear here after dry-run.", id="proposal-text")
                    with Horizontal(classes="button-row"):
                        yield Button("Edit", id="btn-edit", variant="default")
                        yield Button("Apply", id="btn-apply", variant="success")
                        yield Button("Skip", id="btn-skip", variant="error")

            # --- Tab 3: Action Editor ---
            with TabPane("Action Editor", id="editor-tab"):
                yield Select(
                    ACTION_CHOICES, id="action-select", prompt="Action type", value="send_input"
                )
                yield TextArea(id="input-editor", language=None)
                yield Static("", id="editor-reasoning")
                with Horizontal(classes="button-row"):
                    yield Button("Apply Edited", id="btn-apply-edited", variant="success")
                    yield Button("Cancel", id="btn-cancel", variant="error")

            # --- Tab 4: Projects ---
            with TabPane("Projects", id="projects-tab"):
                with Horizontal(id="project-add-bar"):
                    yield Input(
                        placeholder="https://github.com/owner/repo",
                        id="project-repo-input",
                    )
                    yield Button("Add", id="btn-add-project", variant="success")
                    yield Button("Remove", id="btn-remove-project", variant="error")
                yield DataTable(id="project-table", cursor_type="row")

            # --- Tab 5: New Session ---
            with TabPane("New Session", id="new-session-tab"):
                yield Static(
                    "[bold]Create a new agent session on a VM[/bold]", id="new-session-header"
                )
                with Horizontal(id="new-session-form"):
                    yield Select([], id="vm-select", prompt="Select VM")
                    yield Select(
                        [
                            ("claude", "claude"),
                            ("copilot", "copilot"),
                            ("amplifier", "amplifier"),
                        ],
                        id="agent-select",
                        prompt="Agent type",
                        value="claude",
                    )
                    yield Button("Create Session", id="btn-create-session", variant="success")

        yield LoadingIndicator(id="loading-overlay")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        # Set up managed data table columns
        table = self.query_one("#session-table", DataTable)
        table.add_columns("St", "VM", "Session", "State", "Branch", "PR")

        # Set up all-sessions data table columns (extra "Mgd" column)
        all_table = self.query_one("#all-session-table", DataTable)
        all_table.add_columns("St", "VM", "Session", "State", "Branch", "PR", "Mgd")

        # Set up project table columns
        proj_table = self.query_one("#project-table", DataTable)
        proj_table.add_columns("Name", "Repo", "Identity", "Priority", "VMs", "Tasks", "PRs")

        # Focus the main session table so arrow keys work immediately
        table.focus()

        # Initial load
        self._schedule_refresh()

        # Periodic refresh
        self.set_interval(self._refresh_interval, self._schedule_refresh)

    # ------------------------------------------------------------------
    # Refresh logic (background worker)
    # ------------------------------------------------------------------

    def _schedule_refresh(self) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        self._refresh_generation += 1
        self.add_class("active-loading")
        self._do_refresh()

    @staticmethod
    def _build_rows_and_cache(
        vms: list[VMView],
        old_cache: dict[str, _CachedSession],
        managed_vm_names: set[str] | None = None,
        include_mgd_column: bool = False,
    ) -> tuple[list[tuple[str, list[str]]], dict[str, _CachedSession]]:
        """Build table rows and cache from VM views.

        Args:
            vms: VM view list from FleetTUI.
            old_cache: Previous cache to preserve proposals.
            managed_vm_names: If provided, used to determine managed status.
            include_mgd_column: If True, append a Mgd column to each row.

        Returns:
            (rows, new_cache) tuple.
        """
        new_cache: dict[str, _CachedSession] = {}
        rows: list[tuple[str, list[str]]] = []

        for vm in vms:
            if not vm.is_running:
                continue

            is_managed = managed_vm_names is None or vm.name in managed_vm_names

            if not vm.sessions:
                key = f"{vm.name}/(no sessions)"
                icon, style = "\u25cb", "dim"
                cell_style = "" if is_managed else "dim"
                cells = [
                    f"[{style}]{icon}[/]",
                    f"[{cell_style}]{vm.name}[/]" if cell_style else vm.name,
                    f"[{cell_style}](none)[/]" if cell_style else "(none)",
                    f"[{cell_style}]stopped[/]" if cell_style else "stopped",
                    "",
                    "",
                ]
                if include_mgd_column:
                    cells.append("[green]\u2713[/]" if is_managed else "[red]\u2717[/]")
                rows.append((key, cells))
                new_cache[key] = _CachedSession(
                    view=SessionView(vm_name=vm.name, session_name="(none)", status="empty"),
                )
                continue

            for sess in vm.sessions:
                key = f"{vm.name}/{sess.session_name}"
                icon, style = STATUS_STYLES.get(sess.status, ("\u25cb", "dim"))
                branch = sess.branch[:24] + "..." if len(sess.branch) > 24 else sess.branch
                pr = sess.pr or ""
                state_label = sess.status.upper()[:8]

                if is_managed:
                    cells = [
                        f"[bold {style}]{icon}[/]",
                        f"[bold]{vm.name}[/]",
                        sess.session_name,
                        f"[{style}]{state_label}[/]",
                        f"[dim]{branch}[/]",
                        f"[bold cyan]{pr}[/]" if pr else "",
                    ]
                else:
                    # Dim all cells for unmanaged
                    cells = [
                        f"[dim]{icon}[/]",
                        f"[dim]{vm.name}[/]",
                        f"[dim]{sess.session_name}[/]",
                        f"[dim]{state_label}[/]",
                        f"[dim]{branch}[/]",
                        f"[dim]{pr}[/]" if pr else "",
                    ]

                if include_mgd_column:
                    cells.append("[green]\u2713[/]" if is_managed else "[red]\u2717[/]")

                rows.append((key, cells))
                old = old_cache.get(key)
                entry = _CachedSession(view=sess)
                if old and old.proposal:
                    entry.proposal = old.proposal
                new_cache[key] = entry

        return rows, new_cache

    @work(thread=True)
    def _do_refresh(self) -> None:
        """Poll all VMs via azlin in a background thread.

        Two-phase refresh for fast UX:
        1. Quick phase (~6s): Get VM list only (no session polling)
           → Update table immediately so user sees VMs
        2. Slow phase (30-60s per VM): Poll tmux sessions via Bastion
           → Update table again with session details

        Uses a generation counter to discard stale results when a new
        refresh is triggered while this one is still running.
        """
        worker = get_current_worker()
        my_generation = self._refresh_generation

        # PHASE 1: Quick VM list (no sessions) — show something fast
        try:
            vm_list = self._fleet._get_vm_list()
        except Exception as exc:
            logger.error("Phase 1 VM list fetch failed: %s", exc)
            self.call_from_thread(
                self.notify,
                f"VM list fetch failed: {exc}",
                severity="error",
            )
            vm_list = []

        if worker.is_cancelled:
            return

        # Build quick view with VMs but no sessions
        quick_managed: list[VMView] = []
        quick_all: list[VMView] = []
        for name, region, is_running in vm_list:
            vm = VMView(name=name, region=region, is_running=is_running)
            quick_all.append(vm)
            if name not in self._fleet.exclude_vms:
                quick_managed.append(vm)

        managed_vm_names = {vm.name for vm in quick_managed}
        managed_rows, new_cache = self._build_rows_and_cache(quick_managed, self._cache)
        all_rows, all_cache = self._build_rows_and_cache(
            quick_all,
            self._cache,
            include_mgd_column=True,
            managed_vm_names=managed_vm_names,
        )
        new_cache.update(all_cache)

        # Show VMs immediately (no sessions yet)
        self.call_from_thread(
            self._apply_refresh,
            quick_managed,
            managed_rows,
            new_cache,
            all_rows,
            all_cache,
            managed_vm_names,
        )

        if worker.is_cancelled:
            return

        # PHASE 2: Progressive session polling — update table per-VM
        all_vms: list[VMView] = []
        try:
            for vm in self._fleet.refresh_iter(exclude=False):
                if worker.is_cancelled or my_generation != self._refresh_generation:
                    return
                all_vms.append(vm)

                # Rebuild tables with what we have so far
                managed_vm_names = {
                    v.name for v in all_vms if v.name not in self._fleet.exclude_vms
                }
                managed_vms = [v for v in all_vms if v.name not in self._fleet.exclude_vms]
                managed_rows, new_cache = self._build_rows_and_cache(managed_vms, self._cache)
                all_rows, all_cache = self._build_rows_and_cache(
                    all_vms,
                    self._all_cache,
                    managed_vm_names=managed_vm_names,
                    include_mgd_column=True,
                )

                # Push incremental update to UI
                self.call_from_thread(
                    self._apply_refresh,
                    managed_vms,
                    managed_rows,
                    new_cache,
                    all_rows,
                    all_cache,
                    managed_vm_names,
                )
        except Exception as exc:
            logger.warning("Fleet refresh failed: %s", exc)
            self.call_from_thread(
                self.notify,
                f"Fleet refresh failed: {exc}",
                severity="warning",
            )
        finally:
            # Mark refresh complete so next schedule can proceed
            self.call_from_thread(self._finish_refresh)

    def _finish_refresh(self) -> None:
        """Mark refresh cycle complete (called on main thread after Phase 2)."""
        self._refreshing = False
        self.remove_class("active-loading")

    def _apply_refresh(
        self,
        vms: list[VMView],
        rows: list[tuple[str, list[str]]],
        new_cache: dict[str, _CachedSession],
        all_rows: list[tuple[str, list[str]]],
        all_cache: dict[str, _CachedSession],
        managed_vm_names: set[str],
    ) -> None:
        """Update UI with refreshed data (called on the main thread)."""
        self._cache = new_cache
        self._all_cache = all_cache
        self._managed_vm_names = managed_vm_names

        # Rebuild managed data table
        table = self.query_one("#session-table", DataTable)
        table.clear()
        for key, cells in rows:
            table.add_row(*cells, key=key)

        # Rebuild all-sessions data table
        all_table = self.query_one("#all-session-table", DataTable)
        all_table.clear()
        for key, cells in all_rows:
            all_table.add_row(*cells, key=key)

        # Rebuild projects table
        self._refresh_projects_table()

        # Summary bar
        total_sessions = sum(1 for v in vms for _ in v.sessions if v.is_running)
        active = sum(
            1
            for v in vms
            for s in v.sessions
            if v.is_running and s.status in ("thinking", "working", "running", "waiting_input")
        )
        idle = sum(1 for v in vms for s in v.sessions if v.is_running and s.status == "idle")
        errors = sum(1 for v in vms for s in v.sessions if v.is_running and s.status == "error")
        now = datetime.now().strftime("%H:%M:%S")
        summary = (
            f"  {len(vms)} VMs | {total_sessions} sessions | "
            f"[green]{active} active[/] | [yellow]{idle} idle[/] | "
            f"[red]{errors} error[/] | "
            f"Updated {now} | Refresh every {self._refresh_interval}s"
        )
        self.query_one("#fleet-summary", Static).update(summary)

    @staticmethod
    def _get_dashboard():
        """Create a FleetDashboard instance with the standard persist path."""
        from amplihack.fleet.fleet_dashboard import FleetDashboard

        dash_path = Path.home() / ".amplihack" / "fleet" / "dashboard.json"
        return FleetDashboard(persist_path=dash_path)

    def _refresh_projects_table(self) -> None:
        """Populate the projects tab DataTable from FleetDashboard."""
        dash = self._get_dashboard()

        proj_table = self.query_one("#project-table", DataTable)
        proj_table.clear()

        for proj in dash.projects:
            prio_colors = {"high": "red", "medium": "yellow", "low": "dim"}
            prio_style = prio_colors.get(proj.priority, "dim")
            proj_table.add_row(
                f"[bold]{proj.name}[/]",
                proj.repo_url[:40] + ("..." if len(proj.repo_url) > 40 else ""),
                proj.github_identity or "[dim]--[/]",
                f"[{prio_style}]{proj.priority}[/]",
                str(len(proj.vms)),
                f"{proj.tasks_completed}/{proj.tasks_total}",
                str(len(proj.prs_created)),
                key=proj.name,
            )

    # ------------------------------------------------------------------
    # DataTable events
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """When the cursor moves in a fleet table, update the appropriate preview pane."""
        if event.row_key is None:
            return
        key = str(event.row_key.value)

        # Determine which table/preview to use
        table_id = event.data_table.id
        if table_id == "all-session-table":
            entry = self._all_cache.get(key)
            preview = self.query_one("#all-preview-pane", RichLog)
        else:
            entry = self._cache.get(key)
            preview = self.query_one("#preview-pane", RichLog)

        self._selected_key = key

        if entry is None:
            return

        preview.clear()
        preview.write(f"[bold]{key}[/bold]")
        preview.write(f"Status: {entry.view.status}")
        if entry.view.branch:
            preview.write(f"Branch: {entry.view.branch}")
        if entry.view.pr:
            preview.write(f"PR: {entry.view.pr}")
        if entry.view.last_line:
            preview.write("\n[dim]Last output:[/dim]")
            preview.write(entry.view.last_line)
        if entry.tmux_capture:
            preview.write("\n[dim]--- tmux capture ---[/dim]")
            for line in entry.tmux_capture.split("\n")[-15:]:
                preview.write(line)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_force_refresh(self) -> None:
        self._schedule_refresh()
        self.notify("Refreshing fleet data...")

    def action_toggle_logo(self) -> None:
        """Toggle visibility of the pirate ship logo."""
        logo = self.query_one("#pirate-logo", Static)
        logo.toggle_class("hidden")

    def action_adopt_session(self) -> None:
        """Adopt the highlighted unmanaged session into fleet management."""
        if not self._selected_key:
            self.notify("No session selected", severity="warning")
            return

        # Check if session is already managed
        entry = self._all_cache.get(self._selected_key)
        if entry is None:
            entry = self._cache.get(self._selected_key)
        if entry is None:
            self.notify("Session not found in cache", severity="warning")
            return

        vm_name = entry.view.vm_name
        if vm_name in self._managed_vm_names:
            self.notify(f"{vm_name} is already managed", severity="information")
            return

        session_name = entry.view.session_name
        if session_name == "(none)":
            self.notify("Cannot adopt a VM with no sessions", severity="warning")
            return

        self.notify(f"Adopting {vm_name}/{session_name}...")
        self._adopt_session_bg(vm_name, session_name)

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
        # Trigger a refresh to update tables
        self.call_from_thread(self._schedule_refresh)

    def action_open_detail(self) -> None:
        """Switch to Session Detail tab and kick off tmux capture + reasoning."""
        if not self._selected_key:
            self.notify("No session selected", severity="warning")
            return

        entry = self._cache.get(self._selected_key)
        if entry is None:
            return

        # Switch tab
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "detail-tab"

        # Update header
        header = self.query_one("#detail-header", Static)
        header.update(
            f"[bold]{entry.view.vm_name}[/bold] / "
            f"[bold]{entry.view.session_name}[/bold]  "
            f"Branch: {entry.view.branch or 'n/a'}  "
            f"PR: {entry.view.pr or 'n/a'}  "
            f"Status: {entry.view.status}"
        )

        # Clear capture and proposal
        self.query_one("#tmux-capture", RichLog).clear()
        self.query_one("#proposal-text", Static).update("Fetching tmux capture...")

        # Background: get full capture
        self._fetch_tmux_capture(entry.view.vm_name, entry.view.session_name)

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
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                capture_text = result.stdout
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            capture_text = "(failed to capture tmux output)"

        if worker.is_cancelled:
            return

        # Cache the capture
        entry = self._cache.get(key)
        if entry:
            entry.tmux_capture = capture_text

        self.call_from_thread(self._show_tmux_capture, capture_text)

    def _show_tmux_capture(self, text: str) -> None:
        """Display the tmux capture in the detail view (main thread)."""
        log = self.query_one("#tmux-capture", RichLog)
        log.clear()
        for line in text.split("\n"):
            log.write(line)

        self.query_one("#proposal-text", Static).update(
            "Press [bold]d[/bold] to run dry-run reasoning for this session."
        )

    def action_back_to_fleet(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "fleet-tab"
        # Focus the session table so arrow keys work for navigation
        try:
            self.query_one("#session-table", DataTable).focus()
        except Exception:
            logger.warning("Could not focus session table after returning to fleet")

    def action_tab_fleet(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "fleet-tab"
        try:
            self.query_one("#session-table", DataTable).focus()
        except Exception:
            logger.warning("Could not focus session table in fleet tab")

    def action_tab_detail(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "detail-tab"
        tabs.focus()

    def action_tab_editor(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "editor-tab"
        tabs.focus()

    def action_tab_projects(self) -> None:
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "projects-tab"
        tabs.focus()

    def action_dry_run_session(self) -> None:
        """Run LLM reasoning for the currently selected session."""
        if not self._selected_key:
            self.notify("No session selected", severity="warning")
            return

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            self.notify(
                "ANTHROPIC_API_KEY not set -- cannot run reasoning",
                severity="error",
            )
            self.query_one("#proposal-text", Static).update(
                "[red]No ANTHROPIC_API_KEY. Set the env var to enable director proposals.[/red]"
            )
            return

        entry = self._cache.get(self._selected_key)
        if entry is None:
            return

        self.query_one("#proposal-text", Static).update("[yellow]Running LLM reasoning...[/yellow]")
        self._run_reasoning(entry.view.vm_name, entry.view.session_name)

    @work(thread=True)
    def _run_reasoning(self, vm_name: str, session_name: str) -> None:
        """Call SessionReasoner in a background thread."""
        worker = get_current_worker()
        key = f"{vm_name}/{session_name}"

        try:
            reasoner = SessionReasoner(
                azlin_path=self._fleet.azlin_path,
                backend=AnthropicBackend(),
                dry_run=True,
            )
            decision = reasoner.reason_about_session(
                vm_name=vm_name,
                session_name=session_name,
            )
        except Exception as exc:
            decision = SessionDecision(
                session_name=session_name,
                vm_name=vm_name,
                action="escalate",
                reasoning=f"Reasoning failed: {exc}",
                confidence=0.0,
            )

        if worker.is_cancelled:
            return

        # Cache the proposal
        entry = self._cache.get(key)
        if entry:
            entry.proposal = decision

        self.call_from_thread(self._show_proposal, decision)

    def _show_proposal(self, decision: SessionDecision) -> None:
        """Display the proposal in the detail view (main thread)."""
        lines = [
            f"[bold]Action:[/bold] {decision.action}",
            f"[bold]Confidence:[/bold] {decision.confidence:.0%}",
            f"[bold]Reasoning:[/bold] {decision.reasoning}",
        ]
        if decision.input_text:
            display = decision.input_text.replace("\n", "\\n")[:200]
            lines.append(f'[bold]Input:[/bold] "{display}"')
        self.query_one("#proposal-text", Static).update("\n".join(lines))

    def action_edit_proposal(self) -> None:
        """Switch to Action Editor tab with the current proposal pre-filled."""
        if not self._selected_key:
            self.notify("No session selected", severity="warning")
            return

        entry = self._cache.get(self._selected_key)
        if entry is None or entry.proposal is None:
            self.notify("No proposal to edit. Run dry-run first (d).", severity="warning")
            return

        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "editor-tab"

        # Populate editor fields
        select = self.query_one("#action-select", Select)
        select.value = entry.proposal.action

        editor = self.query_one("#input-editor", TextArea)
        editor.load_text(entry.proposal.input_text or "")

        reasoning_widget = self.query_one("#editor-reasoning", Static)
        reasoning_widget.update(
            f"[dim]Reasoning:[/dim] {entry.proposal.reasoning}\n"
            f"[dim]Confidence:[/dim] {entry.proposal.confidence:.0%}\n"
            f"[dim]Session:[/dim] {self._selected_key}"
        )

    def action_apply_proposal(self) -> None:
        """Apply the current proposal as-is."""
        if not self._selected_key:
            self.notify("No session selected", severity="warning")
            return

        entry = self._cache.get(self._selected_key)
        if entry is None or entry.proposal is None:
            self.notify("No proposal to apply. Run dry-run first (d).", severity="warning")
            return

        self._apply_decision(entry.proposal)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "btn-edit":
            self.action_edit_proposal()

        elif button_id == "btn-apply":
            self.action_apply_proposal()

        elif button_id == "btn-skip":
            self.query_one("#proposal-text", Static).update("Skipped.")
            self.notify("Proposal skipped.")

        elif button_id == "btn-apply-edited":
            self._apply_from_editor()

        elif button_id == "btn-cancel":
            tabs = self.query_one("#tabs", TabbedContent)
            tabs.active = "detail-tab"

        elif button_id == "btn-add-project":
            self._add_project_from_input()

        elif button_id == "btn-remove-project":
            self._remove_selected_project()

        elif button_id == "btn-create-session":
            self._create_new_session()

    def _apply_from_editor(self) -> None:
        """Build a decision from the editor fields and apply it."""
        if not self._selected_key:
            self.notify("No session selected", severity="warning")
            return

        entry = self._cache.get(self._selected_key)
        if entry is None:
            return

        select = self.query_one("#action-select", Select)
        editor = self.query_one("#input-editor", TextArea)

        action_type = str(select.value) if select.value is not Select.BLANK else "wait"
        input_text = editor.text.strip()

        decision = SessionDecision(
            session_name=entry.view.session_name,
            vm_name=entry.view.vm_name,
            action=action_type,
            input_text=input_text,
            reasoning="Manually edited by operator",
            confidence=1.0,
        )

        self._apply_decision(decision)
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "detail-tab"

    def _apply_decision(self, decision: SessionDecision) -> None:
        """Validate and apply a decision (dangerous input check, then execute)."""
        if decision.action == "send_input" and decision.input_text:
            if is_dangerous_input(decision.input_text):
                self.notify(
                    f"BLOCKED: Input contains dangerous pattern. "
                    f"Matches against: {', '.join(p.pattern for p in DANGEROUS_PATTERNS[:3])}...",
                    severity="error",
                    timeout=8,
                )
                return

        # Execute in background
        self._execute_decision_bg(decision)

    # ------------------------------------------------------------------
    # Project management
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

        # The key is the project name (set when adding rows)
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
    # New session creation
    # ------------------------------------------------------------------

    def action_new_session(self) -> None:
        """Switch to the New Session tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        tabs.active = "new-session-tab"
        # Populate VM select with running VMs
        self._populate_vm_select()

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
        options = [(name, name) for name in sorted(all_vms)]
        vm_select.set_options(options)

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

    @work(thread=True)
    def _create_session_bg(self, vm_name: str, agent_type: str) -> None:
        """Create a new tmux session on a VM in background."""
        import shlex
        import subprocess

        validate_vm_name(vm_name)
        worker = get_current_worker()

        # Map agent types to amplihack launch commands
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

        # Create a new tmux session and run the agent inside it
        session_name = f"{agent_type}-{int(__import__('time').time()) % 10000}"
        remote_cmd = f"tmux new-session -d -s {shlex.quote(session_name)} {shlex.quote(launch_cmd)}"

        try:
            result = subprocess.run(
                [self._fleet.azlin_path, "connect", vm_name, "--no-tmux", "--", remote_cmd],
                capture_output=True,
                text=True,
                timeout=60,
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
                azlin_path=self._fleet.azlin_path,
                backend=AnthropicBackend(),
                dry_run=False,
            )
            # Use the internal execute method directly
            reasoner.execute_decision(decision)
            msg = f"Applied: {decision.action}"
            severity = "information"
        except Exception as exc:
            msg = f"Failed to apply: {exc}"
            severity = "error"

        if worker.is_cancelled:
            return

        self.call_from_thread(self.notify, msg, severity=severity)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_dashboard(interval: int = 30) -> None:
    """Launch the interactive fleet dashboard.

    Args:
        interval: Auto-refresh interval in seconds.
    """
    app = FleetDashboardApp(refresh_interval=interval)
    app.run()
