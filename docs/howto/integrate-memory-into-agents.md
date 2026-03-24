# How to Integrate Memory Into Agents

Use this guide when you want to add memory to generated agent code without mixing it up with the top-level CLI memory backend.

## Generate the Scaffold

The supported generator entrypoint is `amplihack new`, not the older `goal-agent generate` commands.

```bash
amplihack new \
  --file prompt.md \
  --name my-memory-agent \
  --enable-memory \
  --sdk copilot
```

This gives you a standalone package with:

- `main.py`
- `memory_config.yaml`
- `memory/`
- `amplihack-memory-lib` in `requirements.txt`
- helper functions injected into `main.py`

## Install the Package Dependencies

```bash
cd goal_agents/my-memory-agent
python -m pip install -r requirements.txt
```

## Use the Generated Memory Helpers

The generated package exposes helper functions such as:

- `store_success(context, outcome, confidence=...)`
- `store_failure(context, outcome, confidence=...)`
- `store_pattern(context, outcome, confidence=...)`
- `store_insight(context, outcome, confidence=...)`
- `recall_relevant(query, limit=...)`
- `cleanup_memory()`

A minimal integration pattern is to recall relevant experience before the run and store the result afterward.

```python
recent = recall_relevant(initial_prompt, limit=3)
for item in recent:
    print("Previous experience: {} -> {}".format(item.context, item.outcome))

exit_code = auto_mode.run()

if exit_code == 0:
    store_success(
        context="Goal execution completed",
        outcome=initial_prompt,
        confidence=0.95,
    )
else:
    store_failure(
        context="Goal execution failed",
        outcome="Exit code {}".format(exit_code),
        confidence=0.95,
    )
```

## Keep the Two Memory Surfaces Straight

The generated package and the top-level CLI graph are different systems.

| Surface                  | Entry Point                                           | Storage                                             |
| ------------------------ | ----------------------------------------------------- | --------------------------------------------------- |
| generated agent scaffold | `amplihack new --enable-memory`                       | local `./memory/` directory                         |
| top-level CLI graph      | `amplihack memory tree`                               | SQLite `MemoryDatabase` at `~/.amplihack/memory.db` |
| agent-local transfer     | `amplihack memory export` / `amplihack memory import` | hierarchical Kuzu store for the named agent         |

If you want to inspect the top-level CLI graph, use:

```bash
amplihack memory tree --depth 2
```

If you want to move an agent-local hierarchical memory store between environments, use:

```bash
amplihack memory export --agent incident-memory-agent --output ./incident-memory.json
amplihack memory import --agent incident-memory-agent --input ./incident-memory.json --merge
```

Do not expect those commands to be a direct live view into a generated agent's local `./memory/` directory.

## Configure Kuzu-backed Graph Paths

For lower-level Kuzu graph integrations and agent-local hierarchical stores, the preferred environment variable is:

```bash
export AMPLIHACK_GRAPH_DB_PATH=/path/to/memory_kuzu.db
```

`AMPLIHACK_KUZU_DB_PATH` still exists as a deprecated alias.

The top-level `amplihack memory tree` command does not read this setting; it opens the SQLite `MemoryDatabase` unless you change code.

## Related Docs

- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md)
- [Memory tutorial](../tutorials/memory-enabled-agents-getting-started.md)
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md)
- [Memory CLI reference](../reference/memory-cli-reference.md)
