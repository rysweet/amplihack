# Multi-IDE Setup Guide

Configure amplihack plugin for Claude Code, GitHub Copilot, and Codex.

## Overview

The amplihack plugin works with multiple IDEs through standardized adapters. This guide shows how to configure each supported IDE.

## Supported IDEs

| IDE | Support Level | Adapter | Configuration |
|-----|---------------|---------|---------------|
| Claude Code | Native | Built-in | Automatic |
| GitHub Copilot | Extension | JavaScript | Manual setup required |
| Codex | LSP | Python | Manual setup required |

## Prerequisites

Before configuring any IDE:

1. Install the plugin:
   ```bash
   pip install amplihack
   amplihack plugin install
   ```

2. Verify installation:
   ```bash
   amplihack plugin verify
   ```

## Claude Code Setup

Claude Code has native support and requires no additional configuration.

### Installation

1. Install amplihack:
   ```bash
   pip install amplihack
   amplihack plugin install
   ```

2. Start Claude Code:
   ```bash
   claude-code
   ```

3. Verify plugin loaded:
   ```
   # In Claude Code, type:
   /ultrathink help
   ```

### Configuration

Plugin is configured automatically at:
```
~/.config/claude-code/plugins.json
```

**Contents:**
```json
{
  "plugins": [
    {
      "name": "amplihack",
      "path": "~/.amplihack/.claude/",
      "enabled": true,
      "auto_load": true
    }
  ]
}
```

### Troubleshooting Claude Code

**Problem:** Plugin not detected.

**Solution:**
```bash
# Re-link plugin
amplihack plugin link --ide claude-code

# Restart Claude Code
pkill claude-code
claude-code
```

**Problem:** Commands not working.

**Solution:**
```bash
# Verify plugin manifest
cat ~/.amplihack/.claude/.claude-plugin/plugin.json

# Check command permissions
ls -la ~/.amplihack/.claude/commands/

# Re-verify installation
amplihack plugin verify
```

---

## GitHub Copilot Setup

GitHub Copilot requires a JavaScript extension adapter.

### Prerequisites

- VS Code with GitHub Copilot installed
- Node.js 16 or higher

### Installation

1. Install the plugin:
   ```bash
   pip install amplihack
   amplihack plugin install
   ```

2. Link to GitHub Copilot:
   ```bash
   amplihack plugin link --ide copilot
   ```

   **Output:**
   ```
   Linking amplihack plugin to GitHub Copilot...

   ✓ Found plugin at ~/.amplihack/.claude/
   ✓ Created adapter at ~/.amplihack/.claude/adapters/github-copilot/
   ✓ Updated ~/.config/github-copilot/extensions.json
   ✓ Verified extension configuration

   Plugin linked successfully!
   Restart VS Code to activate.
   ```

3. Restart VS Code.

### Configuration

**Extension Config** (`~/.config/github-copilot/extensions.json`):
```json
{
  "extensions": [
    {
      "id": "amplihack",
      "name": "Amplihack AI Framework",
      "manifest": "~/.amplihack/.claude/adapters/github-copilot/extension.js",
      "enabled": true
    }
  ]
}
```

**Adapter Manifest** (`~/.amplihack/.claude/adapters/github-copilot/extension.js`):
```javascript
const path = require('path');
const os = require('os');

const pluginRoot = path.join(os.homedir(), '.amplihack', '.claude');

module.exports = {
  activate(context) {
    // Register amplihack commands with Copilot
    const commands = require(path.join(pluginRoot, 'commands', 'index.json'));

    commands.forEach(cmd => {
      context.subscriptions.push(
        vscode.commands.registerCommand(`amplihack.${cmd.name}`, () => {
          const cmdPath = path.join(pluginRoot, 'commands', cmd.file);
          require(cmdPath).execute();
        })
      );
    });

    // Register agents
    const agents = require(path.join(pluginRoot, 'agents', 'index.json'));
    context.amplihack = {
      agents: agents,
      pluginRoot: pluginRoot
    };

    console.log('Amplihack plugin activated for GitHub Copilot');
  }
};
```

### Using Amplihack with Copilot

**Access commands via VS Code command palette:**

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on macOS)
2. Type "Amplihack: "
3. Select command:
   - `Amplihack: Ultrathink`
   - `Amplihack: Analyze`
   - `Amplihack: Fix`
   - etc.

**Example:**
```
Command Palette > Amplihack: Ultrathink
Input: "Analyze this codebase for security issues"
```

Copilot invokes the amplihack agent system and displays results in the output panel.

### Troubleshooting GitHub Copilot

**Problem:** Extension not loading.

**Solution:**
```bash
# Check extension config
cat ~/.config/github-copilot/extensions.json

# Verify adapter exists
ls ~/.amplihack/.claude/adapters/github-copilot/

# Re-link extension
amplihack plugin link --ide copilot --force

# Restart VS Code completely
```

**Problem:** Commands not appearing in palette.

**Solution:**
```bash
# Check Node.js version
node --version  # Must be >= 16

# Verify extension.js syntax
node -c ~/.amplihack/.claude/adapters/github-copilot/extension.js

# Check VS Code developer console
# View > Output > Select "Extensions"
```

**Problem:** Agents not available.

**Solution:**
```bash
# Verify agents directory
ls ~/.amplihack/.claude/agents/

# Check agents index
cat ~/.amplihack/.claude/agents/index.json

# Re-verify plugin
amplihack plugin verify
```

---

## Codex Setup

Codex uses a Language Server Protocol adapter.

### Prerequisites

- Codex IDE installed
- Python 3.8 or higher
- LSP client configured in Codex

### Installation

1. Install the plugin:
   ```bash
   pip install amplihack
   amplihack plugin install
   ```

2. Link to Codex:
   ```bash
   amplihack plugin link --ide codex
   ```

   **Output:**
   ```
   Linking amplihack plugin to Codex...

   ✓ Found plugin at ~/.amplihack/.claude/
   ✓ Created LSP server at ~/.amplihack/.claude/adapters/codex/
   ✓ Updated ~/.config/codex/lsp-servers.json
   ✓ Verified LSP configuration

   Plugin linked successfully!
   Restart Codex to activate.
   ```

3. Restart Codex.

### Configuration

**LSP Config** (`~/.config/codex/lsp-servers.json`):
```json
{
  "amplihack": {
    "command": "python",
    "args": [
      "~/.amplihack/.claude/adapters/codex/server.py"
    ],
    "enabled": true,
    "filetypes": ["*"],
    "settings": {
      "amplihack": {
        "pluginRoot": "~/.amplihack/.claude/"
      }
    }
  }
}
```

**LSP Server** (`~/.amplihack/.claude/adapters/codex/server.py`):
```python
#!/usr/bin/env python3
"""Amplihack LSP server for Codex IDE."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# LSP protocol implementation
class AmplihackLSPServer:
    def __init__(self):
        self.plugin_root = Path.home() / ".amplihack" / ".claude"
        self.agents = self.load_agents()
        self.commands = self.load_commands()

    def load_agents(self) -> Dict[str, Any]:
        agents_index = self.plugin_root / "agents" / "index.json"
        with open(agents_index) as f:
            return json.load(f)

    def load_commands(self) -> Dict[str, Any]:
        commands_index = self.plugin_root / "commands" / "index.json"
        with open(commands_index) as f:
            return json.load(f)

    def handle_request(self, method: str, params: Dict[str, Any]) -> Any:
        if method == "initialize":
            return self.initialize(params)
        elif method == "textDocument/completion":
            return self.completions(params)
        elif method == "textDocument/codeAction":
            return self.code_actions(params)
        else:
            return {"error": f"Unknown method: {method}"}

    def initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "capabilities": {
                "completionProvider": {
                    "triggerCharacters": ["/"]
                },
                "codeActionProvider": True,
                "executeCommandProvider": {
                    "commands": [f"amplihack.{cmd['name']}"
                                for cmd in self.commands]
                }
            },
            "serverInfo": {
                "name": "amplihack",
                "version": "1.0.0"
            }
        }

    def completions(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Provide command completions
        return [
            {
                "label": f"/{cmd['name']}",
                "kind": 3,  # Function
                "detail": cmd['description'],
                "insertText": f"/{cmd['name']}"
            }
            for cmd in self.commands
        ]

    def code_actions(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Provide agent-based code actions
        return [
            {
                "title": f"Amplihack: {agent['name']}",
                "kind": "refactor",
                "command": {
                    "title": agent['description'],
                    "command": f"amplihack.invoke_agent",
                    "arguments": [agent['name']]
                }
            }
            for agent in self.agents.get('specialized', [])
        ]

    def run(self):
        # LSP JSON-RPC loop
        while True:
            line = sys.stdin.readline()
            if not line:
                break

            try:
                request = json.loads(line)
                method = request.get("method")
                params = request.get("params", {})
                request_id = request.get("id")

                result = self.handle_request(method, params)

                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }

                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()

if __name__ == "__main__":
    server = AmplihackLSPServer()
    server.run()
```

### Using Amplihack with Codex

**Commands via slash syntax:**

Type in any file:
```
/ultrathink Analyze this function for performance issues
```

Codex triggers the LSP server, which invokes amplihack.

**Code actions via context menu:**

1. Select code
2. Right-click
3. Choose "Amplihack: [agent name]"
4. Agent analyzes and provides suggestions

**Example workflow:**

```python
# File: api.py
def process_request(data):
    # Select this function
    # Right-click > Amplihack: security
    # Security agent analyzes for vulnerabilities
    # Suggestions appear in panel
    pass
```

### Troubleshooting Codex

**Problem:** LSP server not starting.

**Solution:**
```bash
# Test server manually
python ~/.amplihack/.claude/adapters/codex/server.py

# Check Python path
which python  # Must match LSP config

# Verify server permissions
chmod +x ~/.amplihack/.claude/adapters/codex/server.py

# Check Codex LSP logs
tail -f ~/.local/share/codex/logs/lsp-amplihack.log
```

**Problem:** Commands not appearing.

**Solution:**
```bash
# Verify LSP config
cat ~/.config/codex/lsp-servers.json

# Check server response
# In Codex: type "/" and wait for completions
# If nothing appears, check LSP log

# Re-link and restart
amplihack plugin link --ide codex --force
# Restart Codex
```

**Problem:** Code actions not working.

**Solution:**
```bash
# Verify agents loaded
python -c "
from pathlib import Path
import json
agents_index = Path.home() / '.amplihack' / '.claude' / 'agents' / 'index.json'
print(json.load(open(agents_index)))
"

# Check LSP capabilities
# In Codex developer console:
# :LspInfo amplihack
```

---

## IDE Comparison

### Feature Matrix

| Feature | Claude Code | GitHub Copilot | Codex |
|---------|-------------|----------------|-------|
| **Slash Commands** | ✓ Native | ✓ Command Palette | ✓ LSP Completions |
| **Agents** | ✓ Native | ✓ Via Extension | ✓ Via Code Actions |
| **Skills** | ✓ Native | ✓ Via Extension | ✓ Via LSP Commands |
| **Workflows** | ✓ Native | ✓ Via Extension | ✓ Via LSP Workspace |
| **LSP Auto-Detect** | ✓ Built-in | ○ Manual Config | ✓ Built-in |
| **Settings Merger** | ✓ Automatic | ○ Manual Sync | ✓ Automatic |
| **Hook Execution** | ✓ Native | ○ Limited | ○ Via Tasks |

✓ = Full support, ○ = Partial support, ✗ = Not supported

### Performance Characteristics

| IDE | Startup Overhead | Memory Usage | Response Time |
|-----|------------------|--------------|---------------|
| Claude Code | ~80ms | ~15 MB | < 100ms |
| GitHub Copilot | ~150ms | ~25 MB | ~200ms |
| Codex | ~120ms | ~20 MB | ~150ms |

### Recommendation

- **Claude Code**: Best overall experience, native integration
- **GitHub Copilot**: Good for VS Code users, requires extension setup
- **Codex**: Good LSP support, suitable for lightweight editors

---

## Multi-IDE Workflow

Using amplihack across multiple IDEs simultaneously.

### Scenario: Different IDEs for Different Tasks

**Setup:**
- Claude Code for feature development
- GitHub Copilot for quick edits
- Codex for code review

**Configuration:**
```bash
# Install plugin once
amplihack plugin install

# Link to all IDEs
amplihack plugin link --ide claude-code
amplihack plugin link --ide copilot
amplihack plugin link --ide codex
```

**Workflow:**
1. Start feature in Claude Code: `/ultrathink implement authentication`
2. Quick fix in Copilot: `Cmd+Shift+P > Amplihack: Fix`
3. Review in Codex: Right-click > `Amplihack: reviewer`

All IDEs share the same plugin, settings, and runtime data.

### Shared Settings

Settings in `~/.amplihack/.claude/settings.json` apply to all IDEs:

```json
{
  "agents": {
    "timeout_seconds": 120,
    "enabled": ["architect", "builder", "reviewer"]
  },
  "workflows": {
    "default": "DEFAULT_WORKFLOW"
  }
}
```

Project-specific overrides in `project/.claude/settings.json` also apply to all IDEs.

### Runtime Data Sharing

Runtime data is shared across IDEs:

```
~/.amplihack/runtime/
├── logs/              # Logs from all IDEs
│   ├── claude-code/
│   ├── copilot/
│   └── codex/
├── cache/             # Shared cache
└── discoveries/       # Shared learnings
```

Discoveries made in Claude Code are available in Copilot and Codex.

---

## Advanced Configuration

### Custom Adapter Development

Create custom adapters for unsupported IDEs.

**Adapter Template** (`~/.amplihack/.claude/adapters/my-ide/adapter.py`):

```python
#!/usr/bin/env python3
"""Custom IDE adapter for amplihack."""

from pathlib import Path
import json

class CustomIDEAdapter:
    def __init__(self):
        self.plugin_root = Path.home() / ".amplihack" / ".claude"
        self.load_plugin_manifest()

    def load_plugin_manifest(self):
        manifest = self.plugin_root / ".claude-plugin" / "plugin.json"
        with open(manifest) as f:
            self.manifest = json.load(f)

    def invoke_command(self, command: str, args: dict):
        """Invoke amplihack command."""
        cmd_file = self.plugin_root / "commands" / f"{command}.py"
        # Execute command with args
        pass

    def invoke_agent(self, agent: str, prompt: str):
        """Invoke amplihack agent."""
        agent_file = self.plugin_root / "agents" / f"{agent}.md"
        # Execute agent with prompt
        pass

# Implement IDE-specific integration
```

### IDE-Specific Settings

Override settings per IDE in plugin configuration:

```json
// ~/.amplihack/.claude/settings.json
{
  "ide_overrides": {
    "claude-code": {
      "workflows": {
        "default": "DEFAULT_WORKFLOW"
      }
    },
    "copilot": {
      "workflows": {
        "default": "INVESTIGATION_WORKFLOW"
      }
    },
    "codex": {
      "agents": {
        "enabled": ["architect", "reviewer"]
      }
    }
  }
}
```

---

## Related Documentation

- [Installation Guide](./INSTALLATION.md) - Install the plugin
- [Architecture Overview](./ARCHITECTURE.md) - How the plugin system works
- [Migration Guide](./MIGRATION.md) - Migrate from per-project mode
- [CLI Reference](./CLI_REFERENCE.md) - Command-line tools

---

**Last updated:** 2026-01-19
**Plugin version:** 1.0.0
