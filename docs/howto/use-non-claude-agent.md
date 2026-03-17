# How to Use amplihack with a Non-Claude Agent

amplihack is agent-agnostic. While it defaults to `claude` (Claude Code CLI),
you can run any compatible agent binary by setting the `AMPLIHACK_AGENT_BINARY`
environment variable.

## Prerequisites

- amplihack installed and configured
- Your target agent CLI installed and in `PATH`

## Set the agent binary

```bash
export AMPLIHACK_AGENT_BINARY=your-agent-binary
```

All subprocess orchestration — including nested agents spawned by the recipe
runner, fleet, multi-task, and auto_mode — will use this binary.

### Examples

```bash
# Use the default (Claude Code)
export AMPLIHACK_AGENT_BINARY=claude

# Use GitHub Copilot CLI (if installed)
export AMPLIHACK_AGENT_BINARY=copilot
```

## Verify propagation

After setting the variable, confirm it is visible to subprocesses:

```bash
amplihack env | grep AMPLIHACK_AGENT_BINARY
# Should print: AMPLIHACK_AGENT_BINARY=your-agent-binary
```

When the recipe runner launches nested agent steps, it inherits this variable.
You will see `AMPLIHACK_AGENT_BINARY` in the child process environment rather
than a hardcoded `claude` invocation.

## Fallback behaviour

If `AMPLIHACK_AGENT_BINARY` is not set, amplihack falls back to `claude` and
emits a warning:

```
WARNING: AMPLIHACK_AGENT_BINARY is not set; defaulting to 'claude'.
         Set AMPLIHACK_AGENT_BINARY to suppress this warning.
```

This preserves backward compatibility for environments that do not set the
variable (direct Python imports, existing test suites, legacy configurations).

## Python API (knowledge builder)

If you call the knowledge builder directly from Python, note that the
`claude_cmd` parameter was renamed to `agent_cmd` in March 2026:

```python
# Old (deprecated)
orchestrator = KnowledgeOrchestrator(claude_cmd="claude")

# New
orchestrator = KnowledgeOrchestrator(agent_cmd="claude")
```

## Nested agent sessions

The dev-orchestrator recipe runner preserves `AMPLIHACK_AGENT_BINARY` when
launching sub-recipes. If you set the variable before your first `/dev` call,
all workstreams — including parallel ones — inherit it.

## See Also

- [Dev-Orchestrator Tutorial](../tutorials/dev-orchestrator-tutorial.md#execution-modes)
- [Recent Fixes March 2026](../recipes/RECENT_FIXES_MARCH_2026.md#agent-agnostic-binary-selection-pr-3174)
