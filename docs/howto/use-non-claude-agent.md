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
printenv AMPLIHACK_AGENT_BINARY
# Should print: your-agent-binary
```

When the recipe runner launches nested agent steps, it inherits this variable.
You will see `AMPLIHACK_AGENT_BINARY` in the child process environment rather
than a hardcoded `claude` invocation.

## Fallback behaviour

If `AMPLIHACK_AGENT_BINARY` is not set, amplihack falls back to `claude` and
emits a warning that the variable was not set and `claude` is being used as
the fallback agent. The exact wording varies slightly between top-level
launcher code paths and nested Rust-runner code paths.

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

### Nested Copilot prompt compatibility

Nested Copilot launches still need a small compatibility bridge because the
Rust recipe runner can emit Claude-style prompt flags that Copilot CLI does
not accept directly.

When `AMPLIHACK_AGENT_BINARY=copilot`, amplihack prepends a narrow wrapper to
`PATH` for nested recipe-runner launches only. That wrapper:

- rewrites `--system-prompt` and `--append-system-prompt` into one merged `-p`
  prompt for Copilot CLI
- drops Claude-only `--dangerously-skip-permissions`
- converts Claude-style `--disallowed-tools` into a no-tools prompt instruction
  without reintroducing `--allow-all-tools`
- preserves explicit Copilot permission flags when they are already present
- injects broad Copilot permission defaults only when the nested launch did not
  provide explicit permission flags
- leaves top-level `amplihack copilot` launcher behavior unchanged

This is an adapter for the current nested launch contract, not a general
argument normalization layer for every Copilot invocation.

## Smart-orchestrator classify step

The `/dev` command uses the smart-orchestrator recipe, which begins with a
`classify-and-decompose` step. This step invokes the agent binary to classify
the task as Q&A, Operations, Investigation, or Development.

When `AMPLIHACK_AGENT_BINARY=copilot` (or any `*copilot*`/`*codex*` binary),
the classify step automatically:

- Omits `--dangerously-skip-permissions`, `--disallowed-tools`, and
  `--append-system-prompt` (Claude-only flags that Copilot rejects)
- Uses `--allow-all-tools` instead
- Injects the classifier constraint directly into the prompt text

When the agent binary is `claude` (or unset), the existing Claude-specific flags
are passed as before.

If the classify step fails (non-zero exit), the recipe prints the agent binary
name, exit code, and stderr to help diagnose the issue. Common causes include
the binary not being installed, a missing API key, or network problems.

## See Also

- [Dev-Orchestrator Tutorial](../tutorials/dev-orchestrator-tutorial.md#execution-modes)
- [Tutorial: Enable the Copilot parity control plane](../tutorials/copilot-parity-control-plane.md)
- [How to Configure the Copilot Parity Control Plane](./configure-copilot-parity-control-plane.md)
- [Copilot Parity Control Plane Reference](../reference/copilot-parity-control-plane.md)
- [Recent Fixes March 2026](../recipes/RECENT_FIXES_MARCH_2026.md#agent-agnostic-binary-selection-pr-3174)
