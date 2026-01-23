# LSP Auto-Configuration Feature

## Overview

The LSP Auto-Configuration feature provides zero-configuration Language Server Protocol (LSP) setup when you launch Claude Code via amplihack. It automatically detects programming languages in your project and configures the required LSP servers, plugins, and environment settings—no manual intervention needed.

**Key Benefits:**

- **Zero Configuration**: LSP works automatically when you run `amplihack claude`
- **Multi-Language Support**: Detects and configures 16 programming languages
- **Complete Setup**: Handles system binaries, Claude Code plugins, and project config
- **Intelligent Detection**: Scans your project to identify languages and frameworks
- **Non-Disruptive**: Silent operation with minimal console output

## How It Works

### Automatic Activation

**When you run `amplihack claude`, the LSP auto-configuration runs automatically:**

```bash
$ amplihack claude

# You'll see:
📡 LSP: Detected 3 language(s): python, javascript, typescript
📡 LSP: Enabled ENABLE_LSP_TOOL=1 in .env
📡 LSP: Added plugin marketplace
📡 LSP: Installed pyright plugin ✓
📡 LSP: Installed vtsls plugin ✓

# Then Claude Code starts with LSP fully configured
```

### Architecture

The feature consists of four main components:

1. **Launcher Integration** (`src/amplihack/launcher/core.py`)
   - Calls `_configure_lsp_auto()` during Claude Code launch
   - Executes before Claude Code starts
   - Silently skips if LSP modules unavailable

2. **Language Detector** (`~/.amplihack/.claude/skills/lsp-setup/language_detector.py`)
   - Scans project directory for file extensions
   - Identifies framework markers (package.json, Cargo.toml, etc.)
   - Returns detected languages sorted by file count

3. **LSP Configurator** (`~/.amplihack/.claude/skills/lsp-setup/lsp_configurator.py`)
   - Sets `ENABLE_LSP_TOOL=1` environment variable
   - Creates/updates `.env` file with LSP configuration
   - Detects language-specific settings (Python venv, Node project root)

4. **Plugin Manager** (`~/.amplihack/.claude/skills/lsp-setup/plugin_manager.py`)
   - Installs system LSP binaries via npm/brew/rustup
   - Adds Claude Code plugin marketplace
   - Installs Claude Code LSP plugins via `claude plugin install`

### Configuration Flow

```
amplihack claude command
    ↓
Launcher starts (src/amplihack/launcher/core.py)
    ↓
_configure_lsp_auto() executes
    ↓
Step 1: Detect Languages
    └─ Scan project for .py, .ts, .rs, .go files
    └─ Check for package.json, Cargo.toml markers
    └─ Return: ["python", "typescript", "rust"]
    ↓
Step 2: Set Environment Variable
    └─ os.environ["ENABLE_LSP_TOOL"] = "1"
    ↓
Step 3: Configure .env File
    └─ Create/update .env with ENABLE_LSP_TOOL=1
    └─ Add language-specific settings (Python venv path, etc.)
    ↓
Step 4: Install System LSP Binaries
    └─ npm install -g pyright
    └─ npm install -g typescript-language-server
    └─ rustup component add rust-analyzer
    ↓
Step 5: Add Plugin Marketplace
    └─ claude plugin marketplace add boostvolt/claude-code-lsps
    ↓
Step 6: Install Claude Code Plugins
    └─ claude plugin install pyright@claude-code-lsps
    └─ claude plugin install vtsls@claude-code-lsps
    └─ claude plugin install rust-analyzer@claude-code-lsps
    ↓
LSP Configuration Complete
    ↓
Claude Code launches with LSP enabled
```

## What LSP Provides

When LSP is configured, Claude Code gains powerful code intelligence:

### Real-Time Code Understanding

**Type Information**: Claude sees exact types, not guesses
```python
# Claude knows: user is type User | None from models.User
user = get_current_user()
```

**Diagnostics**: Claude receives LSP warnings/errors
```python
# Pyright reports: "name" is not accessed
from typing import List, Set  # Claude sees this warning
```

**Navigation**: Claude can jump to definitions
```python
# Claude uses LSP goToDefinition to find authenticate() in auth.py
result = authenticate(credentials)
```

### Benefits to Users

1. **More Accurate Responses**: Claude's suggestions match your actual types and APIs
2. **Faster Debugging**: Claude sees the same errors your IDE would show
3. **Better Refactoring**: Claude can safely rename variables using LSP references
4. **Improved Navigation**: Claude finds definitions, usages, implementations precisely

## Supported Languages

| Language   | LSP Server       | Auto-Installed Binary              |
|------------|------------------|-------------------------------------|
| Python     | pyright          | `npm install -g pyright`            |
| TypeScript | vtsls            | `npm install -g @vtsls/language-server` |
| JavaScript | vtsls            | `npm install -g @vtsls/language-server` |
| Rust       | rust-analyzer    | `rustup component add rust-analyzer` |
| Go         | gopls            | `go install golang.org/x/tools/gopls@latest` |
| Java       | jdtls            | Eclipse JDT LS (manual download)    |
| C/C++      | clangd           | `brew install llvm` / `apt install clangd` |
| C#         | omnisharp        | Manual download from omnisharp.net  |
| Ruby       | ruby-lsp         | `gem install ruby-lsp`              |
| PHP        | phpactor         | `composer global require phpactor/phpactor` |
| Bash       | bash-language-server | `npm install -g bash-language-server` |
| YAML       | yaml-language-server | `npm install -g yaml-language-server` |
| JSON       | vscode-json-languageserver | `npm install -g vscode-json-languageserver` |
| HTML       | vscode-html-languageserver | `npm install -g vscode-html-languageserver` |
| CSS        | vscode-css-languageserver  | `npm install -g vscode-css-languageserver` |
| Markdown   | marksman         | `brew install marksman` / GitHub download |

## Manual Control

**Most users never need manual control** - the automatic setup handles everything. However, if you need to troubleshoot or reconfigure:

### Check LSP Status

```bash
# In Claude session, mention "LSP" to activate the skill
"Check LSP status"

# Claude will use /lsp-setup skill to show:
✓ Python (pyright): Connected
✓ TypeScript (vtsls): Connected
✗ Rust (rust-analyzer): Not found
```

### Force Reconfiguration

If LSP isn't working after automatic setup:

```bash
# In Claude session
"Force reconfigure LSP"

# Claude will use /lsp-setup --force to rebuild configuration
```

### Manual Skill Documentation

For detailed troubleshooting and manual control, see:
- [LSP Setup Skill Documentation](../../.claude/skills/lsp-setup/SKILL.md)
- [LSP Usage Examples](../../.claude/skills/lsp-setup/USAGE_EXAMPLES.md)

## Verification

### How to Verify LSP is Working

After `amplihack claude` launches, verify LSP is active:

**Method 1: Ask Claude to analyze a file**
```
You: "What issues do you see in src/main.py?"

If LSP is working:
  → Claude reports specific diagnostics: "Line 15: 'name' is not accessed"

If LSP is NOT working:
  → Claude only sees file content, no specific type errors
```

**Method 2: Request type information**
```
You: "What's the type of the user variable in auth.py line 42?"

If LSP is working:
  → "Type: User | None (from models.User)"

If LSP is NOT working:
  → "It appears to be a User object based on the code"
```

**Method 3: Check console output**
```bash
$ amplihack claude

# Look for:
📡 LSP: Detected 3 language(s): python, javascript, typescript
📡 LSP: Enabled ENABLE_LSP_TOOL=1 in .env
📡 LSP: Installed pyright plugin ✓
📡 LSP: Installed vtsls plugin ✓

# If you see this, LSP is configured
```

## Troubleshooting

### LSP Not Detecting Languages

**Symptom**: No "📡 LSP: Detected..." message when launching

**Cause**: No supported languages found in project

**Solution**: Ensure your project contains files with recognized extensions (.py, .ts, .js, .rs, etc.)

### LSP Plugins Fail to Install

**Symptom**: "📡 LSP: Failed to install pyright" messages

**Cause**: Missing system dependencies or network issues

**Solution**:
1. Manually install system LSP binary: `npm install -g pyright`
2. Manually install plugin: `npx cclsp install pyright`
3. Restart amplihack: `amplihack claude`

### LSP Not Providing Code Intelligence

**Symptom**: Claude doesn't show type information or diagnostics

**Causes**:
1. `ENABLE_LSP_TOOL=1` not set in environment
2. LSP server binary not in PATH
3. Claude Code plugin not installed

**Solution**:
1. Check `.env` file contains `ENABLE_LSP_TOOL=1`
2. Verify binary installed: `which pyright-langserver`
3. Check plugin: `claude plugin list`
4. Force reconfigure: Mention "force reconfigure LSP" to Claude

### Performance Impact

**Symptom**: Claude Code startup slower after LSP configuration

**Cause**: LSP auto-configuration runs synchronously during launch

**Impact**: Adds 2-5 seconds to startup time (one-time per project)

**Solution**: None needed - subsequent launches reuse existing configuration

## Configuration Files

### .env (Project Root)

Created/updated automatically with LSP settings:

```bash
# Required for LSP features to activate
ENABLE_LSP_TOOL=1

# Language-specific settings (auto-detected)
LSP_PYTHON_INTERPRETER=/path/to/.venv/bin/python
LSP_PYRIGHT_PATH=/usr/local/bin/pyright
LSP_VTSLS_PATH=/usr/local/bin/vtsls
```

### Claude Code settings.json

Updated automatically with plugin configuration:

```json
{
  "enabledPlugins": {
    "pyright@claude-code-lsps": true,
    "vtsls@claude-code-lsps": true
  }
}
```

## Related Documentation

- [LSP Setup Skill](../../.claude/skills/lsp-setup/SKILL.md) - Manual control and troubleshooting
- [LSP Usage Examples](../../.claude/skills/lsp-setup/USAGE_EXAMPLES.md) - Practical examples
- [Launcher Documentation](../reference/launcher-api.md) - Amplihack launcher details
- [Plugin System](../concepts/claude-code-plugins.md) - How Claude Code plugins work

## Implementation Details

**Source Code:**
- Launcher Integration: `src/amplihack/launcher/core.py::_configure_lsp_auto()`
- Language Detection: `~/.amplihack/.claude/skills/lsp-setup/language_detector.py`
- LSP Configuration: `~/.amplihack/.claude/skills/lsp-setup/lsp_configurator.py`
- Plugin Management: `~/.amplihack/.claude/skills/lsp-setup/plugin_manager.py`

**Tests:**
- Unit Tests: `~/.amplihack/.claude/skills/lsp-setup/tests/test_*.py`
- Integration Tests: `~/.amplihack/.claude/skills/lsp-setup/tests/test_integration.py`
- E2E Tests: `~/.amplihack/.claude/skills/lsp-setup/tests/test_e2e.py`

---

**Need help?** Check the [Troubleshooting Guide](../troubleshooting/README.md) or mention "LSP" in your Claude session to activate the manual control skill.
