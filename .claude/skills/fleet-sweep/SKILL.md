---
name: fleet-sweep
description: |
  Discover all fleet VMs and sessions, adopt them, run dry-run admiral reasoning,
  and display a status report. Use when: the user asks what their agents are doing,
  wants a fleet overview, or says "sweep", "scan fleet", "fleet report", "fleet status
  with reasoning", or "what are my agents doing".
---

# Fleet Sweep

Discover, adopt, reason about, and report on all fleet sessions in one command.

## When to Use

- User asks "what are my agents doing?"
- User wants a fleet-wide status report with reasoning
- User says "sweep the fleet" or "scan all sessions"
- User wants to adopt existing sessions and see what the admiral would do

## How to Run

Execute via Bash:

```bash
fleet sweep [OPTIONS]
```

### Options

| Flag | Description |
|------|-------------|
| `--vm VM_NAME` | Filter to a single VM (default: all) |
| `--skip-adopt` | Skip adoption, just discover and reason |
| `--save PATH` | Save JSON report to a file |

### Examples

```bash
# Full sweep: discover, adopt, reason, report
fleet sweep

# Quick scan without adopting sessions
fleet sweep --skip-adopt

# Sweep a single VM
fleet sweep --vm dev

# Save results for later analysis
fleet sweep --save /tmp/fleet-report.json
```

## What It Does

1. **Discover** -- Polls all VMs through Bastion SSH, finds tmux sessions
2. **Adopt** -- Brings discovered sessions under fleet task management
3. **Reason** -- Runs dry-run admiral reasoning per session (requires `ANTHROPIC_API_KEY`)
4. **Report** -- Displays plain text summary with per-session status, actions, and reasoning

If `ANTHROPIC_API_KEY` is not set, the report shows session states without LLM reasoning.

## Interpreting the Report

- **wait**: Agent is working normally, no intervention needed
- **send_input**: Admiral suggests sending input to the session
- **escalate**: Session needs human attention
- **mark_complete**: Agent finished its task
- **N/A (no API key)**: LLM reasoning was skipped

## Implementation

This skill runs the `fleet sweep` CLI command defined in
`src/amplihack/fleet/_cli_session_ops.py`. It uses:

- `FleetTUI.refresh_all()` for discovery
- `SessionAdopter` for adoption
- `SessionReasoner(dry_run=True)` for reasoning
- `format_sweep_report()` for the text report
