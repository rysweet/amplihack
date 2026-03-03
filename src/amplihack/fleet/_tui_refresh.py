"""Refresh/polling mixin for FleetDashboardApp.

Handles background data fetching, two-phase refresh, table row building,
and project table updates.  Mixed into FleetDashboardApp via _RefreshMixin.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual import work
from textual.widgets import DataTable, Static
from textual.worker import get_current_worker

if TYPE_CHECKING:
    from amplihack.fleet.fleet_tui import SessionView, VMView

__all__ = ["_CachedSession", "build_rows_and_cache", "_RefreshMixin"]

logger = logging.getLogger(__name__)


@dataclass
class _CachedSession:
    """Internal cache entry for a polled session."""

    view: SessionView
    tmux_capture: str = ""
    proposal: "SessionDecision | None" = None


def build_rows_and_cache(
    vms: list[VMView],
    old_cache: dict[str, _CachedSession],
    managed_vm_names: set[str] | None = None,
    include_mgd_column: bool = False,
) -> tuple[list[tuple[str, list[str]]], dict[str, _CachedSession]]:
    """Build table rows and cache from VM views (pure function)."""
    from amplihack.fleet.fleet_tui import SessionView
    from amplihack.fleet.fleet_tui_dashboard import STATUS_STYLES

    new_cache: dict[str, _CachedSession] = {}
    rows: list[tuple[str, list[str]]] = []

    for vm in vms:
        if not vm.is_running:
            continue
        is_managed = managed_vm_names is None or vm.name in managed_vm_names

        if not vm.sessions:
            key = f"{vm.name}/(no sessions)"
            cell_style = "" if is_managed else "dim"
            cells = [
                "[dim]\u25cb[/]",
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


class _RefreshMixin:
    """Data-fetching and table-refresh methods for FleetDashboardApp."""

    def _schedule_refresh(self) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        self._refresh_generation += 1
        self.add_class("active-loading")
        self._do_refresh()

    @work(thread=True)
    def _do_refresh(self) -> None:
        """Poll all VMs via azlin in a background thread (two-phase)."""
        from amplihack.fleet.fleet_tui import VMView

        worker = get_current_worker()
        my_generation = self._refresh_generation

        try:
            vm_list = self._fleet._get_vm_list()
        except Exception as exc:
            logger.error("Phase 1 VM list fetch failed: %s", exc)
            self.call_from_thread(self.notify, f"VM list fetch failed: {exc}", severity="error")
            vm_list = []

        if worker.is_cancelled:
            return

        quick_managed: list[VMView] = []
        quick_all: list[VMView] = []
        for name, region, is_running in vm_list:
            vm = VMView(name=name, region=region, is_running=is_running)
            quick_all.append(vm)
            if name not in self._fleet.exclude_vms:
                quick_managed.append(vm)

        managed_vm_names = {vm.name for vm in quick_managed}
        managed_rows, new_cache = build_rows_and_cache(quick_managed, self._cache)
        all_rows, all_cache = build_rows_and_cache(
            quick_all, self._cache, include_mgd_column=True, managed_vm_names=managed_vm_names,
        )
        new_cache.update(all_cache)
        self.call_from_thread(
            self._apply_refresh, quick_managed, managed_rows, new_cache,
            all_rows, all_cache, managed_vm_names,
        )

        if worker.is_cancelled:
            return

        # PHASE 2: Progressive session polling
        all_vms: list[VMView] = []
        try:
            for vm in self._fleet.refresh_iter(exclude=False):
                if worker.is_cancelled or my_generation != self._refresh_generation:
                    return
                all_vms.append(vm)
                managed_vm_names = {
                    v.name for v in all_vms if v.name not in self._fleet.exclude_vms
                }
                managed_vms = [v for v in all_vms if v.name not in self._fleet.exclude_vms]
                managed_rows, new_cache = build_rows_and_cache(managed_vms, self._cache)
                all_rows, all_cache = build_rows_and_cache(
                    all_vms, self._all_cache,
                    managed_vm_names=managed_vm_names, include_mgd_column=True,
                )
                self.call_from_thread(
                    self._apply_refresh, managed_vms, managed_rows, new_cache,
                    all_rows, all_cache, managed_vm_names,
                )
        except Exception as exc:
            logger.warning("Fleet refresh failed: %s", exc)
            self.call_from_thread(self.notify, f"Fleet refresh failed: {exc}", severity="warning")
        finally:
            self.call_from_thread(self._finish_refresh)

    def _finish_refresh(self) -> None:
        """Mark refresh cycle complete (main thread)."""
        self._refreshing = False
        self.remove_class("active-loading")

    def _apply_refresh(
        self, vms: list[VMView], rows: list[tuple[str, list[str]]],
        new_cache: dict[str, _CachedSession], all_rows: list[tuple[str, list[str]]],
        all_cache: dict[str, _CachedSession], managed_vm_names: set[str],
    ) -> None:
        """Update UI with refreshed data (main thread).

        Preserves the user's current tab — table updates do not
        steal focus or switch tabs.
        """
        # Remember current tab so refresh doesn't hijack it
        try:
            current_tab = self.query_one("#tabs", TabbedContent).active
        except Exception:
            current_tab = None

        self._cache = new_cache
        self._all_cache = all_cache
        self._managed_vm_names = managed_vm_names

        table = self.query_one("#session-table", DataTable)
        table.clear()
        for key, cells in rows:
            table.add_row(*cells, key=key)

        all_table = self.query_one("#all-session-table", DataTable)
        all_table.clear()
        for key, cells in all_rows:
            all_table.add_row(*cells, key=key)

        # Restore tab if refresh changed it
        if current_tab:
            try:
                tabs = self.query_one("#tabs", TabbedContent)
                if tabs.active != current_tab:
                    tabs.active = current_tab
            except Exception:
                pass

        self._refresh_projects_table()

        total_sessions = sum(1 for v in vms for _ in v.sessions if v.is_running)
        active = sum(
            1 for v in vms for s in v.sessions
            if v.is_running and s.status in ("thinking", "working", "running", "waiting_input")
        )
        idle = sum(1 for v in vms for s in v.sessions if v.is_running and s.status == "idle")
        errors = sum(1 for v in vms for s in v.sessions if v.is_running and s.status == "error")
        now = datetime.now().strftime("%H:%M:%S")
        summary = (
            f"  {len(vms)} VMs | {total_sessions} sessions | "
            f"[green]{active} active[/] | [yellow]{idle} idle[/] | "
            f"[red]{errors} error[/] | Updated {now} | Refresh every {self._refresh_interval}s"
        )
        self.query_one("#fleet-summary", Static).update(summary)

    @staticmethod
    def _get_dashboard():
        """Create a FleetDashboard instance with the standard persist path."""
        from amplihack.fleet.fleet_dashboard import FleetDashboard
        return FleetDashboard(persist_path=Path.home() / ".amplihack" / "fleet" / "dashboard.json")

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
