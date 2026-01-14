# Amplifier-Specific Instructions

This document provides Amplifier-specific guidance for the amplihack bundle.

## Bundle Structure

This is a **thin bundle** that references existing Claude Code components without duplication:

- Skills, agents, and context are in `../.claude/`
- Hook modules wrap existing Claude Code implementations
- No code duplication - same components work in both environments

## Using with Amplifier

### Direct Usage
```bash
amplifier run --bundle amplihack
```

### As a Dependency
```yaml
includes:
  - bundle: git+https://github.com/rysweet/amplihack@main#amplifier-bundle
```

## What's Referenced

| Component | Location | Count |
|-----------|----------|-------|
| Skills | `../.claude/skills/` | 62 |
| Agents | `../.claude/agents/` | 36 |
| Context | `../.claude/context/` | 3 files |
| Workflows | `../.claude/workflow/` | 7 docs |

## Hook Modules (8 Total)

All hook modules wrap existing Claude Code hooks via lazy imports, delegating to the original implementations while providing Amplifier compatibility.

### Session Lifecycle Hooks

| Module | Wraps | Purpose |
|--------|-------|---------|
| `hook-session-start` | `session_start.py` | Version mismatch detection, auto-update, global hook migration, preferences injection, Neo4j startup, context injection |
| `hook-session-stop` | `session_stop.py` | Learning capture, memory storage via MemoryCoordinator (SQLite/Neo4j) |
| `hook-post-tool-use` | `post_tool_use.py` | Tool registry execution, metrics tracking, error detection for file ops |

### Feature Hooks

| Module | Wraps | Purpose |
|--------|-------|---------|
| `hook-power-steering` | `power_steering_*.py` | Session completion verification (21 considerations) |
| `hook-memory` | `agent_memory_hook.py` | Persistent memory injection on prompt, extraction on session end |
| `hook-pre-tool-use` | `pre_tool_use.py` | Block dangerous operations (--no-verify, rm -rf) |
| `hook-pre-compact` | `pre_compact.py` | Export transcript before context compaction |
| `hook-user-prompt` | `user_prompt_submit.py` | Inject user preferences on every prompt |

### Foundation Coverage

The `workflow_tracker` functionality is covered by `hooks-todo-reminder` from Amplifier foundation.

## Design Principles

### Thin Wrapper Pattern

Each hook module follows the same pattern:
1. Lazy load the Claude Code implementation on first use
2. Delegate to the original implementation
3. Fail open - never block user workflow on hook errors
4. Log failures at debug level for diagnostics

### Path Resolution

Wrappers resolve Claude Code paths relative to the bundle location:
```
amplifier-bundle/modules/hook-*/  →  .claude/tools/amplihack/hooks/
```

### Fail-Open Philosophy

All hooks are designed to fail gracefully:
- Missing dependencies → skip functionality
- Exceptions → log and continue
- Never block the user's workflow

## Compatibility

This bundle maintains compatibility with both:
- **Claude Code** - Via the `.claude/` directory structure
- **Amplifier** - Via this bundle packaging with hook wrappers

The same skills, agents, and context work in both environments.
