# amplihack Plugin Documentation

Complete documentation for the amplihack Claude Code plugin architecture.

## Quick Navigation

- **Getting Started**: [README](./README.md) - Overview and quick start
- **Installation**: [Installation Guide](./PLUGIN_INSTALLATION.md) - Complete installation instructions
- **LSP Configuration**: [LSP Guide](./LSP_CONFIGURATION.md) - Language server auto-detection
- **Development**: [Development Guide](./PLUGIN_DEVELOPMENT.md) - Contributing to the plugin

## What is the Plugin Architecture?

The amplihack Claude Code plugin transforms amplihack from a directory-based distribution to a portable, zero-install plugin system that works across all your projects.

**Key Benefits:**

- **Zero Configuration**: Install once, use everywhere
- **Auto-Detection**: LSP integration detects project languages
- **Always Updated**: Update once, applies to all projects
- **Multi-Platform**: Works with Claude Code, GitHub Copilot, Codex

## Documentation Structure

### User Guides

For users who want to install and use amplihack:

| Document                                        | Purpose                  | Audience    |
| ----------------------------------------------- | ------------------------ | ----------- |
| [README](./README.md)                           | Overview and quick start | All users   |
| [PLUGIN_INSTALLATION](./PLUGIN_INSTALLATION.md) | Installation and setup   | New users   |
| [LSP_CONFIGURATION](./LSP_CONFIGURATION.md)     | Language server setup    | Power users |

### Developer Guides

For contributors and plugin developers:

| Document                                      | Purpose            | Audience   |
| --------------------------------------------- | ------------------ | ---------- |
| [PLUGIN_DEVELOPMENT](./PLUGIN_DEVELOPMENT.md) | Contributing guide | Developers |

## Quick Start

### Install Plugin

```bash
# Install amplihack
pip install amplihack

# Install plugin
amplihack plugin install

# Verify
amplihack plugin status
```

### Use in Any Project

```bash
cd my-project
claude

# amplihack commands available
/ultrathink "Add feature"
```

## Architecture Overview

```
~/.amplihack/                    # Plugin home
├── .claude/                    # ${CLAUDE_PLUGIN_ROOT}
│   ├── agents/                # 32 specialized agents
│   ├── commands/              # 25 slash commands
│   ├── skills/                # 90+ auto-loading skills
│   └── workflow/              # Process definitions
└── config/                    # User configuration
    ├── lsp/                  # Language server configs
    └── preferences/          # User preferences
```

## Key Concepts

### Plugin Root

`${CLAUDE_PLUGIN_ROOT}` = `~/.amplihack/.claude/`

All plugin paths resolved relative to this root. Enables portable, location-independent installations.

### LSP Auto-Detection

Plugin automatically detects project languages and configures appropriate language servers:

- TypeScript/JavaScript → tsserver
- Python → pylsp
- Rust → rust-analyzer
- Go → gopls
- And more...

### Global Installation

One plugin installation serves all projects. No per-project setup needed.

## Common Tasks

### Check Plugin Status

```bash
amplihack plugin status
```

### Detect Project Languages

```bash
amplihack plugin lsp-detect
```

### Update Plugin

```bash
amplihack plugin update
```

### Configure Preferences

```bash
amplihack config set communication_style technical
amplihack config set verbosity balanced
```

## Troubleshooting

See detailed troubleshooting in:

- [Installation Guide - Troubleshooting](./PLUGIN_INSTALLATION.md#troubleshooting)
- [LSP Configuration - Troubleshooting](./LSP_CONFIGURATION.md#troubleshooting)

### Quick Fixes

**Plugin not found**:

```bash
amplihack plugin install --force
```

**Commands not available**:

```bash
amplihack plugin link --force
```

**LSP not working**:

```bash
amplihack plugin lsp-detect --force
```

## Migration

Migrating from directory-based amplihack?

```bash
# Backup existing installations
amplihack migrate backup

# Install plugin
amplihack plugin install

# Migrate settings
amplihack migrate settings

# Clean up old installations
amplihack migrate cleanup --confirm
```

## Support

- **Documentation**: This directory
- **Issues**: [GitHub Issues](https://github.com/rysweet/amplihack/issues)
- **Discussions**: [GitHub Discussions](https://github.com/rysweet/amplihack/discussions)

## Contributing

Want to contribute? See [Development Guide](./PLUGIN_DEVELOPMENT.md).

```bash
# Clone repo
git clone https://github.com/rysweet/amplihack.git
cd amplihack

# Install in development mode
pip install -e .
amplihack plugin install --dev

# Make changes and test
pytest tests/plugin/
```

## Philosophy

The plugin follows amplihack's core philosophy:

- **Ruthless Simplicity**: Zero-install, one-command setup
- **Modular Design**: Self-contained, regeneratable components
- **Zero-BS Implementation**: Everything works or doesn't exist
- **Trust in Emergence**: Complex capabilities from simple components

---

**Start here**: [README](./README.md) for overview and quick start.
