# Multitask Reference

## Architecture

```
/multitask skill
    |
    v
orchestrator.py (ParallelOrchestrator)
    |
    +---> Workstream 1: /tmp/ws-123/
    |         run.sh -> unset CLAUDECODE -> launcher.py
    |         launcher.py -> run_recipe_by_name("default-workflow", adapter, context)
    |         CLISubprocessAdapter -> claude -p (per recipe step)
    |
    +---> Workstream 2: /tmp/ws-124/
    |         (same structure)
    |
    +---> Workstream N: /tmp/ws-NNN/
              (same structure)
```

## JSON Config Format

```json
[
  {
    "issue": 123,
    "branch": "feat/my-feature",
    "description": "Brief description shown in reports",
    "task": "Detailed task instructions for the agent",
    "recipe": "default-workflow"
  }
]
```

### Required Fields

| Field    | Type   | Description                            |
| -------- | ------ | -------------------------------------- |
| `issue`  | int    | GitHub issue number                    |
| `branch` | string | Git branch name (must exist in remote) |
| `task`   | string | Detailed task instructions             |

### Optional Fields

| Field         | Type   | Default              | Description                   |
| ------------- | ------ | -------------------- | ----------------------------- |
| `description` | string | `"Issue #N"`         | Short description for reports |
| `recipe`      | string | `"default-workflow"` | Recipe to execute             |

## Orchestrator API

### `ParallelOrchestrator(repo_url, tmp_base, mode)`

| Parameter  | Type | Default                      | Description                               |
| ---------- | ---- | ---------------------------- | ----------------------------------------- |
| `repo_url` | str  | required                     | Git remote URL                            |
| `tmp_base` | str  | `/tmp/amplihack-workstreams` | Base directory for clones                 |
| `mode`     | str  | `"recipe"`                   | Execution mode: `"recipe"` or `"classic"` |

### Methods

- `setup()` - Create clean temporary directory
- `add(issue, branch, description, task, recipe)` - Add and clone a workstream
- `launch(ws)` - Launch single workstream subprocess
- `launch_all()` - Launch all workstreams in parallel
- `get_status()` - Returns `{"running": [...], "completed": [...], "failed": [...]}`
- `monitor(check_interval=60, max_runtime=7200)` - Block until all complete or timeout
- `report()` - Print and save final report, returns report text
- `cleanup_running()` - Terminate all running subprocesses

### `run(config_path, mode, recipe)`

Top-level entry point. Auto-detects repo URL from git remote.

## Recipe Runner Integration

### How Steps Execute

In recipe mode, each workstream runs the Recipe Runner's Python execution loop:

```python
# Inside launcher.py (generated per workstream)
for step in recipe.steps:
    if step.type == "bash":
        result = subprocess.run(["bash", "-c", rendered_command])
    elif step.type == "agent":
        result = subprocess.run(["claude", "-p", rendered_prompt])
```

The `CLISubprocessAdapter` handles the dispatch. Each agent step creates a new `claude -p` session.

### Context Flow Between Steps

Recipe steps pass outputs via template variables:

```yaml
# Step 1 output stored in "clarified_requirements"
- id: "clarify-requirements"
  agent: "amplihack:prompt-writer"
  prompt: "Analyze: {{task_description}}"
  output: "clarified_requirements"

# Step 2 uses that output
- id: "design"
  agent: "amplihack:architect"
  prompt: "Design based on: {{clarified_requirements}}"
```

### Fallback Behavior

If `amplihack` package is not importable in the clone environment, `launcher.py` exits with code 2. The orchestrator reports this as a failure.

To use classic mode as fallback, specify `--mode classic` when invoking the orchestrator.

## Environment Variables

| Variable     | Effect                                                           |
| ------------ | ---------------------------------------------------------------- |
| `CLAUDECODE` | Unset in workstream subprocesses to allow nested Claude sessions |

## File Layout Per Workstream

```
/tmp/amplihack-workstreams/
  ws-123/           # Clone of feat/my-feature branch
    launcher.py     # Recipe runner invocation (recipe mode)
    run.sh          # Shell wrapper (unsets CLAUDECODE)
    TASK.md         # Task description (classic mode only)
    ...             # Full repo clone
  log-123.txt       # Combined stdout/stderr log
  ws-124/
  log-124.txt
  REPORT.md         # Final report from orchestrator
```

## Timeouts

| Operation                         | Timeout       |
| --------------------------------- | ------------- |
| Git clone                         | 120s          |
| Orchestrator max runtime          | 7200s (2h)    |
| Subprocess termination grace      | 10s           |
| Agent step (CLISubprocessAdapter) | 300s per step |
| Bash step (CLISubprocessAdapter)  | 120s per step |

## Error Handling

### Workstream Failures

Failed workstreams do not affect running ones. The orchestrator continues monitoring until all are complete or timed out.

### SIGINT Handling

Ctrl+C terminates all running workstreams gracefully (SIGTERM, then SIGKILL after 10s).

### Clone Failures

If a branch does not exist or the clone fails, `add()` raises and that workstream is not launched.

## Proven Results

**First production use** (2026-02-14, Recipe Runner follow-up):

- 5 workstreams launched in parallel
- 4/5 PRs created successfully (#2295, #2296, #2297, #2303)
- 1 failure (#2291 Copilot SDK - stopped mid-workflow)
- Average runtime: 60-90 minutes per workstream
