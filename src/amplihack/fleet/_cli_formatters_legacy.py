"""Legacy plain-text formatters for fleet scout and advance reports.

These functions operate on raw VM/session dicts and lists produced by the
original FleetTUI pipeline.  They are kept separate from the new dataclass-based
formatters so the main _cli_formatters module stays focused on the structured
ScoutResult / AdvanceResult API.
"""

from __future__ import annotations

from amplihack.utils.logging_utils import log_call


@log_call
def _format_scout_report_legacy(
    all_vms: list,
    decisions: list[dict],
    adopted_count: int,
    skip_adopt: bool,
) -> str:
    """Format the scout report as indented plain text (legacy format).

    Args:
        all_vms: List of VMView objects from FleetTUI.refresh_all().
        decisions: List of decision dicts from reasoning phase.
        adopted_count: Number of sessions adopted (0 if skipped).
        skip_adopt: Whether adoption was skipped.

    Returns:
        Formatted plain text report string.
    """
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("FLEET SCOUT REPORT")
    lines.append("=" * 60)

    running_vms = [v for v in all_vms if v.is_running]
    total_sessions = sum(len(v.sessions) for v in running_vms)
    active_sessions = sum(
        1
        for v in running_vms
        for s in v.sessions
        if s.status in ("thinking", "working", "running", "waiting_input")
    )
    idle_sessions = sum(1 for v in running_vms for s in v.sessions if s.status == "idle")
    shell_sessions = sum(1 for v in running_vms for s in v.sessions if s.status == "shell")

    lines.append("")
    lines.append(f"Running VMs: {len(running_vms)}")
    lines.append(f"Total sessions: {total_sessions}")
    lines.append(f"Active: {active_sessions}  Idle: {idle_sessions}  Dead: {shell_sessions}")
    if not skip_adopt:
        lines.append(f"Adopted: {adopted_count}")

    # Build flat session list with decisions
    rows: list[dict] = []
    for vm in sorted(running_vms, key=lambda v: v.name):
        for sess in vm.sessions:
            d = None
            for dd in decisions:
                if dd["vm"] == vm.name and dd["session"] == sess.session_name:
                    d = dd
                    break

            display_status = sess.status
            if sess.status == "shell" and getattr(sess, "agent_alive", False):
                display_status = "suspended"

            icon = {
                "thinking": "~",
                "running": ">",
                "idle": ".",
                "shell": "X",
                "suspended": "Z",
                "error": "!",
                "completed": "+",
                "waiting_input": "?",
                "unknown": "-",
            }.get(display_status, "-")

            action = d.get("action", "?") if d and "error" not in d else ("ERR" if d else "?")
            conf = d.get("confidence", 0) if d and "error" not in d else 0
            reasoning = ""
            input_text = ""
            if d and "error" not in d:
                reasoning = d.get("reasoning", "")
                input_text = d.get("input_text", "")
            elif d:
                reasoning = d.get("error", "")

            rows.append(
                {
                    "vm": vm.name,
                    "session": sess.session_name,
                    "icon": icon,
                    "status": display_status,
                    "branch": sess.branch or "",
                    "action": action,
                    "conf": conf,
                    "summary": reasoning,
                    "input": input_text,
                    "project": d.get("project", "") if d else "",
                    "objectives": d.get("objectives", []) if d else [],
                }
            )

    # Table -- status + action
    lines.append("")
    lines.append(f"  {'VM':12s} {'Session':22s} {'Status':10s} {'Action':15s} {'Conf':>5s}")
    lines.append("  " + "-" * 68)

    for r in rows:
        conf_str = f"{r['conf']:.0%}" if r["conf"] else ""
        lines.append(
            f"  {r['vm']:12s} [{r['icon']}] {r['session']:18s} "
            f"{r['status']:10s} {r['action']:15s} {conf_str:>5s}"
        )

    # Decision counts
    lines.append("")
    action_counts: dict[str, int] = {}
    for r in rows:
        action_counts[r["action"]] = action_counts.get(r["action"], 0) + 1
    counts_str = "  ".join(f"{a}: {c}" for a, c in sorted(action_counts.items()))
    lines.append(f"  Decisions: {counts_str}")

    # Group by project (if decisions carry project info)
    project_rows: dict[str, list[dict]] = {}
    unassigned_rows: list[dict] = []
    for r in rows:
        proj = r.get("project", "")
        if proj:
            project_rows.setdefault(proj, []).append(r)
        else:
            unassigned_rows.append(r)

    if project_rows:
        lines.append("")
        lines.append("--- By Project ---")
        for proj_name, proj_sessions in sorted(project_rows.items()):
            objectives = proj_sessions[0].get("objectives", [])
            lines.append(f"\n  [{proj_name}]")
            if objectives:
                for o in objectives:
                    lines.append(f"    objective #{o['number']}: {o['title']}")
            for r in proj_sessions:
                lines.append(f"    {r['vm']}/{r['session']} [{r['status']}] -> {r['action']}")
        if unassigned_rows:
            lines.append("\n  [unassigned]")
            for r in unassigned_rows:
                lines.append(f"    {r['vm']}/{r['session']} [{r['status']}] -> {r['action']}")

    # Session summaries (separate section)
    sessions_with_summary = [r for r in rows if r["summary"]]
    if sessions_with_summary:
        lines.append("")
        lines.append("--- Session Summaries ---")
        for r in sessions_with_summary:
            lines.append(f"  {r['vm']}/{r['session']}:")
            lines.append(f"    {r['summary'][:140]}")
            if r["input"]:
                lines.append(f'    >> "{r["input"][:120]}"')
            lines.append("")

    # Actionable follow-up commands
    actionable = [r for r in rows if r["action"] in ("send_input", "restart")]
    completable = [r for r in rows if r["action"] == "mark_complete"]
    dead = [r for r in rows if r["status"] in ("shell", "error")]

    lines.append("")
    lines.append("--- Next Steps ---")

    if actionable:
        lines.append("")
        lines.append("  # Send next command to all sessions:")
        lines.append("  fleet advance")
        lines.append("")
        lines.append("  # Review each action before executing:")
        lines.append("  fleet advance --confirm")

        for r in actionable:
            lines.append("")
            lines.append(f"  # Advance {r['vm']}/{r['session']} only:")
            lines.append(f"  fleet advance --session {r['vm']}:{r['session']}")
            if r["input"]:
                lines.append(f'  #   >> "{r["input"][:90]}"')

    if completable:
        lines.append("")
        for r in completable:
            lines.append(f"  # {r['vm']}/{r['session']} is done -- mark complete")

    if dead:
        lines.append("")
        for r in dead:
            lines.append(f"  # {r['vm']}/{r['session']} is dead -- inspect:")
            lines.append(f"  fleet watch {r['vm']} {r['session']}")

    if not actionable and not completable and not dead:
        lines.append("")
        lines.append("  All sessions are active -- no actions needed.")

    # Always show general hints
    lines.append("")
    lines.append("  # Other useful commands:")
    lines.append("  fleet advance                            # Send next command to all sessions")
    lines.append("  fleet advance --session <vm>:<session>   # Advance one session")
    lines.append("  fleet scout --session <vm>:<session>     # Scout one session")
    lines.append("  fleet watch <vm> <session>               # Live terminal snapshot")
    lines.append("  fleet status                             # Quick fleet overview")

    return "\n".join(lines)


@log_call
def _format_advance_report_legacy(
    decisions: list[dict],
    executed: list[dict],
) -> str:
    """Format the advance report showing what was decided and executed (legacy format).

    Args:
        decisions: List of decision dicts from reasoning phase.
        executed: List of execution result dicts (vm, session, action, executed, error).

    Returns:
        Formatted plain text report string.
    """
    lines: list[str] = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("FLEET ADVANCE REPORT")
    lines.append("=" * 60)

    lines.append("")
    lines.append(f"Sessions analyzed: {len(decisions)}")

    action_counts: dict[str, int] = {}
    for d in decisions:
        action = d.get("action", "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
    for action, count in sorted(action_counts.items()):
        lines.append(f"  {action}: {count}")

    if executed:
        lines.append("")
        lines.append("--- Actions Executed ---")
        for ex in executed:
            status = "OK" if ex.get("executed") else "SKIPPED"
            if ex.get("error"):
                status = "ERROR"
            lines.append(f"  [{status}] {ex['vm']}/{ex['session']}: {ex['action']}")
            if ex.get("input_text"):
                lines.append(f"    Input: {ex['input_text'][:80]}")
            if ex.get("error"):
                lines.append(f"    Error: {ex['error'][:80]}")
            if ex.get("reasoning"):
                lines.append(f"    Reason: {ex['reasoning'][:100]}")

    return "\n".join(lines)
