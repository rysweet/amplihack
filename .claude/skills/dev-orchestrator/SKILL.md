---
name: dev-orchestrator
description: |
  Default task orchestrator for all development and investigation work.
  Classifies tasks, decomposes into parallel workstreams if appropriate,
  and routes execution through the recipe runner. Replaces ultrathink-orchestrator.
version: 2.0.0
auto_activates:
  - "implement"
  - "build"
  - "create"
  - "add feature"
  - "fix bug"
  - "refactor"
  - "investigate"
  - "analyze"
  - "research"
  - "explore"
  - "develop"
  - "make"
priority: 5
---

# Dev Orchestrator Skill

## Purpose

This is the **default orchestrator** for all non-trivial development and investigation tasks
in amplihack. It replaces the `ultrathink-orchestrator` skill.

When a user asks you to build, implement, fix, investigate, or create anything non-trivial,
this skill ensures:

1. **Task is classified** — Q&A / Operations / Investigation / Development
2. **Goal is formulated** — clear success criteria identified
3. **Workstreams detected** — parallel tasks split automatically
4. **Recipe runner used** — code-enforced workflow execution
5. **Outcome verified** — reflection confirms goal achievement

## How It Works

```
User request
     │
     ▼
[Classify] ──→ Q&A ──────────────────→ analyzer agent (technical/code questions)
     │
     ├──────→ Ops ────────────────────→ builder agent
     │
     └──→ Development / Investigation
             │
         [Recursion guard] (AMPLIHACK_SESSION_DEPTH vs AMPLIHACK_MAX_DEPTH=3)
             │         │
           ALLOWED   BLOCKED → [announce-depth-limited banner]
                                    ↓
                           [execute-single-fallback-blocked]
                                    ↓
                           [Execute round 1 (single-session)]
             │
         [Decompose]
             │         │
             1 ws     N ws ──→ [multitask parallel] + tree context in env
             │
         [Execute round 1]
             │
         [Reflect] ──→ ACHIEVED ──→ [Summarize]
             │
           PARTIAL/NOT_ACHIEVED
             │
         [Execute round 2]
             │
         [Reflect] ──→ ACHIEVED ──→ [Summarize]
             │
           PARTIAL/NOT_ACHIEVED
             │
         [Execute round 3 (final)]
             │
         [Final reflect + Summarize]
```

**Session tree enforcement** (prevents infinite recursion):
- Each subprocess inherits `AMPLIHACK_TREE_ID`, `AMPLIHACK_SESSION_DEPTH`, `AMPLIHACK_MAX_DEPTH`
- Depth >= 3: recursion guard blocks sub-workstream spawning, falls back to single-session
- Max 10 concurrent sessions per tree; extras queue in FIFO order
- State tracked in `/tmp/amplihack-session-trees/{tree_id}.json`

## Activation

This skill auto-activates for development and investigation keywords. It is also the
**default behavior** per CLAUDE.md — invoke it for any non-trivial task.

The `UserPromptSubmit` hook reinforces this by injecting a classification reminder
that references `/dev` as the entry point.

## Execution Instructions

When this skill is activated:

### Step 1: Check Recipe Runner availability

```python
try:
    from amplihack.recipes import run_recipe_by_name
    RECIPE_RUNNER_AVAILABLE = True
except ImportError:
    RECIPE_RUNNER_AVAILABLE = False
```

### Step 2: Route to appropriate execution method

**PREFERRED — Recipe Runner (when available)**:

```python
from amplihack.recipes import run_recipe_by_name
from amplihack.recipes.adapters.sdk import ClaudeSDKAdapter

adapter = ClaudeSDKAdapter()
result = run_recipe_by_name(
    "smart-orchestrator",
    adapter=adapter,
    user_context={
        "task_description": TASK_DESCRIPTION,
        "repo_path": ".",
    }
)
```

**FALLBACK — Direct workflow execution (if Recipe Runner unavailable)**:

- Q&A / Operations: Respond directly
- Investigation: `Skill(skill="investigation-workflow")`
- Development with single task: `Skill(skill="default-workflow")`
- Development with parallel tasks: Invoke `Task(subagent_type="general-purpose")` to run
  the multitask orchestrator

### Step 3: Reflect and verify

After execution completes, verify the goal was achieved. If not:

- For missing information: ask the user
- For fixable gaps: re-invoke with the remaining work description

## Task Type Classification

| Type          | Keywords                                                      | Action                        |
| ------------- | ------------------------------------------------------------- | ----------------------------- |
| Q&A           | "what is", "explain", "how do I", "quick question"            | Respond directly              |
| Operations    | "cleanup", "delete", "git status", "run command"              | Execute directly              |
| Investigation | "investigate", "analyze", "how does", "understand", "explore" | investigation-workflow        |
| Development   | "implement", "build", "create", "add", "fix", "refactor"      | smart-orchestrator            |
| Hybrid        | Both investigation + development keywords                     | investigation first, then dev |

## Workstream Decomposition Examples

| Request                                  | Workstreams                             |
| ---------------------------------------- | --------------------------------------- |
| "implement JWT auth"                     | 1: auth (default-workflow)              |
| "build a webui and an api"               | 2: api + webui (parallel)               |
| "add logging and add metrics"            | 2: logging + metrics (parallel)         |
| "investigate auth system then add OAuth" | 2: investigate + implement (sequential) |
| "fix bug in payment flow"                | 1: bugfix (default-workflow)            |

## Override Options

**Single workstream override**: Pass `force_single_workstream: "true"` in the
recipe user_context to prevent automatic parallel decomposition regardless of
task structure. This is a programmatic option (not directly settable from `/dev`):

```python
run_recipe_by_name(
    "smart-orchestrator",
    adapter=adapter,
    user_context={
        "task_description": task,
        "repo_path": ".",
        "force_single_workstream": "true",  # disables parallel decomposition
    }
)
```

## Canonical Sources

- **Recipe**: `amplifier-bundle/recipes/smart-orchestrator.yaml`
- **Parallel execution**: `.claude/skills/multitask/orchestrator.py`
- **Development workflow**: `amplifier-bundle/recipes/default-workflow.yaml`
- **Investigation workflow**: `amplifier-bundle/recipes/investigation-workflow.yaml`
- **CLAUDE.md**: Defines this as the default orchestrator

## Relationship to Other Skills

| Skill                     | Relationship                                         |
| ------------------------- | ---------------------------------------------------- |
| `ultrathink-orchestrator` | Deprecated — redirects here                          |
| `default-workflow`        | Called by this orchestrator for single dev tasks     |
| `investigation-workflow`  | Called by this orchestrator for research tasks       |
| `multitask`               | Called by this orchestrator for parallel workstreams |
| `work-delegator`          | Orthogonal — for backlog-driven delegation           |

## Entry Points

- **Primary**: `/dev <task description>`
- **Auto-activation**: Via CLAUDE.md default behavior + hook injection
- **Legacy**: `/ultrathink <task>` (deprecated alias → redirects to `/dev`)

## Status Signal Reference

The orchestrator uses two status signal formats:

### Execution status (from builder agents)

Appears at the end of round execution steps:

- `STATUS: COMPLETE` — the round's work is fully done
- `STATUS: CONTINUE` — more work remains after this round

### Goal status (from reviewer agents)

Appears at the end of reflection steps:

- `GOAL_STATUS: ACHIEVED` — all success criteria met, task is done
- `GOAL_STATUS: PARTIAL — [description]` — some criteria met, more work needed
- `GOAL_STATUS: NOT_ACHIEVED — [reason]` — goal not met, another round needed

The goal-seeking loop uses GOAL_STATUS signals to decide whether to run round 2 or 3.

**BLOCKED path (recursion guard)**: When multi-workstream spawning is blocked
by the depth limit, the orchestrator falls back to single-session execution:
1. `announce-depth-limited` — prints a warning banner with remediation info
2. `execute-single-fallback-blocked` — executes the full task as a single
   builder agent session (same as single-workstream path, produces
   `STATUS: COMPLETE` or `STATUS: CONTINUE`)
