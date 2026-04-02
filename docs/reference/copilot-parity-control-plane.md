---
title: "Copilot Parity Control Plane Reference"
description: "Reference for the Copilot launcher wrapper contract, XPIA precedence, Rust runner discovery, and nested Copilot normalization."
last_updated: 2026-04-02
review_schedule: as-needed
owner: amplihack
doc_type: reference
---

# Copilot Parity Control Plane Reference

## Overview

The Copilot parity control plane gives GitHub Copilot CLI the same staged amplihack surfaces that Claude Code receives through `.claude/` settings, while respecting Copilot's native `.github/` hook and agent discovery model.

## Components

| Component                          | Path                                               | Responsibility                                                                                                       |
| ---------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Copilot launcher                   | `src/amplihack/launcher/copilot.py`                | Stages agents, hooks, commands, recipes, and generated wrappers before launching Copilot CLI                         |
| Rust recipe runner bridge          | `src/amplihack/recipes/rust_runner.py`             | Discovers `recipe-runner-rs`, enforces version compatibility, builds subprocess environment, and parses JSON results |
| Nested Copilot compatibility layer | `src/amplihack/recipes/rust_runner_copilot.py`     | Merges prompt fragments and injects permissive defaults only when explicit Copilot permission flags are absent       |
| Smart-orchestrator classify step   | `amplifier-bundle/recipes/smart-orchestrator.yaml` | Case-switches on `AMPLIHACK_AGENT_BINARY` to omit Claude-only flags for Copilot/codex binaries                       |
| Canonical XPIA hook                | `.claude/tools/xpia/hooks/pre_tool_use.py`         | Fail-closed Bash policy evaluation backed by `xpia-defend`                                                           |
| XPIA compatibility shim            | `.claude/tools/xpia/hooks/pre_tool_use_rust.py`    | Delegates to `pre_tool_use.py` so both historical entrypoints behave identically                                     |
| Generated wrapper                  | `.github/hooks/pre-tool-use`                       | Emits the single Copilot-facing permission payload after evaluating amplihack and XPIA outputs                       |

## Generated Copilot Hook Wrappers

| Wrapper                            | Generated scripts                                              | Notes                                                                |
| ---------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| `.github/hooks/session-start`      | `session_start.py`                                             | Single-script wrapper                                                |
| `.github/hooks/session-stop`       | `stop.py`, `session_stop.py`                                   | Multi-script wrapper; captures stdin once and pipes it to both hooks |
| `.github/hooks/pre-tool-use`       | `pre_tool_use.py` plus XPIA `pre_tool_use.py`                  | Special wrapper with JSON aggregation                                |
| `.github/hooks/post-tool-use`      | `post_tool_use.py`                                             | Single-script wrapper                                                |
| `.github/hooks/user-prompt-submit` | `user_prompt_submit.py`, `workflow_classification_reminder.py` | Multi-script wrapper                                                 |

## Pre-Tool-Use Decision Precedence

The generated `.github/hooks/pre-tool-use` wrapper evaluates both hook stacks and emits one final JSON object.

| Priority | Source    | Accepted signal                                  | Result                                                   |
| -------- | --------- | ------------------------------------------------ | -------------------------------------------------------- |
| 1        | XPIA      | `permissionDecision` = `allow`, `deny`, or `ask` | Return the XPIA payload unchanged                        |
| 2        | amplihack | `permissionDecision` = `allow`, `deny`, or `ask` | Return the amplihack payload unchanged                   |
| 3        | amplihack | `block: true`                                    | Convert to `{"permissionDecision":"deny","message":...}` |
| 4        | none      | no explicit decision                             | Return `{}`                                              |

This contract keeps XPIA in control of explicit Bash security decisions while preserving existing amplihack block semantics.

## XPIA Hook Contract

### Input

`pre_tool_use.py` accepts JSON on stdin or as the first argv value.

```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "pwd"
  },
  "cwd": "/path/to/repo",
  "session_id": "optional-session-id"
}
```

### Output

Allow:

```json
{}
```

Deny:

```json
{
  "permissionDecision": "deny",
  "message": "..."
}
```

### Canonical and compatibility entrypoints

| Entrypoint                                      | Behavior                        |
| ----------------------------------------------- | ------------------------------- |
| `.claude/tools/xpia/hooks/pre_tool_use.py`      | Canonical fail-closed hook      |
| `.claude/tools/xpia/hooks/pre_tool_use_rust.py` | Delegates to the canonical hook |

### Audit logging

The canonical XPIA hook writes audit events to:

```text
~/.claude/logs/xpia/rust_security_YYYYMMDD.log
```

## Rust Runner Discovery and Execution

### Binary discovery order

`rust_runner.py` resolves the runner in this order:

1. `RECIPE_RUNNER_RS_PATH`
2. `recipe-runner-rs` on `PATH`
3. `~/.cargo/bin/recipe-runner-rs`
4. `~/.local/bin/recipe-runner-rs`

If the runner is still missing, the bridge raises `RustRunnerNotFoundError`.

### Version gating

The bridge checks the discovered binary before execution. Unknown, unparseable, or too-old versions are rejected with an explicit version error. The Rust-selected path does not silently fall back to a Python runner.

### Startup banners

The bridge emits two stderr banners during execution:

```text
[amplihack] recipe-runner --- starting: <recipe>
[amplihack] recipe-runner --- executing: <recipe>
```

### Response contract

The Rust runner must emit JSON on stdout. If stdout is unparseable:

- non-zero exit codes become explicit runtime errors
- signal termination is surfaced as a signal-specific error
- empty or malformed stdout becomes an "unparseable output" error

## Smart-Orchestrator Classify Step

The `classify-and-decompose` step in `smart-orchestrator.yaml` uses a `bash`
step type with a case-switch on `AMPLIHACK_AGENT_BINARY`:

| Binary pattern         | Flags used                                                                       | Classifier constraint               |
| ---------------------- | -------------------------------------------------------------------------------- | ----------------------------------- |
| `*copilot*`, `*codex*` | `--allow-all-tools`                                                              | Injected into prompt text           |
| `*` (default/claude)   | `--dangerously-skip-permissions`, `--disallowed-tools`, `--append-system-prompt` | Passed via `--append-system-prompt` |

Both branches unset `CLAUDECODE` via `env -u CLAUDECODE` to prevent the
subprocess from detecting a parent Claude Code session, which would alter
agent behavior. Both branches deliver the prompt via `-p`.

On failure, the step emits the binary name, exit code, and stderr content (or a
diagnostic hint if stderr is empty) before propagating the exit code.

**Fixed in:** commit `3dc141ccb` (issues #4118, #4108, #4107).

## Nested Copilot Normalization Rules

The compatibility layer normalizes nested Copilot launches created by the Rust recipe runner.

### Prompt merging

The normalizer removes and merges these flags into one final `-p` payload:

- `--system-prompt`
- `--append-system-prompt`
- `-p`
- `--prompt=`

Merged prompt parts are joined with a blank line.

The normalizer also drops Claude-only `--dangerously-skip-permissions` because
Copilot CLI does not accept it.

### Permission preservation

The normalizer treats these as explicit tool-permission flags:

- `--allow-all-tools`
- `--allow-tool`
- `--deny-tool`

It treats these as explicit path-permission flags:

- `--allow-all-paths`
- `--allow-path`
- `--deny-path`

If no explicit tool or path permission appears, it prefixes the nested command with:

```text
--allow-all-tools --allow-all-paths
```

If explicit flags are already present, it preserves them and does not widen permissions.

When a Claude-oriented nested launch passes `--disallowed-tools`, the normalizer
removes that unsupported flag, treats it as an explicit no-tools decision, and
adds a no-tools instruction to the merged prompt. That prevents the wrapper from
re-introducing `--allow-all-tools` behind the caller's back.

## Environment Variables

| Variable                        | Scope                      | Default     | Meaning                                               |
| ------------------------------- | -------------------------- | ----------- | ----------------------------------------------------- |
| `AMPLIHACK_AGENT_BINARY`        | launcher and nested runner | `claude`    | Selects the agent binary for nested recipe execution  |
| `AMPLIHACK_HOOK_ENGINE`         | launcher                   | auto-detect | Selects `rust` or `python` for amplihack hook staging |
| `RECIPE_RUNNER_RS_PATH`         | Rust runner bridge         | unset       | Explicit path to `recipe-runner-rs`                   |
| `RECIPE_RUNNER_INSTALL_TIMEOUT` | Rust runner install helper | `300`       | Timeout, in seconds, for auto-install attempts        |

## Context Spillover Rules

Large recipe context values are passed safely.

| Limit                   | Behavior                                             |
| ----------------------- | ---------------------------------------------------- |
| `< 32,768` UTF-8 bytes  | Passed inline via `--set key=value`                  |
| `>= 32,768` UTF-8 bytes | Spilled to a temp file and passed as a `file://` URI |

Spill directories are created with `tempfile.mkdtemp(...)`, which produces a private process-scoped directory and avoids predictable temp paths.

## Safe Command Example

```bash
printf '%s\n' '{"tool_name":"Bash","tool_input":{"command":"pwd"}}' \
  | python3 .claude/tools/xpia/hooks/pre_tool_use.py
# Output: {}
```

## Related Documents

- [Tutorial: Enable the Copilot parity control plane](../tutorials/copilot-parity-control-plane.md)
- [How to Configure the Copilot Parity Control Plane](../howto/configure-copilot-parity-control-plane.md)
- [Understanding the Copilot Parity Control Plane](../concepts/copilot-parity-control-plane.md)
- [Hooks Comparison](../HOOKS_COMPARISON.md)
