# amplihack Plugin Quick Reference

One-page reference for the amplihack Claude Code plugin.

## Installation

```bash
# Install
pip install amplihack
amplihack plugin install

# Verify
amplihack plugin status
```

## Essential Commands

| Command | Purpose |
|---------|---------|
| `amplihack plugin status` | Check plugin status |
| `amplihack plugin update` | Update to latest version |
| `amplihack plugin lsp-detect` | Detect project languages |
| `amplihack plugin lsp-status` | Show LSP configuration |
| `amplihack config show` | View preferences |
| `amplihack config set KEY VALUE` | Set preference |

## Directory Structure

```
~/.amplihack/
├── .claude/                    # ${CLAUDE_PLUGIN_ROOT}
│   ├── agents/                # 32 AI agents
│   ├── commands/              # 25 slash commands
│   ├── skills/                # 90+ skills
│   └── workflow/              # Process definitions
└── config/
    ├── lsp/                  # Language servers
    └── preferences/          # User settings
```

## Usage

```bash
# In any project
cd my-project
claude

# amplihack available immediately
/ultrathink "Add feature"
/analyze src/
```

## Supported Languages

| Language | LSP Server | Auto-Detect |
|----------|-----------|-------------|
| TypeScript | tsserver | ✓ |
| Python | pylsp | ✓ |
| Rust | rust-analyzer | ✓ |
| Go | gopls | ✓ |
| Java | jdtls | ✓ |

## Configuration

```bash
# Set preferences
amplihack config set communication_style technical
amplihack config set verbosity balanced

# Configure LSP
amplihack plugin lsp-configure --lang python --server pylsp

# View config
cat ~/.amplihack/config/preferences/USER_PREFERENCES.md
cat ~/.amplihack/config/lsp/python.json
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Plugin not found | `amplihack plugin install --force` |
| Commands unavailable | `amplihack plugin link --force` |
| LSP not working | `amplihack plugin lsp-detect --force` |
| Version mismatch | `amplihack plugin update --sync` |

## Key Concepts

- **Plugin Root**: `${CLAUDE_PLUGIN_ROOT}` = `~/.amplihack/.claude/`
- **Global Install**: One installation serves all projects
- **LSP Auto-Detection**: Automatically configures language servers
- **Zero Configuration**: Works out-of-the-box for common languages

## Environment Variables

```bash
# Custom plugin location
export CLAUDE_PLUGIN_ROOT=/custom/path/.claude

# Debug mode
export AMPLIHACK_LOG_LEVEL=debug
export AMPLIHACK_DEV_MODE=1
```

## LSP Installation

```bash
# TypeScript
npm install -g typescript-language-server typescript

# Python
pip install python-lsp-server[all]

# Rust
rustup component add rust-analyzer

# Go
go install golang.org/x/tools/gopls@latest
```

## Documentation

- **Overview**: [docs/plugin/README.md](./README.md)
- **Installation**: [docs/plugin/PLUGIN_INSTALLATION.md](./PLUGIN_INSTALLATION.md)
- **LSP Config**: [docs/plugin/LSP_CONFIGURATION.md](./LSP_CONFIGURATION.md)
- **Development**: [docs/plugin/PLUGIN_DEVELOPMENT.md](./PLUGIN_DEVELOPMENT.md)

## Support

- **GitHub Issues**: https://github.com/rysweet/amplihack/issues
- **Discussions**: https://github.com/rysweet/amplihack/discussions
- **Documentation**: https://rysweet.github.io/amplihack/

---

**Get started**: `pip install amplihack && amplihack plugin install`
