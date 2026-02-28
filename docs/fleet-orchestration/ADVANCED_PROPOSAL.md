# Fleet Orchestration: Advanced Design

## Vision

You type `fleet dry-run` and see what every agent session needs. You type
`fleet start --adopt` and the director takes over — answering agent questions,
approving safe operations, escalating complex decisions. You check in with
`fleet watch` and `fleet dashboard` to see progress.

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the module breakdown and
per-session reasoning loop.

## Design Principles

1. **Observe first, act carefully** — dry-run mode shows reasoning before acting
2. **Never interrupt thinking** — detect active LLM/tool processing and wait
3. **SDK-agnostic** — LLMBackend protocol supports Claude and Copilot
4. **Adopt, don't replace** — bring existing manual sessions under management
5. **No ML** — rules and LLM reasoning, not trained models

## Composable Reasoner Chain

The director's `reason()` delegates to a chain of composable reasoners:

```
LifecycleReasoner → PreemptionReasoner → CoordinationReasoner → BatchAssignReasoner
```

Each reasoner sees prior decisions and can add its own. Adding a new reasoner
is one class + one append to the chain.

| Reasoner | Purpose |
|----------|---------|
| Lifecycle | Detect completions, failures, stuck agents. Respects protected (deep work) tasks. |
| Preemption | Pause low-priority work when CRITICAL tasks arrive with no idle capacity. |
| Coordination | Write shared context files so agents on same repo don't duplicate work. |
| BatchAssign | Dependency-aware batch assignment (not greedy one-at-a-time). |

## Scaling Path

| Scale | Architecture |
|-------|-------------|
| 6-15 VMs | Current centralized director |
| 15-30 VMs | Add parallel Bastion tunnels + push-based heartbeats |
| 30-50 VMs | SQLite task queue + persistent SSH tunnels |
| 50+ VMs | Hub-spoke: regional directors reporting to coordinator |

## Future Directions

- Integration with GitHub Issues for task sourcing
- Push-based heartbeats via shared NFS (avoid polling)
- Parallel Bastion tunnel connections
- Connection to hive mind memory for cross-agent knowledge
- Fleet replay timeline for debugging
