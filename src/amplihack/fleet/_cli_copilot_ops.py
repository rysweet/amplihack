"""Copilot operations CLI commands -- copilot-status, copilot-log.

Registered by _cli_commands.register_commands().
This module should NOT be imported directly by external code.
"""

from __future__ import annotations

import json

import click


def register_copilot_ops(fleet_cli: click.Group) -> None:
    """Register copilot operation commands (copilot-status, copilot-log).

    All module-level references (COPILOT_LOCK_DIR, COPILOT_LOG_DIR) are
    read from _cli_commands at call time so tests can patch them.
    """
    import amplihack.fleet._cli_commands as _cmd

    # ------------------------------------------------------------------
    # fleet copilot-status
    # ------------------------------------------------------------------

    @fleet_cli.command("copilot-status")
    def copilot_status():
        """Show current copilot lock/goal state."""
        lock_dir = _cmd.COPILOT_LOCK_DIR if _cmd.COPILOT_LOCK_DIR is not None else _cmd._copilot_lock_dir()
        lock_file = lock_dir / ".lock_active"
        goal_file = lock_dir / ".lock_goal"

        if not lock_file.exists():
            click.echo("Copilot: not active")
            return

        if goal_file.exists():
            goal_text = goal_file.read_text().strip()
            click.echo(f"Copilot: active")
            click.echo(f"Goal: {goal_text}")
        else:
            click.echo("Copilot: active (no goal)")

    # ------------------------------------------------------------------
    # fleet copilot-log
    # ------------------------------------------------------------------

    @fleet_cli.command("copilot-log")
    @click.option("--tail", default=0, type=int, help="Show last N entries only")
    def copilot_log(tail):
        """Show copilot decision history."""
        log_dir = _cmd.COPILOT_LOG_DIR if _cmd.COPILOT_LOG_DIR is not None else _cmd._copilot_log_dir()
        decisions_file = log_dir / "decisions.jsonl"

        if not decisions_file.exists():
            click.echo("No decisions recorded.")
            return

        text = decisions_file.read_text().strip()
        if not text:
            click.echo("No decisions recorded.")
            return

        lines = text.splitlines()
        entries = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    click.echo("  (skipped malformed entry)", err=True)

        if not entries:
            click.echo("No decisions recorded.")
            return

        if tail > 0:
            entries = entries[-tail:]

        for entry in entries:
            ts = entry.get("timestamp", "?")
            action = entry.get("action", "?")
            reasoning = entry.get("reasoning", "")
            confidence = entry.get("confidence", "")
            click.echo(f"[{ts}] {action} (confidence={confidence})")
            if reasoning:
                click.echo(f"  {reasoning}")
