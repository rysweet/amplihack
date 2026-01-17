---
name: lsp-setup
description: Auto-discovers and configures Language Server Protocol (LSP) servers for your project's languages
type: skill
activationStrategy: lazy-aggressive
activationKeywords:
  - LSP
  - Language Server Protocol
  - LSP setup
  - LSP configuration
  - configure LSP
  - enable LSP
  - lsp-setup
  - language server
  - code intelligence
  - code completion
  - pyright
  - rust-analyzer
  - gopls
activationContextWindow: 3
persistenceThreshold: 20
---

# LSP Auto-Configuration Skill

**Auto-discovers and configures Language Server Protocol (LSP) servers for your project's languages.**

## Overview

The LSP Setup skill automatically detects programming languages in your codebase and generates the LSP configuration needed for Claude Code to provide intelligent code completion, diagnostics, and navigation. It supports 16 popular programming languages out of the box.

## When to Use This Skill

Use `/lsp-setup` when you:

- Start working on a new project in Claude Code
- Add a new programming language to an existing project
- Experience missing or incorrect code intelligence features
- Want to verify your LSP configuration is correct
- Need to troubleshoot LSP server connection issues

## How It Works

### LSP Architecture - Three Layers

Claude Code's LSP system uses a three-layer architecture that must all be configured for LSP features to work:

**Layer 1: System LSP Binaries** (User-installed)
- LSP server executables installed on your system via npm, brew, rustup, etc.
- Example: `npm install -g pyright` installs the Pyright LSP server binary
- These are the actual language analysis engines

**Layer 2: Claude Code LSP Plugins** (Installed via cclsp)
- Claude Code plugins that connect to Layer 1 binaries
- Installed using: `npx cclsp install <server-name>`
- The `cclsp` tool uses the `claude-code-lsps` plugin marketplace
- These act as bridges between Claude Code and LSP servers

**Layer 3: Project Configuration** (.env file)
- Project-specific settings: virtual environments, project roots, etc.
- Must include `ENABLE_LSP_TOOL=1` to activate LSP features
- Stored in `.env` at project root

**Important**: `cclsp` and `claude-code-lsps` work together. `cclsp` is the installation tool, `claude-code-lsps` is the plugin marketplace it uses. They are complementary, not alternatives.

### The Skill's 4-Phase Process

The `/lsp-setup` skill automates the workflow from `npx cclsp@latest setup`:

#### Phase 1: Language Detection

Scans your project directory to identify programming languages based on file extensions and framework markers. Detects 16 languages including Python, TypeScript, JavaScript, Rust, Go, Java, and more.

#### Phase 2: LSP Configuration

Generates the appropriate LSP server configuration for each detected language. Checks if:
1. System LSP binaries are installed (Layer 1)
2. Claude Code plugins are installed (Layer 2)

Provides installation guidance if either is missing. **NEVER auto-installs** - user has full control.

#### Phase 3: Project Configuration

Creates or updates `.env` file with project-specific LSP settings (Layer 3):
- Workspace-specific options (Python virtual environments, Node.js project roots, etc.)
- **ENABLE_LSP_TOOL=1** (required for LSP features to activate)

#### Phase 4: Verification

Tests each LSP server connection and reports status. Provides actionable guidance for any configuration issues.

## Usage

### Basic Usage

```bash
/lsp-setup
```

Detects all languages in your project and configures LSP servers automatically.

### Check Status Only

```bash
/lsp-setup --status-only
```

Reports current LSP configuration and server availability without making changes.

### Force Reconfiguration

```bash
/lsp-setup --force
```

Regenerates LSP configuration even if valid configuration already exists.

### Specific Languages

```bash
/lsp-setup --languages python,typescript
```

Configures LSP servers only for specified languages.

### Manual Plugin Management

If you need to manage Claude Code LSP plugins directly, use the `cclsp` command:

```bash
# Install a plugin (Layer 2)
npx cclsp install pyright

# List installed plugins
npx cclsp list

# Remove a plugin
npx cclsp remove pyright

# Full setup workflow (what /lsp-setup automates)
npx cclsp@latest setup
```

The `/lsp-setup` skill automates the `npx cclsp@latest setup` workflow, adding intelligent language detection and project-specific configuration.

## Supported Languages

| Language   | LSP Server       | System Binary Installation (Layer 1) | Claude Code Plugin (Layer 2) |
|------------|------------------|--------------------------------------|------------------------------|
| Python     | pyright          | `npm install -g pyright`             | `npx cclsp install pyright`  |
| TypeScript | vtsls            | `npm install -g @vtsls/language-server` | `npx cclsp install vtsls` |
| JavaScript | vtsls            | `npm install -g @vtsls/language-server` | `npx cclsp install vtsls` |
| Rust       | rust-analyzer    | `rustup component add rust-analyzer` | `npx cclsp install rust-analyzer` |
| Go         | gopls            | `go install golang.org/x/tools/gopls@latest` | `npx cclsp install gopls` |
| Java       | jdtls            | Download from eclipse.org/jdtls      | `npx cclsp install jdtls`    |
| C/C++      | clangd           | `brew install llvm` (macOS) / `apt install clangd` (Linux) | `npx cclsp install clangd` |
| C#         | omnisharp        | Download from omnisharp.net          | `npx cclsp install omnisharp` |
| Ruby       | ruby-lsp         | `gem install ruby-lsp`               | `npx cclsp install ruby-lsp` |
| PHP        | phpactor         | `composer global require phpactor/phpactor` | `npx cclsp install phpactor` |
| Bash       | bash-language-server | `npm install -g bash-language-server` | `npx cclsp install bash-language-server` |
| YAML       | yaml-language-server | `npm install -g yaml-language-server` | `npx cclsp install yaml-language-server` |
| JSON       | vscode-json-languageserver | `npm install -g vscode-json-languageserver` | `npx cclsp install vscode-json-languageserver` |
| HTML       | vscode-html-languageserver | `npm install -g vscode-html-languageserver` | `npx cclsp install vscode-html-languageserver` |
| CSS        | vscode-css-languageserver | `npm install -g vscode-css-languageserver` | `npx cclsp install vscode-css-languageserver` |
| Markdown   | marksman         | `brew install marksman` (macOS) / Download from GitHub | `npx cclsp install marksman` |

**Note**: Both Layer 1 (system binary) and Layer 2 (Claude Code plugin) must be installed for LSP features to work.

## Example: Python Project Setup

```bash
$ cd my-python-project
$ /lsp-setup

[LSP Setup] Detecting languages...
✓ Found: Python (23 files)
✓ Found: YAML (2 files)
✓ Found: Markdown (1 file)

[LSP Setup] Configuring LSP servers...
✓ pyright: Installed at /usr/local/bin/pyright
✓ yaml-language-server: Installed at /usr/local/bin/yaml-language-server
✓ marksman: Installed at /usr/local/bin/marksman

[LSP Setup] Configuring project...
✓ Created .env with LSP configuration
✓ Detected Python virtual environment: .venv
✓ Configured pyright to use .venv/bin/python

[LSP Setup] Verifying connections...
✓ pyright: Connected (Python 3.11.5)
✓ yaml-language-server: Connected
✓ marksman: Connected

Configuration complete! LSP servers ready.
```

## Example: Polyglot Project Setup

```bash
$ cd my-fullstack-app
$ /lsp-setup

[LSP Setup] Detecting languages...
✓ Found: TypeScript (45 files)
✓ Found: Python (12 files)
✓ Found: Rust (8 files)
✓ Found: JSON (6 files)

[LSP Setup] Configuring LSP servers...
✓ vtsls: Installed
✓ pyright: Installed
✗ rust-analyzer: Not found

[LSP Setup] Installation guidance:
To install rust-analyzer:
  $ rustup component add rust-analyzer

Would you like to continue with available servers? [Y/n] y

[LSP Setup] Configuring project...
✓ Created .env with LSP configuration
✓ Detected Node.js project root: ./frontend
✓ Detected Python project root: ./backend
✓ Detected Rust workspace: ./services

[LSP Setup] Verifying connections...
✓ vtsls: Connected (TypeScript 5.3.3)
✓ pyright: Connected (Python 3.11.5)
⚠ rust-analyzer: Skipped (not installed)

Configuration complete! 2/3 LSP servers ready.
Run `rustup component add rust-analyzer` to enable Rust support.
```

## Troubleshooting

### Issue: LSP server not found

**Symptom**: "rust-analyzer: Not found" during configuration

**Solution**: Install the LSP server using the provided installation command

```bash
$ rustup component add rust-analyzer
$ /lsp-setup --force  # Reconfigure after installation
```

### Issue: LSP server crashes on startup

**Symptom**: "pyright: Connection failed" during verification

**Solution**: Check LSP server logs and verify installation

```bash
# Check if server is properly installed
$ which pyright
/usr/local/bin/pyright

# Test server manually
$ pyright --version
pyright 1.1.332

# Check Claude Code LSP logs
$ cat ~/.claude-code/lsp-logs/pyright.log
```

### Issue: Wrong Python interpreter used

**Symptom**: Import errors despite packages being installed in virtual environment

**Solution**: Verify `.env` configuration points to correct Python interpreter

```bash
# Check current configuration
$ cat .env | grep PYTHON

# Should show:
LSP_PYTHON_INTERPRETER=/path/to/.venv/bin/python

# If incorrect, update manually or run:
$ /lsp-setup --force
```

### Issue: TypeScript project not detected

**Symptom**: No TypeScript LSP configuration despite `.ts` files present

**Solution**: Ensure `tsconfig.json` exists in project root

```bash
# Create minimal tsconfig.json
$ cat > tsconfig.json << EOF
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "strict": true
  }
}
EOF

$ /lsp-setup --force
```

### Issue: Multiple Python versions causing conflicts

**Symptom**: "Module not found" errors when LSP server uses wrong Python version

**Solution**: Explicitly set Python interpreter in `.env`

```bash
# Edit .env manually
LSP_PYTHON_INTERPRETER=/usr/bin/python3.11

# Or activate the correct virtual environment before running
$ source .venv/bin/activate
$ /lsp-setup --force
```

## Configuration Files

### `.env` (Project Root)

The skill creates or updates `.env` with LSP-specific configuration:

```bash
# LSP Configuration - Auto-generated by /lsp-setup
ENABLE_LSP_TOOL=1  # REQUIRED: Activates LSP features in Claude Code

# Project-specific settings (Layer 3)
LSP_PYTHON_INTERPRETER=/path/to/.venv/bin/python
LSP_NODE_PROJECT_ROOT=/path/to/frontend
LSP_RUST_WORKSPACE=/path/to/services
LSP_GO_MODULE=/path/to/go.mod

# Language Server Paths (auto-detected)
LSP_PYRIGHT_PATH=/usr/local/bin/pyright
LSP_VTSLS_PATH=/usr/local/bin/vtsls
LSP_RUST_ANALYZER_PATH=/usr/local/bin/rust-analyzer
```

**Critical**: `ENABLE_LSP_TOOL=1` must be present for LSP features to work. Without it, LSP servers won't be activated.

### Claude Code LSP Configuration

The skill automatically updates Claude Code's LSP configuration. No manual editing required.

## Integration with Claude Code

Once configured, Claude Code automatically:

- Provides code completion based on project context
- Shows real-time diagnostics (errors, warnings)
- Enables "Go to Definition" navigation
- Offers inline documentation on hover
- Suggests intelligent refactorings

## Best Practices

1. **Run at project start**: Configure LSP servers when you first open a project
2. **Update after adding languages**: Rerun `/lsp-setup` when adding new language files
3. **Commit `.env`**: Include LSP configuration in version control for team consistency
4. **Verify after installation**: Use `--status-only` to check server availability
5. **Keep servers updated**: Regularly update LSP servers to latest versions

## Technical Details

**Skill Type**: Interactive command-driven workflow

**Dependencies**: None (pure skill, no external packages)

**Execution Time**: 2-10 seconds depending on project size

**Persistence**: Configuration stored in `.env` and Claude Code settings

**Supported Platforms**: macOS, Linux, WSL

## Related Skills

- `environment-setup` - General development environment configuration
- `dependency-manager` - Package and dependency management
- `project-init` - New project initialization

## Maintenance

The LSP Setup skill requires no manual maintenance. It automatically adapts to your project structure and detects language changes on each run.

To update LSP server definitions or add new languages, see the developer documentation in `README.md`.

---

## Execution Instructions (For Claude Code)

When this skill is activated via `/lsp-setup` or activation keywords, execute the following workflow:

### Phase 1: Language Detection

```python
from pathlib import Path
from lsp_setup import LanguageDetector

# Detect languages in current project
detector = LanguageDetector()
project_root = Path.cwd()
languages = detector.detect_languages(project_root)

# Report findings
print(f"Detected {len(languages)} language(s):")
for lang in languages:
    print(f"  - {lang.language}: {lang.file_count} files")
```

### Phase 2: Check Current Status

```python
from lsp_setup import StatusTracker

# Get current LSP setup status
language_names = [lang.language for lang in languages]
tracker = StatusTracker(project_root, language_names)
status = tracker.get_full_status()

# Show status
print(tracker.generate_user_guidance())
```

### Phase 3: Configure LSP (If Needed)

```python
from lsp_setup import LSPConfigurator

# Configure .env file
configurator = LSPConfigurator(project_root)

# Enable LSP
if not configurator.is_lsp_enabled():
    configurator.enable_lsp()
    print("✓ Enabled LSP in .env")
```

### Phase 4: Install Plugins (If Needed)

```python
from lsp_setup import PluginManager

# Install Claude Code plugins for detected languages
manager = PluginManager()

# Check prerequisites
if not manager.check_npx_available():
    print("⚠ npx not found. Install Node.js first:")
    print("  macOS: brew install node")
    print("  Linux: sudo apt install nodejs")
    exit(1)

# Install plugins for languages with missing Layer 2
for lang_name in language_names:
    layer_2_status = status["layer_2"][lang_name]
    if not layer_2_status["installed"]:
        print(f"Installing {lang_name} plugin...")
        success = manager.install_plugin(lang_name)
        if success:
            print(f"✓ {lang_name} plugin installed")
        else:
            print(f"✗ Failed to install {lang_name} plugin")
            print(f"  {layer_2_status.get('install_guide', 'See docs')}")
```

### Phase 5: Final Status Report

```python
# Recheck status after installation
final_status = tracker.get_full_status()

if final_status["overall_ready"]:
    print("\n✅ LSP setup complete! All layers configured.")
else:
    print("\n⚠ LSP partially configured. Next steps:")
    print(tracker.generate_user_guidance())
```

### Command-Line Arguments (Optional)

Support these arguments if provided by user:

- `--status-only`: Skip installation, just report current status
- `--force`: Reinstall all plugins even if already installed
- `--languages <lang1,lang2>`: Configure only specific languages
- `--dry-run`: Show what would be done without making changes
