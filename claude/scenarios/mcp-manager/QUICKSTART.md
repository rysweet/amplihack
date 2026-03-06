# MCP Manager Quickstart Guide

Get started managing MCP (Model Context Protocol) servers in Claude Code in under 5 minutes.

## What is MCP Manager?

MCP Manager helps you configure, enable, and disable MCP servers through simple commands or natural conversation with Claude.

**Two ways to use it:**

1. **Conversational** (recommended): "List my MCPs", "Enable the filesystem server"
2. **CLI**: Direct commands for scripts and automation

## Quick Start (CLI)

### 1. List Your Current MCPs

```bash
cd .claude/scenarios
python3 -m mcp-manager.cli list
```

**Output:**

```
No MCP servers configured
```

### 2. Add Your First MCP Server

Let's add the filesystem MCP server:

```bash
python3 -m mcp-manager.cli add filesystem npx -- -y @modelcontextprotocol/server-filesystem
```

**Output:**

```
Created backup: settings_backup_20251124_020634_786095.json
Successfully added server: filesystem (enabled)
```

### 3. List Servers Again

```bash
python3 -m mcp-manager.cli list
```

**Output:**

```
+-----------------+---------+---------------------------------------------+---------+----------+
| Name            | Command | Args                                        | Enabled | Env Vars |
+-----------------+---------+---------------------------------------------+---------+----------+
| filesystem      | npx     | -y @modelcontextprotocol/server-filesyst... | Yes     | (none)   |
+-----------------+---------+---------------------------------------------+---------+----------+
```

### 4. Show Server Details

```bash
python3 -m mcp-manager.cli show filesystem
```

**Output:**

```
Server: filesystem
=======================
Command:  npx
Args:     -y @modelcontextprotocol/server-filesystem
Enabled:  Yes

Environment Variables: (none)
```

### 5. Disable a Server

```bash
python3 -m mcp-manager.cli disable filesystem
```

**Output:**

```
Created backup: settings_backup_20251124_020747_827593.json
Successfully disabled server: filesystem
```

### 6. Re-enable a Server

```bash
python3 -m mcp-manager.cli enable filesystem
```

**Output:**

```
Created backup: settings_backup_20251124_020759_130192.json
Successfully enabled server: filesystem
```

### 7. Remove a Server

```bash
python3 -m mcp-manager.cli remove filesystem --force
```

**Output:**

```
Created backup: settings_backup_20251124_020811_018707.json
Successfully removed server: filesystem
```

---

## Quick Start (Conversational)

Just talk to Claude naturally:

```
You: "List all my MCPs"
Claude: [Shows formatted list of MCP servers]

You: "Add the filesystem MCP server"
Claude: [Guides you through interactive setup]

You: "Enable the filesystem server"
Claude: [Enables the server and confirms]

You: "Show me the filesystem MCP details"
Claude: [Displays server configuration]
```

**The skill automatically activates when you mention "MCP" or related keywords.**

---

## Common MCP Servers

### Filesystem MCP

```bash
python3 -m mcp-manager.cli add filesystem npx -- -y @modelcontextprotocol/server-filesystem
```

### GitHub MCP

```bash
python3 -m mcp-manager.cli add github npx -- -y @modelcontextprotocol/server-github
```

### Puppeteer MCP (Browser Automation)

```bash
python3 -m mcp-manager.cli add puppeteer npx -- -y @modelcontextprotocol/server-puppeteer
```

### Azure MCP (with environment variables)

```bash
python3 -m mcp-manager.cli add azure npx -- -y @modelcontextprotocol/server-azure \
  --env AZURE_SUBSCRIPTION_ID=your-sub-id \
  --env AZURE_TENANT_ID=your-tenant-id
```

---

## Key Commands Reference

| Command    | Purpose          | Example                                                     |
| ---------- | ---------------- | ----------------------------------------------------------- |
| `list`     | Show all servers | `python3 -m mcp-manager.cli list`                           |
| `add`      | Add new server   | `python3 -m mcp-manager.cli add <name> <command> <args...>` |
| `enable`   | Enable server    | `python3 -m mcp-manager.cli enable <name>`                  |
| `disable`  | Disable server   | `python3 -m mcp-manager.cli disable <name>`                 |
| `show`     | Show details     | `python3 -m mcp-manager.cli show <name>`                    |
| `remove`   | Remove server    | `python3 -m mcp-manager.cli remove <name>`                  |
| `validate` | Check config     | `python3 -m mcp-manager.cli validate`                       |
| `export`   | Export config    | `python3 -m mcp-manager.cli export backup.json`             |
| `import`   | Import config    | `python3 -m mcp-manager.cli import backup.json`             |

---

## Safety Features

Every modification:

- **Creates automatic backup** (timestamped)
- **Uses atomic writes** (no partial updates)
- **Validates configuration** before writing
- **Rolls back on errors** (restores from backup)

**Backups are stored in:** `~/.amplihack/.claude/backups/settings_backup_*.json`

---

## Next Steps

- **Full documentation**: See [README.md](./README.md)
- **Developer guide**: See [HOW_TO_CREATE_YOUR_OWN.md](./HOW_TO_CREATE_YOUR_OWN.md)
- **Examples**: See [examples/basic_usage.py](./examples/basic_usage.py)

---

**Ready to manage your MCPs! Start with:** `python3 -m mcp-manager.cli list`
