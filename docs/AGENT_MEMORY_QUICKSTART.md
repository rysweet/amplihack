# Agent Memory Quickstart

This quickstart covers the memory surfaces verified in this checkout today:

- the top-level `amplihack memory tree` graph view
- the agent-local `amplihack memory export` / `amplihack memory import` transfer commands
- generated goal-agent packages created with `amplihack new --enable-memory`

## 1. Inspect the Top-Level CLI Memory Graph

The top-level graph view uses `MemoryDatabase`, a SQLite store at `~/.amplihack/memory.db` by default.

```bash
amplihack memory tree
```

Useful variants:

```bash
amplihack memory tree --depth 2
amplihack memory tree --session test_session_01
amplihack memory tree --type learning
```

`memory tree --type` currently accepts the legacy compatibility names:

- `conversation`
- `decision`
- `pattern`
- `context`
- `learning`
- `artifact`

## 2. Generate a Memory-Enabled Goal Agent

```bash
printf '%s\n' \
  'Build an agent that investigates deployment failures, remembers repeated causes, and suggests the next debugging step.' \
  > goal.md

amplihack new \
  --file goal.md \
  --name incident-memory-agent \
  --enable-memory \
  --sdk copilot
```

That creates a package under `./goal_agents/incident-memory-agent/`.

## 3. Install and Run the Generated Agent

```bash
cd goal_agents/incident-memory-agent
python -m pip install -r requirements.txt
python main.py
```

When `--enable-memory` is set, the generated package includes:

- `memory_config.yaml`
- a local `./memory/` directory
- helper functions in `main.py` such as `store_success()`, `store_failure()`, and `recall_relevant()`
- `amplihack-memory-lib` in `requirements.txt`

## 4. Export or Import an Agent-Local Memory Store

Use the transfer commands when you want to move an agent's hierarchical memory between environments.

```bash
amplihack memory export --agent incident-memory-agent --output ./incident-memory.json
amplihack memory import --agent incident-memory-agent --input ./incident-memory.json --merge
```

For raw Kuzu store replacement instead of JSON merge:

```bash
amplihack memory export --agent incident-memory-agent --output ./incident-memory-kuzu --format kuzu
amplihack memory import --agent incident-memory-agent --input ./incident-memory-kuzu --format kuzu
```

## 5. Know Which Memory System You Are Looking At

There are three related but different surfaces in this repo:

- the top-level CLI graph view, which reads SQLite `MemoryDatabase` at `~/.amplihack/memory.db`
- the agent-local hierarchical store used by `memory export` / `memory import`
- the generated package created by `--enable-memory`, which scaffolds `amplihack_memory` helpers and stores local data under `./memory/`

Those surfaces are related, but they are not the same storage location.

## Next Steps

- [Memory docs landing page](./memory/README.md)
- [Memory-enabled agents architecture](./concepts/memory-enabled-agents-architecture.md)
- [Memory tutorial](./tutorials/memory-enabled-agents-getting-started.md)
- [Memory CLI reference](./reference/memory-cli-reference.md)
- [How to integrate memory into agents](./howto/integrate-memory-into-agents.md)
