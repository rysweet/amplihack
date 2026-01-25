# GitHub Copilot CLI Examples

Practical examples for GitHub Copilot CLI usage.

**Last Updated**: 2026-01-25

---

## Installation Examples

### Fresh Install on macOS

```bash
# Install with Homebrew
brew install copilot-cli

# Verify installation
copilot --version

# Launch and authenticate
copilot
# Follow /login prompt when prompted
```

### Fresh Install on Linux (Ubuntu/Debian)

```bash
# Option 1: Using npm (requires Node.js 22+)
npm install -g @github/copilot

# Option 2: Using install script
curl -fsSL https://gh.io/copilot-install | bash

# Add to PATH if using script (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"

# Launch
copilot
```

### Fresh Install on Windows

```powershell
# Using WinGet
winget install GitHub.Copilot

# Launch in PowerShell
copilot
```

### Update to Latest Version

```bash
# Homebrew
brew upgrade copilot-cli

# npm
npm update -g @github/copilot

# WinGet
winget upgrade GitHub.Copilot

# Verify version
copilot --version
```

### Install Specific Version

```bash
# npm
npm install -g @github/copilot@0.0.394

# Install script
curl -fsSL https://gh.io/copilot-install | VERSION="v0.0.394" bash
```

---

## Authentication Examples

### Browser Authentication (Recommended)

```bash
copilot
# When prompted:
> /login
# Browser opens, complete GitHub OAuth flow
# Return to terminal - authenticated!
```

### PAT Authentication

```bash
# 1. Create PAT at: https://github.com/settings/personal-access-tokens/new
# 2. Add "Copilot Requests" permission
# 3. Set environment variable

# Linux/macOS (add to ~/.bashrc or ~/.zshrc)
export GH_TOKEN=ghp_xxxxxxxxxxxx

# Windows PowerShell
$env:GH_TOKEN = "ghp_xxxxxxxxxxxx"

# Launch - automatically authenticated
copilot
```

---

## Basic Usage Examples

### Ask Questions

```
> What does this codebase do?

> Explain the authentication flow in this project

> How do I run the tests?
```

### Include Files in Context

```
> @src/auth/login.ts Explain this authentication logic

> @package.json What dependencies are outdated?

> @config/database.yml and @src/db/connection.py - are these consistent?
```

### Execute Shell Commands

```
> !git status

> !npm test

> !ls -la src/
```

### Create and Modify Code

```
> Create a new React component for user profile

> Fix the bug in @src/utils/parser.js where empty arrays cause errors

> Add input validation to the signup form
```

---

## Slash Command Examples

### Context Management

```bash
# View current token usage
/context

# Compress conversation to save tokens
/compact

# Clear and start fresh
/clear
```

### Working Directory

```bash
# Show current directory
/cwd

# Change directory
/cd ~/projects/my-app

# Add trusted directory
/add-dir /path/to/external/lib

# List all trusted directories
/list-dirs
```

### Model Selection

```bash
# See available models
/model

# Select specific model
/model claude-sonnet-4.5
/model gpt-5
```

### Session Management

```bash
# View session info
/session

# View checkpoints
/session checkpoints

# View modified files
/session files

# Rename session
/rename "feature-authentication"

# Resume previous session
/resume

# Share session to file
/share file session-log.md

# Share to GitHub Gist
/share gist
```

---

## MCP Server Examples

### View Configured Servers

```bash
/mcp show
```

### Add Filesystem Server

```bash
/mcp add
# Interactive prompts:
# Name: filesystem-server
# Command: npx
# Args: -y @modelcontextprotocol/server-filesystem /path/to/project
# (Tab between fields, Ctrl+S to save)
```

### Add Custom API Server

```bash
/mcp add
# Name: custom-api
# Command: node
# Args: /path/to/my-mcp-server.js
# Environment variables as needed
```

### Manual Configuration

Edit `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@github/mcp-server"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/projects"]
    },
    "database": {
      "command": "node",
      "args": ["/path/to/db-mcp-server.js"],
      "env": {
        "DATABASE_URL": "postgres://localhost:5432/mydb"
      }
    }
  }
}
```

### Manage Servers

```bash
# Disable without removing
/mcp disable database

# Re-enable
/mcp enable database

# Edit configuration
/mcp edit filesystem

# Delete permanently
/mcp delete old-server
```

---

## Skills Examples

### View Available Skills

```bash
/skills list
```

### Create a Simple Skill

Create `.github/skills/my-debugging-skill/SKILL.md`:

````markdown
---
name: my-debugging-skill
description: Debug failing tests with systematic approach. Use when tests fail or debugging is needed.
---

# Test Debugging Skill

## When to Use

Activate when:

- Tests are failing
- Need systematic debugging approach
- Investigating test flakiness

## Debugging Process

1. Run the failing test in isolation
2. Add verbose logging to identify failure point
3. Check test data and fixtures
4. Verify mocking is correct
5. Run with debugger if needed

## Commands

```bash
# Run single test
pytest tests/test_file.py::test_function -v

# With debugger
pytest tests/test_file.py::test_function --pdb
```
````

```

### Create Skill with Scripts

Directory structure:
```

.github/skills/api-testing/
├── SKILL.md
└── scripts/
└── test_api.sh

````

SKILL.md:
```markdown
---
name: api-testing
description: Test REST APIs with curl commands. Use for API testing and validation.
---

# API Testing Skill

## Quick Test

Run `scripts/test_api.sh <endpoint>` for standard API validation.

## Manual Testing

```bash
# GET request
curl -X GET https://api.example.com/resource

# POST with JSON
curl -X POST -H "Content-Type: application/json" \
  -d '{"key": "value"}' https://api.example.com/resource
````

````

### Personal vs Project Skills

```bash
# Project skill (current repo only)
mkdir -p .github/skills/my-skill
# OR
mkdir -p .claude/skills/my-skill

# Personal skill (all projects)
mkdir -p ~/.copilot/skills/my-skill
# OR
mkdir -p ~/.claude/skills/my-skill
````

---

## Custom Agent Examples

### Create a Refactoring Agent

Create `~/.copilot/agents/refactor-agent.md`:

```markdown
# Refactoring Agent

You are a code refactoring specialist. When asked to refactor code:

1. **Analyze First**: Understand current structure before changing
2. **Small Steps**: Make incremental changes, test after each
3. **Preserve Behavior**: Never change functionality during refactoring
4. **Document**: Explain each refactoring decision

## Refactoring Patterns to Apply

- Extract Method: Break up large functions
- Rename: Use intention-revealing names
- Remove Duplication: DRY principle
- Simplify Conditionals: Guard clauses, early returns

## Anti-Patterns to Avoid

- Over-abstraction
- Premature optimization
- Breaking existing tests
```

### Use Custom Agent

```bash
# Interactive selection
/agent
# Select "refactor-agent" from list

# In prompt
Use the refactoring agent to improve the code in @src/utils.js

# Command line
copilot --agent=refactor-agent --prompt "Refactor the authentication module"
```

### Repository-Level Agent

Create `.github/agents/code-reviewer.md`:

```markdown
# Project Code Reviewer

You review code for this specific project. Apply these rules:

1. Check for project coding standards (see CONTRIBUTING.md)
2. Verify test coverage for new code
3. Ensure documentation is updated
4. Check for security vulnerabilities
5. Validate performance considerations
```

---

## Delegation Examples

### Delegate to Copilot Coding Agent

```bash
# Hand off current work to remote agent
/delegate complete the API integration and add tests

# Copilot will:
# 1. Commit unstaged changes
# 2. Create new branch
# 3. Open draft PR
# 4. Copilot coding agent continues work remotely
# 5. Returns link to PR
```

### Resume Delegated Session

```bash
# Launch with resume
copilot --resume

# Select the delegated session
# Continue work locally with full context
```

---

## Workflow Examples

### Feature Development Workflow

```bash
# 1. Start in project directory
cd ~/projects/my-app
copilot

# 2. Understand current state
> What's the structure of this codebase?

# 3. Plan implementation
/plan implement user authentication with JWT

# 4. Begin implementation
> Create the authentication module

# 5. Test
> Run the authentication tests

# 6. Review changes
/diff

# 7. Delegate for PR creation
/delegate create PR with proper description and tests
```

### Debugging Workflow

```bash
# 1. Start in project with failing tests
copilot

# 2. Run tests to see failures
> !npm test

# 3. Investigate
> @tests/auth.test.js Why is this test failing?

# 4. Fix
> Fix the issue in the authentication test

# 5. Verify
> Run the tests again to confirm the fix
```

### Code Review Workflow

```bash
# 1. Use review agent
/review Check the changes in this branch for issues

# 2. Or manually
> Review @src/new-feature.js for bugs, security issues, and best practices

# 3. Apply suggestions
> Apply the suggested improvements
```

---

## Troubleshooting Examples

### Copilot Not Found

```bash
# Check if installed
which copilot

# If not found, check PATH
echo $PATH

# Add to PATH (bash/zsh)
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc
```

### Authentication Issues

```bash
# Clear and re-authenticate
/logout
/login

# Check token (if using PAT)
echo $GH_TOKEN | head -c 10
```

### MCP Server Not Working

```bash
# Check configuration
cat ~/.copilot/mcp-config.json | jq

# Test server manually
npx -y @modelcontextprotocol/server-filesystem $(pwd)

# Check for errors in server logs
/mcp show
```

### Skill Not Activating

```bash
# Verify skill location
ls -la .github/skills/my-skill/SKILL.md
ls -la ~/.copilot/skills/my-skill/SKILL.md

# Reload skills
/skills reload

# Check skill is listed
/skills list

# Verify YAML frontmatter is valid
head -20 .github/skills/my-skill/SKILL.md
```

---

## Integration with amplihack

### Reference amplihack Agents

```bash
> Use the architect agent to design this system

> Apply the reviewer agent's checklist to this code

> Reference the builder agent's patterns for implementation
```

### Use amplihack Skills

```bash
/skills list
# Shows all amplihack skills available

> Use the code-smell-detector skill on @src/
```

### Follow amplihack Workflows

```bash
> Follow the DEFAULT_WORKFLOW for implementing this feature

> Use the investigation workflow to understand this codebase
```

---

**Maintainer**: amplihack framework
**Last Review**: 2026-01-25
