---
title: "How to Configure the Copilot Parity Control Plane"
description: "Configure hook engine selection, Rust runner discovery, XPIA validation, and nested Copilot behavior for the parity control plane."
last_updated: 2026-03-24
review_schedule: as-needed
owner: amplihack
doc_type: howto
---

# How to Configure the Copilot Parity Control Plane

Use this guide when you need to control how `amplihack copilot` stages hooks, locates the Rust recipe runner, and validates Bash commands through XPIA.

## Prerequisites

- [ ] GitHub Copilot CLI is installed and authenticated
- [ ] `amplihack` is installed
- [ ] `recipe-runner-rs` is installed or available at a known path
- [ ] the repo contains `.claude/tools/xpia/hooks/pre_tool_use.py`

## 1. Select the agent binary and hook engine

Set `AMPLIHACK_AGENT_BINARY=copilot` so nested recipe execution keeps using Copilot. Set `AMPLIHACK_HOOK_ENGINE` explicitly when you need predictable staging behavior.

```bash
export AMPLIHACK_AGENT_BINARY=copilot
export AMPLIHACK_HOOK_ENGINE=rust
```

Use `python` only when you intentionally need the legacy amplihack hook engine:

```bash
export AMPLIHACK_HOOK_ENGINE=python
```

> **Note**: even when the amplihack hook engine is `rust`, the XPIA `pre_tool_use.py` bridge remains the canonical Bash policy entrypoint.

## 2. Pin the Rust recipe runner if auto-discovery is not enough

The runner lookup checks `RECIPE_RUNNER_RS_PATH` first, then known install locations, then `PATH`.

```bash
export RECIPE_RUNNER_RS_PATH="$HOME/.cargo/bin/recipe-runner-rs"
export RECIPE_RUNNER_INSTALL_TIMEOUT=300
recipe-runner-rs --version
```

Use this when:

- you have multiple runner builds installed
- the runner is outside `PATH`
- you need a repeatable CI or developer-shell configuration

## 3. Restage Copilot hooks through the launcher

Run the launcher after changing engine or binary settings.

```bash
amplihack copilot
```

This regenerates `.github/hooks/` wrappers, including the aggregated `pre-tool-use` wrapper.

## 4. Verify the staged wrapper contract

Check that the generated wrapper is syntactically valid and references both hook stacks.

```bash
bash -n .github/hooks/pre-tool-use
rg -n "pre_tool_use.py|permissionDecision|Blocked by amplihack" .github/hooks/pre-tool-use
```

You should see:

- the amplihack hook capture block
- the XPIA hook capture block
- precedence logic that returns one final JSON payload

## 5. Verify XPIA fail-closed behavior

The parity control plane treats `xpia-defend` as security-critical. If the binary is missing or invalid, Bash stays blocked.

```bash
printf '%s\n' '{"tool_name":"Bash","tool_input":{"command":"pwd"}}' \
  | python3 .claude/tools/xpia/hooks/pre_tool_use.py
```

### If the command is allowed

The hook prints `{}`.

### If the defender is unavailable

The hook prints a deny payload that explains that `xpia-defend` is missing and Bash will remain blocked until it is installed.

## 6. Preserve explicit Copilot permission flags

Nested Copilot normalization only injects permissive defaults when the caller did not already supply an explicit permission flag.

Use explicit flags when you need a narrower nested launch contract:

```bash
copilot --allow-tool=Bash --deny-path=.git -p "Summarize the repository layout"
```

The nested compatibility layer preserves these explicit flags. It does not replace them with `--allow-all-tools` or `--allow-all-paths`.

## Variations

### Force the legacy Python amplihack hook engine

```bash
export AMPLIHACK_HOOK_ENGINE=python
amplihack copilot
```

Use this when you are debugging the hook engine itself or comparing generated wrappers across engines.

### Point at a non-default runner path

```bash
export RECIPE_RUNNER_RS_PATH="/opt/amplihack/bin/recipe-runner-rs"
amplihack recipe --version
```

### Keep Copilot for nested recipes only

If your top-level shell already uses a different agent, set the variable only for the recipe invocation:

```bash
AMPLIHACK_AGENT_BINARY=copilot python -m amplihack recipe run amplifier-bundle/recipes/investigation-workflow.yaml \
  --dry-run \
  -c task_description="Describe the docs tree" \
  -c repo_path="."
```

## Troubleshooting

### `recipe-runner-rs binary not found`

Set `RECIPE_RUNNER_RS_PATH` or install the runner in a standard location.

### `Rust runner version is too old`

Upgrade the installed runner. The parity path does not silently fall back when Rust is selected.

### Bash commands are all denied

Check the XPIA defender first:

```bash
which xpia-defend
python3 .claude/tools/xpia/hooks/pre_tool_use.py <<< '{"tool_name":"Bash","tool_input":{"command":"pwd"}}'
```

### Nested Copilot launches fail on prompt flags

Verify that `AMPLIHACK_AGENT_BINARY=copilot` is present in the environment used to start the recipe runner. The compatibility wrapper is only injected for nested Copilot launches.

## See Also

- [How to Use amplihack with a Non-Claude Agent](./use-non-claude-agent.md)
- [How-To: Settings Hook Configuration](./settings-hook-configuration.md)
- [Copilot Parity Control Plane Reference](../reference/copilot-parity-control-plane.md)
- [Understanding the Copilot Parity Control Plane](../concepts/copilot-parity-control-plane.md)
