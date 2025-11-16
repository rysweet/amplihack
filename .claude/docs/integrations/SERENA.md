# Serena MCP Integration

## What is Serena?

Serena is a Model Context Protocol (MCP) server that provides advanced AI capabilities for Claude Code. It extends Claude's functionality with additional tools and context management features.

- **Repository**: https://github.com/oraios/serena
- **Type**: MCP Server
- **Delivery**: Via `uvx` (UV package executor)

## How It Works

Serena is automatically configured when you install amplihack. The configuration is included in the default `settings.json` template:

```json
{
  "enabledMcpjsonServers": [
    {
      "name": "serena",
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/oraios/serena",
        "serena"
      ],
      "env": {}
    }
  ]
}
```

### What Serena Provides

When active, Serena adds:

- Enhanced context management capabilities
- Additional AI-powered tools for development workflows
- Integration with UV-based Python ecosystem
- Seamless integration with Claude Code's existing functionality

## Requirements

Serena requires the `uv` package manager to be installed on your system.

### Installing UV

If you don't have `uv` installed, you'll see a warning at session start. Install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or on macOS/Linux:

```bash
# macOS (via Homebrew)
brew install astral-sh/tap/uv

# Ubuntu/Debian
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, restart your terminal or source your shell configuration:

```bash
source ~/.bashrc  # or ~/.zshrc, ~/.profile, etc.
```

## Configuration

### Default Setup

Serena is configured automatically when you run:

```bash
amplihack install
```

No additional configuration is needed - it's ready to use!

### Disabling Serena

If you don't want to use Serena, you can disable it by editing your `~/.claude/settings.json`:

1. Open `~/.claude/settings.json`
2. Find the `enabledMcpjsonServers` array
3. Remove the Serena entry:

```json
{
  "enabledMcpjsonServers": []
}
```

Or comment it out by wrapping in a disabled array:

```json
{
  "enabledMcpjsonServers": [],
  "disabledMcpjsonServers": [
    {
      "name": "serena",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/oraios/serena", "serena"],
      "env": {}
    }
  ]
}
```

### Re-enabling Serena

To re-enable Serena, simply add it back to the `enabledMcpjsonServers` array or run:

```bash
amplihack install  # Re-run installation to restore defaults
```

## Troubleshooting

### Serena Won't Start

**Check UV Installation:**

```bash
which uv
```

If this returns nothing, UV is not installed or not in your PATH.

**Check Logs:**

Claude Code logs MCP server startup information. Check for errors related to Serena in the session output.

**Manual Test:**

You can test if Serena works directly:

```bash
uvx --from git+https://github.com/oraios/serena serena
```

### UV Command Not Found

If you see "uv: command not found" after installation:

1. Restart your terminal
2. Check if UV's bin directory is in your PATH:
   ```bash
   echo $PATH | grep -o "[^:]*uv[^:]*"
   ```
3. Manually add to PATH if needed (add to `~/.bashrc` or `~/.zshrc`):
   ```bash
   export PATH="$HOME/.cargo/bin:$PATH"
   ```

### Serena Fails to Clone Repository

If you see git-related errors:

1. Ensure you have internet connectivity
2. Check if git is installed: `which git`
3. Verify GitHub is accessible: `curl -I https://github.com`

## Updates

Serena updates automatically via `uvx` when Claude Code starts. The latest version from the repository will be fetched on demand.

To force an update, you can clear UV's cache:

```bash
uv cache clean
```

## Philosophy Alignment

Serena integration follows amplihack's ruthless simplicity principles:

- **Zero Configuration**: Works out of the box after `amplihack install`
- **Non-Blocking**: Missing `uv` shows a warning but doesn't break the system
- **Self-Contained**: Managed entirely via `settings.json` configuration
- **No Lock-In**: Easy to disable if not needed

## More Information

- **Serena Repository**: https://github.com/oraios/serena
- **UV Documentation**: https://github.com/astral-sh/uv
- **MCP Protocol**: https://modelcontextprotocol.io

---

**Last Updated**: 2025-11-16
**Integration Status**: Active by default in amplihack
