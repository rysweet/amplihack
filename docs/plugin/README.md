# amplihack Claude Code Plugin

**The AI-powered development framework as a portable, zero-install Claude Code plugin.**

## What is This?

The amplihack Claude Code Plugin brings the full power of amplihack's specialized agents, workflows, and tools to your Claude Code environment through a simple plugin installation. No more copying directories - install once, use everywhere.

## Quick Start

```bash
# Install the plugin
amplihack plugin install

# Verify installation
amplihack plugin status

# Start using amplihack in any project
cd my-project
claude  # amplihack is now available!
```

That's it! amplihack is now available in all your Claude Code sessions.

## Contents

- [Installation Guide](./PLUGIN_INSTALLATION.md) - Complete installation instructions
- [LSP Configuration](./LSP_CONFIGURATION.md) - Language server auto-detection
- [Development Guide](./PLUGIN_DEVELOPMENT.md) - Contributing to the plugin
- [Troubleshooting](#troubleshooting) - Common issues and solutions

## What You Get

### Core Features

**Specialized AI Agents**

- 30+ production-ready agents (architect, builder, tester, security, etc.)
- Parallel execution by default
- Auto-detection of which agents to use

**Automated Workflows**

- DEFAULT_WORKFLOW: Standard 22-step development process
- Investigation workflow: Deep codebase analysis
- Document-Driven Development: Docs-first approach
- Fault tolerance patterns: N-version, debate, cascade

**Claude Code Skills**

- 90+ skills auto-load when needed
- Mermaid diagrams, documentation writing, code analysis
- Testing, validation, and quality checks

**Multi-Platform Support**

- Claude Code (primary)
- GitHub Copilot CLI
- Codex
- Any Claude-compatible environment

### Plugin Benefits

**Zero Configuration**

- Installs to `~/.amplihack/.claude/`
- Works in any project directory
- No per-project setup needed

**Auto-Detection**

- LSP integration detects project languages
- Appropriate agents auto-activate
- Context-aware assistance

**Always Up-to-Date**

- Update once, applies everywhere
- No scattered installations
- Consistent experience across projects

## Architecture

```
~/.amplihack/
├── .claude/              # Plugin root (${CLAUDE_PLUGIN_ROOT})
│   ├── agents/          # 30+ specialized agents
│   ├── commands/        # Slash commands (/ultrathink, etc.)
│   ├── context/         # Philosophy, patterns, trust
│   ├── skills/          # 90+ auto-loading skills
│   ├── templates/       # Reusable templates
│   ├── tools/           # LSP integration, hooks
│   └── workflow/        # Process definitions
└── config/              # User configuration
    ├── lsp/            # Language server configs
    └── preferences/    # User preferences
```

**Key Concepts:**

- **Plugin Root**: `${CLAUDE_PLUGIN_ROOT}` = `~/.amplihack/.claude/`
- **Global Install**: One installation serves all projects
- **Path Resolution**: All internal paths use `${CLAUDE_PLUGIN_ROOT}`
- **LSP Integration**: Auto-detects TypeScript, Python, Rust, Go, etc.

## Installation

See [PLUGIN_INSTALLATION.md](./PLUGIN_INSTALLATION.md) for complete instructions.

**Quick install:**

```bash
# From PyPI
pip install amplihack
amplihack plugin install

# From source
git clone https://github.com/rysweet/amplihack.git
cd amplihack
pip install -e .
amplihack plugin install
```

## Usage

Once installed, amplihack is available in all Claude Code sessions:

```bash
# In any project
cd ~/projects/my-app
claude

# amplihack commands are available
/ultrathink "Add authentication"
/analyze src/
/amplihack:ddd:1-plan
```

**No project-specific installation needed!**

## LSP Configuration

The plugin automatically configures language servers for your projects:

```bash
# Auto-detects project languages
amplihack plugin lsp-detect

# Shows detected LSP configs
amplihack plugin lsp-status

# Manually configure
amplihack plugin lsp-configure --lang typescript
```

See [LSP_CONFIGURATION.md](./LSP_CONFIGURATION.md) for details.

## Configuration

### User Preferences

Preferences stored in `~/.amplihack/config/preferences/USER_PREFERENCES.md`:

```bash
# Set preferences (applies to all projects)
amplihack config set communication_style pirate
amplihack config set verbosity balanced

# Show current config
amplihack config show
```

### Project-Specific Overrides

Override plugin defaults for specific projects:

```bash
cd my-project

# Create local override
amplihack local init

# Configure project-specific settings
amplihack local set coding_standards "2-space indentation"
```

Local settings in `.amplihack/local/` override plugin defaults.

## Updating

```bash
# Update the plugin
amplihack plugin update

# Check for updates
amplihack plugin check-updates

# Update to specific version
amplihack plugin update --version 1.2.0
```

## Uninstalling

```bash
# Remove plugin (preserves user config)
amplihack plugin uninstall

# Remove everything including config
amplihack plugin uninstall --purge
```

## Troubleshooting

### Plugin Not Found

```bash
# Check installation status
amplihack plugin status

# Verify path
echo $CLAUDE_PLUGIN_ROOT
# Should show: /home/username/.amplihack/.claude

# Reinstall if needed
amplihack plugin install --force
```

### Claude Code Not Detecting Plugin

```bash
# Verify Claude Code integration
claude --list-plugins

# Re-link if needed
amplihack plugin link
```

### LSP Not Working

```bash
# Check LSP status
amplihack plugin lsp-status

# Re-detect languages
amplihack plugin lsp-detect --force

# View logs
amplihack plugin logs --filter lsp
```

### Commands Not Available

```bash
# Verify plugin is active
amplihack plugin status

# Check command registration
amplihack plugin commands

# Restart Claude Code
# (sometimes needed after first install)
```

For more help, see [PLUGIN_INSTALLATION.md](./PLUGIN_INSTALLATION.md#troubleshooting).

## Examples

### Example 1: New Project Setup

```bash
# Create new project
mkdir my-app && cd my-app
git init

# Start Claude Code (plugin auto-loads)
claude

# Use amplihack immediately
/ultrathink "Create a FastAPI REST API"
```

### Example 2: Adding to Existing Project

```bash
# Navigate to existing project
cd existing-project

# Start Claude Code
claude

# Investigate codebase
/amplihack:investigate "Understand authentication flow"

# Make improvements
/ultrathink "Add rate limiting to API endpoints"
```

### Example 3: Multi-Project Usage

```bash
# Project A
cd ~/projects/frontend
claude
/ultrathink "Add dark mode"

# Project B (same plugin, different project)
cd ~/projects/backend
claude
/ultrathink "Optimize database queries"

# Both use the same plugin installation!
```

## Marketplace

The plugin is available from multiple sources:

- **GitHub**: `github.com/rysweet/amplihack`
- **PyPI**: `pip install amplihack`
- **uvx**: `uvx --from amplihack plugin-install`

## Development

Want to contribute? See [PLUGIN_DEVELOPMENT.md](./PLUGIN_DEVELOPMENT.md).

```bash
# Clone repo
git clone https://github.com/rysweet/amplihack.git
cd amplihack

# Install in development mode
pip install -e .

# Install plugin from source
amplihack plugin install --dev

# Run tests
pytest tests/plugin/
```

## Migration

### From Directory-Based amplihack

If you're using the old directory-copy distribution:

```bash
# Backup existing installations
amplihack migrate backup

# Install plugin
amplihack plugin install

# Migrate settings
amplihack migrate settings

# Remove old installations
amplihack migrate cleanup --confirm
```

See [Migration Guide](./PLUGIN_MIGRATION.md) for details.

## Philosophy

The plugin follows amplihack's core philosophy:

- **Ruthless Simplicity**: Zero-install, one-command setup
- **Modular Design**: Self-contained, regeneratable components
- **Zero-BS Implementation**: Everything works or doesn't exist
- **Trust in Emergence**: Complex capabilities from simple components

## Support

- **Documentation**: [docs/plugin/](./index.md)
- **Issues**: [GitHub Issues](https://github.com/rysweet/amplihack/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rysweet/amplihack/discussions)

## License

MIT License - see [LICENSE](../../LICENSE) for details.

---

**Next Steps:**

- [Install the plugin](./PLUGIN_INSTALLATION.md)
- [Configure LSP](./LSP_CONFIGURATION.md)
- [Start developing](./PLUGIN_DEVELOPMENT.md)
