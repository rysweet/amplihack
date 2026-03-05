---
name: fleet
description: |
  Fleet management commands for multi-VM coding agent orchestration.
  Invoked as `/fleet <command>`. Available commands: sweep, advance.
  Use when: user asks about fleet status, agent progress, wants to scan
  sessions, advance the fleet, or says "what are my agents doing".
---

# /fleet

Fleet management skill. Invoke as `/fleet <command>`.

## Commands

### /fleet sweep

Discover sessions, adopt them, run dry-run reasoning, show report. **Read-only — no actions executed.**

```bash
fleet sweep [--vm VM] [--skip-adopt] [--save PATH]
```

### /fleet advance

Discover sessions, reason, and **execute** admiral decisions (send input, restart agents).

```bash
fleet advance [--vm VM] [--confirm] [--save PATH]
```

Both commands require `ANTHROPIC_API_KEY`.

## Quick Reference

| Intent | Command |
|--------|---------|
| "What are my agents doing?" | `fleet sweep` |
| "Send next steps to sessions" | `fleet advance` |
| "Advance but let me review each" | `fleet advance --confirm` |
| "Just scan one VM" | `fleet sweep --vm dev` |

## Actions

| Action | sweep | advance |
|--------|-------|---------|
| **wait** | Reported | No-op |
| **send_input** | Reported | Types into tmux pane |
| **restart** | Reported | Ctrl-C + re-runs last cmd |
| **escalate** | Reported | No-op (flagged for human) |

## Safety (advance only)

- Confidence < 60% suppresses `send_input`
- Confidence < 80% suppresses `restart`
- Dangerous input patterns blocked
- `--confirm` prompts before each action

## How to Run

Execute the command via Bash. Example:

```bash
fleet sweep --skip-adopt
fleet advance --confirm --save /tmp/advance.json
```
