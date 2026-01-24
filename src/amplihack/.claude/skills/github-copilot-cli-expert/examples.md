# GitHub Copilot CLI Examples

Practical examples and workflows for GitHub Copilot CLI.

## Local Development Workflows

### Example 1: Code Understanding

**Scenario**: Understand a new codebase

```bash
# Start Copilot in your project
cd /path/to/project
copilot

# Ask about the project
What does this codebase do?

# Explore specific files
Explain @src/main.py

# Understand dependencies
What libraries does this project use and why?

# Find patterns
Show me how authentication is handled in this codebase
```

### Example 2: Bug Fixing

**Scenario**: Debug and fix an issue

```bash
copilot

# Describe the problem
The API returns 500 error when users submit forms with empty fields

# Let Copilot investigate
Show me the form validation logic in @src/api/forms.py

# Get fix suggestions
Fix the validation to properly handle empty fields

# Review the changes before committing
/diff
```

### Example 3: Feature Implementation

**Scenario**: Add a new feature

```bash
copilot

# Describe the feature
Add a rate limiting middleware that limits requests to 100 per minute per IP

# Get implementation plan first
/plan implement rate limiting for the API

# Implement with guidance
Create the rate limiter following the plan

# Test it
Run the tests and show me the results
```

## GitHub Integration Workflows

### Example 4: Creating Pull Requests

**Scenario**: Make changes and create a PR

```bash
copilot

# Make code changes
Add input validation to the user registration endpoint

# Review what changed
/diff

# Create PR directly on GitHub
Create a pull request for these changes with a descriptive title and body
```

**Expected**: Copilot creates a PR on GitHub with you as the author.

### Example 5: Working with Issues

**Scenario**: Address an assigned issue

```bash
copilot

# Start from an issue
I've been assigned issue https://github.com/myorg/myrepo/issues/42
Start working on this in a new branch

# Copilot will:
# 1. Create a branch
# 2. Read the issue
# 3. Start implementing
```

### Example 6: Code Review

**Scenario**: Review a PR for issues

```bash
copilot

# Review a specific PR
Check the changes in PR https://github.com/myorg/myrepo/pull/123
Report any bugs, security issues, or code quality problems

# Get summary of findings
Copilot provides inline analysis of the PR changes
```

### Example 7: Managing PRs

**Scenario**: Merge or close PRs

```bash
copilot

# Merge approved PRs
Merge all approved PRs I've created in myorg/myrepo

# Close a specific PR
Close PR #45 on myorg/myrepo with a comment explaining why
```

## Delegation Workflows

### Example 8: Delegate to Copilot Agent

**Scenario**: Hand off work to run in background on GitHub

```bash
copilot

# Start with some local context
I've been working on the authentication refactor

# Delegate remaining work
/delegate complete the password reset flow and fix the test failures

# Copilot will:
# 1. Create a checkpoint commit
# 2. Push to a new branch
# 3. Open a draft PR
# 4. Run Copilot coding agent in background
# 5. Provide link to PR and agent session
```

### Example 9: Resume Remote Session

**Scenario**: Bring GitHub agent work back locally

```bash
# List available sessions
copilot --resume

# Select the session from the delegation
# Now you can continue the work locally
```

## Custom Agent Workflows

### Example 10: Using Built-in Agents

**Scenario**: Quick codebase exploration

```bash
copilot

# Use explore agent (doesn't add to main context)
Use the explore agent to find all API endpoints in this project

# Use plan agent for complex tasks
Use the plan agent to create an implementation plan for adding OAuth support

# Use code-review agent
Use the code-review agent to review the changes in the staging branch
```

### Example 11: Creating Custom Agents

**Step 1**: Create agent file at `~/.copilot/agents/security-checker.md`:

```markdown
# Security Checker Agent

You are a security-focused code reviewer. When reviewing code:

1. Check for SQL injection vulnerabilities
2. Look for XSS vulnerabilities
3. Identify authentication/authorization issues
4. Flag sensitive data exposure
5. Check for insecure dependencies

Always provide severity ratings (Critical/High/Medium/Low) and
remediation suggestions.
```

**Step 2**: Use the agent:

```bash
copilot --agent=security-checker

Review @src/api/ for security issues
```

### Example 12: Repository-Level Agents

Create `.github/agents/frontend-expert.md` in your repo:

```markdown
# Frontend Expert

You specialize in React and TypeScript development for this project.

Follow these conventions:
- Use functional components with hooks
- Prefer TypeScript strict mode
- Use our component library from @/components
- Follow accessibility best practices
```

Then use it:

```bash
copilot

Use the frontend-expert agent to create a new dashboard component
```

## MCP Server Workflows

### Example 13: Adding MCP Servers

**Add filesystem access to additional directories**:

```bash
copilot

/mcp add

# Fill in:
# Name: my-docs
# Command: npx
# Args: -y @modelcontextprotocol/server-filesystem /path/to/docs

# Press Ctrl+S to save
```

### Example 14: Using GitHub MCP Server

**The GitHub MCP server is included by default**:

```bash
copilot

# Search issues
Use the GitHub MCP server to find good first issues in octocat/hello-world

# List workflow runs
Show me the recent GitHub Actions runs for this repo

# Manage labels
Add the "needs-review" label to issue #42
```

## Programmatic Workflows

### Example 15: CI/CD Integration

**In your GitHub Actions workflow**:

```yaml
- name: Generate Docs
  run: |
    copilot -p "Generate API documentation for src/api/" \
      --allow-tool 'write' \
      --allow-tool 'shell(npm)'
```

### Example 16: Scripted Code Generation

```bash
#!/bin/bash
# generate-tests.sh

copilot -p "Generate unit tests for $1" \
  --allow-tool 'write' \
  --allow-tool 'shell(npm test)'
```

Usage:
```bash
./generate-tests.sh src/utils/validator.ts
```

### Example 17: Batch Operations

```bash
# Fix linting in all files, auto-approve common tools
copilot -p "Fix all ESLint errors in src/" \
  --allow-all-tools \
  --deny-tool 'shell(rm)' \
  --deny-tool 'shell(git push)'
```

## Context Management

### Example 18: Managing Large Sessions

```bash
copilot

# Work on a complex feature...
# (many prompts later)

# Check context usage
/context

# If approaching limit, summarize
/compact

# View session statistics
/usage
```

### Example 19: Session Persistence

```bash
# End session, then later:
copilot --continue  # Resume last session

# Or pick from list
copilot --resume  # Shows all sessions
```

### Example 20: Sharing Sessions

```bash
copilot

# After a productive session, share it:

# Export to file
/share file ./session-notes.md

# Or share as gist
/share gist
```

## GitHub Actions Workflows

### Example 21: Create Workflow

```bash
copilot

Create a GitHub Actions workflow that:
1. Runs on pull requests to main
2. Runs ESLint on changed files
3. Shows errors as PR annotations
4. Fails the check if there are errors
5. Push the workflow file and create a PR
```

### Example 22: Debug Failing Actions

```bash
copilot

The CI pipeline is failing. Check the workflow file at .github/workflows/ci.yml
and the recent run logs to diagnose the issue.

# Copilot can access GitHub Actions data via MCP
```

## Security-Conscious Workflows

### Example 23: Restricted Automation

```bash
# Allow git read-only, deny destructive commands
copilot -p "Analyze the git history and summarize changes" \
  --allow-tool 'shell(git log)' \
  --allow-tool 'shell(git show)' \
  --allow-tool 'shell(git diff)' \
  --deny-tool 'shell(git push)' \
  --deny-tool 'shell(git reset)' \
  --deny-tool 'shell(rm)'
```

### Example 24: Read-Only Analysis

```bash
# Deny all write operations
copilot -p "Audit this codebase for security issues" \
  --deny-tool 'write' \
  --deny-tool 'shell'
```

## Tips & Best Practices

### Effective Prompts

**Good prompts are specific:**
```
# Instead of:
Fix the bug

# Say:
Fix the TypeError in @src/api/users.py line 42 where user.email
is accessed before checking if user exists
```

### Using File References

```bash
# Reference multiple files
Explain the relationship between @src/models/user.py and @src/api/auth.py

# Reference directories
Review all files in @tests/ for test coverage gaps
```

### Iterative Development

```bash
# Build incrementally
Create the data model for a blog post

# Then extend
Add validation to the BlogPost model

# Then integrate
Create an API endpoint to create blog posts

# Review everything
/diff
```

### Working with Large Codebases

```bash
# Use explore agent to keep main context clean
Use explore agent: How is caching implemented?

# Then focus on specific areas
Show me @src/cache/redis.py in detail
```
