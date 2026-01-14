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

## Hook Modules

These Amplifier modules wrap existing Claude Code hooks:

| Module | Wraps | Purpose |
|--------|-------|---------|
| `hook-power-steering` | `power_steering_*.py` | Session completion verification |
| `hook-memory` | `agent_memory_hook.py` | Persistent memory injection/extraction |
| `hook-pre-tool-use` | `pre_tool_use.py` | Block dangerous operations |
| `hook-pre-compact` | `pre_compact.py` | Export transcript before compaction |
| `hook-user-prompt` | `user_prompt_submit.py` | Inject user preferences |

### Already Covered by Amplifier

These Claude Code hooks have Amplifier equivalents in foundation:

| Claude Code | Amplifier Module | Notes |
|-------------|------------------|-------|
| `session_start.py` | `hooks-logging` | Session lifecycle logging |
| `session_stop.py` | `hooks-logging` | Session end logging |
| `post_tool_use.py` | `hooks-logging`, `hooks-streaming-ui` | Tool execution tracking |
| `workflow_tracker.py` | `hooks-todo-reminder` | Workflow state injection |

## Compatibility

This bundle maintains compatibility with both:
- **Claude Code** - Via the `.claude/` directory structure
- **Amplifier** - Via this bundle packaging with hook wrappers

The same skills, agents, and context work in both environments. Hook modules delegate to the existing Claude Code implementations, avoiding duplication while providing Amplifier compatibility.
