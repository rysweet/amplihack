# Fleet Orchestration Architecture

## Problem

A developer manages multiple cloud VMs, each running multiple tmux sessions
with coding agents (Claude Code, GitHub Copilot, Amplifier). Today this
requires manual auth setup, agent startup, monitoring, and priority management
across all sessions.

## Solution: Fleet Admiral

A centralized admiral that manages agent sessions using a per-session
PERCEIVE->REASON->ACT->LEARN loop. The admiral reads each session's terminal
output and transcript, uses an LLM to decide what action to take, and
injects keystrokes via tmux to continue work.

```
+--------------------------------------------------------------+
|                     FLEET ADMIRAL                            |
|                                                               |
|  For each session:                                            |
|    PERCEIVE -> REASON -> ACT -> LEARN                         |
|       |          |       |      |                             |
|    tmux capture  LLM   tmux   record                          |
|    JSONL logs   decide  send   outcome                        |
|    health check  what   keys                                  |
|                  to type                                       |
+----------------------------+---------------------------------+
                             | azlin + Bastion tunnels
               +-------------+-------------+
               v             v             v
           [VM-1]        [VM-2]        [VM-3]
           tmux A,B      tmux C,D      tmux E,F
```

## Per-Session Reasoning Loop

For each tmux session on each cycle:

1. **PERCEIVE** (single SSH call): Capture tmux pane, read working directory,
   git branch, JSONL transcript summary, process health
2. **REASON**: Feed context to LLM backend (Claude or Copilot SDK) which
   returns a decision: send_input, wait, escalate, mark_complete, or restart
3. **ACT**: Execute decision -- inject keystrokes via `tmux send-keys` or
   show reasoning in dry-run mode
4. **LEARN**: Record decision and outcome for future reference

### Thinking Detection

The admiral detects when an agent is actively thinking/processing and
does NOT interrupt. Indicators:

| Agent       | Thinking Indicator | Meaning                      |
| ----------- | ------------------ | ---------------------------- |
| Claude Code | `●` prefix         | Tool call active             |
| Claude Code | `⎿` prefix         | Streaming tool output        |
| Claude Code | `✻ Sauteed for`    | Processing complete (timing) |
| Copilot     | `Thinking...`      | LLM call in flight           |
| Copilot     | `Running:`         | Tool execution               |

When thinking is detected, the admiral skips the LLM reasoning call
entirely (fast-path WAIT) to save cost.

### Safety Mechanisms

**Dangerous input blocklist**: The session reasoner blocks commands matching
destructive patterns (`rm -rf`, `git push --force`, `DROP TABLE`, fork bombs,
etc.) regardless of LLM confidence.

**Confidence thresholds**: Actions require minimum confidence of 0.6 to execute.
Restart actions require 0.8. Below-threshold decisions are logged but not acted on.

## Modules

The fleet package contains 54 source files (51 functional modules, 1 package
init, 1 CLI entry point, 1 `__main__`):

### Core Loop

| Module                   | File                        | Purpose                                                                                                                                                                                                                                                                             |
| ------------------------ | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fleet_admiral`          | `fleet_admiral.py`          | Central control plane. Orchestrates the PERCEIVE->REASON->ACT->LEARN loop across all VMs. Manages session lifecycle (start, stop, reassign, mark complete).                                                                                                                         |
| `fleet_session_reasoner` | `fleet_session_reasoner.py` | Per-session LLM reasoning. Captures tmux pane + JSONL logs, sends to Anthropic SDK, parses structured decisions. Implements dry-run mode, dangerous input blocking, and confidence thresholds.                                                                                      |
| `fleet_reasoners`        | `fleet_reasoners.py`        | Composable reasoning chain with four pluggable reasoners: LifecycleReasoner (completions, failures, stuck detection), PreemptionReasoner (emergency priority escalation), CoordinationReasoner (inter-agent context sharing), BatchAssignReasoner (context-aware batch assignment). |

### Perception Layer

| Module                | File                     | Purpose                                                                                                                                                                                 |
| --------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fleet_state`         | `fleet_state.py`         | Real-time VM and session inventory. Polls azlin and tmux to maintain current fleet state. Provides `FleetState`, `VMInfo`, `TmuxSessionInfo`, `AgentStatus`.                            |
| `fleet_observer`      | `fleet_observer.py`      | Pattern-based agent state classification via tmux capture-pane. Detects running, idle, completed, stuck, error, and waiting_input states using regex patterns.                          |
| `fleet_health`        | `fleet_health.py`        | Process-level health monitoring beyond tmux. Checks agent processes (pgrep), heartbeat files, memory usage, disk usage, and load average on each VM.                                    |
| `fleet_logs`          | `fleet_logs.py`          | Claude Code JSONL transcript reader. Extracts tasks, tool usage, PRs created, errors, token counts, and session duration from remote JSONL logs. Powers the LEARN phase.                |
| `transcript_analyzer` | `transcript_analyzer.py` | Cross-session transcript analysis. Gathers JSONL files from local machine and remote VMs, analyzes tool usage frequency, strategy patterns, agent invocations, and workflow compliance. |
| `_vm_discovery`       | `_vm_discovery.py`       | VM discovery from azlin list, resource group config, session dedup.                                                                                                                     |

### Session Management

| Module               | File                    | Purpose                                                                                                                                                                                                             |
| -------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fleet_adopt`        | `fleet_adopt.py`        | Bring existing sessions under management. Discovers tmux sessions via SSH, infers repo/branch/agent from pane content and git state, creates tracking records. Non-disruptive: observes without injecting commands. |
| `fleet_tasks`        | `fleet_tasks.py`        | Priority-ordered task queue with JSON persistence. Manages task lifecycle: queued -> assigned -> running -> completed/failed. Supports priority levels (critical, high, medium, low).                               |
| `fleet_auth`         | `fleet_auth.py`         | Auth propagation with multi-GitHub identity support. Copies GitHub CLI, Azure CLI, and Claude API credentials to target VMs. Uses azlin cp for secure transfer. Supports per-VM GitHub account switching.           |
| `fleet_setup`        | `fleet_setup.py`        | Automated workspace preparation on remote VMs. Clones repositories, creates working branches, detects project type, installs dependencies, and verifies builds.                                                     |
| `_session_lifecycle` | `_session_lifecycle.py` | Fleet session lifecycle (start, stop, scout, advance, persist).                                                                                                                                                     |

### Tracking and Knowledge

| Module            | File                 | Purpose                                                                                                                                                                                                      |
| ----------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `fleet_results`   | `fleet_results.py`   | Structured outcome collection for the LEARN phase. Stores PR URLs, commit SHAs, test results, error summaries, and timing data as JSON per task.                                                             |
| `fleet_dashboard` | `fleet_dashboard.py` | Meta-project tracking. Fleet-wide metrics: project count, agent utilization, cost estimates per VM, PR counts, completion rates, time-to-completion trends.                                                  |
| `fleet_graph`     | `fleet_graph.py`     | Lightweight JSON knowledge graph. Tracks relationships between projects, tasks, agents, VMs, and PRs. Detects task dependencies and prevents conflicting file modifications.                                 |
| `_projects`       | `_projects.py`       | Project and objective tracking via `projects.toml`. `Project` dataclass with objectives (GitHub issues labeled `fleet-objective`). Read/write/merge functions. Scout enriches sessions with project context. |

### User Interface

| Module                   | File                        | Purpose                                                                                                                                                                                                                                                                                                                                         |
| ------------------------ | --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fleet_tui`              | `fleet_tui.py`              | Standard-library terminal dashboard. Uses ANSI escape codes for rendering, `select()` for input, `termios` for raw mode. `refresh_all()` uses sequential VM polling via azlin. Session discovery from azlin list (no SSH). Pane capture via sequential SSH. Caches Bastion tunnels for reuse. No external dependencies beyond standard library. |
| `fleet_tui_dashboard`    | `fleet_tui_dashboard.py`    | Interactive Textual-based dashboard (requires `amplihack[fleet-tui]`). Three-tab interface: Fleet Overview (session table + preview), Session Detail (full tmux capture + admiral proposal), Action Editor (edit and apply actions). Auto-refreshes via background workers.                                                                     |
| `fleet_cli`              | `fleet_cli.py`              | Click-based CLI entry point. Registers all subcommands (status, dashboard, tui, add-task, start, run-once, watch, snapshot, adopt, report, auth, observe, dry-run, graph, queue). Default command (no subcommand) launches the TUI dashboard.                                                                                                   |
| `fleet_copilot`          | `fleet_copilot.py`          | Local session co-pilot, watches JSONL transcripts, suggests next actions.                                                                                                                                                                                                                                                                       |
| `_cli_formatters_legacy` | `_cli_formatters_legacy.py` | Legacy scout/advance report formatters.                                                                                                                                                                                                                                                                                                         |

### Package

| Module     | File          | Purpose                                                                                                                                                                                                                                                                                                        |
| ---------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `__init__` | `__init__.py` | Package init. Exports public API: FleetAdmiral (with FleetDirector backward-compat alias), FleetState, TaskQueue, AuthPropagator, GitHubIdentity, FleetObserver, FleetDashboard, ResultCollector, HealthChecker, RepoSetup, SessionAdopter, FleetGraph, ReasonerChain, LogReader, and associated data classes. |

## LLM Backend Protocol

The session reasoner uses a pluggable LLM backend:

```python
class LLMBackend(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...

class AnthropicBackend(LLMBackend): ...  # Claude SDK
```

New backends can be added by implementing the `complete` method.

## Key CLI Commands

```bash
amplihack fleet                 # Launch interactive TUI dashboard
amplihack fleet status          # VM/session inventory
amplihack fleet dry-run         # Show what admiral would do (no action)
amplihack fleet dry-run --vm devo   # Dry-run for specific VM
amplihack fleet watch vm session    # Live snapshot of remote session
amplihack fleet snapshot        # Capture all sessions at once
amplihack fleet observe vm      # Pattern-based session classification
amplihack fleet adopt vm        # Bring existing sessions under management
amplihack fleet start           # Start autonomous admiral loop
amplihack fleet start --adopt   # Start admiral, adopt all at startup
amplihack fleet run-once        # Single PERCEIVE->REASON->ACT cycle
amplihack fleet add-task "prompt"   # Queue a task for the fleet
amplihack fleet queue           # Show task queue
amplihack fleet dashboard       # Meta-project tracking view
amplihack fleet auth vm         # Propagate auth tokens to a VM
amplihack fleet graph           # Show knowledge graph summary
amplihack fleet report          # Generate fleet status report
amplihack fleet project add <url>  # Register a project for tracking
amplihack fleet project list       # List registered projects
amplihack fleet project add-issue <proj> <num>  # Track issue as objective
amplihack fleet project track-issue <proj>      # Sync objectives from GitHub
amplihack fleet project remove <name>           # Remove a project
```

### Session Targeting

Use `--session vm:session` to target a specific session across scout, advance,
and dry-run commands:

```bash
amplihack fleet scout --session dev:cybergym-intg
amplihack fleet advance --session dev:parallel-deploy-wk
```

### Default LLM Configuration

| Setting               | Value                    |
| --------------------- | ------------------------ |
| Model                 | `claude-opus-4-6`        |
| Max output tokens     | 128,000 (reasoning JSON) |
| Max transcript tokens | 128,000 (input context)  |

These defaults are defined in `_constants.py` and can be overridden via the
`--backend` flag or environment variables.

## Session Adoption

Users can start sessions manually, then hand them to the admiral:

```bash
amplihack fleet adopt devo          # Discovers sessions, infers context, begins tracking
amplihack fleet start --adopt       # Adopt all managed VMs at startup
```

The admiral discovers existing tmux sessions via SSH, infers what they're
working on (from tmux pane content, git state, and JSONL logs), creates
tracking records, and begins observing without disruption.

## Data Persistence

Fleet state is stored under `~/.amplihack/fleet/`:

| File              | Content                                          |
| ----------------- | ------------------------------------------------ |
| `task_queue.json` | Priority-ordered task queue                      |
| `dashboard.json`  | Project metrics and cost tracking                |
| `graph.json`      | Knowledge graph (projects, tasks, VMs, PRs)      |
| `last_scout.json` | Last scout results for incremental mode          |
| `projects.toml`   | Project registry with objectives (GitHub issues) |
| `logs/`           | Admiral decision logs                            |

## Constraints

- Azure Bastion tunnels: ~30s per connection setup
- No public IPs allowed
- Auth propagation via shared NFS storage (azlin blocks credential file copies)
- No ML -- rules and LLM reasoning only
