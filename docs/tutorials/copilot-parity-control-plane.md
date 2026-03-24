---
title: "Tutorial: Enable the Copilot parity control plane"
description: "Launch amplihack with GitHub Copilot CLI, verify staged hooks, and validate the Rust-backed parity control plane end to end."
last_updated: 2026-03-24
review_schedule: as-needed
owner: amplihack
doc_type: tutorial
---

# Tutorial: Enable the Copilot parity control plane

Use this tutorial to launch `amplihack` with GitHub Copilot CLI, stage the parity hooks, and verify the finished control-plane behavior.

## What You'll Build

By the end of this tutorial you will have:

- launched `amplihack copilot` with the parity control plane enabled
- verified the generated `.github/hooks/pre-tool-use` wrapper
- confirmed that the canonical XPIA hook allows safe Bash input
- validated that recipe execution keeps using Copilot in nested contexts

## Prerequisites

- `amplihack` installed and available on `PATH`
- GitHub Copilot CLI installed and authenticated
- `recipe-runner-rs` installed or discoverable on `PATH`
- repository checkout with `.claude/tools/xpia/hooks/pre_tool_use.py` present

## Step 1: Select Copilot and the Rust hook engine

Set the agent binary explicitly so nested recipe execution stays on Copilot. Set the hook engine to `rust` for deterministic parity behavior.

```bash
export AMPLIHACK_AGENT_BINARY=copilot
export AMPLIHACK_HOOK_ENGINE=rust
recipe-runner-rs --version
```

**Checkpoint**: `recipe-runner-rs --version` prints a version string instead of `command not found`.

## Step 2: Launch Copilot through amplihack

Start Copilot through the amplihack launcher so it can stage hooks, agents, recipes, and supporting files before handing off to the CLI.

```bash
amplihack copilot
```

**Checkpoint**: the launcher stages `.github/hooks/` and reports that the XPIA defender is ready, or warns that Bash tool use will remain blocked until `xpia-defend` is available.

## Step 3: Verify the generated pre-tool wrapper

The parity slice uses a single Copilot-facing wrapper that collects the amplihack and XPIA results, then emits one final JSON permission payload.

```bash
ls .github/hooks
bash -n .github/hooks/pre-tool-use
sed -n '1,40p' .github/hooks/pre-tool-use
```

**Checkpoint**:

- `.github/hooks/pre-tool-use` exists
- `bash -n` exits cleanly
- the wrapper references both `tools/amplihack/hooks/pre_tool_use.py` and `tools/xpia/hooks/pre_tool_use.py`

## Step 4: Validate the canonical XPIA Bash policy hook

Run the canonical XPIA hook directly with a harmless Bash payload.

```bash
printf '%s\n' '{"tool_name":"Bash","tool_input":{"command":"pwd"}}' \
  | python3 .claude/tools/xpia/hooks/pre_tool_use.py
# Output: {}
```

**Checkpoint**: the hook prints `{}` for the safe command.

> **Note**: `pre_tool_use_rust.py` is a compatibility alias. It delegates to `pre_tool_use.py`, so both entrypoints return the same decision.

## Step 5: Dry-run a recipe with Copilot selected

Use a dry run first. This validates Rust-runner discovery, environment construction, and recipe targeting without starting a long nested agent session.

```bash
AMPLIHACK_AGENT_BINARY=copilot amplihack recipe run investigation-workflow \
  --dry-run \
  --context '{"task_description":"Describe the top-level docs layout","repo_path":"."}'
```

**Checkpoint**: you see the recipe-runner startup banner and the recipe is resolved without argument-normalization errors.

## Step 6: Run a nested Copilot session for real

When the dry run looks correct, remove `--dry-run` to exercise a full nested Copilot launch.

```bash
AMPLIHACK_AGENT_BINARY=copilot amplihack recipe run investigation-workflow \
  --context '{"task_description":"Describe the top-level docs layout","repo_path":"."}'
```

**Checkpoint**: nested Copilot execution starts without `--system-prompt`, `--append-system-prompt`, or permission-flag compatibility errors.

## Summary

You now have a working Copilot parity control plane:

- the launcher staged one Copilot-facing `pre-tool-use` wrapper
- XPIA remained the canonical Bash security policy evaluator
- the Rust recipe runner stayed strict about binary discovery and version gating
- nested Copilot launches normalized prompt fragments without overriding explicit permission flags

## Next Steps

- Use [How to Configure the Copilot Parity Control Plane](../howto/configure-copilot-parity-control-plane.md) to pin binaries or switch hook engines.
- Read [Copilot Parity Control Plane Reference](../reference/copilot-parity-control-plane.md) for the full contract tables.
- Read [Understanding the Copilot Parity Control Plane](../concepts/copilot-parity-control-plane.md) for architecture and trade-offs.
