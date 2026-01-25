# Unified .claude/ Staging Architecture

Explains why amplihack stages all framework files to `~/.amplihack/.claude/` and how the staging mechanism works.

## The Problem

Before unified staging, only `amplihack claude` populated `~/.amplihack/.claude/`. This meant:

- Users of `amplihack copilot` had no access to agents/skills
- Users of `amplihack amplifier` couldn't use framework tools
- Each command required manual setup
- Inconsistent experience across tools

## The Solution

**All amplihack commands now stage to `~/.amplihack/.claude/` automatically.**

When you run any command (`copilot`, `amplifier`, `rustyclawd`, `codex`), the framework:

1. Detects it's running in UVX deployment mode
2. Calls `_ensure_amplihack_staged()` before launching
3. Copies framework files to `~/.amplihack/.claude/`
4. Launches the requested tool with full framework access

## Why This Location

`~/.amplihack/.claude/` was chosen because:

1. **User-writable**: No sudo/admin permissions required
2. **Tool-agnostic**: Not tied to any specific CLI tool
3. **Persistent**: Survives tool updates and reinstalls
4. **Conventional**: Follows XDG Base Directory pattern
5. **Isolated**: Won't interfere with project-specific `.claude/` directories

## Architecture

### Staging Process

```
amplihack [command] invoked
    ↓
Detect deployment mode (UVX)
    ↓
_ensure_amplihack_staged()
    ↓
copytree_manifest(
    source=package/.claude/,
    dest=~/.amplihack/.claude/,
    manifest=STAGING_MANIFEST
)
    ↓
Launch requested tool
```

### Key Components

**`_ensure_amplihack_staged()`**

Called by all non-Claude commands before launching. Handles:

- Deployment mode detection (only runs in UVX mode)
- Directory creation if missing
- File copying via `copytree_manifest()`
- Error handling and user feedback

**`copytree_manifest()`**

Efficient file copying mechanism that:

- Uses manifest to copy only essential files
- Preserves directory structure
- Skips unnecessary files (tests, examples, cache)
- Idempotent - safe to run multiple times

**`STAGING_MANIFEST`**

Defines what gets staged:

```python
STAGING_MANIFEST = {
    "agents": ["**/*.md"],
    "skills": ["**/*.md", "**/*.py"],
    "commands": ["**/*.py", "**/*.sh"],
    "tools": ["**/*.py"],
    "hooks": ["**/*.py", "**/*.sh"],
    "context": ["**/*.md"],
    "workflow": ["**/*.md"],
}
```

## Design Decisions

### Why Not Per-Tool Directories?

We considered `~/.copilot/.claude/`, `~/.amplifier/.claude/`, etc. but rejected this because:

- **Duplication**: Same files copied multiple times
- **Inconsistency**: Updates to one tool don't propagate
- **Complexity**: Multiple staging locations to manage

### Why Not System-Wide?

We considered `/usr/local/share/amplihack/` but rejected this because:

- **Permissions**: Requires sudo/admin access
- **Security**: System-wide installations are attack vectors
- **Flexibility**: Users can't easily modify or customize

### Why Only in UVX Mode?

In development mode, we want developers working directly with source files. Only deployed UVX packages need staging.

## Staging Lifecycle

### First Run

```bash
# User runs command for first time
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot

# Staging happens automatically
# Output: "Staging amplihack to ~/.amplihack/.claude/..."
# Output: "✓ Staged successfully"

# Tool launches with full framework access
```

### Subsequent Runs

```bash
# User runs command again
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot

# Staging detects existing directory
# Skips copying if files are up-to-date
# Launches immediately
```

### After Package Update

```bash
# User updates amplihack package
uvx --from git+https://github.com/rysweet/amplihack@main amplihack copilot

# Staging detects version mismatch
# Re-copies all files with new versions
# Output: "Updating staged files..."
# Launches with latest framework
```

## Performance Characteristics

**Initial staging**: ~500ms (copies ~200 files)
**Subsequent runs**: ~50ms (skips if up-to-date)
**Disk usage**: ~5MB in `~/.amplihack/.claude/`

## Security Considerations

Files in `~/.amplihack/.claude/` are:

- **User-owned**: No privilege escalation risk
- **Read-only after staging**: Tools don't modify staged files
- **Version-locked**: Updates only happen on package upgrade
- **Isolated**: Separate from project code

## Comparison to Plugin Mode

| Feature          | Plugin Mode (Claude Only) | Unified Staging (All Tools) |
| ---------------- | ------------------------- | --------------------------- |
| Location         | `~/.config/claude/`       | `~/.amplihack/.claude/`     |
| Tools supported  | Claude Code only          | All tools                   |
| Auto-update      | Via plugin system         | On package upgrade          |
| User control     | Managed by Claude         | Direct file access          |
| Setup complexity | Plugin install required   | Automatic                   |

## Related

- [Verify Staging](../howto/verify-claude-staging.md) - Check if staging worked
- [Staging API Reference](../reference/staging-api.md) - Developer details
- [Plugin Architecture](../plugin/ARCHITECTURE.md) - Claude Code plugin mode
