# Fleet Orchestration Tutorial

Manage coding agents (Claude Code, GitHub Copilot, Amplifier) running across multiple Azure VMs from a single terminal.

## Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [First Run](#first-run)
- [The Dashboard](#the-dashboard)
- [Observing Your Fleet](#observing-your-fleet)
- [Adopting Existing Sessions](#adopting-existing-sessions)
- [The Director: Dry-Run First](#the-director-dry-run-first)
- [Running the Director Live](#running-the-director-live)
- [Task Management](#task-management)
- [Environment Variables](#environment-variables)
- [Running in tmux](#running-in-tmux)

## Prerequisites

Before you begin, you need:

1. **azlin** installed and on your PATH. azlin manages SSH connections to Azure VMs through Bastion tunnels. See [github.com/rysweet/azlin](https://github.com/rysweet/azlin) for installation.

2. **Azure VMs provisioned** and reachable via azlin. Verify with:

   ```bash
   azlin list
   ```

   You should see your VMs listed with their status.

3. **Coding agents running in tmux** on those VMs. Each VM should have one or more tmux sessions with Claude Code, Copilot, or Amplifier running inside them. The fleet director observes and manages these sessions.

4. **An Anthropic API key** set in your environment. The director uses Claude to reason about what each agent session needs:

   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

## Installation

Install amplihack with the TUI extra for the interactive dashboard:

```bash
pip install amplihack[fleet-tui]
```

Or run directly from the repository without installing:

```bash
uvx --from "git+https://github.com/rysweet/amplihack@feat/fleet-orchestration[fleet-tui]" amplihack fleet
```

The `fleet-tui` extra adds [Textual](https://textual.textualize.io/) for the interactive terminal dashboard. Without it, all text-based commands (`status`, `dry-run`, `watch`) still work.

## First Run

Verify that amplihack can see your VMs:

```bash
amplihack fleet status
```

This runs `azlin list` under the hood and displays each VM with its tmux sessions and detected agent states. If you see your VMs listed, the fleet module is working.

## The Dashboard

### Launching the TUI

Running `amplihack fleet` with no subcommand launches the interactive Textual dashboard:

```bash
amplihack fleet
```

If Textual is not installed, you get a helpful fallback message pointing you to text-based alternatives.

You can also launch explicitly:

```bash
amplihack fleet tui
amplihack fleet tui --interval 15   # Faster refresh (default: 30s)
```

### Navigation

| Key       | Action                                      |
|-----------|---------------------------------------------|
| Arrow keys | Move between sessions in the fleet table   |
| Enter     | Dive into Session Detail for selected row    |
| Escape    | Go back to Fleet Overview                    |
| e         | Open Action Editor for the selected session  |
| a         | Apply the director's proposed action         |
| d         | Run dry-run reasoning for selected session   |
| r         | Force refresh all sessions                   |
| q         | Quit the dashboard                           |

### Three Tabs

1. **Fleet Overview** -- The main view. A table of all sessions across all VMs with a preview pane on the right showing the last few lines of terminal output for the selected session.

2. **Session Detail** -- Deep view of a single session. Shows the full tmux capture (what the agent's terminal looks like right now) and the director's proposed action with its reasoning.

3. **Action Editor** -- Edit and override the director's proposed action before applying it. Choose an action type (send_input, wait, escalate, mark_complete, restart) and modify the input text.

### Status Icons

The dashboard uses icons to show session state at a glance:

| Icon | Status | Meaning |
|------|--------|---------|
| `◉` (green) | thinking / working / running | Agent is actively processing |
| `◉` (green) | waiting_input | Agent asked a question, awaiting response |
| `●` (yellow) | idle | Session exists but agent is not actively working |
| `○` (dim) | shell / empty | No agent detected in this session |
| `✗` (red) | error | Error detected in session output |
| `✓` (blue) | completed | Agent finished its task (PR created, workflow complete) |

## Observing Your Fleet

Four commands give you visibility into what your agents are doing, without changing anything.

### Quick Text Summary

```bash
amplihack fleet status
```

Shows every VM, its region, tmux sessions, and detected agent state. Fast, no LLM calls.

### Watch a Single Session

```bash
amplihack fleet watch devo claude-session-1
```

Captures the last 30 lines of a specific tmux session on a specific VM. Like peeking over the agent's shoulder. Use `--lines 50` for more context.

### Snapshot All Sessions

```bash
amplihack fleet snapshot
```

Captures every session on every managed VM in one pass. Shows the last 3 lines of output per session with the observer's status classification.

### Observe with Pattern Classification

```bash
amplihack fleet observe devo
```

Runs the pattern-based observer on all sessions of a specific VM. Shows the detected status, confidence level, and which pattern matched. More detailed than `status` because it actually reads the terminal output.

## Adopting Existing Sessions

You do not need to start sessions through the fleet director. If you already have agents running in tmux sessions on your VMs (started manually or by another tool), you can bring them under fleet management.

### Adopt Sessions on a Single VM

```bash
amplihack fleet adopt devo
```

This connects to the VM, discovers all tmux sessions, and for each session:

1. Reads the tmux pane content to see what the agent is doing
2. Checks git state (repo, branch) in the working directory
3. Reads Claude Code JSONL logs if available
4. Creates a tracking record with inferred context
5. Begins observing without sending any commands

The output shows what was discovered:

```
Discovering sessions on devo...
Found 3 sessions:
  claude-session-1
    Repo: https://github.com/org/project
    Branch: feat/add-auth
    Agent: claude
  claude-session-2
    Repo: https://github.com/org/other-project
    Branch: fix/login-bug
    Agent: claude
  amplifier-session
    Agent: amplifier

Adopted 3 sessions:
  claude-session-1 -> task abc123
  claude-session-2 -> task def456
  amplifier-session -> task ghi789
```

### Adopt at Director Startup

```bash
amplihack fleet start --adopt
```

When starting the director, `--adopt` scans all managed VMs and brings existing sessions under management before beginning the autonomous loop.

### Adopt Specific Sessions

```bash
amplihack fleet adopt devo --sessions claude-session-1 --sessions claude-session-2
```

Only adopt named sessions, leaving others alone.

## The Director: Dry-Run First

The director is the autonomous reasoning engine. Before letting it act, use dry-run mode to see what it would do.

### Running a Dry-Run

```bash
amplihack fleet dry-run
```

For each session on each managed VM, the director:

1. **PERCEIVE**: Captures the tmux pane and reads JSONL transcript summaries via SSH
2. **REASON**: Sends the captured context to Claude, which decides what action to take
3. **Display**: Shows the full reasoning chain without executing anything

You can target specific VMs:

```bash
amplihack fleet dry-run --vm devo
amplihack fleet dry-run --vm devo --vm devi
```

And provide project priorities to guide decisions:

```bash
amplihack fleet dry-run --priorities "auth feature is highest priority, fix CI on project-x"
```

### What Dry-Run Shows

For each session, you see the director's decision:

- **Action**: `send_input`, `wait`, `escalate`, `mark_complete`, or `restart`
- **Confidence**: How sure the director is (0.0 to 1.0)
- **Reasoning**: Why it chose this action
- **Proposed input**: What it would type into the session (if `send_input`)

### Safety Mechanisms

The director has built-in safety at multiple levels:

**Thinking detection**: If an agent is actively processing (Claude Code shows `●` or `⎿`, Copilot shows `Thinking...`), the director skips the LLM call entirely and fast-paths to WAIT. It never interrupts a working agent.

**Confidence thresholds**: Actions below 0.6 confidence are not executed. Restart actions require 0.8 confidence.

**Dangerous input blocklist**: The director refuses to send commands matching dangerous patterns, regardless of confidence:

- `rm -rf`, `rm -r /`
- `git push --force`, `git push -f`
- `git reset --hard`
- `DROP TABLE`, `DROP DATABASE`
- Fork bombs and disk-destructive commands

## Running the Director Live

After reviewing dry-run output and confirming the director's reasoning looks sound:

```bash
amplihack fleet start
```

The director begins the autonomous loop: PERCEIVE, REASON, ACT, LEARN. It polls all sessions at a configurable interval, decides what each session needs, and acts.

### Controlling the Loop

```bash
amplihack fleet start --interval 30    # Poll every 30 seconds (default: 60)
amplihack fleet start --max-cycles 10  # Stop after 10 cycles
amplihack fleet start --adopt          # Adopt existing sessions first
```

Press `Ctrl+C` to stop the director gracefully.

### Single Cycle

Run one complete cycle without looping:

```bash
amplihack fleet run-once
```

Reports how many actions were taken and what they were. Useful for testing or manual orchestration.

## Task Management

The fleet has a priority-ordered task queue. Tasks describe work to be assigned to agent sessions.

### Adding Tasks

```bash
amplihack fleet add-task "Fix the authentication bug where JWT tokens expire too early" \
  --priority high \
  --repo https://github.com/org/project
```

Options:

| Flag | Values | Default | Purpose |
|------|--------|---------|---------|
| `--priority` | critical, high, medium, low | medium | Queue ordering |
| `--repo` | URL | (none) | Repository to clone on the target VM |
| `--agent` | claude, amplifier, copilot | claude | Which agent to use |
| `--mode` | auto, ultrathink | auto | Agent execution mode |
| `--max-turns` | integer | 20 | Maximum agent turns |
| `--protected` | flag | false | Deep work mode -- director will not preempt |

### Viewing the Queue

```bash
amplihack fleet queue
```

Shows all tasks sorted by priority with their status (queued, assigned, running, completed, failed).

### Project-Level Tracking

```bash
amplihack fleet dashboard
```

Shows fleet-wide metrics: active projects, agent utilization, cost estimates, PR counts, and task completion rates.

### Knowledge Graph

```bash
amplihack fleet graph
```

Shows the relationship graph between projects, tasks, agents, VMs, and PRs. Useful for understanding what depends on what.

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `AZLIN_PATH` | Path to the azlin binary | Auto-detected via `which azlin`, falls back to `/home/azureuser/src/azlin/.venv/bin/azlin` |
| `ANTHROPIC_API_KEY` | API key for Claude (required for dry-run and director reasoning) | (none -- must be set) |

## Running in tmux

The fleet dashboard is designed to run in its own tmux session so you can detach and reattach freely:

```bash
# Start the dashboard in a detached tmux session
tmux new-session -d -s fleet-dashboard "amplihack fleet"

# Attach anytime
tmux attach -t fleet-dashboard

# Detach without stopping: Ctrl+b, then d
```

For the director loop:

```bash
tmux new-session -d -s fleet-director "amplihack fleet start --adopt --interval 30"

# Check on it
tmux attach -t fleet-director
```

## Auth Propagation

If your VMs need authentication tokens (GitHub CLI, Azure CLI, Claude API key):

```bash
amplihack fleet auth devo
amplihack fleet auth devo --services github azure claude
```

This copies credential files to the target VM and verifies they work.

## Next Steps

- Read the [Architecture](./ARCHITECTURE.md) document to understand how the modules fit together
- Read the [Strategy Dictionary](../../src/amplihack/fleet/STRATEGY_DICTIONARY.md) to understand the director's 20 decision strategies
- Run `amplihack fleet --help` for the full command reference
