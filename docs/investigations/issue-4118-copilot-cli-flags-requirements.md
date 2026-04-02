# Requirements: Fix Smart-Orchestrator Copilot CLI Flag Compatibility

**Issues**: #4118, #4108, #4107 (duplicates, same root cause)
**Date**: 2026-04-02
**Classification**: Bugfix
**Complexity**: Simple-Medium (30-60 lines, 2-4 hours)

## Task Summary

Make CLI flag injection in smart-orchestrator classify-and-decompose step conditional on agent binary type to prevent Copilot failures.

## Root Cause

When `AMPLIHACK_AGENT_BINARY=copilot`, several Python code paths unconditionally pass Claude-specific CLI flags (`--dangerously-skip-permissions`, `--append-system-prompt`) that the Copilot binary rejects with `error: unknown option --dangerously-skip-permissions` (exit 1).

## Affected Code Paths

### 1. `launcher/core.py` `build_claude_command()` (lines 513, 556)

Unconditionally adds `--dangerously-skip-permissions` and `--append-system-prompt`. This is the primary launcher entry point. **NEEDS FIX.**

### 2. `launcher/auto_mode.py` `_run_sdk_subprocess()` (lines 345-357)

The `else` branch (line 356-357) reads `AMPLIHACK_AGENT_BINARY` but then unconditionally passes `--dangerously-skip-permissions`. The `copilot` and `codex` branches (lines 345-354) are correctly handled with their own flag sets. **NEEDS FIX** in the else-branch.

### 3. `amplifier-bundle/tools/amplihack/orchestration/claude_process.py` (lines 22-26)

`DELEGATE_COMMANDS` dict already correctly maps Copilot to `--subprocess-safe` instead of `--dangerously-skip-permissions`. **ALREADY FIXED.**

### 4. `recipes/rust_runner_execution.py` (line 105)

Already has Copilot-aware env handling (`AMPLIHACK_COPILOT_NESTED`). **ALREADY FIXED.**

## Explicit Requirements (CANNOT be optimized away)

1. When `AMPLIHACK_AGENT_BINARY=copilot` (or any non-Claude binary), the flags `--dangerously-skip-permissions`, `--disallowed-tools`, and `--append-system-prompt` MUST NOT be passed on the CLI
2. When `AMPLIHACK_AGENT_BINARY=claude` (or unset/default), existing Claude-specific flags MUST continue to be passed exactly as before -- no regression
3. The fix must cover ALL code paths that build CLI invocations for agent subprocesses
4. If a non-Claude agent binary cannot support classification, the system MUST fail loudly -- no silent degradation
5. Issues #4118, #4108, #4107 must all be closeable by this fix

## Acceptance Criteria

- [ ] `AMPLIHACK_AGENT_BINARY=copilot amplihack dev 'any task'` does NOT produce `error: unknown option --dangerously-skip-permissions`
- [ ] `AMPLIHACK_AGENT_BINARY=copilot amplihack dev 'any task'` does NOT produce `error: unknown option --append-system-prompt`
- [ ] `AMPLIHACK_AGENT_BINARY=copilot amplihack dev 'any task'` does NOT produce `error: unknown option --disallowed-tools`
- [ ] Default (claude) binary still passes `--dangerously-skip-permissions` and works identically
- [ ] Unit tests verify: (a) Claude delegate gets Claude-specific flags, (b) Copilot delegate does NOT, (c) Unknown delegate falls back safely with warning
- [ ] `launcher/core.py` `build_claude_command()` is conditional on agent binary
- [ ] `auto_mode.py` `_run_sdk_subprocess()` else-branch does not pass `--dangerously-skip-permissions` when agent != claude

## Out of Scope

- Changing the Copilot CLI itself or its flag surface
- Adding new Copilot-specific equivalent flags
- Modifying the Rust recipe runner binary
- ~~Changing `smart-orchestrator.yaml` recipe definition~~ (moved to in-scope: classify-and-decompose bash step was a root cause)
- Fixing other Copilot compatibility issues beyond the three flagged issues

## Assumptions

1. The Rust recipe runner binary reads `AMPLIHACK_AGENT_BINARY` from env and selects the appropriate agent binary
2. `claude_process.py` `DELEGATE_COMMANDS` already correctly handles Copilot (uses `--subprocess-safe`)
3. The remaining unfixed paths are `launcher/core.py` and `auto_mode.py`
4. `--disallowed-tools` flag not found in Python codebase -- may be Rust-runner-only or planned. If not present, no change needed
5. Issues #4118, #4108, #4107 are duplicates with the same root cause

## Implementation Notes for Builder

**Pattern to follow**: See `claude_process.py` `DELEGATE_COMMANDS` dict and `_build_command()` method -- this is the reference implementation that already works correctly.

**Key detection**: Use `os.environ.get("AMPLIHACK_AGENT_BINARY", "claude")` to determine the binary. If not "claude", omit Claude-specific flags.

**Files to modify**:

1. `src/amplihack/launcher/core.py` -- Make `build_claude_command()` agent-binary-aware
2. `src/amplihack/launcher/auto_mode.py` -- Fix else-branch in `_run_sdk_subprocess()`
3. Add/extend tests in the relevant test directories

## Structured Output

```json
{
  "task_summary": "Make CLI flag injection in smart-orchestrator classify-and-decompose step conditional on agent binary type to prevent Copilot failures",
  "explicit_requirements": [
    "When AMPLIHACK_AGENT_BINARY=copilot, omit --dangerously-skip-permissions, --disallowed-tools, --append-system-prompt",
    "When AMPLIHACK_AGENT_BINARY=claude (or unset), keep all existing flags -- no regression",
    "Fix launcher/core.py build_claude_command() and auto_mode.py _run_sdk_subprocess()",
    "Fail loudly if non-Claude binary cannot support classification",
    "Close issues #4118, #4108, #4107"
  ],
  "acceptance_criteria": [
    "AMPLIHACK_AGENT_BINARY=copilot does not produce unknown option errors",
    "Default claude binary works identically to current behavior",
    "Unit tests cover Claude, Copilot, and unknown delegate cases",
    "launcher/core.py and auto_mode.py are agent-binary-aware"
  ],
  "out_of_scope": [
    "Changing Copilot CLI flag surface",
    "Modifying Rust recipe runner binary",
    "Changing smart-orchestrator.yaml recipe definition",
    "Other Copilot compatibility issues"
  ],
  "assumptions": [
    "claude_process.py DELEGATE_COMMANDS already correctly handles Copilot",
    "Remaining unfixed paths are launcher/core.py and auto_mode.py",
    "--disallowed-tools not in Python codebase, may not need changes"
  ],
  "questions_resolved": [
    "Flags are injected in Python CLI builders, not in recipe YAML",
    "claude_process.py is already fixed via DELEGATE_COMMANDS",
    "--disallowed-tools not found in codebase grep"
  ],
  "estimated_complexity": "medium",
  "classification": "bugfix"
}
```
