# Fleet Orchestration Architecture

## Problem Statement

A developer manages 6+ cloud VMs, each running multiple tmux sessions with
coding agents (amplihack claude/amplifier/copilot). Today this requires:

1. **Manual auth setup** on each VM (gh, az cli tokens)
2. **Manual repo cloning** on each VM
3. **Manual agent startup** in each tmux session
4. **Manual tab-switching** to monitor progress across all sessions
5. **Manual prioritization** of what to work on next across projects
6. **No unified view** of all agent status across all VMs

The goal: agentic directors that manage fleets of VMs/tmux sessions, each
containing fleets of coding agents, with cross-project priority management.

## Current Capabilities (Building Blocks)

| Capability | Tool | Status |
|-----------|------|--------|
| VM provisioning | `azlin new --size l` | Production |
| Remote command execution | `azlin connect vm cmd` | Production |
| File transfer | `azlin cp` / `azlin sync` | Production |
| Tmux session creation | `execute_remote_tmux()` | Production |
| Tmux status polling | `check_tmux_status()` | Production |
| Virtual TTY observation | gadugi-agentic-test | Production |
| Goal-seeking agent loop | PERCEIVE→REASON→ACT→LEARN | Production |
| Parallel workstream exec | `/multitask` recipe runner | Production |
| Persistent agent memory | Kuzu graph DB | Production |
| Session tree recursion guard | session_tree.py | Production |

## Candidate Architectures

### Option A: Fleet Director (Centralized Control Plane)

```
┌─────────────────────────────────────────────────┐
│              FLEET DIRECTOR AGENT                │
│  (runs on control plane VM or local machine)     │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Priority │ │ Fleet    │ │ Health Monitor   │ │
│  │ Queue    │ │ State    │ │ (poll tmux/VM)   │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Auth     │ │ Task     │ │ Results          │ │
│  │ Propagator│ │ Router   │ │ Aggregator       │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└──────────────────┬──────────────────────────────┘
                   │ azlin API
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌────────┐   ┌────────┐   ┌────────┐
│ VM-1   │   │ VM-2   │   │ VM-3   │
│ ┌────┐ │   │ ┌────┐ │   │ ┌────┐ │
│ │tmux│ │   │ │tmux│ │   │ │tmux│ │
│ │sess│ │   │ │sess│ │   │ │sess│ │
│ │ A  │ │   │ │ C  │ │   │ │ E  │ │
│ └────┘ │   │ └────┘ │   │ └────┘ │
│ ┌────┐ │   │ ┌────┐ │   │ ┌────┐ │
│ │tmux│ │   │ │tmux│ │   │ │tmux│ │
│ │sess│ │   │ │sess│ │   │ │sess│ │
│ │ B  │ │   │ │ D  │ │   │ │ F  │ │
│ └────┘ │   │ └────┘ │   │ └────┘ │
└────────┘   └────────┘   └────────┘
```

**Pros:** Single source of truth, simple mental model, easy to observe
**Cons:** Single point of failure, bottleneck at director

### Option B: Hub-Spoke with Local Supervisors

```
┌──────────────────────────────────────┐
│         FLEET COORDINATOR            │
│  (priority queue, task assignment)    │
└──────────┬───────────┬───────────────┘
           │           │
    ┌──────▼──┐  ┌─────▼───┐  ┌──────────┐
    │ VM-1    │  │ VM-2    │  │ VM-3     │
    │ ┌─────┐ │  │ ┌─────┐ │  │ ┌─────┐  │
    │ │Super│ │  │ │Super│ │  │ │Super│  │
    │ │visor│ │  │ │visor│ │  │ │visor│  │
    │ └──┬──┘ │  │ └──┬──┘ │  │ └──┬──┘  │
    │    │    │  │    │    │  │    │     │
    │ ┌──▼──┐ │  │ ┌──▼──┐ │  │ ┌──▼──┐  │
    │ │Agent│ │  │ │Agent│ │  │ │Agent│  │
    │ │Pool │ │  │ │Pool │ │  │ │Pool │  │
    │ └─────┘ │  │ └─────┘ │  │ └─────┘  │
    └─────────┘  └─────────┘  └──────────┘
```

**Pros:** Fault-tolerant, local supervisors recover independently
**Cons:** More complexity, coordination overhead, harder to observe

### Option C: Self-Organizing Fleet (Shared Queue)

```
    ┌─────────────────────────────┐
    │     SHARED TASK QUEUE       │
    │     (NFS or git-based)      │
    └──┬──────────┬───────────┬───┘
       │          │           │
    ┌──▼────┐  ┌──▼────┐  ┌──▼────┐
    │ VM-1  │  │ VM-2  │  │ VM-3  │
    │ Agent │  │ Agent │  │ Agent │
    │ claims│  │ claims│  │ claims│
    │ tasks │  │ tasks │  │ tasks │
    └───────┘  └───────┘  └───────┘
```

**Pros:** No SPOF, scales naturally, simple protocol
**Cons:** No global coordination, priority conflicts, harder to observe

## Recommended: Option A (Fleet Director) — Start Simple

For the initial experiments, Option A is the right choice because:

1. **Ruthless simplicity** — one agent to rule them all
2. **Observable** — single place to see fleet state
3. **Iterative** — can evolve to hub-spoke if needed
4. **Matches user workflow** — user already acts as the director manually

We can build Option A as a goal-seeking agent with the PERCEIVE→REASON→ACT→LEARN
loop, where:

- **PERCEIVE**: Poll all VMs/tmux sessions, read agent output
- **REASON**: Compare progress vs priorities, identify blockers
- **ACT**: Start/stop agents, reassign work, escalate to human
- **LEARN**: Track what task types succeed on which VMs, refine routing

## Module Design

### Module 1: Auth Propagator (`fleet_auth.py`)

Copies authentication tokens from a source machine to target VMs:
- `~/.config/gh/hosts.yml` → GitHub CLI auth
- `~/.azure/msal_token_cache.json` + `~/.azure/azureProfile.json` → Azure CLI
- `~/.claude.json` → Claude Code API key (if present)
- Uses `azlin cp` for secure transfer

### Module 2: Fleet State Manager (`fleet_state.py`)

Maintains real-time state of all VMs and their tmux sessions:
- VM inventory (from `azlin list`)
- Tmux session inventory (from `azlin connect vm "tmux ls"`)
- Agent status per session (running, idle, completed, stuck)
- Resource utilization (CPU, memory via `azlin health`)

### Module 3: Task Queue (`fleet_tasks.py`)

Priority-ordered task queue with assignment tracking:
- Task definition: repo, branch, prompt, priority, estimated_complexity
- Assignment: task → VM → tmux session
- Status tracking: queued, assigned, running, completed, failed
- Persistence: JSON file (simple, can upgrade to DB later)

### Module 4: Fleet Director (`fleet_director.py`)

The goal-seeking agent loop:
```python
class FleetDirector:
    def perceive(self) -> FleetState:
        """Poll all VMs, tmux sessions, agent outputs"""

    def reason(self, state: FleetState) -> List[Action]:
        """Decide: start agents, reassign, escalate, report"""

    def act(self, actions: List[Action]) -> List[Result]:
        """Execute decisions via azlin API"""

    def learn(self, results: List[Result]):
        """Update patterns: which VM/agent combos work best"""
```

### Module 5: Virtual TTY Observer (`fleet_observer.py`)

Uses gadugi-agentic-test to observe agent sessions:
- Capture tmux pane content (`tmux capture-pane -t session -p`)
- Parse for known patterns (errors, completion, waiting for input)
- Detect stuck agents (no output change for N minutes)
- Detect completed work (PR created, tests passing)

### Module 6: Fleet CLI (`fleet_cli.py`)

User interface for managing the fleet:
- `fleet status` — show all VMs, sessions, agent states
- `fleet add-task "prompt" --repo x --priority high` — queue task
- `fleet start` — begin autonomous director loop
- `fleet stop` — gracefully stop director
- `fleet report` — generate summary of all work in progress

## Experiment Design

### Experiment 1: Auth Propagation

**Hypothesis H1:** Automated auth propagation saves >80% of setup time per VM.

**Method:**
1. Create 2 new VMs via `azlin new --size l --region eastus`
2. Time manual auth setup (baseline)
3. Build auth propagator module
4. Time automated auth propagation
5. Verify auth works (gh auth status, az account show)

**Success Criteria:** < 30 seconds for full auth propagation (vs ~5 min manual)

### Experiment 2: Fleet State Observation

**Hypothesis H2:** Virtual TTY observation can detect agent state (running,
stuck, completed) with >90% accuracy.

**Method:**
1. Start 3 tmux sessions with known agent states
2. Build observer module
3. Run observer against known states
4. Measure detection accuracy

**Success Criteria:** >90% correct state detection across 10 test scenarios

### Experiment 3: Autonomous Task Routing

**Hypothesis H3:** A director agent can start, monitor, and complete tasks
across 2-3 VMs without human intervention.

**Method:**
1. Create task queue with 3 tasks of varying priority
2. Provision 2 experiment VMs
3. Start fleet director
4. Observe: does it assign tasks, monitor progress, detect completion?
5. Measure: tasks completed, time vs manual, human interventions needed

**Success Criteria:** 2/3 tasks completed autonomously with ≤1 human intervention

### Experiment 4: Cross-Agent Memory Sharing

**Hypothesis H4:** Shared learnings between agents reduce duplicate investigation
time by >30%.

**Method:**
1. Two agents investigate same codebase independently (baseline)
2. Two agents with shared memory investigate same codebase
3. Measure: time to understanding, duplicate queries, quality of insights

**Success Criteria:** >30% reduction in investigation time with shared memory

## Implementation Plan

### Phase 1: Foundation (Experiments 1-2)
1. Create experiment VMs (new region, don't touch existing)
2. Build auth propagator
3. Build fleet state observer
4. Test both independently

### Phase 2: Director (Experiment 3)
1. Build task queue
2. Build fleet director (PERCEIVE→REASON→ACT loop)
3. Test autonomous task routing on experiment VMs

### Phase 3: Learning (Experiment 4)
1. Add memory/learning to director
2. Test cross-agent knowledge sharing
3. Evaluate improvement

### Phase 4: Quality & Delivery
1. Quality audit all code
2. Outside-in testing for each module
3. Create GitHub issue with findings
4. Form candidate PRs
