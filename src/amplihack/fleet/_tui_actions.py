"""Action/interaction mixin for FleetDashboardApp.

Handles user-triggered actions: keybinding actions, button presses,
cursor events, and UI-thread display helpers.  Background workers and
project/session management live in _tui_workers.py (_WorkersMixin).
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from textual.widgets import (
    Button,
    DataTable,
    RichLog,
    Select,
    Static,
    TabbedContent,
    TextArea,
)

from amplihack.fleet._tui_workers import _WorkersMixin
from amplihack.fleet._validation import DANGEROUS_PATTERNS, is_dangerous_input
from amplihack.fleet.fleet_session_reasoner import SessionDecision

if TYPE_CHECKING:
    from amplihack.fleet._tui_refresh import _CachedSession

logger = logging.getLogger(__name__)


class _ActionsMixin(_WorkersMixin):
    """User-interaction methods for FleetDashboardApp.

    Inherits background workers and project/session management from
    _WorkersMixin.
    """

    # ------------------------------------------------------------------
    # DataTable cursor event
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update the preview pane when the cursor moves."""
        if event.row_key is None:
            return
        key = str(event.row_key.value)
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
    # Keybinding actions
    # ------------------------------------------------------------------

    def action_force_refresh(self) -> None:
        self._schedule_refresh()
        self.notify("Refreshing fleet data...")

    def action_toggle_logo(self) -> None:
        self.query_one("#pirate-logo", Static).toggle_class("hidden")

    def action_adopt_session(self) -> None:
        """Adopt the highlighted unmanaged session into fleet management."""
        if not self._selected_key:
            self.notify("No session selected", severity="warning")
            return
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

    def action_open_detail(self) -> None:
        """Switch to Session Detail tab and kick off tmux capture."""
        if not self._selected_key:
            self.notify("No session selected", severity="warning")
            return
        entry = self._cache.get(self._selected_key)
        if entry is None:
            return
        self.query_one("#tabs", TabbedContent).active = "detail-tab"
        self.query_one("#detail-header", Static).update(
            f"[bold]{entry.view.vm_name}[/bold] / "
            f"[bold]{entry.view.session_name}[/bold]  "
            f"Branch: {entry.view.branch or 'n/a'}  "
            f"PR: {entry.view.pr or 'n/a'}  "
            f"Status: {entry.view.status}"
        )
        self.query_one("#tmux-capture", RichLog).clear()
        self.query_one("#proposal-text", Static).update("Fetching tmux capture...")
        self._fetch_tmux_capture(entry.view.vm_name, entry.view.session_name)

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
        self.query_one("#tabs", TabbedContent).active = "fleet-tab"
        try:
            self.query_one("#session-table", DataTable).focus()
        except Exception:
            logger.warning("Could not focus session table after returning to fleet")

    def action_tab_fleet(self) -> None:
        self.query_one("#tabs", TabbedContent).active = "fleet-tab"
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
            self.notify("ANTHROPIC_API_KEY not set -- cannot run reasoning", severity="error")
            self.query_one("#proposal-text", Static).update(
                "[red]No ANTHROPIC_API_KEY. Set the env var to enable director proposals.[/red]"
            )
            return
        entry = self._cache.get(self._selected_key)
        if entry is None:
            return
        self.query_one("#proposal-text", Static).update("[yellow]Running LLM reasoning...[/yellow]")
        self._run_reasoning(entry.view.vm_name, entry.view.session_name)

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
        """Switch to Action Editor tab with the proposal pre-filled."""
        if not self._selected_key:
            self.notify("No session selected", severity="warning")
            return
        entry = self._cache.get(self._selected_key)
        if entry is None or entry.proposal is None:
            self.notify("No proposal to edit. Run dry-run first (d).", severity="warning")
            return
        self.query_one("#tabs", TabbedContent).active = "editor-tab"
        self.query_one("#action-select", Select).value = entry.proposal.action
        self.query_one("#input-editor", TextArea).load_text(entry.proposal.input_text or "")
        self.query_one("#editor-reasoning", Static).update(
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

    def action_new_session(self) -> None:
        """Switch to the New Session tab."""
        self.query_one("#tabs", TabbedContent).active = "new-session-tab"
        self._populate_vm_select()

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
            self.query_one("#tabs", TabbedContent).active = "detail-tab"
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
        decision = SessionDecision(
            session_name=entry.view.session_name, vm_name=entry.view.vm_name,
            action=action_type, input_text=editor.text.strip(),
            reasoning="Manually edited by operator", confidence=1.0,
        )
        self._apply_decision(decision)
        self.query_one("#tabs", TabbedContent).active = "detail-tab"

    def _apply_decision(self, decision: SessionDecision) -> None:
        """Validate and apply a decision (dangerous input check)."""
        if decision.action == "send_input" and decision.input_text:
            if is_dangerous_input(decision.input_text):
                self.notify(
                    f"BLOCKED: Input contains dangerous pattern. "
                    f"Matches against: {', '.join(p.pattern for p in DANGEROUS_PATTERNS[:3])}...",
                    severity="error", timeout=8,
                )
                return
        self._execute_decision_bg(decision)
