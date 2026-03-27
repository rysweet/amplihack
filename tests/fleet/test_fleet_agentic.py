"""Agentic fleet TUI test — outside-in virtual TTY observation.

Drives the FleetDashboardApp headlessly via Textual's pilot API,
then uses fleet APIs to adopt sessions and dry-run admiral reasoning.

This is an outside-in test: we interact with the TUI as a user would,
observing screen state through the virtual terminal.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Ensure the src directory is on the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

os.environ.setdefault("AZLIN_PATH", "/home/azureuser/src/azlin/.venv/bin/azlin")

from amplihack.fleet._defaults import get_azlin_path
from amplihack.fleet._tui_data import SessionView, VMView
from amplihack.fleet.fleet_tui import FleetTUI


def phase1_discover_fleet() -> list[VMView]:
    """Phase 1: Discover all VMs and sessions via FleetTUI (no TUI render)."""
    print("=" * 60)
    print("PHASE 1: FLEET DISCOVERY")
    print("=" * 60)

    tui = FleetTUI()
    print(f"azlin path: {tui.azlin_path}")
    print(f"exclude VMs: {tui.exclude_vms}")
    print()

    # Get ALL VMs (including excluded)
    print("Polling all VMs (including excluded)...")
    all_vms = tui.refresh_all()
    print(f"Found {len(all_vms)} total VMs")

    # Also get managed VMs
    print("\nPolling managed VMs only...")
    managed_vms = tui.refresh()
    print(f"Found {len(managed_vms)} managed VMs")

    print("\n--- ALL VMs ---")
    total_sessions = 0
    for vm in sorted(all_vms, key=lambda v: v.name):
        status = "RUNNING" if vm.is_running else "STOPPED"
        managed = "managed" if vm.name not in tui.exclude_vms else "EXCLUDED"
        print(f"  {vm.name:20s} [{status:7s}] [{managed}] region={vm.region}")
        if vm.sessions:
            for sess in vm.sessions:
                total_sessions += 1
                print(
                    f"    > {sess.session_name:25s} status={sess.status:12s} "
                    f"branch={sess.branch or '(none)':30s} pr={sess.pr or 'n/a'}"
                )
                if sess.last_line:
                    print(f"      last_line: {sess.last_line[:80]}")
        else:
            print("    (no sessions)")

    print(f"\nTotal: {len(all_vms)} VMs, {total_sessions} sessions")
    return all_vms


def phase2_adopt_sessions(all_vms: list[VMView]) -> list[tuple[str, str]]:
    """Phase 2: Adopt all existing sessions under fleet management."""
    print("\n" + "=" * 60)
    print("PHASE 2: SESSION ADOPTION")
    print("=" * 60)

    from amplihack.fleet.fleet_adopt import SessionAdopter
    from amplihack.fleet.fleet_tasks import TaskQueue

    azlin = get_azlin_path()
    queue_path = Path.home() / ".amplihack" / "fleet" / "task_queue.json"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    adopter = SessionAdopter(azlin_path=azlin)
    queue = TaskQueue(persist_path=queue_path)

    adopted_sessions: list[tuple[str, str]] = []

    for vm in all_vms:
        if not vm.is_running or not vm.sessions:
            continue
        print(f"\nAdopting sessions on {vm.name}...")
        try:
            adopted = adopter.adopt_sessions(vm.name, queue)
            for sess_name in adopted:
                adopted_sessions.append((vm.name, sess_name))
                print(f"  Adopted: {vm.name}/{sess_name}")
            if not adopted:
                print(f"  (all sessions already adopted or no sessions)")
        except Exception as exc:
            print(f"  ERROR adopting on {vm.name}: {exc}")

    print(f"\nTotal adopted: {len(adopted_sessions)} sessions")
    return adopted_sessions


def phase3_dry_run_reasoning(all_vms: list[VMView]) -> list[dict]:
    """Phase 3: Dry-run fleet admiral reasoning for each session."""
    print("\n" + "=" * 60)
    print("PHASE 3: FLEET ADMIRAL DRY-RUN REASONING")
    print("=" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("WARNING: ANTHROPIC_API_KEY not set — skipping LLM reasoning")
        print("Will show session state without proposals")
        return _dry_run_without_llm(all_vms)

    from amplihack.fleet._backends import AnthropicBackend
    from amplihack.fleet.fleet_session_reasoner import SessionReasoner

    azlin = get_azlin_path()
    reasoner = SessionReasoner(
        azlin_path=azlin, backend=AnthropicBackend(), dry_run=True,
    )

    decisions: list[dict] = []
    for vm in all_vms:
        if not vm.is_running or not vm.sessions:
            continue
        for sess in vm.sessions:
            print(f"\nReasoning about {vm.name}/{sess.session_name} (status={sess.status})...")
            try:
                decision = reasoner.reason_about_session(
                    vm_name=vm.name, session_name=sess.session_name,
                )
                d = {
                    "vm": vm.name,
                    "session": sess.session_name,
                    "status": sess.status,
                    "branch": sess.branch,
                    "pr": sess.pr,
                    "action": decision.action,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                    "input_text": decision.input_text,
                }
                decisions.append(d)
                print(f"  Action: {decision.action} (confidence: {decision.confidence:.0%})")
                print(f"  Reasoning: {decision.reasoning[:120]}")
                if decision.input_text:
                    print(f"  Input: {decision.input_text[:80]}")
            except Exception as exc:
                print(f"  ERROR: {exc}")
                decisions.append({
                    "vm": vm.name,
                    "session": sess.session_name,
                    "status": sess.status,
                    "error": str(exc),
                })

    return decisions


def _dry_run_without_llm(all_vms: list[VMView]) -> list[dict]:
    """Fallback: show session states without LLM reasoning."""
    decisions = []
    for vm in all_vms:
        if not vm.is_running or not vm.sessions:
            continue
        for sess in vm.sessions:
            decisions.append({
                "vm": vm.name,
                "session": sess.session_name,
                "status": sess.status,
                "branch": sess.branch,
                "pr": sess.pr,
                "action": "N/A (no API key)",
                "confidence": 0.0,
                "reasoning": "LLM reasoning skipped — no ANTHROPIC_API_KEY",
            })
    return decisions


async def phase4_headless_tui_test():
    """Phase 4: Drive the Textual TUI headlessly (virtual TTY)."""
    print("\n" + "=" * 60)
    print("PHASE 4: HEADLESS TUI TEST (Virtual TTY)")
    print("=" * 60)

    from amplihack.fleet.fleet_tui_dashboard import FleetDashboardApp

    app = FleetDashboardApp(refresh_interval=60)

    async with app.run_test(size=(120, 40)) as pilot:
        # Wait for initial mount and data load
        print("TUI launched in headless mode (120x40)")
        await pilot.pause()
        await asyncio.sleep(2)  # Allow background refresh to start

        # Take a screenshot of the initial fleet overview
        print("\n--- Fleet Overview Tab (screenshot) ---")
        screenshot = app.export_screenshot()
        print(screenshot[:2000] if screenshot else "(empty screenshot)")

        # Check if data loaded
        from textual.widgets import DataTable
        table = app.query_one("#session-table", DataTable)
        row_count = table.row_count
        print(f"\nSession table rows: {row_count}")

        if row_count > 0:
            # Navigate down through rows
            for i in range(min(row_count, 5)):
                await pilot.press("down")
                await pilot.pause()

            # Press Enter to open detail
            print("\nOpening session detail...")
            await pilot.press("enter")
            await pilot.pause()
            await asyncio.sleep(1)

            # Take screenshot of detail view
            detail_screenshot = app.export_screenshot()
            print("\n--- Session Detail Tab (screenshot) ---")
            print(detail_screenshot[:2000] if detail_screenshot else "(empty)")

            # Go back to fleet overview
            await pilot.press("escape")
            await pilot.pause()

            # Switch to All Sessions tab
            print("\nSwitching to All Sessions sub-tab...")
            # The All Sessions is a sub-tab, would need different navigation

        # Switch to Projects tab
        print("\nSwitching to Projects tab (press 'p')...")
        await pilot.press("p")
        await pilot.pause()
        proj_screenshot = app.export_screenshot()
        print("\n--- Projects Tab (screenshot) ---")
        print(proj_screenshot[:1000] if proj_screenshot else "(empty)")

        print("\nHeadless TUI test complete.")


def phase5_summary_report(all_vms: list[VMView], decisions: list[dict]):
    """Phase 5: Generate comprehensive summary report."""
    print("\n" + "=" * 60)
    print("PHASE 5: FLEET STATUS SUMMARY REPORT")
    print("=" * 60)

    running_vms = [v for v in all_vms if v.is_running]
    total_sessions = sum(len(v.sessions) for v in running_vms)
    active_sessions = sum(
        1 for v in running_vms for s in v.sessions
        if s.status in ("thinking", "working", "running", "waiting_input")
    )
    idle_sessions = sum(
        1 for v in running_vms for s in v.sessions if s.status == "idle"
    )

    print(f"\nRunning VMs: {len(running_vms)}")
    print(f"Total sessions: {total_sessions}")
    print(f"Active sessions: {active_sessions}")
    print(f"Idle sessions: {idle_sessions}")

    print("\n--- Per-VM Summary ---")
    for vm in sorted(running_vms, key=lambda v: v.name):
        print(f"\n  {vm.name} ({vm.region}):")
        for sess in vm.sessions:
            print(f"    {sess.session_name:25s} [{sess.status:12s}] branch={sess.branch or 'n/a'}")
            # Find matching decision
            for d in decisions:
                if d["vm"] == vm.name and d["session"] == sess.session_name:
                    if "error" in d:
                        print(f"      Admiral: ERROR - {d['error'][:80]}")
                    else:
                        print(f"      Admiral: {d['action']} (conf={d.get('confidence', 0):.0%})")
                        if d.get("reasoning"):
                            print(f"      Reason: {d['reasoning'][:100]}")
                    break

    print("\n--- Decisions Summary ---")
    action_counts: dict[str, int] = {}
    for d in decisions:
        action = d.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
    for action, count in sorted(action_counts.items()):
        print(f"  {action}: {count}")

    # Save report to file
    report_path = Path.home() / ".amplihack" / "fleet" / "fleet_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "running_vms": len(running_vms),
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "idle_sessions": idle_sessions,
        "decisions": decisions,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved to: {report_path}")


def main():
    print("Fleet Agentic TUI Test — Outside-In Virtual TTY Observation")
    print("=" * 60)
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"AZLIN_PATH: {os.environ.get('AZLIN_PATH', '(not set)')}")
    print()

    # Phase 1: Discover
    all_vms = phase1_discover_fleet()

    # Phase 2: Adopt
    phase2_adopt_sessions(all_vms)

    # Phase 3: Dry-run reasoning
    decisions = phase3_dry_run_reasoning(all_vms)

    # Phase 4: Headless TUI test
    try:
        asyncio.run(phase4_headless_tui_test())
    except Exception as exc:
        print(f"\nHeadless TUI test failed: {exc}")
        print("Continuing with report generation...")

    # Phase 5: Summary report
    phase5_summary_report(all_vms, decisions)


if __name__ == "__main__":
    main()
