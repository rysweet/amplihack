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

The `UserPromptSubmit` hook reinforces this by injecting a classification prompt
that instructs Claude to invoke `Skill(skill="dev-orchestrator")` for dev/investigation tasks.

## Execution Instructions

**CRITICAL**: Development and Investigation tasks have exactly ONE execution
path: the recipe runner via `run_recipe_by_name("smart-orchestrator")`.
Direct classification, direct skill invocation, or inline workflow execution
are PROHIBITED for these task types. Violations skip the 23-step workflow,
recursion guards, and goal verification.

When this skill is activated:

### REQUIRED: Execute via Recipe Runner

```python
from amplihack.recipes import run_recipe_by_name
from amplihack.recipes.adapters import ClaudeSDKAdapter

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

**There are no fallback paths for Development or Investigation tasks.** The
recipe runner is required. If it fails with an ImportError, report the error
to the user and stop. Do not silently fall back to direct skill invocation
or manual classification.

**Q&A and Operations only** may bypass the recipe runner:

- Q&A: Respond directly (analyzer agent)
- Operations: Builder agent (direct execution, no workflow steps)

### After Execution: Reflect and verify

After execution completes, verify the goal was achieved. If not:

- For missing information: ask the user
- For fixable gaps: re-invoke with the remaining work description

## Task Type Classification

| Type          | Keywords                                                       | Action                                              |
| ------------- | -------------------------------------------------------------- | --------------------------------------------------- |
| Q&A           | "what is", "explain", "how does", "how do I", "quick question" | Respond directly                                    |
| Operations    | "clean up", "delete", "git status", "run command"              | builder agent (direct execution, no workflow steps) |
| Investigation | "investigate", "analyze", "understand", "explore"              | investigation-workflow                              |
| Development   | "implement", "build", "create", "add", "fix", "refactor"       | smart-orchestrator                                  |
| Hybrid\*      | Both investigation + development keywords                      | Decomposed into investigation + dev workstreams     |

\* Hybrid is not a distinct task_type — the orchestrator classifies as Development and decomposes into multiple workstreams (one investigation, one development).

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

**To force single-workstream execution without modifying recipe context:**
Set `AMPLIHACK_MAX_DEPTH=0` before running `/dev`. This causes the recursion guard
to block parallel spawning and fall back to single-session mode for all tasks:

```bash
export AMPLIHACK_MAX_DEPTH=0  # set in your shell first
/dev build a webui and an api  # then type in Claude Code
```

Note: The env var must be set in your shell before starting Claude Code — it cannot
be prefixed inline on the `/dev` command. This affects all depth checks, not just
parallel workstream spawning.

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
- `STATUS: PARTIAL` — the final round (round 3) reached partial completion
- `STATUS: DEPTH_LIMITED` — (legacy, no longer emitted; use BLOCKED path instead)

### Goal status (from reviewer agents)

Appears at the end of reflection steps:

- `GOAL_STATUS: ACHIEVED` — all success criteria met, task is done
- `GOAL_STATUS: PARTIAL -- [description]` — some criteria met, more work needed
- `GOAL_STATUS: NOT_ACHIEVED -- [reason]` — goal not met, another round needed

The goal-seeking loop uses GOAL_STATUS signals to decide whether to run round 2 or 3.

**BLOCKED path (recursion guard)**: When multi-workstream spawning is blocked
by the depth limit, the orchestrator falls back to single-session execution:

1. `announce-depth-limited` — prints a warning banner with remediation info
2. `execute-single-fallback-blocked` — executes the full task as a single
   builder agent session (same as single-workstream path, produces
   `STATUS: COMPLETE` or `STATUS: CONTINUE`)
