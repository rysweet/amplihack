# GitHub Copilot CLI Reference

Complete reference documentation for GitHub Copilot CLI.

## All Slash Commands

### Session Management

| Command          | Arguments                                       | Description                               |
| ---------------- | ----------------------------------------------- | ----------------------------------------- |
| `/clear`, `/new` | -                                               | Clear conversation history                |
| `/compact`       | -                                               | Summarize conversation to reduce context  |
| `/context`       | -                                               | Show token usage visualization            |
| `/usage`         | -                                               | Display session metrics and statistics    |
| `/exit`, `/quit` | -                                               | Exit the CLI                              |
| `/session`       | `[checkpoints [n]\|files\|plan\|rename <name>]` | Show session info, manage checkpoints     |
| `/rename`        | `<name>`                                        | Rename current session                    |
| `/resume`        | `[sessionId]`                                   | Switch to different session               |
| `/share`         | `[file\|gist] [path]`                           | Export session to markdown or GitHub gist |

### Configuration & Tools

| Command                | Arguments                                                  | Description                        |
| ---------------------- | ---------------------------------------------------------- | ---------------------------------- |
| `/model`, `/models`    | `[model]`                                                  | Select AI model                    |
| `/mcp`                 | `[show\|add\|edit\|delete\|disable\|enable] [server-name]` | Manage MCP servers                 |
| `/agent`               | -                                                          | Browse and select available agents |
| `/skills`              | `[list\|info\|add\|remove\|reload] [args...]`              | Manage skills                      |
| `/theme`               | `[show\|set\|list] [auto\|dark\|light]`                    | Configure terminal theme           |
| `/terminal-setup`      | -                                                          | Configure multiline input support  |
| `/reset-allowed-tools` | -                                                          | Reset tool permissions             |

### File & Directory Access

| Command       | Arguments     | Description                              |
| ------------- | ------------- | ---------------------------------------- |
| `/add-dir`    | `<directory>` | Add directory to allowed list            |
| `/list-dirs`  | -             | Display all allowed directories          |
| `/cwd`, `/cd` | `[directory]` | Change or show working directory         |
| `/diff`       | -             | Review changes made in current directory |

### Authentication & User

| Command   | Arguments              | Description                 |
| --------- | ---------------------- | --------------------------- |
| `/login`  | -                      | Log in to Copilot           |
| `/logout` | -                      | Log out of Copilot          |
| `/user`   | `[show\|list\|switch]` | Manage GitHub user accounts |

### Task Delegation

| Command     | Arguments  | Description                                    |
| ----------- | ---------- | ---------------------------------------------- |
| `/delegate` | `<prompt>` | Push session to Copilot coding agent on GitHub |
| `/plan`     | `[prompt]` | Create implementation plan before coding       |
| `/review`   | `[prompt]` | Run code review agent                          |

### Help & Feedback

| Command     | Arguments | Description                                    |
| ----------- | --------- | ---------------------------------------------- |
| `/help`     | -         | Show help for interactive commands             |
| `/feedback` | -         | Submit feedback, bug reports, feature requests |
| `/ide`      | -         | Connect to an IDE workspace                    |

## Command-Line Options

### Basic Options

```bash
copilot [options]

Options:
  -p, --prompt <text>     Run with single prompt (programmatic mode)
  --resume                Cycle through and resume sessions
  --continue              Resume most recent session
  --agent <name>          Specify custom agent to use
  --banner                Show animated banner
  --version               Show version number
  --help                  Show help
```

### Tool Approval Options

```bash
--allow-all-tools         Allow all tools without approval
--allow-tool <spec>       Allow specific tool (repeatable)
--deny-tool <spec>        Deny specific tool (repeatable)
```

**Tool Specification Formats:**

- `'shell'` - All shell commands
- `'shell(git)'` - Specific command
- `'shell(git push)'` - Command with subcommand
- `'write'` - File modification tools
- `'MCP_SERVER_NAME'` - All tools from MCP server
- `'MCP_SERVER_NAME(tool_name)'` - Specific MCP tool

### Path & URL Options

```bash
--allow-all-paths         Disable path verification
--allow-all-urls          Disable URL verification
--allow-url <domain>      Pre-approve specific domain
```

## Environment Variables

| Variable          | Description                                       |
| ----------------- | ------------------------------------------------- |
| `GH_TOKEN`        | GitHub personal access token (highest priority)   |
| `GITHUB_TOKEN`    | GitHub personal access token (fallback)           |
| `XDG_CONFIG_HOME` | Override config directory (default: `~/.copilot`) |
| `HOME`            | User home directory                               |
| `TMPDIR`          | Temporary directory                               |
| `PWD`             | Current working directory                         |

## Configuration Files

### Main Configuration

**Location**: `~/.copilot/config.json`

```json
{
  "trusted_folders": ["/path/to/trusted/project1", "/path/to/trusted/project2"],
  "theme": "auto",
  "model": "claude-sonnet-4-5"
}
```

### MCP Server Configuration

**Location**: `~/.copilot/mcp-config.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GH_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    }
  }
}
```

## Custom Instructions Locations

Copilot CLI reads instructions from (in order):

1. `CLAUDE.md` (in git root & cwd)
2. `GEMINI.md` (in git root & cwd)
3. `AGENTS.md` (in git root & cwd)
4. `.github/instructions/**/*.instructions.md` (in git root & cwd)
5. `.github/copilot-instructions.md`
6. `$HOME/.copilot/copilot-instructions.md`
7. `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` (additional directories via env var)

## Custom Agents

### Built-in Agents

| Agent         | Description                                                                |
| ------------- | -------------------------------------------------------------------------- |
| `explore`     | Fast codebase analysis, answering questions without adding to context      |
| `task`        | Execute commands (tests, builds), brief on success, full output on failure |
| `plan`        | Create implementation plans before coding                                  |
| `code-review` | Review changes, surface only genuine issues                                |

### Agent Loading Locations

| Priority    | Location                  | Scope                     |
| ----------- | ------------------------- | ------------------------- |
| 1 (highest) | `~/.copilot/agents/`      | User-level (all projects) |
| 2           | `.github/agents/`         | Repository-level          |
| 3 (lowest)  | `.github-private/agents/` | Organization/Enterprise   |

### Invoking Custom Agents

```bash
# Interactive - select from list
/agent

# In prompt - auto-infer
Use the refactoring agent to clean up this code

# Command-line - explicit
copilot --agent=my-agent --prompt "Do the thing"
```

## Security Model

### Trusted Directories

On first launch, you're asked to trust the current directory:

1. **Yes, proceed** - Trust for this session only
2. **Yes, and remember** - Trust for all future sessions
3. **No, exit** - Cancel session

Edit permanently: `~/.copilot/config.json` → `trusted_folders` array

### Tool Approval Flow

When Copilot needs to use a potentially dangerous tool:

1. **Yes** - Allow this time only
2. **Yes, approve for session** - Allow all uses of this tool type in session
3. **No (Esc)** - Cancel and provide different instruction

### Permission Scopes

**Path Permissions:**

- Default: Current directory, subdirectories, system temp
- Limitations: Custom env vars not expanded, symlinks resolved only for existing files

**URL Permissions:**

- Default: All URLs require approval
- Limitations: URLs in files/configs not detected, obfuscated URLs may bypass

### Risk Mitigation

For automated workflows with `--allow-all-tools`:

- Use in VMs, containers, or isolated environments
- Restrict network access
- Use specific `--deny-tool` for dangerous commands

## Models

### Available Models

Use `/model` to see current options. Typical choices:

- **Claude Sonnet 4.5** (1x) - Default
- **Claude Sonnet 4** (1x)
- **GPT-5** (varies)
- Additional models based on subscription

### Premium Request Multipliers

Each prompt costs premium requests × model multiplier. Check `/model` for current multipliers.

## Help Commands (Terminal)

```bash
copilot help           # General help
copilot help config    # Configuration settings
copilot help environment  # Environment variables
copilot help logging   # Logging levels
copilot help permissions  # Tool permissions
```

## Programmatic Mode Examples

### Simple Query

```bash
copilot -p "What does this repo do?"
```

### With Tool Approval

```bash
copilot -p "Run the tests" --allow-tool 'shell(npm)'
```

### Full Automation

```bash
copilot -p "Fix linting errors and commit" \
  --allow-all-tools \
  --deny-tool 'shell(git push)' \
  --deny-tool 'shell(rm)'
```

### Piping Input

```bash
echo "Explain this code" | copilot
cat script.sh | copilot -p "What does this do?"
```

## Prerequisites

- **Active Copilot subscription** ([Plans](https://github.com/features/copilot/plans))
- **Windows**: PowerShell v6+
- **npm install**: Node.js 22+

## Version Management

### Check Version

```bash
copilot --version
```

### Upgrade Commands

```bash
# Homebrew
brew upgrade copilot-cli

# npm
npm update -g @github/copilot

# WinGet
winget upgrade GitHub.Copilot

# Install script (reinstall latest)
curl -fsSL https://gh.io/copilot-install | bash
```

### Install Specific Version

```bash
# npm
npm install -g @github/copilot@0.0.393

# Install script
curl -fsSL https://gh.io/copilot-install | VERSION="v0.0.393" bash
```

### Prerelease Channel

```bash
brew install copilot-cli@prerelease
npm install -g @github/copilot@prerelease
winget install GitHub.Copilot.Prerelease
```

### Direct Download

Executables available at: https://github.com/github/copilot-cli/releases/

## Troubleshooting

### "Copilot not found"

Ensure installation path is in `$PATH`:

- Homebrew: `/opt/homebrew/bin` or `/usr/local/bin`
- npm: Global npm bin directory
- Script: `$HOME/.local/bin` or `/usr/local/bin`

### "Not logged in"

```bash
# In interactive mode
/login

# Or set environment variable
export GH_TOKEN="ghp_xxxxxxxxxxxx"
```

### "Tool permission denied"

- Add directory to trusted: `/add-dir /path`
- Or restart with `--allow-all-paths`

### "Context window full"

```bash
/compact    # Summarize and free space
/clear      # Start fresh (loses context)
```

### MCP Server Errors

```bash
/mcp show          # Check status
/mcp edit <name>   # Fix configuration
/mcp disable <name> # Temporarily disable
```
