# Plugin CLI Commands Reference

Complete reference fer `amplihack plugin` and `amplihack mode` commands.

## Quick Reference

```bash
# Plugin Management
amplihack plugin install <source>     # Install plugin
amplihack plugin uninstall <name>     # Remove plugin
amplihack plugin verify <name>        # Verify installation

# Mode Management
amplihack mode status                 # Show current mode
amplihack mode migrate-to-plugin      # Migrate to plugin
amplihack mode migrate-to-local       # Create local .claude/
```

## Plugin Commands

### `amplihack plugin install`

Install amplihack plugin from git repository or local directory.

**Synopsis:**
```bash
amplihack plugin install <source> [--force]
```

**Arguments:**
- `<source>`: Git URL or local directory path
  - Git URL: `https://github.com/rysweet/amplihack`
  - Local path: `/path/to/amplihack`
- `--force`: Overwrite existing plugin installation (optional)

**Examples:**

```bash
# Install from GitHub (recommended)
amplihack plugin install https://github.com/rysweet/amplihack

# Install from local directory (development)
amplihack plugin install /home/user/dev/amplihack

# Force reinstall (update)
amplihack plugin install --force https://github.com/rysweet/amplihack

# Install from specific branch
amplihack plugin install https://github.com/rysweet/amplihack@feat/new-feature
```

**Output:**

Success:
```
✅ Plugin installed: amplihack
   Location: /home/user/.amplihack/.claude/
   Plugin be ready fer use!
```

Failure:
```
❌ Installation failed: Invalid plugin manifest
   Plugin must have .claude-plugin/plugin.json
```

**What It Does:**

1. Clones git repository or copies local directory t' temporary location
2. Validates `plugin.json` manifest exists and be valid
3. Copies plugin content t' `~/.amplihack/.claude/`
4. Updates `~/.claude/settings.json`:
   - Adds plugin t' `enabledPlugins` array
   - Registers marketplace in `extraKnownMarketplaces`
   - Registers hooks with `${CLAUDE_PLUGIN_ROOT}` paths
5. Cleans up temporary files

**Files Modified:**
- `~/.amplihack/.claude/` (plugin content)
- `~/.amplihack/.claude-plugin/plugin.json` (manifest)
- `~/.claude/settings.json` (plugin registration)

**Exit Codes:**
- `0`: Installation successful
- `1`: Installation failed (invalid source, validation error, copy error)

---

### `amplihack plugin uninstall`

Remove installed plugin cleanly.

**Synopsis:**
```bash
amplihack plugin uninstall <plugin_name>
```

**Arguments:**
- `<plugin_name>`: Name o' plugin t' remove (e.g., "amplihack")

**Examples:**

```bash
# Uninstall amplihack plugin
amplihack plugin uninstall amplihack
```

**Output:**

Success:
```
✅ Plugin removed: amplihack
```

Failure:
```
❌ Failed to remove plugin: amplihack
   Plugin may not be installed or removal failed
```

**What It Does:**

1. Removes `~/.amplihack/.claude/` directory
2. Removes `~/.amplihack/.claude-plugin/` directory
3. Updates `~/.claude/settings.json`:
   - Removes plugin from `enabledPlugins` array
   - Removes marketplace from `extraKnownMarketplaces`
   - Removes hook registrations

**Files Modified:**
- `~/.amplihack/` (removed)
- `~/.claude/settings.json` (plugin deregistration)

**Exit Codes:**
- `0`: Uninstall successful
- `1`: Uninstall failed (plugin not found, removal error)

---

### `amplihack plugin verify`

Verify plugin installation and discoverability.

**Synopsis:**
```bash
amplihack plugin verify <plugin_name>
```

**Arguments:**
- `<plugin_name>`: Name o' plugin t' verify (e.g., "amplihack")

**Examples:**

```bash
# Verify amplihack plugin
amplihack plugin verify amplihack
```

**Output:**

Success (all checks pass):
```
Plugin: amplihack
  Installed: ✅
  Discoverable: ✅
  Hooks loaded: ✅

Plugin be fully functional!
```

Partial failure (some checks fail):
```
Plugin: amplihack
  Installed: ✅
  Discoverable: ❌
  Hooks loaded: ✅

Diagnostics:
  - Plugin not found in /home/user/.claude/settings.json
  - Run: amplihack plugin install --force
```

Complete failure:
```
Plugin: amplihack
  Installed: ❌
  Discoverable: ❌
  Hooks loaded: ❌

Diagnostics:
  - Plugin directory not found: /home/user/.amplihack/.claude/
  - Plugin not found in /home/user/.claude/settings.json
  - Hooks not registered or hooks.json missing
  - Run: amplihack plugin install https://github.com/rysweet/amplihack
```

**Verification Checks:**

1. **Installed**: Plugin directory exists at `~/.amplihack/.claude/`
   - Checks for `~/.amplihack/.claude-plugin/plugin.json`
   - Verifies essential directories (agents, commands, skills, tools)

2. **Discoverable**: Plugin registered in Claude Code settings
   - Checks `~/.claude/settings.json` contains plugin name
   - Verifies `enabledPlugins` array includes plugin

3. **Hooks Loaded**: Hook configuration be valid
   - Checks `~/.amplihack/.claude/tools/amplihack/hooks/hooks.json` exists
   - Verifies hooks.json be valid JSON
   - Confirms at least one hook be defined

**Exit Codes:**
- `0`: All checks passed
- `1`: One or more checks failed

---

## Mode Commands

### `amplihack mode status`

Show current Claude installation mode fer the project.

**Synopsis:**
```bash
amplihack mode status
```

**Examples:**

```bash
# Check current mode
cd ~/project
amplihack mode status
```

**Output:**

Plugin mode:
```
Current mode: plugin
  Using: /home/user/.amplihack/.claude
```

Local mode:
```
Current mode: local
  Using: /home/user/project/.claude
```

No installation:
```
Current mode: none
  No .claude installation found
  Install plugin: amplihack plugin install
```

**Mode Detection:**

Precedence order:
1. **LOCAL**: Project has `.claude/` directory → Use local
2. **PLUGIN**: Plugin installed at `~/.amplihack/.claude/` → Use plugin
3. **NONE**: No installation found → Prompt t' install

**Environment Override:**

```bash
# Force plugin mode (override local)
AMPLIHACK_MODE=plugin amplihack mode status

# Force local mode (if exists)
AMPLIHACK_MODE=local amplihack mode status
```

**Exit Codes:**
- `0`: Always successful (informational command)

---

### `amplihack mode migrate-to-plugin`

Migrate project from local `.claude/` t' plugin mode.

**Synopsis:**
```bash
amplihack mode migrate-to-plugin
```

**Prerequisites:**
- Plugin must be installed (`amplihack plugin install`)
- Project must have local `.claude/` directory
- Local `.claude/` must not have custom modifications (or be backed up)

**Examples:**

```bash
# Migrate current project
cd ~/project
amplihack mode migrate-to-plugin
```

**Output:**

Success:
```
Removing local .claude/ from /home/user/project
Migration complete. Project now uses plugin.
```

Failure (no local .claude/):
```
No local .claude/ directory found
```

Failure (plugin not installed):
```
Plugin not installed. Install plugin first:
  amplihack plugin install
```

Warning (custom files):
```
Warning: Local .claude/ has custom files:
  - agents/my-custom-agent.md
  - commands/my-command/

These will be lost. Backup first or use --preserve-custom
```

**What It Does:**

1. Checks fer plugin installation
2. Checks fer local `.claude/` directory
3. Detects custom modifications (files not in plugin)
4. Removes local `.claude/` directory
5. Project now uses plugin automatically (no local override)

**Files Modified:**
- `project/.claude/` (removed)

**Exit Codes:**
- `0`: Migration successful
- `1`: Migration failed (no plugin, no local, or custom files detected)

---

### `amplihack mode migrate-to-local`

Create local `.claude/` from plugin fer project-specific customization.

**Synopsis:**
```bash
amplihack mode migrate-to-local
```

**Prerequisites:**
- Plugin must be installed (`amplihack plugin install`)
- Project must NOT have local `.claude/` directory

**Examples:**

```bash
# Create local .claude/ from plugin
cd ~/project
amplihack mode migrate-to-local
```

**Output:**

Success:
```
Creating local .claude/ from plugin
Migration complete. Project now uses local .claude/
You can now customize .claude/ for this project.
```

Failure (local already exists):
```
Local .claude/ already exists at /home/user/project
```

Failure (no plugin):
```
Plugin not installed. Cannot create local copy.
```

**What It Does:**

1. Checks fer plugin installation
2. Checks local `.claude/` does NOT exist
3. Copies plugin content t' project's `.claude/` directory
4. Project now uses local `.claude/` (takes precedence over plugin)

**Files Modified:**
- `project/.claude/` (created, copied from plugin)

**Exit Codes:**
- `0`: Migration successful
- `1`: Migration failed (no plugin or local already exists)

---

## Environment Variables

### `AMPLIHACK_MODE`

Override automatic mode detection.

**Values:**
- `plugin`: Force plugin mode
- `local`: Force local mode (if `.claude/` exists)

**Usage:**

```bash
# Use plugin even if local .claude/ exists
AMPLIHACK_MODE=plugin amplihack launch

# Use local mode (requires .claude/ directory)
AMPLIHACK_MODE=local amplihack launch
```

**Verification:**

```bash
AMPLIHACK_MODE=plugin amplihack mode status
# Output: Current mode: plugin
```

### `AMPLIHACK_DEBUG`

Enable debug output fer plugin operations.

**Usage:**

```bash
# Enable debug mode
AMPLIHACK_DEBUG=1 amplihack plugin install https://github.com/rysweet/amplihack

# Output includes:
# - Temporary directory paths
# - Validation steps
# - File copy operations
# - Settings updates
```

---

## Common Workflows

### Fresh Installation

```bash
# 1. Install plugin
amplihack plugin install https://github.com/rysweet/amplihack

# 2. Verify installation
amplihack plugin verify amplihack

# 3. Launch in any project
cd ~/any-project
amplihack launch
```

### Update Plugin

```bash
# Force reinstall with latest version
amplihack plugin install --force https://github.com/rysweet/amplihack
```

### Migrate Existing Projects

```bash
# For each project with .claude/
cd ~/project1
amplihack mode migrate-to-plugin

cd ~/project2
amplihack mode migrate-to-plugin
```

### Revert t' Per-Project Mode

```bash
# Create local .claude/ from plugin
cd ~/project
amplihack mode migrate-to-local

# Customize
vim .claude/agents/custom-agent.md
```

### Troubleshoot Installation

```bash
# Check what's wrong
amplihack plugin verify amplihack

# Reinstall if needed
amplihack plugin install --force https://github.com/rysweet/amplihack

# Check mode
amplihack mode status
```

---

## Exit Codes Summary

All commands use standard Unix exit codes:

- `0`: Success
- `1`: Failure (with diagnostic message)

**Usage in Scripts:**

```bash
# Check if plugin installed
if amplihack plugin verify amplihack; then
  echo "Plugin be ready!"
else
  echo "Plugin not ready, installin'..."
  amplihack plugin install https://github.com/rysweet/amplihack
fi
```

---

## Help Text

**Get help fer any command:**

```bash
amplihack plugin --help
amplihack plugin install --help
amplihack plugin verify --help
amplihack mode --help
```

**Output:**

```
usage: amplihack plugin <command> [options]

Plugin management commands

subcommands:
  install               Install plugin from git URL or local path
  uninstall             Remove plugin
  verify                Verify plugin installation and discoverability

Use 'amplihack plugin <command> --help' fer command-specific help.
```

---

## Next Steps

- [Plugin Architecture](./PLUGIN_ARCHITECTURE.md) - Technical details
- [Migration Guide](./MIGRATION_GUIDE.md) - Step-by-step migration
- [README Plugin Section](../README.md#plugin-installation) - Quick start
