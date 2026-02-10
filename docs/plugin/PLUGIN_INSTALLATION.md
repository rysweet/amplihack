# Plugin Installation Guide

Complete guide to installing the amplihack Claude Code plugin.

## Prerequisites

Before installing the plugin, ensure you have:

- **Python 3.9+** installed
- **pip** or **uv** package manager
- **Claude Code** installed and configured
- **Git** (for source installation)

### System Requirements

| Platform | Requirement                              |
| -------- | ---------------------------------------- |
| macOS    | 10.15+ (Catalina or later)               |
| Linux    | Ubuntu 20.04+, Fedora 35+, or equivalent |
| Windows  | Windows 10+ with WSL2                    |

### Claude Code Requirement

Verify Claude Code is installed:

```bash
claude --version
# Should output: Claude Code v1.x.x or later
```

If not installed, install with:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

> **Security Note**: For additional security, you can inspect the installation script before running it:
>
> ```bash
> curl -fsSL https://claude.ai/install.sh -o install.sh
> # Review the script contents
> less install.sh
> # Then run it
> bash install.sh
> ```

## Installation Methods

### Method 1: Quick Install (Recommended)

Install from PyPI with one command:

```bash
# Install amplihack
pip install amplihack

# Install the plugin
amplihack plugin install

# Verify
amplihack plugin status
```

**Output:**

```
✓ Plugin installed at ~/.amplihack/.claude/
✓ LSP integration configured
✓ Commands registered: 25
✓ Agents available: 32
✓ Skills available: 90

Plugin is ready! Start using with: claude
```

### Method 2: Install with uv (Faster)

```bash
# Install using uv
uv pip install amplihack

# Install plugin
uvx --from amplihack plugin-install

# Verify
amplihack plugin status
```

### Method 3: Install from Source

For development or latest features:

```bash
# Clone repository
git clone https://github.com/rysweet/amplihack.git
cd amplihack

# Install in editable mode
pip install -e .

# Install plugin from source
amplihack plugin install --dev

# Verify
amplihack plugin status
```

### Method 4: Install from GitHub (No Clone)

```bash
# Install directly from GitHub
pip install git+https://github.com/rysweet/amplihack.git

# Install plugin
amplihack plugin install

# Verify
amplihack plugin status
```

## Installation Process

The `amplihack plugin install` command performs these steps:

1. **Creates plugin directory**: `~/.amplihack/.claude/`
2. **Copies framework files**: Agents, commands, skills, workflows
3. **Configures LSP**: Auto-detects and configures language servers
4. **Registers commands**: Makes `/ultrathink`, `/analyze`, etc. available
5. **Sets up preferences**: Creates default user configuration
6. **Links to Claude Code**: Registers plugin with Claude Code

### Installation Locations

```
~/.amplihack/                    # Plugin home
├── .claude/                    # ${CLAUDE_PLUGIN_ROOT}
│   ├── agents/                # 32 specialized agents
│   ├── commands/              # 25 slash commands
│   ├── context/               # Philosophy, patterns, trust
│   ├── skills/                # 90+ auto-loading skills
│   ├── templates/             # Reusable templates
│   ├── tools/                 # LSP, hooks, utilities
│   └── workflow/              # Process definitions
├── config/                    # User configuration
│   ├── lsp/                  # Language server configs
│   │   ├── typescript.json
│   │   ├── python.json
│   │   └── rust.json
│   └── preferences/          # User preferences
│       └── USER_PREFERENCES.md
└── logs/                      # Plugin logs
    └── install.log
```

## Verification

### Check Installation Status

```bash
# Full status check
amplihack plugin status

# Output:
# Plugin Status:
# - Installed: Yes
# - Location: /home/username/.amplihack/.claude
# - Version: 0.9.0
# - Agents: 32 available
# - Commands: 25 registered
# - Skills: 90 loaded
# - LSP: Configured for 5 languages
```

### Test Plugin Functionality

```bash
# Test in a project directory
cd ~/test-project
claude

# Try a command
/ultrathink "Test installation"

# Expected: UltraThink workflow starts successfully
```

### Verify LSP Integration

```bash
# Check LSP status
amplihack plugin lsp-status

# Output:
# Language Server Status:
# - TypeScript: ✓ Configured (tsserver)
# - Python: ✓ Configured (pylsp)
# - Rust: ✓ Configured (rust-analyzer)
# - Go: ✓ Configured (gopls)
# - JavaScript: ✓ Configured (tsserver)
```

## Configuration

### Set User Preferences

```bash
# Configure communication style
amplihack config set communication_style technical

# Set verbosity
amplihack config set verbosity balanced

# Configure collaboration style
amplihack config set collaboration_style autonomous

# View all preferences
amplihack config show
```

**Config file location**: `~/.amplihack/config/preferences/USER_PREFERENCES.md`

### Configure LSP

```bash
# Auto-detect project languages
amplihack plugin lsp-detect

# Manually configure specific language
amplihack plugin lsp-configure --lang python --server pylsp

# View LSP config
cat ~/.amplihack/config/lsp/python.json
```

**Example LSP config**:

```json
{
  "language": "python",
  "server": "pylsp",
  "command": "pylsp",
  "initialization_options": {
    "pylsp": {
      "plugins": {
        "pycodestyle": { "enabled": true },
        "pyflakes": { "enabled": true }
      }
    }
  }
}
```

## Platform-Specific Instructions

### macOS

```bash
# Install with Homebrew Python
brew install python@3.11
pip3 install amplihack
amplihack plugin install

# If using multiple Python versions
python3.11 -m pip install amplihack
python3.11 -m amplihack plugin install
```

### Linux (Ubuntu/Debian)

```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv

# Install amplihack
pip3 install amplihack
amplihack plugin install

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Linux (Fedora)

```bash
# Install dependencies
sudo dnf install python3-pip python3-virtualenv

# Install amplihack
pip3 install amplihack
amplihack plugin install
```

### Windows (WSL2)

```bash
# Inside WSL2
sudo apt update
sudo apt install python3-pip

# Install amplihack
pip3 install amplihack
amplihack plugin install

# Verify Windows path access
amplihack plugin status --verbose
```

## Updating

### Update to Latest Version

```bash
# Update amplihack package
pip install --upgrade amplihack

# Update plugin
amplihack plugin update

# Verify update
amplihack plugin status
```

### Update to Specific Version

```bash
# Install specific version
pip install amplihack==0.9.0

# Update plugin to match
amplihack plugin update --version 0.9.0
```

### Check for Updates

```bash
# Check without updating
amplihack plugin check-updates

# Output:
# Current version: 0.8.5
# Latest version: 0.9.0
# Update available: Yes
```

## Uninstalling

### Standard Uninstall (Preserves Config)

```bash
# Remove plugin (keeps config)
amplihack plugin uninstall

# Output:
# ✓ Plugin removed from ~/.amplihack/.claude/
# ✓ Commands unregistered
# ✓ Config preserved in ~/.amplihack/config/
```

Config files remain in `~/.amplihack/config/` for reinstallation.

### Complete Uninstall (Removes Everything)

```bash
# Remove plugin and config
amplihack plugin uninstall --purge

# Remove amplihack package
pip uninstall amplihack

# Verify removal
ls ~/.amplihack/
# Directory should not exist
```

## Troubleshooting

### Installation Fails

**Issue**: `amplihack plugin install` fails with permission error

**Solution**:

```bash
# Check permissions
ls -la ~/.amplihack/

# Fix ownership
chown -R $USER:$USER ~/.amplihack/

# Retry installation
amplihack plugin install --force
```

### Plugin Not Found After Install

**Issue**: `amplihack plugin status` says "Not installed"

**Solution**:

```bash
# Check installation directory
ls -la ~/.amplihack/.claude/

# If missing, reinstall
amplihack plugin install --clean

# Verify CLAUDE_PLUGIN_ROOT
echo $CLAUDE_PLUGIN_ROOT
# Should output: /home/username/.amplihack/.claude
```

### Commands Not Available in Claude Code

**Issue**: `/ultrathink` and other commands not recognized

**Solution**:

```bash
# Verify plugin registration
amplihack plugin status

# Re-register commands
amplihack plugin link --force

# Restart Claude Code
# Close all Claude Code instances and restart
```

### LSP Not Detecting Languages

**Issue**: Language servers not auto-configuring

**Solution**:

```bash
# Force LSP detection
amplihack plugin lsp-detect --force

# Check LSP logs
amplihack plugin logs --filter lsp

# Manually configure
amplihack plugin lsp-configure --lang typescript --server tsserver
```

### Version Mismatch

**Issue**: Plugin version doesn't match package version

**Solution**:

```bash
# Check versions
amplihack --version        # Package version
amplihack plugin status    # Plugin version

# Update plugin to match
amplihack plugin update --sync

# Verify match
amplihack plugin status
```

### Permission Denied on macOS

**Issue**: Installation fails with "Permission denied" on macOS

**Solution**:

```bash
# Don't use sudo with pip
pip3 install --user amplihack

# Install plugin (no sudo needed)
amplihack plugin install

# If ~/.amplihack/ is owned by root
sudo chown -R $USER:staff ~/.amplihack/
```

### WSL Path Issues

**Issue**: Windows paths not working in WSL

**Solution**:

```bash
# Use WSL paths only
cd ~/projects/my-app  # Not /mnt/c/Users/...

# Configure WSL path
amplihack config set wsl_mode enabled

# Verify
amplihack plugin status --verbose
```

### Import Errors

**Issue**: `ImportError: No module named 'amplihack'`

**Solution**:

```bash
# Verify installation
pip list | grep amplihack

# If missing, reinstall
pip install amplihack

# Check Python version
python --version  # Must be 3.9+

# If multiple Python versions
python3.11 -m pip install amplihack
```

## Advanced Installation

### Custom Plugin Location

```bash
# Install to custom location
export CLAUDE_PLUGIN_ROOT=/custom/path/.claude
amplihack plugin install --location $CLAUDE_PLUGIN_ROOT

# Verify
amplihack plugin status
# Location: /custom/path/.claude
```

### Offline Installation

```bash
# On internet-connected machine
pip download amplihack -d ~/amplihack-offline/

# Transfer ~/amplihack-offline/ to offline machine

# On offline machine
pip install ~/amplihack-offline/amplihack-*.whl
amplihack plugin install --offline
```

### Corporate Proxy

```bash
# Configure proxy
export HTTP_PROXY=http://proxy.corp.com:8080
export HTTPS_PROXY=http://proxy.corp.com:8080

# Install with proxy
pip install amplihack --proxy $HTTP_PROXY
amplihack plugin install
```

### Virtual Environment

```bash
# Create virtual environment
python -m venv ~/venvs/amplihack
source ~/venvs/amplihack/bin/activate

# Install
pip install amplihack
amplihack plugin install

# Plugin persists outside venv at ~/.amplihack/
```

## Migration from Directory-Based Install

If you previously used directory-based amplihack:

```bash
# Backup existing installations
amplihack migrate backup

# Install plugin
amplihack plugin install

# Migrate settings from old installations
amplihack migrate settings --from .claude/

# Verify migration
amplihack plugin status

# Clean up old installations (optional)
amplihack migrate cleanup --confirm
```

See [Migration Guide](./PLUGIN_MIGRATION.md) for details.

## Getting Help

### View Logs

```bash
# View installation log
amplihack plugin logs --type install

# View recent errors
amplihack plugin logs --level error --tail 50

# Follow live logs
amplihack plugin logs --follow
```

### Diagnostic Report

```bash
# Generate diagnostic report
amplihack plugin diagnose

# Output:
# Diagnostic Report
# ================
# OS: Linux 5.15.0
# Python: 3.11.5
# Plugin: 0.9.0
# Claude Code: 1.2.3
# LSP Status: 5 configured
# Recent Errors: None
#
# Report saved: ~/.amplihack/logs/diagnostic-2025-01-16.txt
```

### Community Support

- **GitHub Issues**: [Report bugs](https://github.com/rysweet/amplihack/issues)
- **Discussions**: [Ask questions](https://github.com/rysweet/amplihack/discussions)
- **Documentation**: [Full docs](../index.md)

## Next Steps

After successful installation:

1. [Configure LSP for your languages](./LSP_CONFIGURATION.md)
2. [Set user preferences](./PLUGIN_CONFIGURATION.md)
3. [Start using amplihack](./README.md#usage)
4. [Learn plugin development](./PLUGIN_DEVELOPMENT.md)

---

**Installation complete!** Start Claude Code in any project to use amplihack.
