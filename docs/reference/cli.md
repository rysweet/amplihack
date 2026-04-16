# amplihack CLI Reference

Complete command-line reference for the `amplihack` top-level command.

## Contents

- [Synopsis](#synopsis)
- [Global Flags](#global-flags)
- [Subcommands](#subcommands)
- [Exit Codes](#exit-codes)
- [Environment Variables](#environment-variables)
- [Examples](#examples)

---

## Synopsis

```
amplihack [--version] [--help] <subcommand> [<args>]
```

Running `amplihack` with no subcommand launches Claude Code directly. In
user-facing docs, prefer the explicit `amplihack claude` form;
`amplihack launch` remains a compatibility alias.

---

## Global Flags

These flags are accepted before any subcommand.

| Flag           | Description                                       |
| -------------- | ------------------------------------------------- |
| `--version`    | Print `amplihack <version>` to stdout and exit 0. |
| `--help`, `-h` | Print a brief usage summary and exit 0.           |

### `--version`

Prints the installed version string and exits immediately. No network requests, no configuration loading.

```bash
amplihack --version
# amplihack 0.9.2
```

The version string comes from the `__version__` attribute in `amplihack/__init__.py`, which is set from `pyproject.toml` at build time. It follows [Semantic Versioning](https://semver.org/).

---

## Subcommands

| Subcommand   | Description                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------- |
| `version`    | Show amplihack version.                                                                     |
| `install`    | Install amplihack agents and tools to `~/.claude`.                                          |
| `uninstall`  | Remove amplihack agents and tools from `~/.claude`.                                         |
| `update`     | Update amplihack, delegating to the Rust CLI when one is installed.                         |
| `claude`     | Launch Claude Code. Preferred explicit launcher in user-facing docs.                        |
| `launch`     | Compatibility alias for `claude`; `amplihack` with no subcommand also launches Claude Code. |
| `RustyClawd` | Launch RustyClawd (Rust implementation).                                                    |
| `copilot`    | Launch GitHub Copilot CLI.                                                                  |
| `codex`      | Launch OpenAI Codex CLI.                                                                    |
| `amplifier`  | Launch Microsoft Amplifier with amplihack bundle.                                           |
| `uvx-help`   | Get help with UVX deployment.                                                               |
| `plugin`     | Install, uninstall, and list amplihack plugins.                                             |
| `memory`     | Manage the amplihack memory backend.                                                        |
| `new`        | Generate a new goal-seeking agent.                                                          |
| `recipe`     | Run, list, validate, and inspect workflow recipes.                                          |
| `mode`       | Claude installation mode commands.                                                          |
| `fleet`      | Manage coding agents across VMs.                                                            |

See the documentation for each subcommand:

- [Recipe CLI Reference](./recipe-cli-reference.md)
- [Memory CLI Reference](./memory-cli-reference.md)
- [Plugin CLI Reference](../plugin/plugin-cli.md)

---

## Exit Codes

| Code | Meaning                                                               |
| ---- | --------------------------------------------------------------------- |
| `0`  | Completed successfully (or `--version` / `--help` printed).           |
| `1`  | User error (bad argument, missing config). Stderr contains a message. |
| `2`  | Internal error. Stderr contains a traceback.                          |

---

## Environment Variables

These variables are read at startup. All are optional.

| Variable                   | Default         | Effect                                                                                                                                                                                                                                                        |
| -------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AMPLIHACK_AGENT_BINARY`   | set by launcher | Identifies the active tool in the child process environment. Set automatically to `claude`, `copilot`, `codex`, or `amplifier` by the corresponding launcher before spawning the subprocess. Read by skills and hooks to adapt behaviour to the active agent. |
| `AMPLIHACK_DEBUG`          | unset           | Set to `true` to print debug messages during CLI execution.                                                                                                                                                                                                   |
| `AMPLIHACK_DELEGATE`       | unset           | Selects which agent binary the recipe runner uses to spawn agent steps. Accepted values: `amplihack claude`, `amplihack copilot`, `amplihack amplifier`. When unset or unrecognised, falls back to `claude`. See [Delegate flag passthrough](#delegate-flag-passthrough) for Copilot-specific behaviour. |
| `AMPLIHACK_ENABLE_BLARIFY` | unset           | Set to `1` to enable blarify code-graph indexing.                                                                                                                                                                                                             |
| `AMPLIHACK_HOME`           | `~/.amplihack`  | Override the root directory for staged framework files and runtime data. Set automatically by each launcher when not already present in the environment; an existing value is always preserved.                                                               |
| `AMPLIHACK_LOG_LEVEL`      | `WARNING`       | Python logging level for the launcher (`DEBUG`, `INFO`, `WARNING`, `ERROR`).                                                                                                                                                                                  |

---

## Delegate Flag Passthrough

### `amplihack copilot` — `--` separator

When `AMPLIHACK_DELEGATE=amplihack copilot`, the recipe runner builds agent-step commands differently from other delegates.

**Why it is needed**: The Rust `amplihack copilot` subcommand only recognises its own flags (`--auto`, `--max-turns`, etc.). Copilot CLI flags such as `--allow-all-tools`, `-p`, and `--model` are not known to the Rust binary and must be forwarded to the underlying `gh copilot` process via the POSIX `--` end-of-options separator.

**Command shape produced:**

```
amplihack copilot -- --allow-all-tools -p "<prompt>" [--model <model>]
```

Compare with the `amplihack claude` delegate (no separator needed):

```
claude --dangerously-skip-permissions -p "<prompt>" [--model <model>]
```

**Symptom if the separator is missing (versions before 2026-04-14):**

```
error: unexpected argument '-p' found
  tip: to pass '-p' as a value, use '-- -p'
```

This error blocked every recipe runner agent step (smart-orchestrator, quality-audit-cycle, default-workflow) when running under Copilot CLI.

**Fix**: Upgrade amplihack to the version that includes PR #4343 (merged 2026-04-14).

```bash
uvx --from git+https://github.com/rysweet/amplihack amplihack --version
```

---

## Examples

### Check the installed version

```bash
amplihack --version
# amplihack 0.9.2
```

### Launch an interactive Claude session

Prefer `amplihack claude` in user-facing docs. `amplihack launch` remains
supported as a compatibility alias.

```bash
amplihack claude
# or simply:
amplihack
# compatibility alias:
amplihack launch
```

### Launch an interactive Copilot session

```bash
amplihack copilot
```

### Run a workflow recipe non-interactively

```bash
amplihack recipe run default-workflow \
  --context '{"task_description": "Add input validation to the login endpoint"}'
```

### Enable blarify code indexing for a session

```bash
AMPLIHACK_ENABLE_BLARIFY=1 amplihack claude
```

---

## See Also

- [Getting Started](../tutorials/amplihack-tutorial.md)
- [Recipe CLI Reference](./recipe-cli-reference.md)
- [Blarify Code Indexing](../howto/enable-blarify.md)
- [Configuration Guide](../PROXY_CONFIG_GUIDE.md)
