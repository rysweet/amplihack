# Tutorial: Create and Run a Memory-Enabled Goal Agent

This tutorial shows the current generated-agent memory path.

By the end, you will have:

- generated a memory-enabled goal agent package
- installed its dependencies
- run the package locally
- inspected the files that `--enable-memory` adds

## Before You Start

Make sure `amplihack` is installed and the `amplihack` CLI is on your path.

## Step 1: Write a Goal Prompt

Create a prompt file:

```bash
printf '%s\n' \
  'Build an agent that investigates deployment failures, remembers repeated causes, and suggests the next debugging step.' \
  > goal.md
```

## Step 2: Generate the Agent Package

```bash
amplihack new \
  --file goal.md \
  --name incident-memory-agent \
  --enable-memory \
  --sdk copilot
```

This creates a package in `goal_agents/incident-memory-agent/`.

## Step 3: Inspect the Generated Files

```bash
cd goal_agents/incident-memory-agent
find . -maxdepth 2 -type f | sort
```

For a memory-enabled package, the important additions are:

- `main.py`
- `memory_config.yaml`
- `memory/.gitignore`
- `requirements.txt`

Open `main.py` and search for these helper functions:

- `store_success`
- `store_failure`
- `store_pattern`
- `store_insight`
- `recall_relevant`
- `cleanup_memory`

Those helpers are what `--enable-memory` injects into the generated package.

## Step 4: Install the Generated Package Dependencies

```bash
python -m pip install -r requirements.txt
```

The generated `requirements.txt` includes:

- `amplihack`
- `amplihack-memory-lib`

## Step 5: Run the Generated Agent

```bash
python main.py
```

The generated package runs through `AutoMode`, using the SDK you selected when you called `amplihack new`.

## Step 6: Understand Where the Memory Lives

The generated package creates and owns a local `./memory/` directory.

That is separate from the top-level CLI memory backend used by `amplihack memory tree` and `amplihack memory clean`.

## Step 7: Add a Simple Memory Hook

`--enable-memory` gives you helper functions, but you still need to decide where to call them in your generated package.

A simple first step is to record whether the run succeeded. In `main.py`, after `exit_code = auto_mode.run()`, add:

```python
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

You can also recall previous experiences before starting the run:

```python
recent = recall_relevant(initial_prompt, limit=3)
for item in recent:
    print("Previous experience: {} -> {}".format(item.context, item.outcome))
```

## Step 8: Inspect the CLI Memory Graph Separately

The top-level CLI memory graph is a different surface, but it is still useful when you are working on the in-repo backend.

```bash
amplihack memory tree --backend kuzu --depth 2
```

## Next Steps

- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md)
- [How to integrate memory into agents](../howto/integrate-memory-into-agents.md)
- [Memory-enabled agents architecture](../concepts/memory-enabled-agents-architecture.md)
