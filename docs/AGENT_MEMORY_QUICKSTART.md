# Agent Memory Quickstart

This quickstart focuses on the memory surfaces that are verified in this checkout today.

- the top-level CLI memory graph backed by `src/amplihack/memory`
- generated goal-agent packages created with `amplihack new --enable-memory`

## 1. Inspect the CLI Memory Graph

The top-level `memory` command defaults to the Kuzu backend.

```bash
amplihack memory tree
```

Useful variants:

```bash
amplihack memory tree --backend kuzu --depth 2
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

## 4. Know Which Memory System You Are Looking At

There are two real memory surfaces in this repo:

- the top-level CLI memory backend under `src/amplihack/memory`, which defaults to Kuzu and stores data under `~/.amplihack/memory_kuzu.db` unless `AMPLIHACK_GRAPH_DB_PATH` is set
- the generated agent package created by `--enable-memory`, which scaffolds `amplihack_memory` helpers and stores agent-local data under `./memory/`

Those are related, but they are not the same storage location.

## 5. Clean Test Sessions From the CLI Backend

Preview deletions first:

```bash
amplihack memory clean --pattern 'test_*'
```

Delete matching sessions after the dry run looks correct:

```bash
amplihack memory clean --pattern 'test_*' --no-dry-run --confirm
```

## Next Steps

- [Memory docs landing page](./memory/README.md)
- [Memory-enabled agents architecture](./concepts/memory-enabled-agents-architecture.md)
- [Memory tutorial](./tutorials/memory-enabled-agents-getting-started.md)
- [Memory CLI reference](./reference/memory-cli-reference.md)
- [How to integrate memory into agents](./howto/integrate-memory-into-agents.md)
