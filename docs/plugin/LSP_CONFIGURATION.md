# LSP Configuration Guide

Language Server Protocol (LSP) integration enables amplihack to understand your project's programming languages and provide context-aware assistance.

## Overview

The amplihack plugin automatically detects and configures language servers for your projects:

- **Auto-detection**: Scans project files to identify languages
- **Zero-configuration**: Works out-of-the-box for common languages
- **Customizable**: Override defaults for specific needs
- **Multi-language**: Supports TypeScript, Python, Rust, Go, Java, and more

## Supported Languages

| Language | LSP Server | Auto-Detect | Status |
|----------|-----------|-------------|---------|
| TypeScript | tsserver | ✓ | Production |
| JavaScript | tsserver | ✓ | Production |
| Python | pylsp | ✓ | Production |
| Rust | rust-analyzer | ✓ | Production |
| Go | gopls | ✓ | Production |
| Java | jdtls | ✓ | Beta |
| C++ | clangd | ✓ | Beta |
| Ruby | solargraph | ✓ | Beta |
| PHP | intelephense | - | Experimental |
| C# | omnisharp | - | Experimental |

## Quick Start

### Automatic Detection

The plugin auto-detects languages when you start Claude Code:

```bash
cd my-typescript-project
claude

# Output:
# amplihack: Detected languages: typescript, javascript
# amplihack: Configured LSP servers: tsserver
# amplihack: Ready!
```

No manual configuration needed!

### Manual Detection

Force detection in any project:

```bash
# Detect languages in current directory
amplihack plugin lsp-detect

# Output:
# Scanning project...
# Found: TypeScript (15 files)
# Found: Python (3 files)
# Configured: tsserver for TypeScript/JavaScript
# Configured: pylsp for Python
```

### Check LSP Status

```bash
# View current LSP configuration
amplihack plugin lsp-status

# Output:
# Language Server Status:
# ----------------------
# TypeScript
#   Server: tsserver
#   Status: Active
#   Config: ~/.amplihack/config/lsp/typescript.json
#
# Python
#   Server: pylsp
#   Status: Active
#   Config: ~/.amplihack/config/lsp/python.json
```

## Configuration Files

LSP configurations stored in `~/.amplihack/config/lsp/`:

```
~/.amplihack/config/lsp/
├── typescript.json    # TypeScript/JavaScript
├── python.json        # Python
├── rust.json          # Rust
├── go.json            # Go
└── custom/            # User overrides
    └── myproject.json
```

### TypeScript Configuration

**Location**: `~/.amplihack/config/lsp/typescript.json`

```json
{
  "language": "typescript",
  "server": "tsserver",
  "command": "typescript-language-server",
  "args": ["--stdio"],
  "initialization_options": {
    "preferences": {
      "includeCompletionsForModuleExports": true,
      "includeCompletionsWithInsertText": true
    }
  },
  "file_extensions": [".ts", ".tsx", ".js", ".jsx"],
  "root_markers": ["tsconfig.json", "package.json"]
}
```

### Python Configuration

**Location**: `~/.amplihack/config/lsp/python.json`

```json
{
  "language": "python",
  "server": "pylsp",
  "command": "pylsp",
  "initialization_options": {
    "pylsp": {
      "plugins": {
        "pycodestyle": {
          "enabled": true,
          "maxLineLength": 100
        },
        "pyflakes": {"enabled": true},
        "pylint": {"enabled": false},
        "jedi_completion": {"enabled": true},
        "jedi_hover": {"enabled": true},
        "jedi_references": {"enabled": true},
        "jedi_signature_help": {"enabled": true}
      }
    }
  },
  "file_extensions": [".py", ".pyi"],
  "root_markers": ["pyproject.toml", "setup.py", "requirements.txt"]
}
```

### Rust Configuration

**Location**: `~/.amplihack/config/lsp/rust.json`

```json
{
  "language": "rust",
  "server": "rust-analyzer",
  "command": "rust-analyzer",
  "initialization_options": {
    "cargo": {
      "buildScripts": {
        "enable": true
      }
    },
    "procMacro": {
      "enable": true
    }
  },
  "file_extensions": [".rs"],
  "root_markers": ["Cargo.toml"]
}
```

## Auto-Detection Logic

The plugin detects languages using this process:

### 1. File Extension Scan

```bash
# Scans project for known extensions
.ts, .tsx, .js, .jsx    → TypeScript/JavaScript
.py, .pyi               → Python
.rs                     → Rust
.go                     → Go
.java                   → Java
.cpp, .cc, .h           → C++
```

### 2. Configuration File Detection

```bash
# Looks for language-specific config files
tsconfig.json           → TypeScript
package.json            → JavaScript/TypeScript
pyproject.toml          → Python
Cargo.toml              → Rust
go.mod                  → Go
pom.xml                 → Java
CMakeLists.txt          → C++
```

### 3. Priority Rules

When multiple languages detected:

1. **Primary language**: Most files (by count)
2. **Secondary languages**: 20%+ of total files
3. **Tertiary languages**: Present but < 20%

Example:
```bash
Project files:
- 50 TypeScript files  → Primary (71%)
- 15 Python files      → Secondary (21%)
- 5 Shell scripts      → Tertiary (7%)

Configured LSP: tsserver (primary), pylsp (secondary)
```

## Manual Configuration

### Configure Specific Language

```bash
# Configure Python with custom server
amplihack plugin lsp-configure \
  --lang python \
  --server pylsp \
  --command "pylsp" \
  --args "--stdio"

# Verify configuration
amplihack plugin lsp-status --lang python
```

### Add Custom Language

```bash
# Add Elixir support
amplihack plugin lsp-add \
  --lang elixir \
  --server elixir-ls \
  --command "language_server.sh" \
  --extensions ".ex,.exs" \
  --root-markers "mix.exs"

# Test configuration
amplihack plugin lsp-test --lang elixir
```

### Override Default Settings

Create custom configuration in `~/.amplihack/config/lsp/custom/`:

```bash
# Create override for TypeScript
cat > ~/.amplihack/config/lsp/custom/typescript-strict.json << 'EOF'
{
  "language": "typescript",
  "server": "tsserver",
  "initialization_options": {
    "preferences": {
      "strict": true,
      "noImplicitAny": true,
      "strictNullChecks": true
    }
  }
}
EOF

# Apply custom config
amplihack plugin lsp-apply --config typescript-strict
```

## Per-Project Configuration

Override plugin defaults for specific projects:

### Create Project LSP Config

```bash
cd my-project

# Initialize local LSP config
amplihack local lsp-init

# Created: .amplihack/local/lsp.json
```

**Example project config** (`.amplihack/local/lsp.json`):

```json
{
  "languages": {
    "typescript": {
      "server": "tsserver",
      "initialization_options": {
        "preferences": {
          "quotePreference": "single",
          "semicolons": "remove"
        }
      }
    },
    "python": {
      "server": "pyright",
      "initialization_options": {
        "python": {
          "pythonPath": ".venv/bin/python",
          "venvPath": ".",
          "analysis": {
            "typeCheckingMode": "strict"
          }
        }
      }
    }
  }
}
```

### Project Config Priority

Configuration precedence (highest to lowest):

1. `.amplihack/local/lsp.json` (project-specific)
2. `~/.amplihack/config/lsp/custom/*.json` (user overrides)
3. `~/.amplihack/config/lsp/*.json` (plugin defaults)

## Installing LSP Servers

### TypeScript (tsserver)

```bash
# Install via npm
npm install -g typescript-language-server typescript

# Verify
typescript-language-server --version
```

### Python (pylsp)

```bash
# Install via pip
pip install python-lsp-server[all]

# Verify
pylsp --help

# Alternative: pyright
npm install -g pyright
```

### Rust (rust-analyzer)

```bash
# Install via rustup
rustup component add rust-analyzer

# Verify
rust-analyzer --version
```

### Go (gopls)

```bash
# Install via go
go install golang.org/x/tools/gopls@latest

# Verify
gopls version
```

### Java (jdtls)

```bash
# Download Eclipse JDT LS
# See: https://github.com/eclipse/eclipse.jdt.ls

# Or install via package manager
# macOS
brew install jdtls

# Linux (manual)
wget https://download.eclipse.org/jdtls/snapshots/jdt-language-server-latest.tar.gz
tar -xzf jdt-language-server-latest.tar.gz -C ~/jdtls/
```

### C++ (clangd)

```bash
# macOS
brew install llvm

# Linux (Ubuntu/Debian)
sudo apt install clangd

# Verify
clangd --version
```

## Troubleshooting

### LSP Server Not Found

**Issue**: "Language server 'tsserver' not found"

**Solution**:
```bash
# Check if server is installed
which typescript-language-server

# If not found, install
npm install -g typescript-language-server typescript

# Verify installation
amplihack plugin lsp-test --lang typescript
```

### Auto-Detection Not Working

**Issue**: Languages not detected automatically

**Solution**:
```bash
# Force re-detection
amplihack plugin lsp-detect --force --verbose

# Check detection log
amplihack plugin logs --filter lsp-detect

# Manually configure
amplihack plugin lsp-configure --lang typescript
```

### LSP Server Crashes

**Issue**: Language server crashes on startup

**Solution**:
```bash
# Check server logs
amplihack plugin lsp-logs --lang python

# Test server directly
pylsp --stdio  # Should start without errors

# Reset LSP configuration
amplihack plugin lsp-reset --lang python
amplihack plugin lsp-configure --lang python
```

### Wrong Language Detected

**Issue**: Project detected as wrong language

**Solution**:
```bash
# View detection results
amplihack plugin lsp-detect --dry-run

# Manually set primary language
amplihack local lsp-set-primary --lang typescript

# Disable auto-detection for project
echo '{"lsp": {"auto_detect": false}}' > .amplihack/local/config.json
```

### Performance Issues

**Issue**: LSP causing Claude Code to slow down

**Solution**:
```bash
# Disable LSP for large projects
amplihack local lsp-disable

# Or limit to specific languages
amplihack local lsp-enable --only typescript,python

# Check resource usage
amplihack plugin lsp-stats
```

## Advanced Usage

### Multiple LSP Servers per Language

Some languages support multiple LSP servers:

```bash
# Python: pylsp (default)
amplihack plugin lsp-configure --lang python --server pylsp

# Python: pyright (alternative)
amplihack plugin lsp-configure --lang python --server pyright

# Python: jedi (alternative)
amplihack plugin lsp-configure --lang python --server jedi-language-server
```

**Switch between servers**:
```bash
# Current project
amplihack local lsp-set --lang python --server pyright

# Globally
amplihack config set lsp.python.default_server pyright
```

### LSP Workspace Configuration

Configure LSP workspace settings:

```bash
# Set Python virtual environment
amplihack local lsp-workspace python.venvPath .venv

# Set TypeScript project references
amplihack local lsp-workspace typescript.referencesCodeLens true

# View all workspace settings
amplihack local lsp-workspace --show
```

### LSP Features Toggle

Enable/disable specific LSP features:

```bash
# Disable hover tooltips
amplihack config set lsp.features.hover false

# Disable code completion
amplihack config set lsp.features.completion false

# Enable only diagnostics and formatting
amplihack config set lsp.features.diagnostics true
amplihack config set lsp.features.formatting true
amplihack config set lsp.features.completion false
amplihack config set lsp.features.hover false
```

### Custom LSP Server

Add completely custom LSP server:

```bash
# Create custom server config
cat > ~/.amplihack/config/lsp/custom/myserver.json << 'EOF'
{
  "language": "mylang",
  "server": "my-language-server",
  "command": "/path/to/my-server",
  "args": ["--stdio", "--log-level", "debug"],
  "initialization_options": {
    "customOption": "value"
  },
  "file_extensions": [".mylang"],
  "root_markers": ["myproject.config"]
}
EOF

# Register custom language
amplihack plugin lsp-register custom/myserver
```

## Environment Variables

Configure LSP via environment variables:

```bash
# Override LSP server path
export AMPLIHACK_LSP_PYTHON_SERVER=/custom/path/pylsp

# Disable auto-detection
export AMPLIHACK_LSP_AUTO_DETECT=false

# Set log level
export AMPLIHACK_LSP_LOG_LEVEL=debug

# Custom config directory
export AMPLIHACK_LSP_CONFIG_DIR=/custom/lsp/configs
```

## LSP Integration with Agents

Agents use LSP information to provide context-aware assistance:

### Architect Agent

```bash
# Architect uses LSP to understand project structure
/ultrathink "Add authentication"

# Behind the scenes:
# 1. LSP provides TypeScript type information
# 2. Architect designs type-safe auth system
# 3. Builder implements with correct types
```

### Builder Agent

```bash
# Builder uses LSP for code generation
# - Correct imports based on LSP
# - Type-safe implementations
# - Idiomatic code for detected language
```

### Analyzer Agent

```bash
# Analyzer uses LSP for deep understanding
/analyze src/

# Uses LSP to:
# - Find all references
# - Detect unused imports
# - Identify type errors
```

## Best Practices

### 1. Let Auto-Detection Work

Trust auto-detection for standard projects:
```bash
# Good: Let plugin detect
cd my-project
claude

# Avoid: Manual config unless needed
# amplihack plugin lsp-configure ...
```

### 2. Use Project Configs for Exceptions

Override only when necessary:
```bash
# Project needs specific settings
echo '{"lsp": {"python": {"server": "pyright"}}}' > .amplihack/local/lsp.json
```

### 3. Install LSP Servers Globally

Install servers once for all projects:
```bash
npm install -g typescript-language-server
pip install python-lsp-server[all]
```

### 4. Check Status When Troubleshooting

Always start with status check:
```bash
amplihack plugin lsp-status
amplihack plugin lsp-logs
```

### 5. Update LSP Servers Regularly

Keep servers updated:
```bash
# Update TypeScript
npm update -g typescript-language-server typescript

# Update Python
pip install --upgrade python-lsp-server[all]
```

## Reference

### Commands Summary

| Command | Purpose |
|---------|---------|
| `amplihack plugin lsp-detect` | Detect project languages |
| `amplihack plugin lsp-status` | Show LSP configuration |
| `amplihack plugin lsp-configure` | Configure language server |
| `amplihack plugin lsp-add` | Add new language support |
| `amplihack plugin lsp-test` | Test LSP server |
| `amplihack plugin lsp-logs` | View LSP logs |
| `amplihack plugin lsp-reset` | Reset LSP configuration |
| `amplihack plugin lsp-stats` | Show LSP statistics |

### Configuration Schema

Complete LSP configuration schema:

```typescript
interface LSPConfig {
  language: string;              // Language name
  server: string;                // LSP server name
  command: string;               // Server executable
  args?: string[];               // Command arguments
  initialization_options?: any;  // Server-specific options
  file_extensions: string[];     // Recognized extensions
  root_markers: string[];        // Project root indicators
  workspace?: {                  // Workspace settings
    [key: string]: any;
  };
  features?: {                   // Feature toggles
    hover?: boolean;
    completion?: boolean;
    diagnostics?: boolean;
    formatting?: boolean;
  };
}
```

## Next Steps

- [Configure user preferences](./PLUGIN_CONFIGURATION.md)
- [Develop custom LSP integrations](./PLUGIN_DEVELOPMENT.md#lsp-integration)
- [Report LSP issues](https://github.com/rysweet/amplihack/issues)

---

**LSP auto-detection enables context-aware AI assistance in amplihack!**
