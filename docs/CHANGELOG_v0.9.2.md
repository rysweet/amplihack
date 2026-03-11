# Changelog - v0.9.2

Release Date: 2026-03-11

## New Features

### `amplihack update` Command (PR #3035, #3037)

amplihack now ships an explicit `update` subcommand that automates upgrading to
the latest version with a **hybrid Python+Rust strategy**:

- **Rust CLI installed** (detected at `~/.local/bin/amplihack` or
  `~/.cargo/bin/amplihack`): the Python CLI delegates the update to the Rust
  binary, which handles its own self-update.
- **Python-only install**: falls back to `uv tool upgrade amplihack`.

The update delegation enforces a **300-second timeout** (`_RUST_CLI_UPDATE_TIMEOUT`)
to prevent the process from hanging indefinitely on slow networks.

Running `amplihack update` also skips the background auto-update check to
prevent recursive update triggers.

**Usage:**

```bash
amplihack update
```

**Files modified:**

- `src/amplihack/auto_update.py` — `run_update_command()`, `_find_rust_cli()`,
  `_RUST_CLI_UPDATE_TIMEOUT`, `_restart_cli()` argument whitelist
- `src/amplihack/cli.py` — `update` subcommand added to argument parser;
  auto-update skipped when user explicitly invokes `amplihack update`
- `tests/test_auto_update.py` — `TestManualUpdateCommand`, `TestRestartCli`
- `tests/integration/test_cli_platform.py` — end-to-end CLI routing test
- `tests/test_cli_claude_command_guard.py` — `update` added to
  `_NON_CLAUDE_COMMANDS`

---

## Internal Improvements

### Module-level constants in `auto_update.py` (PR #3040)

The private constants `_SAFE_ARG_PATTERNS`, `_SAFE_TOP_LEVEL_COMMANDS`, and
`_SAFE_SUBCOMMANDS` were extracted from inside `_restart_cli()` to module level.

This improves readability and allows the constants to be referenced and tested
independently without calling the function.

**Files modified:**

- `src/amplihack/auto_update.py`

---

## Documentation

### Slim CLAUDE.md (PR #3042)

`CLAUDE.md` was reduced from 1,156 to 330 lines (71% reduction). Reference
material that was duplicated inline has been extracted to dedicated on-demand
files:

- `.claude/context/PARALLEL_EXECUTION.md` — execution templates and decision
  framework
- `.claude/context/COMMANDS_REFERENCE.md` — session tree, `/fix`, fault
  tolerance, `/multitask`, DDD, investigation, scenarios, and tools

The essential routing and dispatch logic (workflow classification, operating
principles, agent delegation, extensibility, project structure) is retained
inline in `CLAUDE.md`.

**Impact:** Reduced every-turn context token cost by ~71%.

---

## Upgrade Notes

No breaking changes. Run `amplihack update` (new in this release) or
`uv tool upgrade amplihack` to get the latest version.
