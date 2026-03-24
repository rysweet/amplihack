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

from amplihack.fleet._constants import DEFAULT_DASHBOARD_REFRESH_SECONDS
from amplihack.fleet._tui_actions import _ActionsMixin
from amplihack.fleet._tui_refresh import _CachedSession, _RefreshMixin
from amplihack.fleet._tui_styles import APP_CSS
from amplihack.fleet.fleet_tui import FleetTUI

logger = logging.getLogger(__name__)

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


# ---------------------------------------------------------------------------
# Textual App
# ---------------------------------------------------------------------------


class FleetDashboardApp(_ActionsMixin, _RefreshMixin, App):
    """Interactive fleet management dashboard built on Textual."""

    TITLE = "Fleet Dashboard"
    SUB_TITLE = "Autonomous Coding Agent Fleet Management"

    CSS = APP_CSS

    COMMAND_PALETTE_BINDING = ""  # Disable command palette (prevents Escape hijack)

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
        # Tab navigation — numeric keys
        Binding("1", "tab_fleet", "[u]F[/u]leet", show=True, priority=True),
        Binding("2", "tab_detail", "[u]S[/u]ession Detail", show=True, priority=True),
        Binding("3", "tab_editor", "Editor", show=True, priority=True),
        Binding("4", "tab_projects", "[u]P[/u]rojects", show=True, priority=True),
        # Tab navigation — letter hotkeys (priority=True so they aren't consumed by child widgets)
        Binding("f", "tab_fleet", "[u]F[/u]leet", show=False, priority=True),
        Binding("s", "tab_detail", "[u]S[/u]ession Detail", show=False, priority=True),
        Binding("p", "tab_projects", "[u]P[/u]rojects", show=False, priority=True),
        # Tab navigation — arrow keys
        Binding("left", "tab_prev", "Prev Tab", show=False),
        Binding("right", "tab_next", "Next Tab", show=False),
    ]

    def __init__(
        self,
        refresh_interval: int = DEFAULT_DASHBOARD_REFRESH_SECONDS,
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
        table = self.query_one("#session-table", DataTable)
        table.add_columns("St", "VM", "Session", "State", "Branch", "PR")

        all_table = self.query_one("#all-session-table", DataTable)
        all_table.add_columns("St", "VM", "Session", "State", "Branch", "PR", "Mgd")

        proj_table = self.query_one("#project-table", DataTable)
        proj_table.add_columns("Name", "Repo", "Identity", "Priority", "VMs", "Tasks", "PRs")

        # Don't focus DataTable — it consumes single-letter keys and
        # blocks app-level hotkeys (f, s, p, etc.) from firing.

        self._schedule_refresh()
        self.set_interval(self._refresh_interval, self._schedule_refresh)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_dashboard(
    interval: int = DEFAULT_DASHBOARD_REFRESH_SECONDS,
    capture_lines: int | None = None,
) -> None:
    """Launch the interactive fleet dashboard.

    Args:
        interval: Auto-refresh interval in seconds.
        capture_lines: Terminal scrollback capture depth (passed to FleetTUI).
    """
    try:
        app = FleetDashboardApp(refresh_interval=interval)
    except ValueError as exc:
        import click

        click.echo(f"ERROR: {exc}", err=True)
        click.echo("Run 'fleet setup' to check prerequisites.", err=True)
        raise SystemExit(1)
    if capture_lines is not None:
        app._fleet.capture_lines = capture_lines
    app.run()
