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

| Subcommand | Description                                                                      |
| ---------- | -------------------------------------------------------------------------------- |
| `launch`   | Start an interactive amplihack session (default when called with no subcommand). |
| `recipe`   | Run, list, validate, and inspect workflow recipes.                               |
| `memory`   | Manage the amplihack memory backend.                                             |
| `plugin`   | Install, uninstall, and list amplihack plugins.                                  |
| `version`  | Alias for `--version`. Prints version and exits.                                 |

See the documentation for each subcommand:

- [Recipe CLI Reference](./recipe-cli-reference.md)
- [Memory CLI Reference](./memory-cli-reference.md)
- [Plugin CLI Reference](../plugin/plugin-cli.md)

---

## Argument Passthrough

Subcommands that launch a subordinate CLI or SDK (*launch-style* commands) automatically
forward unrecognised arguments to the underlying tool. You do not need an explicit `--`
separator:

```bash
# Both are equivalent — --resume is forwarded to the Claude CLI
amplihack copilot --resume
amplihack copilot -- --resume
```

**Launch-style commands** (passthrough enabled): `launch`, `claude`, `copilot`,
`codex`, `amplifier`

**Management commands** (strict parsing, passthrough disabled): `install`,
`plugin`, `memory`, `recipe`, and any other non-launch subcommands

When a management command receives an unrecognised argument, amplihack exits
with code 2 and prints an error:

```
amplihack install --resume
# error: unrecognized arguments: --resume
```

Known amplihack flags are parsed normally before passthrough occurs — for
example `--auto` is consumed by amplihack while the rest is forwarded:

```bash
amplihack copilot --auto --resume session-123
# --auto  → amplihack sets auto mode
# --resume session-123  → forwarded to copilot
```

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
| `AMPLIHACK_ENABLE_BLARIFY` | unset           | Set to `1` to enable blarify code-graph indexing.                                                                                                                                                                                                             |
| `AMPLIHACK_HOME`           | `~/.amplihack`  | Override the root directory for staged framework files and runtime data. Set automatically by each launcher when not already present in the environment; an existing value is always preserved.                                                               |
| `AMPLIHACK_LOG_LEVEL`      | `WARNING`       | Python logging level for the launcher (`DEBUG`, `INFO`, `WARNING`, `ERROR`).                                                                                                                                                                                  |

---

## Examples

### Check the installed version

```bash
amplihack --version
# amplihack 0.9.2
```

### Launch an interactive session

```bash
amplihack launch
# or simply:
amplihack
```

### Run a workflow recipe non-interactively

```bash
amplihack recipe run default-workflow \
  --context '{"task_description": "Add input validation to the login endpoint"}'
```

### Enable blarify code indexing for a session

```bash
AMPLIHACK_ENABLE_BLARIFY=1 amplihack launch
```

---

## See Also

- [Getting Started](../tutorials/amplihack-tutorial.md)
- [Recipe CLI Reference](./recipe-cli-reference.md)
- [Blarify Code Indexing](../howto/enable-blarify.md)
- [Configuration Guide](../PROXY_CONFIG_GUIDE.md)
