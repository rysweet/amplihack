# Fleet Orchestration Architecture

## Problem

A developer manages multiple cloud VMs, each running multiple tmux sessions
with coding agents (Claude Code, GitHub Copilot, Amplifier). Today this
requires manual auth setup, agent startup, monitoring, and priority management
across all sessions.

## Solution: Fleet Director

A centralized director that manages agent sessions using a per-session
PERCEIVE→REASON→ACT→LEARN loop. The director reads each session's terminal
output and transcript, uses an LLM to decide what action to take, and
injects keystrokes via tmux to continue work.

```
┌──────────────────────────────────────────────────────────┐
│                     FLEET DIRECTOR                        │
│                                                           │
│  For each session:                                        │
│    PERCEIVE → REASON → ACT → LEARN                        │
│       │          │       │      │                         │
│    tmux capture  LLM   tmux   record                      │
│    JSONL logs   decide  send   outcome                    │
│    health check  what   keys                              │
│                  to type                                   │
└───────────────────────────┬──────────────────────────────┘
                            │ azlin + Bastion tunnels
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          [VM-1]        [VM-2]        [VM-3]
          tmux A,B      tmux C,D      tmux E,F
```

## Per-Session Reasoning Loop

For each tmux session on each cycle:

1. **PERCEIVE** (single SSH call): Capture tmux pane, read working directory,
   git branch, JSONL transcript summary, process health
2. **REASON**: Feed context to LLM backend (Claude or Copilot SDK) which
   returns a decision: send_input, wait, escalate, mark_complete, or restart
3. **ACT**: Execute decision — inject keystrokes via `tmux send-keys` or
   show reasoning in dry-run mode
4. **LEARN**: Record decision and outcome for future reference

### Thinking Detection

The director detects when an agent is actively thinking/processing and
does NOT interrupt. Indicators:

| Agent | Thinking Indicator | Meaning |
|-------|-------------------|---------|
| Claude Code | `●` prefix | Tool call active |
| Claude Code | `⎿` prefix | Streaming tool output |
| Claude Code | `✻ Sautéed for` | Processing complete (timing) |
| Copilot | `Thinking...` | LLM call in flight |
| Copilot | `Running:` | Tool execution |

When thinking is detected, the director skips the LLM reasoning call
entirely (fast-path WAIT) to save cost.

## Modules

| Module | Purpose |
|--------|---------|
| `fleet_session_reasoner` | Per-session PERCEIVE→REASON→ACT→LEARN with LLM |
| `fleet_state` | VM/tmux session inventory from azlin |
| `fleet_observer` | Pattern-based agent state classification |
| `fleet_health` | Process-level monitoring (memory, disk, load) |
| `fleet_logs` | Claude Code JSONL transcript reader |
| `fleet_tasks` | Priority-ordered task queue with persistence |
| `fleet_director` | Director loop orchestrating all modules |
| `fleet_reasoners` | Composable reasoning chain (lifecycle, preemption, coordination, batch) |
| `fleet_auth` | Auth propagation with multi-GitHub identity |
| `fleet_adopt` | Bring existing sessions under management |
| `fleet_setup` | Automated repo clone + dependency install |
| `fleet_dashboard` | Meta-project tracking |
| `fleet_results` | Structured outcome collection |
| `fleet_graph` | Lightweight JSON knowledge graph |
| `fleet_cli` | CLI commands |

## LLM Backend Protocol

The session reasoner uses a pluggable LLM backend:

```python
class LLMBackend:
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...

class AnthropicBackend(LLMBackend): ...  # Claude SDK
class CopilotBackend(LLMBackend): ...    # GitHub Copilot SDK
```

## Key CLI Commands

```bash
fleet status              # VM/session inventory
fleet dry-run             # Show what director would do (no action)
fleet dry-run --vm devo   # Dry-run for specific VM
fleet watch vm session    # Live snapshot of remote session
fleet snapshot            # Capture all sessions at once
fleet adopt vm            # Bring existing sessions under management
fleet start --adopt       # Start director, adopt all at startup
fleet dashboard           # Meta-project tracking view
fleet add-task "prompt"   # Queue a task for the fleet
```

## Session Adoption

Users can start sessions manually, then hand them to the director:

```bash
fleet adopt devo          # Discovers sessions, infers context, begins tracking
fleet start --adopt       # Adopt all managed VMs at startup
```

The director discovers existing tmux sessions via SSH, infers what they're
working on (from tmux pane content, git state, and JSONL logs), creates
tracking records, and begins observing without disruption.

## Constraints

- Azure Bastion tunnels: ~30s per connection setup
- No public IPs allowed
- Auth propagation via shared NFS storage (azlin blocks credential file copies)
- No ML — rules and LLM reasoning only
