---
name: fleet-sweep
description: |
  Fleet overview and admiral control. Two commands:
  - `fleet sweep`: Dry-run — discover, adopt, reason, show report (safe, read-only)
  - `fleet advance`: Live — reason and EXECUTE actions on sessions (sends input, restarts)
  Use when: user asks what agents are doing, wants fleet status, says "sweep",
  "advance the fleet", "send next steps", or "what are my agents doing".
---

# Fleet Sweep & Advance

Two commands for fleet-wide session management:
- **sweep** — Read-only scan with dry-run reasoning (safe)
- **advance** — Live execution of admiral decisions (sends input, restarts agents)

## When to Use

| User says | Command |
|-----------|---------|
| "what are my agents doing?" | `fleet sweep` |
| "scan the fleet" / "fleet status" | `fleet sweep` |
| "advance the fleet" / "send next steps" | `fleet advance` |
| "have the admiral act on sessions" | `fleet advance` |
| "nudge the stuck agents" | `fleet advance --confirm` |

## fleet sweep (dry-run)

```bash
fleet sweep [OPTIONS]
  --vm VM_NAME       Filter to a single VM
  --skip-adopt       Skip adoption, just discover and reason
  --save PATH        Save JSON report to file
```

Safe, read-only. Shows what the admiral *would* do without acting.
Works without `ANTHROPIC_API_KEY` (shows session states only).

## fleet advance (live)

```bash
fleet advance [OPTIONS]
  --vm VM_NAME       Filter to a single VM
  --confirm          Prompt before each action
  --save PATH        Save JSON report to file
```

**Requires `ANTHROPIC_API_KEY`**. Actually executes admiral decisions:
- `send_input` — types text into the session's tmux pane
- `restart` — sends Ctrl-C and re-runs last command
- `wait` / `escalate` / `mark_complete` — no-op (logged only)

Safety enforced by SessionReasoner:
- Confidence < 60% suppresses `send_input`
- Confidence < 80% suppresses `restart`
- Dangerous input patterns are blocked and escalated

### Examples

```bash
# Let the admiral act on all sessions
fleet advance

# Review each action before executing
fleet advance --confirm

# Advance a single VM only
fleet advance --vm dev

# Save execution log
fleet advance --save /tmp/advance-log.json
```

## Interpreting Actions

| Action | What happens |
|--------|-------------|
| **wait** | No-op. Agent is working fine. |
| **send_input** | Text typed into the tmux pane via `tmux send-keys`. |
| **restart** | Ctrl-C twice, then re-runs last command (`!!`). |
| **escalate** | No-op. Flagged for human review. |
| **mark_complete** | No-op. Task recorded as done. |

## Implementation

Both commands are in `src/amplihack/fleet/_cli_session_ops.py`:
- `fleet sweep` uses `SessionReasoner(dry_run=True)`
- `fleet advance` uses `SessionReasoner(dry_run=False)`
- Reports: `format_sweep_report()` and `format_advance_report()`
