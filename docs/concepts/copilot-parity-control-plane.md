---
title: "Understanding the Copilot Parity Control Plane"
description: "Why amplihack uses a generated Copilot wrapper, strict Rust-runner execution, and a fail-closed XPIA bridge to reach Python-Rust parity."
last_updated: 2026-03-24
review_schedule: as-needed
owner: amplihack
doc_type: explanation
---

# Understanding the Copilot Parity Control Plane

## What It Is

The Copilot parity control plane is the part of amplihack that makes GitHub Copilot CLI behave like a first-class amplihack runtime without pretending that Copilot and Claude Code expose the same hook surface.

It does three things:

- stages amplihack behavior into Copilot's `.github/` discovery model
- preserves strict Rust-runner execution for recipes instead of silently falling back
- keeps Bash security fail-closed through the canonical XPIA hook backed by `xpia-defend`

## Why It Exists

Claude Code and GitHub Copilot CLI both support hooks, but they do not support the same hook capabilities.

- Claude Code can inject context through hook output.
- Copilot CLI can block tool use through `pre-tool-use`, but it does not support the same context-injection contract.
- Recipe execution can launch nested agents, and Copilot does not accept every Claude-style prompt flag directly.

Without a parity control plane, the same amplihack feature would behave differently depending on which top-level CLI launched it.

## How the Pieces Fit Together

### 1. The launcher stages a Copilot-native surface

`src/amplihack/launcher/copilot.py` generates `.github/hooks/*` wrappers and stages agents into `.github/agents/`. That keeps Copilot on its native discovery path instead of layering a second configuration mechanism on top.

### 2. The pre-tool wrapper emits exactly one decision

Copilot expects one JSON permission payload on stdout. The generated `.github/hooks/pre-tool-use` wrapper therefore captures:

- the amplihack hook result
- the XPIA hook result

It then applies a fixed precedence order and prints a single payload. This avoids the ambiguity that would come from multiple hook scripts printing independent JSON objects to the same stdout stream.

### 3. XPIA stays canonical for Bash security

The XPIA hook remains a Python entrypoint even when the amplihack hook engine is Rust-first. That is deliberate.

The canonical file, `.claude/tools/xpia/hooks/pre_tool_use.py`, is already the fail-closed bridge to `xpia-defend`. Keeping one canonical entrypoint means:

- one place to log audit events
- one place to enforce strict JSON parsing
- one place to deny Bash when the defender is missing or invalid

`pre_tool_use_rust.py` exists only so older entrypoints still work.

### 4. The Rust recipe runner remains strict

The parity slice does not weaken recipe execution just because Copilot is selected.

If `recipe-runner-rs` is missing or too old, the bridge raises an explicit error. That is better than silently switching execution modes because it keeps failures visible and protects parity claims.

### 5. Nested Copilot launches normalize only what they must

The compatibility layer merges prompt fragments because Copilot does not accept the same prompt flag mix that Claude-oriented call sites can emit.

It injects `--allow-all-tools` and `--allow-all-paths` only when the caller did not already provide an explicit permission decision. This is the smallest safe normalization surface.

## Security Model

### Fail-closed by default

If `xpia-defend` is unavailable, malformed, or returns an ambiguous result, the canonical XPIA hook denies Bash.

### Precedence favors the explicit security decision

The wrapper gives XPIA first priority because Bash policy evaluation is the security-critical decision in this slice.

### No shell interpolation tricks

The Rust runner and compatibility wrappers build structured subprocess argument lists. They do not depend on shell interpolation to assemble nested commands.

## Trade-offs

| Choice                               | Benefit                                         | Cost                                                                      |
| ------------------------------------ | ----------------------------------------------- | ------------------------------------------------------------------------- |
| One generated `pre-tool-use` wrapper | Copilot sees one unambiguous permission payload | Wrapper logic must preserve precedence correctly                          |
| Canonical Python XPIA bridge         | Single fail-closed security entrypoint          | XPIA is not fully Rust-native yet                                         |
| Strict Rust-runner gating            | Visible failures and real parity                | Missing or outdated binaries stop execution instead of degrading silently |
| Narrow nested-arg normalization      | Preserves explicit permission flags             | Copilot-specific behavior lives in a dedicated compatibility layer        |

## Common Misconceptions

### "Parity means both CLIs behave identically"

Not exactly. Parity means amplihack delivers the same user-level feature outcome while respecting the actual contract of each host CLI.

### "If Rust is unavailable, Python should just take over"

Not for recipe execution. Silent fallback would hide broken environments and make Python-vs-Rust parity impossible to trust.

### "The nested Copilot wrapper is a general CLI adapter"

It is not. It exists only to bridge nested recipe-runner launches into the Copilot CLI contract.

## When to Use This Architecture

Use the parity control plane when you need:

- `amplihack copilot` to stage hooks and agents consistently
- Bash security enforcement that remains active in Copilot sessions
- recipe execution that keeps using Copilot in nested runs
- one documented and testable decision path for Python and Rust control-plane behavior

## When Not to Use It

Do not treat this as a generic wrapper for every Copilot invocation outside amplihack. It is specifically the control plane for staged amplihack launches and nested recipe execution.

## Related Documents

- [Tutorial: Enable the Copilot parity control plane](../tutorials/copilot-parity-control-plane.md)
- [How to Configure the Copilot Parity Control Plane](../howto/configure-copilot-parity-control-plane.md)
- [Copilot Parity Control Plane Reference](../reference/copilot-parity-control-plane.md)
- [Hooks Comparison](../HOOKS_COMPARISON.md)
