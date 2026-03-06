---
name: fleet
description: |
  Fleet orchestration for distributed coding agents across Azure VMs.
  Invoked as `/fleet <command>`. Covers all fleet operations: status, scout,
  advance, adopt, watch, snapshot, dry-run, start, add-task, queue, auth,
  dashboard, tui, and more. Use when: user mentions fleet, agents, VMs,
  sessions, or asks "what are my agents doing".
---

# /fleet

Fleet orchestration — manage coding agents (Claude Code, Copilot, Amplifier) running across multiple Azure VMs via azlin.

Invoke as `/fleet <command>` or just describe what you want and Claude will pick the right command.

## All Commands

### Status & Monitoring

| Command | What it does |
|---------|-------------|
| `fleet status` | Quick text overview of all VMs and sessions |
| `fleet scout` | Discover, adopt, dry-run reason, show report |
| `fleet snapshot` | Point-in-time capture of all managed sessions |
| `fleet watch <vm> <session>` | Live snapshot of a single session |
| `fleet observe <vm>` | Observe sessions with pattern classification |
| `fleet tui` | Interactive Textual TUI dashboard |

### Admiral Control

| Command | What it does |
|---------|-------------|
| `fleet advance` | **LIVE** — reason and execute actions on sessions |
| `fleet dry-run` | Show what the admiral would do (no action) |
| `fleet run-once` | Single PERCEIVE->REASON->ACT cycle |
| `fleet start` | Run autonomous admiral loop |

### Session Management

| Command | What it does |
|---------|-------------|
| `fleet adopt <vm>` | Bring existing tmux sessions under management |
| `fleet auth <vm>` | Propagate auth tokens (GitHub, Azure, Claude) |

### Task Management

| Command | What it does |
|---------|-------------|
| `fleet add-task "prompt"` | Queue work for the fleet |
| `fleet queue` | Show task queue |
| `fleet dashboard` | Project-level tracking |
| `fleet report` | Generate fleet status report |

### Projects & Knowledge

| Command | What it does |
|---------|-------------|
| `fleet project add/list/remove` | Manage fleet projects |
| `fleet graph` | Fleet knowledge graph summary |

### Co-Pilot

| Command | What it does |
|---------|-------------|
| `fleet copilot-status` | Show copilot lock/goal state |
| `fleet copilot-log` | Show copilot decision history |

## Quick Reference

| User says | Command |
|-----------|---------|
| "What are my agents doing?" | `fleet scout` |
| "Show me the fleet" | `fleet status` |
| "Send next steps to all sessions" | `fleet advance` |
| "Advance but let me review each" | `fleet advance --confirm` |
| "Watch what dev/cybergym is doing" | `fleet watch dev cybergym` |
| "Add auth to the new VM" | `fleet auth <vm>` |
| "Queue this task for the fleet" | `fleet add-task "prompt"` |
| "Open the dashboard" | `fleet tui` |

## Key Options

```
fleet scout   [--session vm:session] [--vm VM] [--skip-adopt] [--save PATH]
fleet advance [--session vm:session] [--vm VM] [--confirm] [--save PATH]
fleet dry-run [--vm VM ...] [--backend auto|anthropic|copilot|litellm]
fleet adopt   <vm> [--sessions s1 s2]
fleet watch   <vm> <session> [--lines 30]
fleet auth    <vm> [--services github azure claude]
fleet add-task "prompt" [--priority high] [--repo URL]
fleet start   [--interval 300] [--max-cycles 10]
```

## Environment

| Variable | Required for |
|----------|-------------|
| `AZLIN_PATH` | All commands (auto-detected if azlin on PATH) |
| `ANTHROPIC_API_KEY` | scout, advance, dry-run, run-once, start |

## Admiral Configuration

- **Model**: Claude Opus 4.6 (`claude-opus-4-6`)
- **Max output tokens**: 128,000
- **Context gathered per session**: full tmux scrollback + first 50 & last 200 transcript messages
- **Safety**: 57 dangerous-input patterns blocked, confidence thresholds (60% send_input, 80% restart)
- **Docs**: `docs/fleet-orchestration/ADMIRAL_REASONING.md`

## Status Icons

| Icon | Status | Meaning |
|------|--------|---------|
| `[~]` | thinking | Agent is actively processing |
| `[>]` | running | Agent producing output |
| `[.]` | idle | Agent at prompt, waiting for direction |
| `[X]` | shell (dead agent) | No agent detected in this session |
| `[Z]` | suspended | Agent backgrounded but alive |
| `[!]` | error | Error detected in session output |
| `[+]` | completed | Agent finished its task |
| `[?]` | waiting input | Agent asked a question, awaiting response |

## How to Run

Execute via Bash:

```bash
fleet <command> [options]
```

## Presenting Results

After running `fleet scout` or `fleet advance`, present the output to the user as:

1. **Summary table** — reformat the CLI output into a clean markdown table with columns:
   VM | Session | Status | Action | Conf | Summary

2. **Proposed inputs** — for any `send_input` decisions, show what the admiral wants to send

3. **Follow-up commands** — always end with the actionable next steps from the report:
   - `fleet advance` to send next command to all sessions
   - `fleet advance --confirm` to review each before executing
   - `fleet advance --session vm:session` to advance one specific session
   - `fleet watch <vm> <session>` to inspect specific sessions
