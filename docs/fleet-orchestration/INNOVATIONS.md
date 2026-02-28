# Fleet Orchestration — Innovations & Architecture Dialogue

## Agent Dialogue Summary

Two architectural reviews were conducted: one with the **Architect** agent
(systems design perspective) and one with the **Philosophy Guardian** (simplicity
and proportionality perspective).

## Key Innovations Identified

### 1. Fleet-Level Context Deduplication (Architect)

**Problem**: Multiple agents investigating the same codebase independently waste
time rediscovering the same patterns.

**Innovation**: Before assigning a task, the director checks if any agent has
already investigated that codebase. If so, it attaches the prior agent's findings
as context to the new task.

```
Director assigns Task B (same repo as completed Task A)
  → Attaches Task A's result summary as context
  → Agent B starts with knowledge instead of from scratch
  → Estimated 10-20 min savings per task
```

### 2. Per-Session Identity (NOT Global Switch) (Architect)

**Critical finding**: Using `gh auth switch` globally on a VM creates race
conditions when multiple tmux sessions run simultaneously. Instead:

- Inject `GH_TOKEN` as environment variable per tmux session
- One VM can safely run multiple GitHub identities in different sessions
- Identity is bound to the task, not the VM

### 3. Push-Based Heartbeats (Architect)

**Problem**: Bastion tunnel setup is ~30s per connection. Sequential polling of
30 VMs takes 15 minutes.

**Innovation**: Each VM runs a tiny cron job writing heartbeat data to shared NFS.
Director reads local files instead of SSH-ing.

```
# On each VM (cron every 30s):
echo '{"vm":"fleet-exp-1","status":"ok","agents":3,"load":2.1}' > /shared/heartbeats/fleet-exp-1.json

# Director PERCEIVE phase:
# Reads local files instead of 30 SSH connections
for f in /shared/heartbeats/*.json; do update_state(f); done
```

### 4. Result Collection Service (Architect — #1 Priority)

**Problem**: Without structured results, the LEARN phase is blind.

**Built**: `fleet_results.py` — TaskResult with PR URLs, test status, error
summaries, timing data. File-based, one JSON per task. Enables the director to
actually learn from outcomes.

### 5. Agent Health Beyond Tmux (Architect + Built)

**Problem**: tmux capture-pane is fragile. Agent process might be dead but tmux
session still shows old output.

**Built**: `fleet_health.py` — Single compound SSH command collects memory, disk,
process list, load average, and uptime. One Bastion connection per VM instead of N.

### 6. Automated Repo Setup (Architect + Built)

**Problem**: Every task assignment starts with 5-10 minutes of manual setup.

**Built**: `fleet_setup.py` — Auto-detects project type (Python/Node/Rust/Go/.NET)
and installs dependencies. Injected into tmux session before agent starts.

## Philosophy Guardian Findings

### What Passed
- **Brick compliance**: All 6 original modules pass (single responsibility, typed contracts)
- **Regenerability**: High — each module can be rebuilt from its docstring + `__all__`
- **Wabi-sabi**: Essential complexity only, minimal embellishment
- **Proportionality**: 1767 lines for distributed fleet management is lean

### What Was Fixed
- **Dead `PROVISION_VM` action type**: Removed (it was never implemented)
- **`_save()` / `save()` duplication**: Collapsed to single `save()` method
- **Missing tests**: Added tests for `fleet_auth` (12) and `fleet_state` (11)
- Total tests: **53 → 80** (51% increase in coverage)

### Future Creep Warning
The guardian warned: when `fleet_director.py` exceeds ~600 lines, or `reason()`
grows beyond 3-4 decision rules, extract strategy into its own module. Currently
471 lines and 3 decision rules — well within bounds.

## Scaling Roadmap (from Architect)

| VM Count | Architecture | Key Changes |
|----------|-------------|-------------|
| 6-15 | Current (centralized) | Works as-is |
| 15-30 | + parallel tunnels | Add connection pooling, push heartbeats |
| 30-50 | + persistent tunnels | SQLite task queue, NFS-based communication |
| 50-100 | Hub-spoke | Regional spokes with local PERCEIVE loops |
| 100+ | Full hub-spoke | REST API between hub and spokes |

## Missing Tools (Priority Ordered)

| # | Tool | Status | Impact |
|---|------|--------|--------|
| 1 | Result collection | BUILT | Enables LEARN phase |
| 2 | Agent health checks | BUILT | Prevents stuck agents |
| 3 | Automated repo setup | BUILT | Saves 5-10 min per task |
| 4 | Multi-identity support | BUILT | Enables multi-org work |
| 5 | Meta-project dashboard | BUILT | Operational visibility |
| 6 | Fleet context cache | TODO | Saves 10-20 min per agent |
| 7 | Parallel Bastion tunnels | TODO | Required at 15+ VMs |
| 8 | Push-based heartbeats | TODO | Required at 30+ VMs |
| 9 | Auto-scaling | SKIP (for now) | Not needed at 6-15 VMs |
| 10 | Hub-spoke split | SKIP (for now) | Not needed until 50+ VMs |
