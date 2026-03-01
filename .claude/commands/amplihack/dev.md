---
name: dev
version: 2.0.0
description: |
  Primary entry point for all development and investigation work.
  Classifies task, decomposes into workstreams if parallel-capable,
  and launches execution via recipe runner. The default orchestrator.
triggers:
  - "implement"
  - "build"
  - "create"
  - "fix"
  - "refactor"
  - "investigate"
  - "develop"
  - "make"
  - "add feature"
invokes:
  - type: recipe
    name: smart-orchestrator
  - type: recipe
    name: default-workflow
  - type: recipe
    name: investigation-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/smart-orchestrator.yaml
examples:
  - "/dev add user authentication"
  - "/dev build a webui and an API for user management"
  - "/dev fix the login timeout bug"
  - "/dev investigate how the caching layer works"
  - "/dev implement OAuth and add structured logging"
---

# Dev Command

## Usage

`/dev <TASK_DESCRIPTION>`

The primary entry point for all development work in amplihack. This command
classifies your task, detects parallel workstreams, and executes via recipe runner.

## Glossary

**Workstream**: An isolated parallel execution unit. When your request contains multiple independent components (e.g., "build an API and a webui"), the orchestrator splits them into separate workstreams that run concurrently in `/tmp/amplihack-workstreams/`.

**Recipe**: A YAML workflow definition that specifies the exact sequence of steps Claude follows. The `smart-orchestrator` recipe is what runs when you invoke `/dev`.

**Recipe Runner**: The Python execution engine (`amplihack.recipes.run_recipe_by_name`) that executes recipes with code-enforced step ordering. It is the REQUIRED execution method for all Development and Investigation tasks. There is no prompt-based alternative.

**Session Tree**: A lightweight state tracker in `/tmp/amplihack-session-trees/` that prevents infinite recursive orchestration by tracking active sessions and enforcing depth and capacity limits.

**Goal-Seeking Loop**: The up-to-3-round retry mechanism. After each execution
round, a reviewer agent evaluates whether the goal was achieved. If PARTIAL or
NOT_ACHIEVED, another round runs automatically (up to 3 total). After all rounds
complete, a `reflect-final` step runs for all completed development and investigation tasks to produce the
definitive `GOAL_STATUS` assessment used in the summary.

**Recursion Guard Fallback**: When the session depth limit is reached and
parallel workstream spawning is blocked, the orchestrator automatically falls
back to single-session execution (via `execute-single-fallback-blocked`). The
task runs as a single Claude session without sub-workstream spawning.

## Examples

**Single task** (one workstream):

```
/dev fix the authentication bug where tokens expire too early
/dev add pagination to the user listing API
/dev investigate how the caching layer works
```

**Parallel tasks** (multiple workstreams launched simultaneously):

```
/dev build a REST API and a React webui for user management
/dev add OAuth support and add structured logging
/dev investigate the auth system then implement refresh tokens
```

## What to Expect During Execution

When you run `/dev fix the login bug`, here is what you will see:

1. **Classification** (~1 minute): The orchestrator analyzes your request and outputs a structured plan. You will see agent reasoning and a JSON decomposition.

2. **Execution** (~5–15min for a typical bug fix, longer for complex features): The builder agent does the actual work — you will see detailed implementation output streaming in real time.

3. **Reflection** (~1 minute): A reviewer evaluates whether the goal was achieved. If not, another round runs automatically (up to 3 total). You will see `GOAL_STATUS: PARTIAL` or `GOAL_STATUS: ACHIEVED` in the output.

4. **Summary**: When complete, look for `# Dev Orchestrator -- Execution Complete` at the bottom. This contains the structured summary including PR links and goal status.

> **Timing varies significantly** based on task complexity, model load, and number of reflection rounds.
> Simple Q&A: seconds. Typical bug fix: 5–15 minutes. Complex multi-workstream features: 30+ minutes.

**If execution takes longer than 2 minutes with no output**, the agent is working — there are no progress bars between major steps.

**If you see `BLOCKED`**: parallel workstream spawning was limited. Your task will still complete as a single-session execution.

## Auto-Routing (Without Typing /dev)

The `UserPromptSubmit` hook automatically injects intent-routing guidance on
every message (except slash commands and short conversational turns). Claude
classifies your intent and invokes `dev-orchestrator` when appropriate.

- **Disable**: `/amplihack:no-auto-dev` (toggles instantly, no restart needed)
- **Re-enable**: `/amplihack:auto-dev`
- **Override for one prompt**: Include "just answer" or "without workflow"
- **Legacy env var**: `export AMPLIHACK_AUTO_DEV=false` (still works)
- **Details**: See the [auto-routing tutorial section](../../../docs/tutorials/dev-orchestrator-tutorial.md#auto-routing-how-it-works)

## How It Works

```
/dev <request>
      │
      ▼
[smart-orchestrator recipe]
      │
      ├─ Q&A ──────────────────────────────→ analyzer agent (direct answer)
      │
      ├─ Ops ──────────────────────────────→ builder agent (executes operation)
      │
      ├─ 1 workstream ──────────────────────→ default-workflow recipe
      │
      ├─ N workstreams (parallel) ──────────→ multitask orchestrator
      │         [if BLOCKED by depth limit: falls back to]
      └─────────────────────────────────────→ single-session execution
                                                    │
                                                    ▼
                                           [Reflect on goal]
```

## Task Description

```
{TASK_DESCRIPTION}
```

## EXECUTION INSTRUCTIONS FOR CLAUDE

> **Note for users**: The section below documents how Claude internally executes this command. You do not need to run any of this code yourself — just type `/dev <your task>`.

**CRITICAL**: Development and Investigation tasks have exactly ONE execution
path: the recipe runner via `run_recipe_by_name("smart-orchestrator")`.
Direct classification, direct skill invocation, or inline workflow execution
are PROHIBITED for these task types. Violations skip the 23-step workflow,
recursion guards, and goal verification.

When this command is invoked with `{TASK_DESCRIPTION}`:

### REQUIRED: Execute via Recipe Runner

> Note: `{TASK_DESCRIPTION}` below is the literal user text passed to this command.
> Claude must substitute the actual task text — do not pass the string `"{TASK_DESCRIPTION}"`.

```python
from amplihack.recipes import run_recipe_by_name
from amplihack.recipes.adapters import ClaudeSDKAdapter

# IMPORTANT: Replace TASK_DESCRIPTION with the actual user request text
task = "<the actual task from the user>"

adapter = ClaudeSDKAdapter()
result = run_recipe_by_name(
    "smart-orchestrator",
    adapter=adapter,
    user_context={
        "task_description": task,  # actual text, not literal "{TASK_DESCRIPTION}"
        "repo_path": ".",
    }
)
```

**There are no fallback paths.** The recipe runner is the only execution method
for Development and Investigation tasks. If the recipe runner fails with an
ImportError, report the error to the user and stop. Do NOT silently fall back
to direct execution, skill invocation, or manual classification.
