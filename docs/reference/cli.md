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

## launch

Start an interactive session or run autonomously in `--auto` mode.

```
amplihack launch [flags] [-- <claude-args>]
amplihack [flags] [-- <claude-args>]
```

Arguments after `--` are forwarded verbatim to the underlying agent binary (Claude Code, Copilot, Codex, or Amplifier). amplihack flags must appear before `--`.

### Flags

| Flag                  | Default | Description                                                                             |
| --------------------- | ------- | --------------------------------------------------------------------------------------- |
| `--auto`, `-a`        | off     | Run in autonomous agentic mode (clarify → plan → execute → evaluate loop).              |
| `--max-turns INT`     | `10`    | Maximum turns in `--auto` mode before stopping.                                         |
| `--append PROMPT`     | —       | Inject PROMPT into an already-running `--auto` session without starting a new one.      |
| `--ui`                | off     | Enable the streaming UI overlay when running `--auto` mode.                             |
| `--no-reflection`     | off     | Skip the post-session reflection analysis written to `.claude/runtime/reflection/`.     |
| `--subprocess-safe`   | off     | Skip staging and environment updates. For use by internal subprocess delegates only.    |
| `--checkout-repo URI` | —       | Clone the GitHub repository at URI and use it as the working directory for the session. |
| `--docker`            | off     | Run the agent binary inside a Docker container rather than on the host.                 |

### Model selection

Model selection behaviour is unchanged from pre-0.10. Pass `--model` explicitly after `--` to choose a model for the session:

```bash
amplihack launch -- --model claude-3-5-sonnet-20241022
```

`AMPLIHACK_DEFAULT_MODEL` is respected only when no `--model` flag is present — identical behaviour to before the proxy removal. The proxy subsystem removal has no effect on how models are selected.

### Passthrough flags

Unknown flags are forwarded to the underlying binary when using a passthrough command (`launch`, `claude`, `copilot`, `codex`, `amplifier`). Use `--` to separate amplihack flags from agent flags explicitly:

```bash
# Pass --model to Claude Code
amplihack launch -- --model claude-3-5-sonnet-20241022

# Pass a prompt non-interactively
amplihack launch -- -p "Explain the auth module"
```

### Examples

```bash
# Interactive session
amplihack launch

# Autonomous mode, up to 20 turns
amplihack launch --auto --max-turns 20

# Use a specific model
amplihack launch -- --model claude-opus-4-5

# Clone a repo and start a session in it
amplihack launch --checkout-repo https://github.com/org/repo

# Append a follow-up prompt to a running auto session
amplihack launch --append "Now add unit tests for the module you just wrote"
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
- [Configure Azure OpenAI](../howto/configure-azure-openai.md)
