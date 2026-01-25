# GitHub CLI Skill

This skill provides expert guidance for using the GitHub CLI (`gh`) as a lightweight alternative to the GitHub MCP server.

## Why This Skill Exists

The GitHub MCP server consumes significant context tokens. For most GitHub operations, the `gh` CLI is more efficient and provides the same functionality with less overhead.

## Features

- **Progressive Disclosure**: Common commands first, advanced features on demand
- **Pattern-Based Guidance**: Real workflow examples (issue→PR, code review, CI debugging)
- **MCP Re-enable Option**: Instructions to restore GitHub MCP if needed

## Prerequisites

```bash
# Install gh CLI
brew install gh          # macOS
sudo apt install gh      # Ubuntu/Debian
winget install GitHub.cli  # Windows

# Authenticate
gh auth login
```

## Usage

The skill auto-activates when you mention:
- GitHub issues, PRs, repos
- `gh` CLI commands
- GitHub Actions/workflows
- GitHub API operations

## When to Use GitHub MCP Instead

The GitHub MCP server may be better for:
- Complex multi-step GitHub operations
- Bulk operations across many repositories
- Advanced GraphQL queries requiring state
- Operations the `gh` CLI doesn't support

To re-enable, ask: "Please use the GitHub MCP server"
