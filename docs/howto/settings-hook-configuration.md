# How-To: Settings Hook Configuration

## Overview

Amplihack automatically configures hooks in `~/.claude/settings.json` during installation and CLI initialization. This guide explains the hook configuration process and how to troubleshoot issues.

## Automatic Configuration (New in v0.5.27)

Starting in v0.5.27, hook configuration is **completely automatic** - no user prompts required.

### What Happens Automatically

When you run `amplihack` or install the framework:

1. **Validation**: Hook files are validated before configuration
2. **Backup**: Settings are backed up to `~/.claude/settings.json.backup.<timestamp>`
3. **Configuration**: Hooks are added/updated in settings.json
4. **Verification**: System confirms hooks are properly configured

**No user intervention required!**

## Hook Validation

### What Is Validated

The system validates that all required hook files exist before configuring them:

**Amplihack Hooks (Required):**

- `session_start.py` - Runs when Claude Code session starts
- `stop.py` - Runs when Claude Code session stops
- `post_tool_use.py` - Runs after each tool invocation
- `pre_compact.py` - Runs before context compaction

**XPIA Hooks (Optional):**

- `session_start.py` - Security initialization
- `post_tool_use.py` - Security monitoring
- `pre_tool_use.py` - Input validation

### Error Messages

If required hooks are missing, you'll see:

```
❌ Hook validation failed - missing required hooks:
   • amplihack/session_start.py (expected at /home/user/.amplihack/.claude/tools/amplihack/hooks/session_start.py)
💡 Please reinstall amplihack to restore missing hooks
```

**Resolution:** Run `amplihack install` to restore missing hooks.

## Backups

### Automatic Backups

Every time settings.json is modified, a backup is created:

```
~/.claude/settings.json.backup.<timestamp>
```

Example: `~/.claude/settings.json.backup.1739673234`

### Restoring from Backup

If you need to restore a previous configuration:

```bash
# Find recent backups
ls -lt ~/.claude/settings.json.backup.* | head -5

# Restore from specific backup
cp ~/.claude/settings.json.backup.1739673234 ~/.claude/settings.json
```

## Troubleshooting

### Problem: "Hook validation failed"

**Symptom:** Error message listing missing hooks during installation

**Cause:** Required hook files are missing from `~/.amplihack/.claude/tools/amplihack/hooks/`

**Solution:**

```bash
# Reinstall amplihack to restore hooks
amplihack install
```

### Problem: Hooks not executing

**Symptom:** Session start hooks or tool hooks don't run

**Cause:** Settings.json not properly configured

**Solution:**

```bash
# Reconfigure settings
amplihack install  # This will reconfigure hooks automatically
```

### Problem: XPIA hooks warning

**Symptom:** Warning about missing XPIA hooks during configuration

**Cause:** XPIA security hooks are optional and not installed

**Solution:**

- This is normal if you haven't installed XPIA
- To install XPIA: Follow XPIA installation instructions
- To disable warning: Ignore (it's informational only)

## Advanced: Path Expansion

Hook paths support environment variable expansion:

- `$HOME` expands to your home directory
- `~` expands to your home directory
- Other environment variables are expanded automatically

Example:

```
$HOME/.amplihack/.claude/tools/amplihack/hooks/session_start.py
→ /home/username/.amplihack/.claude/tools/amplihack/hooks/session_start.py
```

## For Developers

### validate_hook_paths() Function

New in v0.5.27, this function validates hook files exist before configuration:

```python
from amplihack.settings import validate_hook_paths

hooks = [
    {"type": "SessionStart", "file": "session_start.py", "timeout": 10}
]

all_valid, missing = validate_hook_paths(
    "amplihack",
    hooks,
    "~/.amplihack/.claude/tools/amplihack/hooks"
)

if not all_valid:
    print(f"Missing hooks: {missing}")
```

**Returns:**

- `all_valid` (bool): True if all hooks exist
- `missing` (list): List of missing hook descriptions with expected paths

### Running Tests

```bash
# Run hook validation tests
python -m unittest tests.unit.test_validate_hook_paths

# Run all settings tests
python -m unittest discover -s tests -p "test_*settings*.py"
```

## Rust Hook Engine (AMPLIHACK_HOOK_ENGINE=rust)

**New in v0.9.0**: Amplihack supports a high-performance Rust backend for hook execution via the `AMPLIHACK_HOOK_ENGINE` environment variable.

### Enabling the Rust Engine

```bash
export AMPLIHACK_HOOK_ENGINE=rust
amplihack  # Hooks now use the Rust binary
```

When set, hooks are dispatched to the `amplihack-hooks` multicall binary instead of Python scripts.

### Hook Mapping

The following Python hooks have Rust equivalents:

| Python Hook | Rust Subcommand |
|---|---|
| `pre_tool_use.py` | `amplihack-hooks pre-tool-use` |
| `post_tool_use.py` | `amplihack-hooks post-tool-use` |
| `session_start.py` | `amplihack-hooks session-start` |
| `stop.py` | `amplihack-hooks stop` |

Hooks without Rust equivalents (e.g., `workflow_classification_reminder.py`) continue to run as Python scripts regardless of the engine setting.

### Binary Search Order

`amplihack-hooks` is resolved in this priority order:

1. `~/.amplihack/bin/amplihack-hooks` (installed binary — **takes priority**)
2. `~/.cargo/bin/amplihack-hooks` (Cargo-built binary)

Non-executable files at either location are skipped.

### No Silent Fallback

If `AMPLIHACK_HOOK_ENGINE=rust` is set but the binary is missing or not executable, the framework raises `FileNotFoundError`. There is no silent degradation to Python — this is intentional to prevent unexpected behavior.

```
FileNotFoundError: amplihack-hooks binary not found.
Install the Rust binary or unset AMPLIHACK_HOOK_ENGINE.
```

### Mixed Environments

Events with multiple hooks (e.g., `preToolUse`) may have both Rust and Python hooks registered. The engine handles this correctly — Rust hooks run via the binary, Python hooks run via `python3`.

### Hook Ownership

Hook paths are validated for ownership to prevent false matches. A hook path like `~/.amplihack/.claude/tools/xpia/hooks/` is correctly identified as an `xpia` hook, not an `amplihack` hook, even though `amplihack` appears in the path.

### Generating Rust Wrapper Scripts

When using the Copilot launcher with the Rust engine, wrapper scripts are generated automatically:

```bash
# Wrapper generated at staging time:
#!/usr/bin/env bash
exec '/home/user/.amplihack/bin/amplihack-hooks' pre-tool-use "$@"
```

Paths in wrapper scripts are quoted with `shlex.quote()` to protect against `$` expansion.

---

## Related Documentation

- Main README: Setup and installation guide
- PHILOSOPHY.md: Zero-BS principle and validation approach
- Settings migration: See `src/amplihack/settings.py` docstrings
