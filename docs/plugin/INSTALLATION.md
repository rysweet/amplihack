# Plugin Installation Guide

Learn how to install amplihack as a centralized Claude Code plugin.

## What You'll Learn

By the end of this tutorial, you'll have amplihack installed as a global plugin at `~/.amplihack/.claude/`, ready to use across all your projects.

## Prerequisites

- Python 3.8 or higher
- pip or uv package manager
- Claude Code, GitHub Copilot, or Codex IDE

## Installation Methods

### Method 1: Install via pip (Recommended)

The fastest way to install amplihack as a plugin:

```bash
pip install amplihack
amplihack plugin install
```

**Expected Output:**

```
Installing amplihack plugin to ~/.amplihack/.claude/
✓ Created plugin directory structure
✓ Installed agents (42 agents)
✓ Installed commands (18 commands)
✓ Installed skills (12 skills)
✓ Installed workflows (5 workflows)
✓ Configured hooks with ${CLAUDE_PLUGIN_ROOT}
✓ Set up LSP auto-detection

Plugin installed successfully!
Location: /home/username/.amplihack/.claude/

Next steps:
  1. Restart your IDE
  2. Run 'amplihack plugin verify' to test installation
```

### Method 2: Install from Git

Install directly from the repository:

```bash
pip install git+https://github.com/rysweet/amplihack.git
amplihack plugin install
```

This method installs the latest development version.

### Method 3: Install from Marketplace

Install from the Claude Code plugin marketplace:

```bash
claude plugin install github.com/rysweet/amplihack
```

Claude Code automatically runs `amplihack plugin install` after downloading the package.

## Verify Installation

Check that the plugin installed correctly:

```bash
amplihack plugin verify
```

**Expected Output:**

```
Verifying amplihack plugin installation...

✓ Plugin directory exists: ~/.amplihack/.claude/
✓ Plugin manifest valid: .claude-plugin/plugin.json
✓ Agents directory: 42 agents found
✓ Commands directory: 18 commands found
✓ Skills directory: 12 skills found
✓ Workflows directory: 5 workflows found
✓ Hooks configured: 3 hooks with ${CLAUDE_PLUGIN_ROOT}
✓ LSP auto-detection: Enabled

All checks passed! Plugin is ready to use.
```

## Directory Structure

After installation, your `~/.amplihack/.claude/` directory contains:

```
~/.amplihack/.claude/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── agents/                       # 42 specialized agents
│   └── amplihack/
│       ├── core/                 # Core agents
│       ├── specialized/          # Domain-specific agents
│       └── workflow/             # Workflow coordinators
├── commands/                     # 18 slash commands
│   ├── ultrathink.py
│   ├── analyze.py
│   └── ...
├── skills/                       # 12 Claude Code skills
│   ├── documentation-writing/
│   ├── mermaid-diagram-generator/
│   └── ...
├── workflow/                     # 5 workflow definitions
│   ├── DEFAULT_WORKFLOW.md
│   ├── INVESTIGATION_WORKFLOW.md
│   └── ...
├── tools/                        # Hooks and utilities
│   ├── PostInit.sh              # Uses ${CLAUDE_PLUGIN_ROOT}
│   ├── PreCommit.sh             # Uses ${CLAUDE_PLUGIN_ROOT}
│   └── PreCompact.sh            # Uses ${CLAUDE_PLUGIN_ROOT}
└── context/                      # Philosophy and patterns
    ├── PHILOSOPHY.md
    ├── PATTERNS.md
    └── TRUST.md
```

## Project-Specific Settings

Each project can override plugin settings by creating `.claude/settings.json`:

```json
{
  "amplihack": {
    "preferred_workflow": "INVESTIGATION_WORKFLOW",
    "custom_agents": ["./local-agents/domain-expert.md"],
    "disabled_hooks": ["PreCommit"]
  }
}
```

The plugin merges these settings with the base configuration at `~/.amplihack/.claude/settings.json`.

## Troubleshooting

### Plugin directory not found

**Problem:** `amplihack plugin verify` reports directory not found.

**Solution:**

```bash
# Re-run installation
amplihack plugin install

# Check if directory was created
ls -la ~/.amplihack/.claude/
```

### IDE not recognizing plugin

**Problem:** Claude Code doesn't show amplihack commands or agents.

**Solution:**

1. Restart your IDE completely
2. Check IDE plugin settings:

```bash
# For Claude Code
cat ~/.config/claude-code/plugins.json

# Should show:
# {
#   "plugins": [
#     {
#       "name": "amplihack",
#       "path": "~/.amplihack/.claude/"
#     }
#   ]
# }
```

3. Re-link the plugin if needed:

```bash
amplihack plugin link
```

### Hooks not executing

**Problem:** PostInit, PreCommit, or PreCompact hooks don't run.

**Solution:**

1. Verify hook paths use `${CLAUDE_PLUGIN_ROOT}`:

```bash
cat ~/.amplihack/.claude/.claude-plugin/plugin.json | grep hooks
```

2. Check hook permissions:

```bash
chmod +x ~/.amplihack/.claude/tools/*.sh
```

3. Test hook manually:

```bash
export CLAUDE_PLUGIN_ROOT=~/.amplihack/.claude
bash ~/.amplihack/.claude/tools/PostInit.sh
```

### LSP not detecting project language

**Problem:** LSP features (go-to-definition, hover) not working.

**Solution:**

1. Check LSP configuration:

```bash
cat ~/.amplihack/.claude/.claude-plugin/plugin.json | grep lsp
```

2. Verify project has language-specific files:

```bash
# For Python projects
ls *.py pyproject.toml setup.py

# For JavaScript projects
ls *.js package.json
```

3. Manually configure LSP in project `.claude/settings.json`:

```json
{
  "lsp": {
    "python": {
      "command": "pylsp",
      "enabled": true
    }
  }
}
```

### Permission denied errors

**Problem:** Cannot write to `~/.amplihack/.claude/`.

**Solution:**

```bash
# Fix permissions
sudo chown -R $(whoami) ~/.amplihack/

# Verify
ls -la ~/.amplihack/.claude/
```

## Next Steps

After installation:

1. **Read the architecture guide**: See [ARCHITECTURE.md](./ARCHITECTURE.md) to understand how the plugin works
2. **Try a command**: Run `/ultrathink analyze this codebase` in Claude Code
3. **Explore agents**: List available agents with `amplihack agents list`
4. **Migrate existing projects**: See [MIGRATION.md](./MIGRATION.md) if you have per-project `.claude/` directories

## Additional Resources

- [Plugin Architecture](./ARCHITECTURE.md) - How the plugin system works
- [CLI Reference](./CLI_REFERENCE.md) - Complete command documentation
- [Multi-IDE Setup](./MULTI_IDE.md) - Configure for Copilot, Codex, etc.
- [Migration Guide](./MIGRATION.md) - Move from per-project to plugin mode

---

**Last updated:** 2026-01-19
**Plugin version:** 1.0.0
