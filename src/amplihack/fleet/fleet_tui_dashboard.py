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

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    RichLog,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
    Button,
    Select,
    LoadingIndicator,
)
from textual.worker import get_current_worker
from textual import work

from amplihack.fleet.fleet_tui import FleetTUI, SessionView, VMView
from amplihack.fleet.fleet_session_reasoner import (
    SessionReasoner,
    SessionDecision,
    AnthropicBackend,
    _is_dangerous_input,
    DANGEROUS_PATTERNS,
)

__all__ = ["FleetDashboardApp", "run_dashboard"]

# ---------------------------------------------------------------------------
# Status icon mapping (Rich-compatible markup)
# ---------------------------------------------------------------------------
STATUS_STYLES: dict[str, tuple[str, str]] = {
    "thinking":      ("\u25c9", "green"),
    "working":       ("\u25c9", "green"),
    "running":       ("\u25c9", "green"),
    "waiting_input": ("\u25c9", "green"),
    "idle":          ("\u25cf", "yellow"),
    "shell":         ("\u25cb", "dim"),
    "empty":         ("\u25cb", "dim"),
    "no_session":    ("\u25cb", "dim"),
    "unknown":       ("\u25cb", "dim"),
    "error":         ("\u2717", "red"),
    "completed":     ("\u2713", "dodger_blue1"),
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
    proposal: Optional[SessionDecision] = None


# ---------------------------------------------------------------------------
# Textual App
# ---------------------------------------------------------------------------

class FleetDashboardApp(App):
    """Interactive fleet management dashboard built on Textual."""

    TITLE = "Fleet Dashboard v2"

    CSS = """
Screen {
    layout: vertical;
}
#fleet-tab Horizontal {
    height: 1fr;
}
#session-table {
    width: 60%;
}
#preview-pane {
    width: 40%;
    border: solid $accent;
    padding: 0 1;
}
#fleet-summary {
    height: 3;
    dock: bottom;
    padding: 0 1;
    background: $surface;
}
#detail-header {
    height: auto;
    max-height: 5;
    padding: 0 1;
    background: $surface;
}
#tmux-capture {
    height: 1fr;
    min-height: 8;
    border: solid $primary;
}
#proposal-section {
    height: auto;
    max-height: 14;
    border: solid $accent;
    padding: 1;
}
#editor-reasoning {
    height: auto;
    max-height: 6;
    padding: 0 1;
    background: $surface;
}
#input-editor {
    height: 8;
}
Button {
    margin: 0 1;
}
.button-row {
    height: 3;
    layout: horizontal;
    align: center middle;
}
#loading-overlay {
    display: none;
    dock: top;
    height: 3;
    content-align: center middle;
}
.active-loading #loading-overlay {
    display: block;
}
"""

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "force_refresh", "Refresh", show=True),
        Binding("enter", "open_detail", "Detail", show=True),
        Binding("escape", "back_to_fleet", "Back", show=True),
        Binding("e", "edit_proposal", "Edit", show=True),
        Binding("a", "apply_proposal", "Apply", show=True),
        Binding("d", "dry_run_session", "Dry-run", show=True),
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
        self._selected_key: str = ""
        self._refreshing = False

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(id="tabs"):
            # --- Tab 1: Fleet Overview ---
            with TabPane("Fleet Overview", id="fleet-tab"):
                with Horizontal():
                    yield DataTable(id="session-table", cursor_type="row")
                    yield RichLog(id="preview-pane", wrap=True, markup=True)
                yield Static("Loading fleet data...", id="fleet-summary")

            # --- Tab 2: Session Detail ---
            with TabPane("Session Detail", id="detail-tab"):
                yield Static("Select a session from Fleet Overview and press Enter.", id="detail-header")
                yield RichLog(id="tmux-capture", wrap=True, markup=True)
                with Vertical(id="proposal-section"):
                    yield Static("Proposal will appear here after dry-run.", id="proposal-text")
                    with Horizontal(classes="button-row"):
                        yield Button("Edit", id="btn-edit", variant="default")
                        yield Button("Apply", id="btn-apply", variant="success")
                        yield Button("Skip", id="btn-skip", variant="error")

            # --- Tab 3: Action Editor ---
            with TabPane("Action Editor", id="editor-tab"):
                yield Select(ACTION_CHOICES, id="action-select", prompt="Action type", value="send_input")
                yield TextArea(id="input-editor", language=None)
                yield Static("", id="editor-reasoning")
                with Horizontal(classes="button-row"):
                    yield Button("Apply Edited", id="btn-apply-edited", variant="success")
                    yield Button("Cancel", id="btn-cancel", variant="error")

        yield LoadingIndicator(id="loading-overlay")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        # Set up data table columns
        table = self.query_one("#session-table", DataTable)
        table.add_columns("St", "VM", "Session", "State", "Branch", "PR")

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
        self._do_refresh()

    @work(thread=True)
    def _do_refresh(self) -> None:
        """Poll all VMs via azlin in a background thread."""
        worker = get_current_worker()
        try:
            vms: list[VMView] = self._fleet.refresh()
        except Exception:
            vms = []

        if worker.is_cancelled:
            return

        # Build cache from results
        new_cache: dict[str, _CachedSession] = {}
        rows: list[tuple[str, list[str]]] = []

        for vm in vms:
            if not vm.is_running:
                continue
            if not vm.sessions:
                key = f"{vm.name}/(no sessions)"
                icon, style = "\u25cb", "dim"
                rows.append((key, [f"[{style}]{icon}[/]", vm.name, "(none)", "stopped", "", ""]))
                new_cache[key] = _CachedSession(
                    view=SessionView(vm_name=vm.name, session_name="(none)", status="empty"),
                )
                continue

            for sess in vm.sessions:
                key = f"{vm.name}/{sess.session_name}"
                icon, style = STATUS_STYLES.get(sess.status, ("\u25cb", "dim"))
                branch = sess.branch[:24] + "..." if len(sess.branch) > 24 else sess.branch
                pr = sess.pr or ""
                rows.append((
                    key,
                    [
                        f"[{style}]{icon}[/]",
                        vm.name,
                        sess.session_name,
                        sess.status,
                        branch,
                        pr,
                    ],
                ))
                # Preserve existing proposal if present
                old = self._cache.get(key)
                entry = _CachedSession(view=sess)
                if old and old.proposal:
                    entry.proposal = old.proposal
                new_cache[key] = entry

        # Post results back to UI thread
        self.call_from_thread(self._apply_refresh, vms, rows, new_cache)

    def _apply_refresh(
        self,
        vms: list[VMView],
        rows: list[tuple[str, list[str]]],
        new_cache: dict[str, _CachedSession],
    ) -> None:
        """Update UI with refreshed data (called on the main thread)."""
        self._refreshing = False
        self._cache = new_cache

        # Rebuild the data table
        table = self.query_one("#session-table", DataTable)
        table.clear()
        for key, cells in rows:
            table.add_row(*cells, key=key)

        # Summary bar
        total_sessions = sum(1 for v in vms for _ in v.sessions if v.is_running)
        active = sum(
            1 for v in vms for s in v.sessions
            if v.is_running and s.status in ("thinking", "working", "running", "waiting_input")
        )
        idle = sum(
            1 for v in vms for s in v.sessions
            if v.is_running and s.status == "idle"
        )
        errors = sum(
            1 for v in vms for s in v.sessions
            if v.is_running and s.status == "error"
        )
        now = datetime.now().strftime("%H:%M:%S")
        summary = (
            f"  {len(vms)} VMs | {total_sessions} sessions | "
            f"[green]{active} active[/] | [yellow]{idle} idle[/] | "
            f"[red]{errors} error[/] | "
            f"Updated {now} | Refresh every {self._refresh_interval}s"
        )
        self.query_one("#fleet-summary", Static).update(summary)

    # ------------------------------------------------------------------
    # DataTable events
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """When the cursor moves in the fleet table, update the preview pane."""
        if event.row_key is None:
            return
        key = str(event.row_key.value)
        self._selected_key = key
        entry = self._cache.get(key)
        if entry is None:
            return

        preview = self.query_one("#preview-pane", RichLog)
        preview.clear()
        preview.write(f"[bold]{key}[/bold]")
        preview.write(f"Status: {entry.view.status}")
        if entry.view.branch:
            preview.write(f"Branch: {entry.view.branch}")
        if entry.view.pr:
            preview.write(f"PR: {entry.view.pr}")
        if entry.view.last_line:
            preview.write(f"\n[dim]Last output:[/dim]")
            preview.write(entry.view.last_line)
        if entry.tmux_capture:
            preview.write(f"\n[dim]--- tmux capture ---[/dim]")
            for line in entry.tmux_capture.split("\n")[-15:]:
                preview.write(line)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_force_refresh(self) -> None:
        self._schedule_refresh()
        self.notify("Refreshing fleet data...")

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
            if _is_dangerous_input(decision.input_text):
                self.notify(
                    f"BLOCKED: Input contains dangerous pattern. "
                    f"Matches against: {', '.join(DANGEROUS_PATTERNS[:3])}...",
                    severity="error",
                    timeout=8,
                )
                return

        # Execute in background
        self._execute_decision_bg(decision)

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
            reasoner._execute_decision(decision)
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
