# Module Specification: Documentation Updates

## Purpose

Update all documentation to reflect plugin architecture migration and provide clear installation instructions for users.

## Problem

Issue #1948 requires documentation updates but currently:
- README still describes per-project `.claude/` installation
- No plugin installation instructions
- No migration guide
- CLI help text outdated
- PROJECT.md doesn't describe plugin architecture

## Solution Overview

Update six documentation files with plugin architecture information:
1. **README.md** - Installation section
2. **.claude/context/PROJECT.md** - Architecture description
3. **CLI help text** - Plugin commands
4. **MIGRATION_GUIDE.md** - Per-project → Plugin migration
5. **PLUGIN_ARCHITECTURE.md** - Technical details (new)
6. **CHANGELOG.md** - Version 0.9.0 changes

## Contract

### Inputs

**Current Documentation State:**
- README.md: Per-project installation instructions
- PROJECT.md: Generic template
- No plugin-specific documentation

**New Content Needed:**
- Plugin installation steps
- Migration guidance
- Architecture explanation
- CLI command reference

### Outputs

**Updated Documentation:**
- Clear plugin installation instructions
- Migration path from per-project mode
- Architecture diagrams/explanation
- Updated CLI help text

### Side Effects

- Users see updated installation instructions
- Reduces support questions about installation
- Provides migration clarity

## Implementation Design

### File 1: README.md Updates

**Section:** Installation

**Current (Per-Project):**
```markdown
## Installation

```bash
pip install amplihack
amplihack install
```

This copies `.claude/` directory to your project.
```

**New (Plugin Mode):**
```markdown
## Installation

### Quick Start (Recommended - Plugin Mode)

```bash
# Install amplihack
pip install amplihack

# Install plugin (one-time setup)
amplihack plugin install https://github.com/rysweet/amplihack

# Launch Claude Code with amplihack
amplihack
```

The plugin installs to `~/.amplihack/.claude/` and works across all projects.

### Alternative: Per-Project Mode

If you prefer project-specific customization:

```bash
pip install amplihack
amplihack mode migrate-to-local
```

This creates a local `.claude/` directory in your project.

### Which Mode Should I Use?

| Mode | Best For | Pros | Cons |
|------|----------|------|------|
| **Plugin** (Recommended) | Most users | Auto-updates, zero config per project | Global configuration |
| **Local** | Custom agents/workflows | Project-specific customization | Manual updates |

See [Migration Guide](docs/MIGRATION_GUIDE.md) for switching between modes.
```

### File 2: PROJECT.md Updates

**Section:** Architecture

**Location:** `.claude/context/PROJECT.md`

**New Content:**
```markdown
## Project: amplihack-claude-plugin

## Overview

Development framework for Claude Code with specialized agents and automated workflows.
Supports **plugin architecture** for zero-configuration installation and **per-project mode** for customization.

## Architecture

### Plugin Architecture

Amplihack uses Claude Code's plugin system for installation:

```
~/.amplihack/.claude/          # Plugin installation (global)
├── agents/                    # Specialized AI agents
├── commands/                  # Slash commands (/ultrathink, /analyze)
├── skills/                    # Claude Code skills
├── tools/                     # Hooks and utilities
│   └── amplihack/
│       └── hooks/
│           ├── hooks.json     # Hook configuration
│           ├── session_start.py
│           ├── stop.py
│           ├── pre_tool_use.py
│           ├── post_tool_use.py
│           ├── user_prompt_submit.py
│           └── pre_compact.py
└── workflows/                 # Multi-step workflows

project/
└── .claude/
    └── settings.json          # References plugin via ${CLAUDE_PLUGIN_ROOT}
```

**Key Features:**
- **Global Installation:** One install works for all projects
- **Auto-Discovery:** Commands, agents, skills available automatically
- **Hook Integration:** Lifecycle hooks (session start, stop, tool use, etc.)
- **Path Variables:** `${CLAUDE_PLUGIN_ROOT}` resolves to plugin directory

### Dual-Mode Support

Amplihack supports two installation modes:

1. **Plugin Mode (Recommended):**
   - Global installation at `~/.amplihack/.claude/`
   - Zero configuration per project
   - Automatic updates

2. **Local Mode (For Customization):**
   - Project-local `.claude/` directory
   - Full control over agents, commands, workflows
   - Version pinning per project

**Mode Detection:** Amplihack automatically detects which mode to use:
- Local `.claude/` takes precedence if it exists
- Falls back to plugin if no local installation
- Override with `AMPLIHACK_MODE` environment variable

### Technology Stack

- **Language:** Python 3.12+
- **Plugin Format:** Claude Code plugin manifest
- **Hook System:** Claude Code lifecycle hooks
- **LSP Detection:** Automatic language server configuration

## Domain Knowledge

### Key Terminology

- **Plugin:** Global installation of .claude/ directory
- **Brick:** Self-contained module (agents, commands, skills)
- **Stud:** Public API/contract for module
- **Hook:** Lifecycle event handler (session start, tool use, etc.)
- **CLAUDE_PLUGIN_ROOT:** Path variable resolving to plugin directory

## Common Tasks

### Development Workflow

```bash
# Check installation mode
amplihack mode status

# Migrate between modes
amplihack mode migrate-to-plugin  # Local → Plugin
amplihack mode migrate-to-local    # Plugin → Local

# Plugin management
amplihack plugin verify amplihack  # Verify installation
amplihack plugin install <source>  # Install from source
```
```

### File 3: CLI Help Text Updates

**Location:** `src/amplihack/cli.py`

**Plugin Subcommand Help:**
```python
# In create_parser():

plugin_parser = subparsers.add_parser(
    "plugin",
    help="Plugin management commands",
    description="""
    Manage amplihack plugin installation and configuration.

    The plugin installs to ~/.amplihack/.claude/ and provides:
    - Agents: Specialized AI assistants
    - Commands: Slash commands like /ultrathink
    - Skills: Auto-discovered capabilities
    - Hooks: Lifecycle event handlers

    Use 'amplihack plugin <command> --help' for command-specific help.
    """
)

install_parser = plugin_subparsers.add_parser(
    "install",
    help="Install plugin from git URL or local path",
    description="""
    Install amplihack plugin from a source.

    Examples:
      amplihack plugin install https://github.com/rysweet/amplihack
      amplihack plugin install /path/to/local/plugin
      amplihack plugin install <source> --force  # Overwrite existing
    """
)

uninstall_parser = plugin_subparsers.add_parser(
    "uninstall",
    help="Remove plugin",
    description="""
    Uninstall amplihack plugin.

    This removes the plugin from ~/.amplihack/.claude/ and
    updates Claude Code settings.

    Example:
      amplihack plugin uninstall amplihack
    """
)

verify_parser = plugin_subparsers.add_parser(
    "verify",
    help="Verify plugin installation",
    description="""
    Verify plugin is correctly installed and discoverable.

    Checks:
    - Plugin directory exists
    - Plugin in Claude Code settings
    - Hooks are registered

    Example:
      amplihack plugin verify amplihack
    """
)
```

### File 4: Migration Guide (NEW)

**Location:** `docs/MIGRATION_GUIDE.md`

**Content:**
```markdown
# Migration Guide: Per-Project → Plugin

This guide helps you migrate from per-project `.claude/` installations to the plugin architecture.

## Why Migrate?

**Plugin Benefits:**
- ✅ One-time installation (works across all projects)
- ✅ Automatic updates
- ✅ Zero configuration per project
- ✅ Consistent behavior across projects

**Per-Project Benefits:**
- ✅ Project-specific customization
- ✅ Version pinning
- ✅ Experimental agent development

## Migration Steps

### Step 1: Check Current Mode

```bash
amplihack mode status
```

Output:
```
Current mode: local
  Using: /path/to/project/.claude
```

### Step 2: Install Plugin (If Not Installed)

```bash
amplihack plugin install https://github.com/rysweet/amplihack
```

Output:
```
✅ Plugin installed: amplihack
   Location: /home/user/.amplihack/.claude
```

### Step 3: Migrate to Plugin

```bash
cd /path/to/project
amplihack mode migrate-to-plugin
```

This:
1. Checks for custom files (warns if found)
2. Removes local `.claude/` directory
3. Project now uses plugin

### Step 4: Verify

```bash
amplihack mode status
```

Output:
```
Current mode: plugin
  Using: /home/user/.amplihack/.claude
```

## Handling Custom Files

If you have custom agents, commands, or workflows:

### Option 1: Preserve Customizations

1. **Backup local .claude/:**
   ```bash
   cp -r .claude .claude.backup
   ```

2. **Identify custom files:**
   ```bash
   # Compare with plugin
   diff -r .claude ~/.amplihack/.claude
   ```

3. **Migrate customizations to plugin:**
   ```bash
   # Copy custom agents
   cp -r .claude.backup/agents/custom ~/.amplihack/.claude/agents/
   ```

### Option 2: Keep Local Mode

Stay in per-project mode for this project:
```bash
# Do not migrate - keep local .claude/
```

## Reverting to Per-Project Mode

If you need to revert:

```bash
amplihack mode migrate-to-local
```

This creates a local `.claude/` copy from the plugin.

## Multi-Project Workflow

**Recommended Approach:**
- Most projects: Use plugin (zero config)
- Experimental projects: Use local mode

**Example:**
```bash
# Project 1 (standard - use plugin)
cd ~/project1
amplihack mode status
# → plugin

# Project 2 (experimental - use local)
cd ~/project2
amplihack mode migrate-to-local
# → local
```

## FAQ

**Q: Will migration break my workflow?**
A: No. If you have custom files, migration is blocked until you backup.

**Q: Can I use both modes?**
A: Yes! Some projects can use plugin, others can use local.

**Q: How do I update the plugin?**
A: `amplihack plugin install --force` reinstalls the latest version.

**Q: What if I delete local .claude/ by accident?**
A: It will automatically use the plugin (if installed).

## Troubleshooting

### Plugin Not Found

```bash
amplihack plugin verify amplihack
```

If verification fails:
```bash
amplihack plugin install https://github.com/rysweet/amplihack
```

### Local .claude/ Won't Delete

Check for uncommitted changes:
```bash
cd .claude
git status
```

Backup before migrating:
```bash
cp -r .claude .claude.backup
```

### Mode Override

Temporarily force a mode:
```bash
AMPLIHACK_MODE=plugin amplihack  # Force plugin
AMPLIHACK_MODE=local amplihack   # Force local
```
```

### File 5: Plugin Architecture Documentation (NEW)

**Location:** `docs/PLUGIN_ARCHITECTURE.md`

**Content:**
```markdown
# Plugin Architecture

Technical documentation for amplihack's plugin architecture.

## Overview

Amplihack uses Claude Code's plugin system for installation and discovery.

## Directory Structure

```
~/.amplihack/
├── .claude/                   # Plugin content
│   ├── agents/                # Specialized AI agents
│   ├── commands/              # Slash commands
│   ├── skills/                # Auto-discovered capabilities
│   ├── tools/
│   │   └── amplihack/
│   │       └── hooks/
│   │           ├── hooks.json          # Hook configuration
│   │           ├── session_start.py    # SessionStart hook
│   │           ├── stop.py             # Stop hook
│   │           ├── pre_tool_use.py     # PreToolUse hook
│   │           ├── post_tool_use.py    # PostToolUse hook
│   │           ├── user_prompt_submit.py # UserPromptSubmit hook
│   │           └── pre_compact.py      # PreCompact hook
│   └── workflows/             # Multi-step workflows
└── .claude-plugin/
    └── plugin.json            # Plugin manifest

~/.claude/
└── settings.json              # Claude Code settings (references plugin)
```

## Plugin Manifest

**File:** `~/.amplihack/.claude-plugin/plugin.json`

```json
{
  "name": "amplihack",
  "version": "0.9.0",
  "description": "AI-powered development framework...",
  "author": {
    "name": "Microsoft Amplihack Team",
    "url": "https://github.com/rysweet/amplihack"
  },
  "homepage": "https://github.com/rysweet/amplihack",
  "repository": "https://github.com/rysweet/amplihack",
  "license": "MIT",
  "keywords": ["claude-code", "ai", "agents", "workflows"],
  "commands": ["./.claude/commands/"],
  "agents": "./.claude/agents/",
  "skills": "./.claude/skills/",
  "hooks": "./.claude/tools/amplihack/hooks/hooks.json",
  "marketplace": {
    "name": "amplihack",
    "url": "https://github.com/rysweet/amplihack",
    "type": "github"
  }
}
```

## Hook System

### Lifecycle Hooks

| Hook | When | Purpose |
|------|------|---------|
| **SessionStart** | Claude Code starts | Initialize runtime, check version, setup memory |
| **Stop** | Claude Code exits | Cleanup, save state, shutdown services |
| **PreToolUse** | Before tool execution | Validate inputs, log tool calls |
| **PostToolUse** | After tool execution | Process results, update state |
| **UserPromptSubmit** | User submits prompt | Parse intent, route to workflows |
| **PreCompact** | Before context compaction | Save important context |

### Hook Configuration

**File:** `.claude/tools/amplihack/hooks/hooks.json`

```json
{
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/session_start.py",
          "timeout": 10000
        }
      ]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "command": "${CLAUDE_PLUGIN_ROOT}/tools/amplihack/hooks/post_tool_use.py"
        }
      ]
    }
  ]
}
```

### Path Variables

**${CLAUDE_PLUGIN_ROOT}** resolves to `~/.amplihack/.claude/`

This allows hooks to reference files relative to plugin installation.

## Settings Generation

When plugin is installed, `~/.claude/settings.json` is generated:

```json
{
  "extraKnownMarketplaces": [
    {
      "name": "amplihack",
      "url": "https://github.com/rysweet/amplihack"
    }
  ],
  "enabledPlugins": ["amplihack"],
  "hooks": {
    "SessionStart": [...],
    "Stop": [...],
    "PreToolUse": [...],
    "PostToolUse": [...],
    "UserPromptSubmit": [...],
    "PreCompact": [...]
  }
}
```

## Mode Detection

Amplihack supports dual-mode operation:

1. **Plugin Mode:** Uses `~/.amplihack/.claude/`
2. **Local Mode:** Uses `project/.claude/`

**Detection Logic:**
```python
def detect_claude_mode():
    if project_has_local_claude():
        return ClaudeMode.LOCAL  # Precedence
    elif plugin_installed():
        return ClaudeMode.PLUGIN
    else:
        return ClaudeMode.NONE
```

## Installation Process

1. **Install Package:**
   ```bash
   pip install amplihack
   ```

2. **Install Plugin:**
   ```bash
   amplihack plugin install https://github.com/rysweet/amplihack
   ```

3. **Plugin Manager:**
   - Clones repository (if git URL)
   - Validates manifest
   - Copies to `~/.amplihack/.claude/`
   - Registers in `~/.claude/settings.json`

4. **Verification:**
   ```bash
   amplihack plugin verify amplihack
   ```

## Cross-Tool Compatibility

| Tool | Support | Notes |
|------|---------|-------|
| **Claude Code** | ✅ Full | Primary target |
| **GitHub Copilot** | ⚠️ Research needed | Plugin format unknown |
| **Codex** | ⚠️ Research needed | Plugin format unknown |

See [Cross-Tool Compatibility](CROSS_TOOL_COMPATIBILITY.md) for details.

## References

- [Claude Code Plugin Documentation](https://docs.anthropic.com/claude-code/plugins)
- [Issue #1948: Plugin Architecture](https://github.com/rysweet/amplihack/issues/1948)
- [ISSUE_1948_REQUIREMENTS.md](../ISSUE_1948_REQUIREMENTS.md)
```

### File 6: CHANGELOG.md Updates

**Location:** `CHANGELOG.md`

**New Entry:**
```markdown
## [0.9.0] - 2026-01-XX

### Added
- **Plugin Architecture:** Global installation at `~/.amplihack/.claude/`
- **Plugin Commands:** `amplihack plugin install|uninstall|verify`
- **Mode Management:** `amplihack mode status|migrate-to-plugin|migrate-to-local`
- **Dual-Mode Support:** Auto-detect local vs plugin installation
- **Marketplace Configuration:** `extraKnownMarketplaces` for plugin discovery
- **Hook Registration:** All 6 lifecycle hooks with `${CLAUDE_PLUGIN_ROOT}` paths

### Changed
- **Installation:** Recommend plugin mode over per-project copy
- **Settings Generation:** Now includes marketplace configuration
- **Path Resolution:** All hooks use `${CLAUDE_PLUGIN_ROOT}` variable

### Migration
- See [Migration Guide](docs/MIGRATION_GUIDE.md) for upgrading from v0.8.x
- Per-project `.claude/` installations still supported (local mode)
- Plugin mode is now recommended for most users

### Compatibility
- Claude Code: Full support ✅
- GitHub Copilot: Research in progress ⚠️
- Codex: Research in progress ⚠️
```

## Dependencies

- **None** (documentation only)
- **Tools:** Text editor, markdown renderer

## Testing Strategy

### Documentation Tests

```python
def test_readme_has_plugin_installation():
    """Verify README includes plugin installation instructions."""
    readme = Path("README.md").read_text()
    assert "amplihack plugin install" in readme
    assert "Plugin Mode" in readme

def test_project_md_has_architecture():
    """Verify PROJECT.md describes plugin architecture."""
    project_md = Path(".claude/context/PROJECT.md").read_text()
    assert "Plugin Architecture" in project_md
    assert "${CLAUDE_PLUGIN_ROOT}" in project_md

def test_migration_guide_exists():
    """Verify migration guide exists."""
    migration_guide = Path("docs/MIGRATION_GUIDE.md")
    assert migration_guide.exists()

def test_plugin_architecture_doc_exists():
    """Verify plugin architecture documentation exists."""
    arch_doc = Path("docs/PLUGIN_ARCHITECTURE.md")
    assert arch_doc.exists()

def test_changelog_has_0_9_0():
    """Verify CHANGELOG includes v0.9.0 entry."""
    changelog = Path("CHANGELOG.md").read_text()
    assert "[0.9.0]" in changelog
    assert "Plugin Architecture" in changelog
```

## Complexity Assessment

- **Total Lines:** ~1000 lines (documentation)
- **Effort:** 2-3 hours
  - README: 30 min
  - PROJECT.md: 30 min
  - CLI help: 20 min
  - Migration guide: 45 min
  - Architecture doc: 45 min
  - CHANGELOG: 10 min
- **Risk:** Low (documentation only)

## Success Metrics

- [ ] README updated with plugin installation
- [ ] PROJECT.md describes plugin architecture
- [ ] CLI help text includes plugin commands
- [ ] Migration guide complete and clear
- [ ] Plugin architecture documented
- [ ] CHANGELOG updated for v0.9.0
- [ ] All documentation references are accurate

## Philosophy Compliance

- ✅ **Ruthless Simplicity:** Clear, concise documentation
- ✅ **Zero-BS Implementation:** Accurate information only
- ✅ **Modular Design:** Each doc covers one topic
- ✅ **Regeneratable:** Can rebuild docs from code
- ✅ **Single Responsibility:** Each file has clear purpose

## References

- Issue #1948: "Documentation updates"
- `ISSUE_1948_REQUIREMENTS.md`, Gap 6 (documentation)
