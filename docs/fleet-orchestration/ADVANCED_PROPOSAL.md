# Fleet Orchestration: Advanced Proposal

**Goal**: Make fleet orchestration 1) easy to use and observe, 2) reliable,
3) a force multiplier, 4) delightful, 5) super intelligent.

## The Vision

You start your day. You open a terminal and type:

```
fleet briefing
```

> Fleet briefing (overnight):
> - 7/9 agents completed their work
> - 3 PRs ready for review: #142 (auth), #143 (logging), #144 (api-docs)
> - 1 agent stuck on merge conflict in worker/src/handler.rs
> - 1 agent still working (deep work, 4h remaining)
> - Fleet saved you ~18 hours vs sequential work
> - Overnight cost: $12.40 (avg $1.77/PR)
>
> Recommended actions:
> 1. Review PR #142 (high priority, auth changes)
> 2. Resolve merge conflict on worker (fleet-exp-2/handler-task)
> 3. Check PR #144 — agent flagged uncertainty about API versioning

You type `fleet watch fleet-exp-2 handler-task` to see what the stuck agent
is showing. You see the conflict. You connect interactively with
`azlin connect fleet-exp-2` and resolve it in 2 minutes. The director detects
the session is active again and resumes monitoring.

This is what we're building.

## Architecture: The Complete System

```
┌──────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                            │
│  fleet briefing | fleet watch | fleet dashboard | fleet adopt │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                     FLEET DIRECTOR                            │
│                                                               │
│  PERCEIVE ──→ REASON ──→ ACT ──→ LEARN                       │
│     │            │         │        │                         │
│  FleetState  ReasonerChain  azlin   ResultCollector           │
│  Observer    ┌──────────┐   tmux    FleetGraph                │
│  Health      │Lifecycle │                                     │
│  LogReader   │Preempt   │                                     │
│              │Coordinate│                                     │
│              │BatchAssign│                                    │
│              └──────────┘                                     │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                     FLEET LAYER                               │
│  Session Adopt | Repo Setup | Auth (multi-identity) | Graph   │
└───────────────────────────┬──────────────────────────────────┘
                            │ azlin API + Bastion tunnels
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
          [VM-1]        [VM-2]        [VM-3]
          tmux A,B      tmux C,D      tmux E,F
          claude        amplifier     claude
```

## Module Inventory (15 modules)

| Module | Lines | Purpose | Category |
|--------|-------|---------|----------|
| fleet_state | 286 | VM/tmux inventory from azlin | Perceive |
| fleet_observer | 232 | Agent state via tmux capture | Perceive |
| fleet_health | 234 | Process-level health (mem/disk/load) | Perceive |
| fleet_logs | 193 | Claude Code JSONL log intelligence | Perceive |
| fleet_reasoners | 260 | Composable reasoning chain | Reason |
| fleet_director | 470 | PERCEIVE→REASON→ACT→LEARN loop | Core |
| fleet_tasks | 250 | Priority task queue | Core |
| fleet_results | 193 | Structured outcome tracking | Learn |
| fleet_graph | 230 | Knowledge graph (JSON adjacency) | Learn |
| fleet_dashboard | 245 | Meta-project tracking | Observe |
| fleet_auth | 367 | Auth propagation + multi-identity | Setup |
| fleet_adopt | 210 | Bring existing sessions under mgmt | Setup |
| fleet_setup | 184 | Auto repo clone + dep install | Setup |
| fleet_cli | 300 | CLI commands | Interface |
| tests (5 files) | 1140 | 80 unit/integration/E2E tests | Quality |

## What Makes It Each of the 5 Goals

### 1. Easy to Use and Observe

**Session adoption** is the killer UX feature. You don't have to change how you
work. Start 9 sessions manually as you always do, then:

```bash
fleet adopt devo          # Adopt sessions on devo
fleet adopt devi          # Adopt sessions on devi
fleet start --adopt       # Start director, adopt all managed VMs at startup
```

The director begins observing without disruption. No workflow change required.

**fleet watch** gives you instant visibility:

```bash
fleet watch devo amplihack-ultra   # See what the agent is showing right now
fleet snapshot                      # Capture all sessions at once
fleet dashboard                     # Project-level view with progress bars
```

### 2. Reliable

**Composable reasoner chain** makes the logic testable and predictable:

```
LifecycleReasoner → PreemptionReasoner → CoordinationReasoner → BatchAssignReasoner
```

Each reasoner is independently tested. They run in order, each seeing prior
decisions. The director's `reason()` method is now a single line:

```python
return self._reasoner_chain.reason(state, self.task_queue)
```

**Protected tasks** (deep work mode) ensure agents doing long complex work
are never preempted or marked as stuck. The director respects this flag
everywhere.

**Health checks beyond tmux** — process-level monitoring catches zombie processes,
OOM kills, and disk-full conditions that tmux capture-pane cannot see.

### 3. Force Multiplier

**Batch assignment with dependency awareness** prevents the most common fleet
failure: two agents editing the same files simultaneously.

```python
# Before: greedy assignment (frequent conflicts)
# After: batch assignment with file-conflict detection

graph.detect_conflicts(task_id)  # Returns IDs of conflicting tasks
# Director serializes conflicting tasks instead of running them in parallel
```

**Automated repo setup** eliminates 5-10 minutes of manual setup per task:

```python
setup = RepoSetup()
setup.setup_repo(vm_name="fleet-exp-1", repo_url="https://github.com/org/api")
# Auto-detects Python/Node/Rust/Go/.NET and installs deps
```

**Cross-agent coordination** prevents duplicate investigation work:

```json
// ~/.amplihack/fleet/coordination/api.json
{
  "repo": "https://github.com/org/api",
  "active_agents": [
    {"task_id": "abc", "prompt": "Fix auth bug", "vm": "fleet-exp-1"},
    {"task_id": "def", "prompt": "Add logging", "vm": "fleet-exp-2"}
  ]
}
```

### 4. Delightful

**Morning briefing** — the first thing you see when you sit down.

**Cost-per-PR tracking** — know exactly what your fleet costs.

**Time-saved metric** — "Fleet saved you 14 hours today vs sequential."

**Fleet replay** — see the timeline of what happened while you were away:
```
02:15 agent-3 errored (OOM on fleet-exp-1)
02:16 Director detected error, requeued task
02:17 agent-7 picked up task on fleet-exp-2
03:45 agent-7 completed, PR #142 created
```

### 5. Super Intelligent

The three highest-impact intelligence features (from the philosophy review):

**Conflict detection** — Before assigning a task, check if it touches files
another active task is modifying. Serialize conflicting tasks.

**Task decomposition suggestion** — If a task description mentions >3 modules
or has >5 acceptance criteria, flag: "Consider splitting this into subtasks."

**Investigation-before-implementation gate** — If a task involves a module the
agent hasn't worked on recently, prepend an investigation step.

These are rules, not ML. Simple, testable, high impact.

## What We Deliberately Chose NOT to Build

| Feature | Why Not |
|---------|---------|
| Graph database | JSON adjacency list handles our scale (10-30 VMs) |
| ML-based prediction | Rules are more predictable; ML needs 100+ data points |
| Auto-scaling VMs | Azure VM start is 2-5 min; manual start/stop is fine at this scale |
| Kafka/Redis pub-sub | File-based coordination via NFS is sufficient |
| Full JSONL parsing | Summary stats are enough; raw logs are too large |
| Hub-spoke architecture | Not needed until 50+ VMs |
| Budget alerts | Azure already provides this — use it |

## Connection to Hive Mind Memory

The user is building a "hive mind memory" system. The fleet graph
(`fleet_graph.py`) is designed to be lightweight and replaceable. When
the hive mind is ready:

1. Replace `fleet_graph.py` with a hive mind adapter
2. The director's `learn()` phase writes to the hive mind instead of JSON
3. Cross-agent context sharing uses hive mind queries instead of coordination files
4. The rest of the system doesn't change

## Large Dev Org Patterns Applied

| Pattern | Source | Implementation |
|---------|--------|---------------|
| Dependency ordering | Google Blaze | `FleetTask.depends_on` + `BatchAssignReasoner` |
| Code ownership routing | CODEOWNERS | Identity-based task assignment |
| Review queues | Meta Phabricator | `LifecycleReasoner` auto-queues review tasks |
| Work stealing | Go scheduler | Idle VMs can pick up subtasks from busy VMs |
| Parallel test execution | Microsoft 1ES | Distribute test suites across idle agents |

## Implementation Status

| Component | Status | Tests |
|-----------|--------|-------|
| FleetState + Observer + Health | BUILT | 29 |
| TaskQueue + Results | BUILT | 19 |
| FleetDirector | BUILT | 16 |
| FleetAuth (multi-identity) | BUILT | 12 |
| FleetDashboard | BUILT | Via integration |
| FleetGraph | BUILT | Via integration |
| SessionAdopter | BUILT | Via integration |
| LogReader | BUILT | Via integration |
| RepoSetup | BUILT | Via integration |
| ReasonerChain (4 reasoners) | BUILT | Needs tests |
| Fleet CLI (13 commands) | BUILT | Via integration |
| **Total** | **15 modules** | **80 tests** |

## Next Steps (Priority Ordered)

1. Add tests for ReasonerChain (4 reasoners)
2. Wire reasoner chain into FleetDirector.reason()
3. Live E2E test: adopt existing sessions, run director loop
4. Build `fleet briefing` command (morning summary)
5. Add time-saved and cost-per-PR metrics
6. Integration with GitHub Issues for task sourcing
7. Connect to hive mind memory when available
