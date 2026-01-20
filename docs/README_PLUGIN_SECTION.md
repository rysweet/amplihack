# Plugin Installation Section

This content should be added t' the main README.md after the "Quick Start" section.

---

## Plugin Installation

Amplihack now supports Claude Code's plugin architecture fer global installation across all yer projects.

### Installation Methods

**Method 1: Plugin Mode (Recommended)**

Install once, use everywhere:

```bash
# Install plugin globally
amplihack plugin install https://github.com/rysweet/amplihack

# Verify installation
amplihack plugin verify amplihack

# Use in any project
cd ~/any-project
amplihack launch
```

**Benefits:**
- ✅ Install once, available everywhere
- ✅ Automatic updates across all projects
- ✅ Zero per-project configuration
- ✅ 50MB disk space saved per project

**Method 2: Per-Project Mode**

Copy `.claude/` to each project (legacy mode):

```bash
# UVX mode still works
uvx --from git+https://github.com/rysweet/amplihack amplihack launch

# Or install locally and copy
amplihack install
cd ~/project
cp -r ~/.claude ./.claude
```

**When to use per-project:**
- Project needs custom agents or workflows
- Version pinning required
- Experimenting with modifications

### Plugin Location

Plugin installs at:
```
~/.amplihack/.claude/
├── agents/          # 29 specialized agents
├── commands/        # 20+ slash commands
├── skills/          # 54+ reusable skills
├── tools/
│   └── amplihack/
│       └── hooks/   # Lifecycle hooks
├── workflow/        # DEFAULT_WORKFLOW.md
└── context/         # PHILOSOPHY.md, PATTERNS.md
```

Settings registered in:
```
~/.claude/settings.json
{
  "enabledPlugins": ["amplihack"],
  "extraKnownMarketplaces": [{
    "name": "amplihack",
    "url": "https://github.com/rysweet/amplihack"
  }]
}
```

### Mode Detection

Amplihack automatically detects which mode t' use:

```
Mode Precedence (Highest to Lowest)
──────────────────────────────────────
1. LOCAL:  Project has .claude/ directory → Use local
2. PLUGIN: Plugin installed at ~/.amplihack/ → Use plugin
3. NONE:   No installation → Prompt to install
```

Check current mode:
```bash
cd ~/project
amplihack mode status

# Output:
# Current mode: plugin
#   Using: /home/user/.amplihack/.claude
```

### Plugin Commands

```bash
# Installation
amplihack plugin install <source>      # Install from git URL or local path
amplihack plugin install --force       # Reinstall/update plugin
amplihack plugin uninstall amplihack   # Remove plugin
amplihack plugin verify amplihack      # Verify installation

# Mode Management
amplihack mode status                  # Show current mode
amplihack mode migrate-to-plugin       # Migrate project to plugin
amplihack mode migrate-to-local        # Create local .claude/ from plugin

# Environment Override
AMPLIHACK_MODE=plugin amplihack launch # Force plugin mode
```

### Migration from Per-Project

If ye have existing projects with `.claude/` directories:

```bash
# Install plugin
amplihack plugin install https://github.com/rysweet/amplihack

# Migrate each project
cd ~/project1
amplihack mode migrate-to-plugin

cd ~/project2
amplihack mode migrate-to-plugin
```

See [Migration Guide](./docs/MIGRATION_GUIDE.md) fer detailed instructions.

### Verification

After installation, verify everythin' works:

```bash
# Check plugin status
amplihack plugin verify amplihack

# Output:
# Plugin: amplihack
#   Installed: ✅
#   Discoverable: ✅
#   Hooks loaded: ✅

# Test in project
cd ~/any-project
amplihack launch -- -p "quick test"
```

### Updating Plugin

To get latest changes:

```bash
# Force reinstall from git
amplihack plugin install --force https://github.com/rysweet/amplihack

# Or from specific branch
amplihack plugin install --force https://github.com/rysweet/amplihack@main
```

Changes apply t' ALL projects automatically.

### Troubleshooting

**Plugin not found:**
```bash
# Reinstall
amplihack plugin install https://github.com/rysweet/amplihack

# Verify
amplihack plugin verify amplihack
```

**Commands not available:**
```bash
# Check mode
amplihack mode status

# Should show: plugin or local
# If shows: none, install plugin
```

**Local .claude/ takes precedence:**
```bash
# Expected behavior - local overrides plugin
# To use plugin, migrate:
amplihack mode migrate-to-plugin
```

### Documentation

- **[Plugin Architecture](./docs/PLUGIN_ARCHITECTURE.md)** - Technical details, hook registration, settings integration
- **[Migration Guide](./docs/MIGRATION_GUIDE.md)** - Step-by-step migration from per-project to plugin
- **[CLI Commands Reference](./docs/PLUGIN_CLI_HELP.md)** - Complete command documentation with examples
- **[Cross-Tool Compatibility](./docs/PLUGIN_ARCHITECTURE.md#cross-tool-compatibility)** - Claude Code, Copilot, Codex compatibility

### Cross-Tool Support

| Tool | Status | Installation |
|------|--------|--------------|
| **Claude Code** | ✅ Full support | `amplihack plugin install` |
| **GitHub Copilot** | ⚠️ Partial | Manual copy to `.claude/` |
| **Codex** | ⚠️ Unknown | Test with per-project mode |

See [Plugin Architecture](./docs/PLUGIN_ARCHITECTURE.md#cross-tool-compatibility) fer details.

---

**Insert this section into README.md after line 101 (after "Create Alias for Easy Access" section)**
