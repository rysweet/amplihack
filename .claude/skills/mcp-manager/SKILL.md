---
name: mcp-manager
description: Conversational interface for managing MCP (Model Context Protocol) server configurations in Claude Code
type: skill
activationStrategy: lazy-aggressive
activationKeywords:
  - MCP
  - Model Context Protocol
  - MCP server
  - MCP configuration
  - configure MCP
  - manage MCP
  - enable MCP
  - disable MCP
  - add MCP
  - remove MCP
  - list MCPs
  - show MCP
  - validate MCP
  - export MCP
  - import MCP
activationContextWindow: 3
persistenceThreshold: 20
---

# MCP Manager Skill

## Overview

This skill provides a natural language interface to the MCP Manager CLI tool, enabling conversational management of Model Context Protocol server configurations in Claude Code. Instead of manually editing `settings.json` or remembering CLI syntax, users can interact naturally: "enable the filesystem MCP", "add a database server", or "show me all my MCPs". The skill handles intent detection, parameter collection, confirmation workflows, and error recovery, making MCP server management intuitive and safe.

**Key Capabilities:**
- List, enable, disable, show, add, remove MCP servers
- Validate configurations and import/export settings
- Interactive workflows for complex operations (add, remove)
- Confirmation prompts for destructive actions
- Clear error messages with actionable suggestions

## Activation

This skill activates on MCP-related keywords within a 3-message context window:
- Direct mentions: "MCP", "Model Context Protocol", "MCP server"
- Management actions: "configure MCP", "manage MCP", "enable MCP"
- Listing/viewing: "list MCPs", "show MCP", "validate MCP"

**Explicit invocation:** `/mcp-manager` or "Use the MCP manager skill"

The skill persists for 20 messages after activation to maintain context during multi-step workflows.

## Commands Supported

### 1. List MCPs

**Purpose:** Display all configured MCP servers with their status and descriptions.

**Natural Language Examples:**
- "List all my MCPs"
- "Show me my MCP servers"
- "What MCPs are configured?"

**CLI Mapping:** `python3 -m mcp-manager.cli list`

**Example Output:**
```
✓ filesystem (enabled) - Local filesystem access
✓ github (enabled) - GitHub API integration
✗ puppeteer (disabled) - Browser automation
```

---

### 2. Enable MCP

**Purpose:** Enable a disabled MCP server to make it active in Claude Code.

**Natural Language Examples:**
- "Enable the filesystem MCP"
- "Turn on puppeteer"
- "Activate the github server"

**CLI Mapping:** `python3 -m mcp-manager.cli enable <server-name>`

**Example Output:**
```
✓ Successfully enabled 'filesystem' MCP server.
```

---

### 3. Disable MCP

**Purpose:** Disable an active MCP server without removing its configuration.

**Natural Language Examples:**
- "Disable the puppeteer MCP"
- "Turn off github"
- "Deactivate filesystem server"

**CLI Mapping:** `python3 -m mcp-manager.cli disable <server-name>`

**Example Output:**
```
✓ Successfully disabled 'puppeteer' MCP server.
```

**Note:** Requires confirmation prompt before executing.

---

### 4. Add MCP

**Purpose:** Add a new MCP server configuration interactively.

**Natural Language Examples:**
- "Add a new MCP server"
- "Configure a database MCP"
- "Set up a weather MCP"

**CLI Mapping:** `python3 -m mcp-manager.cli add <name> <command> [args...] --env KEY=VALUE`

**Interactive Workflow:**
1. Collect server name
2. Collect startup command
3. Collect environment variables (optional)
4. Confirm and execute

**Example Output:**
```
✓ Successfully added 'postgres-local' MCP server.
Server is currently disabled. Enable with: 'enable postgres-local'
```

---

### 5. Remove MCP

**Purpose:** Delete an MCP server configuration completely.

**Natural Language Examples:**
- "Remove the puppeteer MCP"
- "Delete the old-server"
- "Uninstall github MCP"

**CLI Mapping:** `python3 -m mcp-manager.cli remove <server-name>`

**Example Output:**
```
✓ Successfully removed 'puppeteer' MCP server.
```

**Note:** Requires confirmation prompt with warning about irreversibility.

---

### 6. Show MCP

**Purpose:** Display detailed information about a specific MCP server.

**Natural Language Examples:**
- "Show me the filesystem MCP"
- "Details for github server"
- "What's configured for puppeteer?"

**CLI Mapping:** `python3 -m mcp-manager.cli show <server-name>`

**Example Output:**
```
Server: filesystem
Status: enabled
Command: npx @modelcontextprotocol/server-filesystem /home/user/projects
Environment:
  - LOG_LEVEL=info
Description: Local filesystem access
```

---

### 7. Validate MCPs

**Purpose:** Check all MCP configurations for errors or issues.

**Natural Language Examples:**
- "Validate my MCP configuration"
- "Check for MCP errors"
- "Are my MCPs configured correctly?"

**CLI Mapping:** `python3 -m mcp-manager.cli validate`

**Example Output:**
```
✓ All MCP server configurations are valid.
3 servers configured, 2 enabled.
```

---

### 8. Export MCPs

**Purpose:** Export MCP configurations to a JSON file for backup or sharing.

**Natural Language Examples:**
- "Export my MCP configuration"
- "Back up my MCPs"
- "Save MCPs to a file"

**CLI Mapping:** `python3 -m mcp-manager.cli export [output-file]`

**Example Output:**
```
✓ Exported 3 MCP servers to mcp-config-backup.json
```

---

### 9. Import MCPs

**Purpose:** Import MCP configurations from a JSON file.

**Natural Language Examples:**
- "Import MCPs from backup.json"
- "Load MCP configuration from file"
- "Restore my MCPs"

**CLI Mapping:** `python3 -m mcp-manager.cli import <input-file> [--merge]`

**Example Output:**
```
✓ Successfully imported 3 MCP servers from backup.json
Added: filesystem, github, puppeteer
```

## Intent Mapping Reference

| User Request | Intent | CLI Command | Confirmation Required |
|--------------|--------|-------------|----------------------|
| "list all my MCPs" | list_mcps | `list` | No |
| "enable filesystem" | enable_mcp | `enable filesystem` | No |
| "disable puppeteer" | disable_mcp | `disable puppeteer` | Yes |
| "remove old-server" | remove_mcp | `remove old-server` | Yes |
| "add new MCP" | add_mcp | `add` (interactive) | No |
| "show github MCP" | show_mcp | `show github` | No |
| "validate config" | validate_mcps | `validate` | No |
| "export MCPs" | export_config | `export` | No |
| "import from file" | import_config | `import <path>` | No |

## Usage Examples

### Example 1: List MCPs

**User:** "List all my MCPs"

**Skill Response:**
"I'll check your MCP configurations..."

[Executes: `cd /home/azureuser/src/amplihack3/worktrees/feat/issue-1547-mcp-manager/.claude/scenarios && python3 -m mcp-manager.cli list`]

"You have 3 MCP servers configured:

✓ **filesystem** (enabled) - Local filesystem access
✓ **github** (enabled) - GitHub API integration
✗ **puppeteer** (disabled) - Browser automation

Would you like to enable/disable any servers or see more details?"

---

### Example 2: Enable/Disable MCP

**User:** "Turn on the puppeteer MCP"

**Skill Response:**
"I'll enable the puppeteer MCP server..."

[Executes: `cd /home/azureuser/src/amplihack3/worktrees/feat/issue-1547-mcp-manager/.claude/scenarios && python3 -m mcp-manager.cli enable puppeteer`]

"✓ Successfully enabled 'puppeteer' MCP server.

The puppeteer server is now active and Claude Code can use it for browser automation."

**Follow-up:** "Actually, disable it again"

**Skill Response:**
"⚠️  You're about to disable the 'puppeteer' MCP server. This will stop Claude Code from using it until re-enabled.

Are you sure you want to proceed? (yes/no)"

[User confirms: "yes"]

[Executes: `cd /home/azureuser/src/amplihack3/worktrees/feat/issue-1547-mcp-manager/.claude/scenarios && python3 -m mcp-manager.cli disable puppeteer`]

"✓ Successfully disabled 'puppeteer' MCP server.

You can re-enable it anytime with: 'enable puppeteer'"

---

### Example 3: Add New MCP (Interactive)

**User:** "Add a new MCP for database access"

**Skill Response:**
"I'll help you add a new MCP server. I need a few details:

**1. Server name** (e.g., 'database', 'postgres-mcp'):"

[User provides: "postgres-local"]

"**2. Command to start the server** (e.g., 'node server.js', 'python main.py'):"

[User provides: "node /opt/mcp-servers/postgres/index.js"]

"**3. Any command-line arguments?** (optional, press Enter to skip):"

[User provides: "--port 5432 --host localhost"]

"**4. Environment variables?** (optional, format: KEY=value KEY2=value2, press Enter to skip):"

[User provides: "DATABASE_URL=postgresql://localhost:5432/mydb"]

"Great! Adding MCP server with these settings:
- **Name:** postgres-local
- **Command:** node /opt/mcp-servers/postgres/index.js
- **Arguments:** --port 5432 --host localhost
- **Environment:** DATABASE_URL=postgresql://localhost:5432/mydb"

[Executes: `cd /home/azureuser/src/amplihack3/worktrees/feat/issue-1547-mcp-manager/.claude/scenarios && python3 -m mcp-manager.cli add postgres-local "node /opt/mcp-servers/postgres/index.js" --port 5432 --host localhost --env "DATABASE_URL=postgresql://localhost:5432/mydb"`]

"✓ Successfully added 'postgres-local' MCP server.

The server has been added but is currently **disabled**. Would you like to enable it now?"

---

### Example 4: Show MCP Details

**User:** "Show me details for the github MCP"

**Skill Response:**
"I'll retrieve the github MCP configuration..."

[Executes: `cd /home/azureuser/src/amplihack3/worktrees/feat/issue-1547-mcp-manager/.claude/scenarios && python3 -m mcp-manager.cli show github`]

"**Server:** github
**Status:** enabled
**Command:** npx @modelcontextprotocol/server-github
**Arguments:**
  - --token ${GITHUB_TOKEN}
  - --repo rysweet/amplihack3
**Environment Variables:**
  - GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx (redacted)
**Description:** GitHub API integration for repository access

This server allows Claude Code to interact with GitHub repositories, issues, and pull requests."

---

### Example 5: Remove MCP (with Confirmation)

**User:** "Remove the puppeteer MCP"

**Skill Response:**
"⚠️  **WARNING: Destructive Operation**

You're about to remove the 'puppeteer' MCP server. This will:
- Delete the server configuration from settings.json
- Remove all associated settings and environment variables
- Stop the server if currently running
- **This action cannot be undone**

Current configuration:
- **Status:** disabled
- **Command:** npx @modelcontextprotocol/server-puppeteer
- **Last used:** 3 days ago

Are you sure you want to proceed? Type 'yes' to confirm or 'no' to cancel."

[User confirms: "yes"]

[Executes: `cd /home/azureuser/src/amplihack3/worktrees/feat/issue-1547-mcp-manager/.claude/scenarios && python3 -m mcp-manager.cli remove puppeteer`]

"✓ Successfully removed 'puppeteer' MCP server.

The server has been completely removed from your configuration. You can add it back later with: 'Add the puppeteer MCP server'"

## Error Handling

### Error Scenario 1: CLI Tool Not Found

**Trigger:** MCP Manager CLI is not installed or not in the expected location.

**Detection:** Bash command returns "command not found" or "No module named mcp-manager"

**Response:**
"❌ Error: MCP Manager CLI tool not found.

The MCP Manager tool doesn't appear to be installed. I can help you install it:

1. **Install from scenarios directory:**
   ```bash
   cd .claude/scenarios/mcp-manager
   pip install -e .
   ```

2. **Or run without installation:**
   ```bash
   cd .claude/scenarios
   python3 -m mcp-manager.cli --help
   ```

Would you like me to attempt installation?"

---

### Error Scenario 2: Settings File Malformed

**Trigger:** `settings.json` has invalid JSON or corrupt structure.

**Detection:** CLI returns error about JSON parsing.

**Response:**
"❌ Error: MCP configuration file is malformed.

The `.claude/settings.json` file appears to be corrupted or contains invalid JSON. This usually happens after manual editing.

**Recommended actions:**

1. **Validate JSON syntax:**
   I can check the file for syntax errors.

2. **Restore from backup:**
   Check if `.claude/settings.json.backup` exists.

3. **Reset to defaults:**
   I can create a fresh configuration (warning: loses existing MCPs).

Which would you like me to do?"

---

### Error Scenario 3: Server Not Found

**Trigger:** User references an MCP server that doesn't exist.

**Detection:** CLI returns "Server not found" error.

**Response:**
"❌ Error: MCP server 'database' not found.

**Available servers:**
- filesystem
- github
- puppeteer

Did you mean one of these? Or would you like to:
1. **Add** a new 'database' server
2. **List** all servers to see what's available
3. **Import** servers from a backup file

What would you like to do?"

---

### Error Scenario 4: Server Already Exists

**Trigger:** Attempting to add an MCP server with a name that's already taken.

**Detection:** CLI returns "Server already exists" error.

**Response:**
"❌ Error: MCP server 'github' already exists.

A server with this name is already configured. You can:

1. **Show existing configuration:**
   'Show me the github MCP details'

2. **Remove and re-add:**
   'Remove github MCP' then add it again

3. **Choose a different name:**
   Try 'github-v2' or 'github-personal'

Which would you prefer?"

---

### Error Scenario 5: Permission Denied

**Trigger:** Cannot write to `settings.json` due to filesystem permissions.

**Detection:** CLI returns permission error or "Read-only file system".

**Response:**
"❌ Error: Permission denied when updating MCP configuration.

Cannot write to `.claude/settings.json`. This usually means:

1. **File permissions issue:**
   ```bash
   chmod 644 .claude/settings.json
   ```

2. **Directory permissions issue:**
   ```bash
   chmod 755 .claude/
   ```

3. **File is locked by another process:**
   Close any editors or tools using settings.json

Would you like me to check the file permissions?"

---

### Error Scenario 6: Invalid Command Syntax

**Trigger:** User request cannot be parsed into a valid CLI command.

**Detection:** Ambiguous intent, missing required parameters, or malformed input.

**Response:**
"❌ Error: I couldn't understand that request.

I recognize you're trying to work with MCPs, but I need a bit more information.

**Common commands:**
- **List:** 'List all my MCPs'
- **Enable:** 'Enable the [server-name] MCP'
- **Disable:** 'Disable the [server-name] MCP'
- **Add:** 'Add a new MCP server'
- **Remove:** 'Remove the [server-name] MCP'
- **Show:** 'Show details for [server-name]'

Could you rephrase your request using one of these patterns?"

## Tool Invocation Patterns

This skill calls the MCP Manager CLI tool using the Bash tool. All commands execute from the `.claude/scenarios/` directory.

### Base Invocation Pattern

```bash
cd /home/azureuser/src/amplihack3/worktrees/feat/issue-1547-mcp-manager/.claude/scenarios && python3 -m mcp-manager.cli <command> [args]
```

### Command Reference

**List all MCPs:**
```bash
python3 -m mcp-manager.cli list
```

**Enable MCP:**
```bash
python3 -m mcp-manager.cli enable <server-name>
```

**Disable MCP:**
```bash
python3 -m mcp-manager.cli disable <server-name>
```

**Add MCP (with environment variables):**
```bash
python3 -m mcp-manager.cli add <name> <command> [args...] --env KEY=VALUE --env KEY2=VALUE2
```

**Add MCP (without environment variables):**
```bash
python3 -m mcp-manager.cli add <name> <command> [args...]
```

**Remove MCP:**
```bash
python3 -m mcp-manager.cli remove <server-name>
```

**Show MCP details:**
```bash
python3 -m mcp-manager.cli show <server-name>
```

**Validate configuration:**
```bash
python3 -m mcp-manager.cli validate
```

**Export configuration:**
```bash
python3 -m mcp-manager.cli export [output-file]
```
*(Defaults to `mcp-config-backup.json` if no file specified)*

**Import configuration:**
```bash
python3 -m mcp-manager.cli import <input-file>
```

**Import with merge:**
```bash
python3 -m mcp-manager.cli import <input-file> --merge
```
*(Merges with existing configuration instead of replacing)*

### Output Handling

**Success Detection:**
- Exit code 0
- stdout contains success messages (✓ prefix)
- No errors in stderr

**Error Detection:**
- Exit code non-zero
- stderr contains error messages
- stdout contains error indicators (❌ prefix)

**Output Formatting:**
- Preserve table formatting from CLI
- Maintain color codes where supported
- Extract key information for natural language responses
- Redact sensitive information (tokens, passwords) in environment variables

### Working Directory

All commands execute from: `/home/azureuser/src/amplihack3/worktrees/feat/issue-1547-mcp-manager/.claude/scenarios/`

This ensures the CLI tool is accessible via Python module syntax (`-m mcp-manager.cli`).

### Error Handling in Invocations

1. **Check exit code** before parsing output
2. **Read stderr** for error details
3. **Parse error type** from CLI message
4. **Map to error scenario** (see Error Handling section)
5. **Provide actionable response** to user

## Related Documentation

- **CLI Tool Documentation:** `.claude/scenarios/mcp-manager/README.md`
- **MCP Protocol Specification:** https://modelcontextprotocol.io/
- **Claude Code Settings:** `.claude/settings.json`

## Best Practices

1. **Always confirm destructive operations** (disable, remove)
2. **Validate server names** before executing commands
3. **Provide clear error messages** with actionable next steps
4. **Offer alternatives** when operations fail
5. **Show current state** before and after changes
6. **Redact sensitive information** (API keys, tokens) in responses

## Troubleshooting

**Skill not activating?**
- Use explicit invocation: `/mcp-manager`
- Check if keywords are within 3-message window
- Verify skill file is in `.claude/skills/mcp-manager/`

**CLI commands failing?**
- Ensure you're in the correct working directory
- Verify MCP Manager tool is installed
- Check settings.json exists and is writable

**Configuration not updating?**
- Restart Claude Code after settings.json changes
- Verify JSON syntax in settings.json
- Check file permissions on .claude directory

---

**Skill Version:** 1.0.0
**Last Updated:** 2025-11-24
**Maintainer:** amplihack team
