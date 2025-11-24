# MCP Manager

A command-line tool for managing MCP (Model Context Protocol) server configurations in Claude Code's settings.json file.

## Overview

MCP Manager provides safe, atomic operations for managing MCP servers with automatic backup and rollback capabilities. It follows the amplihack philosophy of ruthless simplicity and modular design.

## Features

- **List all MCP servers** with status
- **Enable/disable servers** with atomic writes
- **Validate configuration** for errors
- **Automatic backups** before modifications
- **Rollback on errors** to prevent data loss
- **Immutable operations** for safety

## ⚠️ Important: Schema Compatibility

**Current Status**: This tool uses an **extended object schema** for MCP server configuration. Claude Code's actual schema may differ and requires verification.

**What this means**:

- **Current implementation**: Stores full MCP server configs as objects in `.claude/settings.json`
- **Claude Code standard** (per azure-admin docs): May expect servers defined in global `~/.config/claude-code/mcp.json` with project settings only referencing server names as strings

**Impact**:

- Tool works for **standalone project-level MCP management**
- Compatibility with Claude Code's global MCP system **unverified**
- Full schema refactor may be needed after testing with actual Claude Code

**Next Steps**:

1. Test with actual Claude Code installation
2. Verify schema compatibility
3. Refactor to support global mcp.json if needed (see issue #1547)

This limitation is documented in PR #1550 and will be addressed in a future update.

## Installation

No installation required. Run directly from the scenarios directory:

```bash
cd /path/to/amplihack3/.claude/scenarios/mcp-manager
python cli.py <command>
```

## Usage

### List All MCP Servers

```bash
python cli.py list
```

Output:

```
+----------------+-----------+----------------------+---------+----------+
| Name           | Command   | Args                 | Enabled | Env Vars |
+----------------+-----------+----------------------+---------+----------+
| test-server-1  | node      | server.js            | Yes     | API_KEY  |
| test-server-2  | python    | -m test_module       | No      | (none)   |
+----------------+-----------+----------------------+---------+----------+
```

### Enable an MCP Server

```bash
python cli.py enable <server-name>
```

Example:

```bash
python cli.py enable test-server-2
```

Output:

```
Created backup: settings_backup_20231123_153045.json
Successfully enabled server: test-server-2
```

### Disable an MCP Server

```bash
python cli.py disable <server-name>
```

Example:

```bash
python cli.py disable test-server-1
```

Output:

```
Created backup: settings_backup_20231123_153120.json
Successfully disabled server: test-server-1
```

### Validate Configuration

```bash
python cli.py validate
```

Output (valid):

```
✓ Configuration is valid
```

Output (invalid):

```
Configuration validation errors:
  - Server 'bad-server' (index 2): name is required
  - Duplicate server name: test-server
```

## Architecture

MCP Manager follows a modular brick architecture with clear separation of concerns:

### Module 1: config_manager.py

**Purpose**: Safe atomic operations on .claude/settings.json

- `read_config()` - Read and parse settings.json
- `write_config()` - Atomic write with temp file pattern
- `backup_config()` - Create timestamped backup
- `restore_config()` - Restore from backup

### Module 2: mcp_operations.py

**Purpose**: Business logic for MCP server management

- `MCPServer` - Data model with validation
- `list_servers()` - Get all servers from config
- `enable_server()` - Enable server (immutable)
- `disable_server()` - Disable server (immutable)
- `validate_config()` - Validate entire configuration

### Module 3: cli.py

**Purpose**: Command-line interface

- `cmd_list()` - List command handler
- `cmd_enable()` - Enable command handler
- `cmd_disable()` - Disable command handler
- `cmd_validate()` - Validate command handler
- `main()` - CLI entry point

### Module 4: **init**.py

**Purpose**: Public API surface

Exports all public functions and classes for programmatic use.

## Configuration Schema

MCP Manager operates on `.claude/settings.json` with this structure:

```json
{
  "enabledMcpjsonServers": [
    {
      "name": "server-name",
      "command": "path/to/command",
      "args": ["--arg1", "value1"],
      "env": { "KEY": "value" },
      "enabled": true
    }
  ]
}
```

**IMPORTANT**: Only the `enabledMcpjsonServers` array is modified. All other settings are preserved.

## Safety Features

### Atomic Writes

All modifications use atomic write pattern:

1. Write to temporary `.tmp` file
2. Rename to target (atomic on POSIX)
3. No partial writes if interrupted

### Automatic Backups

Before any modification:

1. Create timestamped backup
2. Keep last 10 backups
3. Auto-cleanup older backups

### Rollback on Error

If any operation fails:

1. Restore from backup automatically
2. Configuration remains unchanged
3. Error message explains what went wrong

### Immutable Operations

Business logic operations:

- Never modify input config
- Always return new config dict
- Safe for concurrent use

## Programmatic Usage

You can also use MCP Manager as a Python library:

```python
from pathlib import Path
from mcp_manager import (
    read_config,
    list_servers,
    enable_server,
    write_config,
    backup_config,
)

# Read config
config_path = Path(".claude/settings.json")
config = read_config(config_path)

# List servers
servers = list_servers(config)
for server in servers:
    print(f"{server.name}: {'enabled' if server.enabled else 'disabled'}")

# Enable a server
backup_path = backup_config(config_path)
new_config = enable_server(config, "my-server")
write_config(config_path, new_config)
```

## Testing

Run the test suite with pytest:

```bash
cd /path/to/amplihack3/.claude/scenarios/mcp-manager
pytest tests/
```

Test coverage:

- `test_config_manager.py` - Config I/O operations
- `test_mcp_operations.py` - Business logic
- `test_cli.py` - CLI interface

## Error Handling

### Server Not Found

```bash
$ python cli.py enable nonexistent
Error enabling server (rolled back): Server not found: nonexistent
```

### Invalid Configuration

```bash
$ python cli.py validate
Configuration validation errors:
  - Server '' (index 0): Server name is required
  - Server 'Bad Name' (index 1): Server name must be lowercase with no spaces
```

### File Not Found

```bash
$ python cli.py list
Error listing servers: Configuration file not found: .claude/settings.json
```

## Phase 2 Commands (Coming Soon)

The following commands are planned for Phase 2:

- `add` - Add a new MCP server
- `remove` - Remove an MCP server
- `show <name>` - Show detailed server information
- `edit <name>` - Edit server configuration interactively

## Philosophy Compliance

MCP Manager follows amplihack's core principles:

✓ **Ruthless Simplicity** - Each module has ONE clear purpose
✓ **Modular Design** - Self-contained bricks with clear contracts
✓ **Zero-BS Implementation** - No placeholders, everything works
✓ **Regeneratable** - Can be rebuilt from specification

## Contributing

When extending MCP Manager:

1. Follow the brick architecture pattern
2. Maintain immutability in operations
3. Add tests for new functionality
4. Update this README

## License

Part of the amplihack3 project.
