# Troubleshooting Guide: Copilot CLI with amplihack

Solutions to common issues when using GitHub Copilot CLI with amplihack.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Agent Problems](#agent-problems)
- [Context Issues](#context-issues)
- [Performance Problems](#performance-problems)
- [Integration Issues](#integration-issues)
- [Error Messages](#error-messages)
- [Debug Techniques](#debug-techniques)

## Installation Issues

### Copilot CLI Not Found

**Symptom:**

```bash
$ copilot --version
command not found: copilot
```

**Solution:**

```bash
# Install Copilot CLI
npm install -g @github/copilot

# Verify installation
copilot --version

# If still not found, check npm global bin path
npm config get prefix

# Add to PATH if needed
export PATH="$PATH:$(npm config get prefix)/bin"
```

### Authentication Failed

**Symptom:**

```
Error: Authentication required
```

**Solution:**

```bash
# Authenticate with GitHub
gh auth login

# Verify authentication
gh auth status

# If Copilot not enabled, check subscription
# Visit: https://github.com/settings/copilot
```

### amplihack Not Found

**Symptom:**

```bash
$ amplihack --version
command not found: amplihack
```

**Solution:**

```bash
# Install amplihack
pip install git+https://github.com/rysweet/amplihack

# Or use uvx
uvx --from git+https://github.com/rysweet/amplihack amplihack --version

# Verify installation
amplihack --version
```

### Permission Denied

**Symptom:**

```
Error: EACCES: permission denied
```

**Solution:**

```bash
# Fix npm permissions (preferred method)
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Reinstall Copilot CLI
npm install -g @github/copilot
```

## Agent Problems

### Agents Not Available

**Symptom:**

```
> @architect: Design module
Error: Agent not found
```

**Solution:**

```bash
# Check if agents converted
ls .github/agents/

# If empty, convert agents
cd /path/to/project
amplihack convert-agents

# Verify conversion
cat .github/agents/REGISTRY.json
```

### Agent Responses Generic

**Symptom:**

Agent provides generic responses without amplihack context.

**Solution:**

Provide explicit context in prompts:

```markdown
❌ @architect: Design auth module

✓  Following amplihack brick philosophy, @architect: Design authentication
   module with clear public API, single responsibility, and zero-BS
   implementation. Reference PATTERNS.md for appropriate patterns.
```

### Agent Conversion Failed

**Symptom:**

```
Error: Agent validation failed
```

**Solution:**

```bash
# Check agent frontmatter
cat .claude/agents/core/architect.md

# Validate agent has required fields:
# - name
# - description

# Fix agent, then retry conversion
amplihack convert-agents --force
```

### Wrong Agent Invoked

**Symptom:**

Wrong agent responds or generic response provided.

**Solution:**

Use exact agent names from registry:

```bash
# Check available agents
cat .github/agents/REGISTRY.json | grep -A 2 '"name"'

# Use exact name
> @architect: [task]  # Not @architecture or @design
```

## Context Issues

### Philosophy Not Referenced

**Symptom:**

Copilot doesn't reference amplihack philosophy in responses.

**Solution:**

```bash
# Verify copilot-instructions.md exists
cat .github/copilot-instructions.md

# If missing, regenerate
amplihack init --force

# Explicitly reference in prompts
> Following amplihack philosophy from PHILOSOPHY.md, [task]
```

### Patterns Not Applied

**Symptom:**

Copilot doesn't use amplihack patterns.

**Solution:**

```bash
# Verify PATTERNS.md accessible
cat .claude/context/PATTERNS.md

# Explicitly reference patterns
> Using the Safe Subprocess Wrapper pattern from PATTERNS.md, [task]

# Or ask for pattern recommendation
> Which amplihack pattern should I use for [problem]?
```

### Context Window Exceeded

**Symptom:**

```
Error: Context length exceeded
```

**Solution:**

```markdown
# Break large requests into smaller parts
❌ > Analyze entire codebase and refactor everything

✓  > @analyzer: Analyze src/auth/ module structure
   [Then in follow-up]
   > @cleanup: Simplify the authentication function
```

### Project Context Missing

**Symptom:**

Copilot doesn't know about yer project structure.

**Solution:**

```bash
# Initialize amplihack in project
cd /path/to/project
amplihack init

# Launch with directory access
copilot --allow-all-tools --add-dir /path/to/project

# Or use amplihack launcher
amplihack copilot
```

## Performance Problems

### Slow Response Times

**Symptom:**

Copilot takes a long time to respond.

**Causes & Solutions:**

#### Too Much Context

```markdown
# Reduce context scope
❌ > Analyze this 10k line file

✓  > @analyzer: Analyze the authenticate() function (lines 150-200)
```

#### Complex Request

```markdown
# Break into steps
❌ > Design, implement, test, and deploy authentication

✓  Step 1: @architect: Design authentication module
   Step 2: @builder: Implement from spec
   Step 3: @tester: Generate tests
```

#### Network Issues

```bash
# Check connection
ping api.github.com

# Check GitHub status
curl https://www.githubstatus.com/api/v2/status.json
```

### High Token Usage

**Symptom:**

Hitting token limits quickly.

**Solution:**

```markdown
# Be specific and concise
❌ > Tell me everything about authentication and how to implement it
    with all possible features and security measures

✓  > @architect: Design basic JWT authentication for REST API

# Use summaries
> Summarize the key points from our discussion
```

### Memory Issues

**Symptom:**

Copilot forgets earlier conversation context.

**Solution:**

```markdown
# Reference previous decisions explicitly
> Earlier you recommended the Safe Subprocess Wrapper pattern.
  Apply that to this git command handling.

# Save important context to files
> Save this architecture decision to docs/ARCHITECTURE.md
```

## Integration Issues

### Git Commands Not Working

**Symptom:**

```
> Use git to create branch
Error: git not found
```

**Solution:**

```bash
# Verify git installed
git --version

# If missing, install git
# macOS: brew install git
# Ubuntu: sudo apt install git
# Windows: Download from git-scm.com

# Launch Copilot with tool access
copilot --allow-all-tools
```

### Python Tools Not Accessible

**Symptom:**

```
> Run amplihack analyze
Error: command not found
```

**Solution:**

```bash
# Verify amplihack installed
amplihack --version

# Add to PATH if needed
which amplihack

# Use full path if necessary
/path/to/python/bin/amplihack analyze ./src
```

### MCP Servers Not Available

**Symptom:**

MCP tools not accessible in Copilot CLI.

**Solution:**

```markdown
Note: MCP server support in Copilot CLI is limited compared to Claude Code.

# Workaround: Use direct commands
❌ > Use MCP file system tools

✓  > Use standard file commands: ls, cat, find
```

### GitHub CLI Not Working

**Symptom:**

```
> Create GitHub issue
Error: gh not found
```

**Solution:**

```bash
# Install GitHub CLI
# macOS: brew install gh
# Ubuntu: (see https://github.com/cli/cli/blob/trunk/docs/install_linux.md)
# Windows: winget install --id GitHub.cli

# Authenticate
gh auth login

# Verify
gh auth status
```

## Error Messages

### "Agent validation failed"

**Cause:** Agent frontmatter missing required fields.

**Solution:**

```bash
# Check agent structure
cat .claude/agents/core/architect.md

# Required fields in frontmatter:
---
name: architect
description: Design systems and decompose problems
---

# Fix and reconvert
amplihack convert-agents --force
```

### "Target exists (use --force to overwrite)"

**Cause:** Converted agents already exist.

**Solution:**

```bash
# Overwrite existing agents
amplihack convert-agents --force

# Or manually remove and reconvert
rm -rf .github/agents/
amplihack convert-agents
```

### "Source directory not found"

**Cause:** `.claude/agents/` directory missing.

**Solution:**

```bash
# Initialize amplihack
amplihack init

# Verify directory created
ls .claude/agents/
```

### "Missing required GitHub configuration"

**Cause:** GitHub authentication not configured.

**Solution:**

```bash
# Authenticate with GitHub
gh auth login

# Verify Copilot access
gh copilot --version
```

### "Command not found"

**Cause:** Command not in PATH or not installed.

**Solution:**

```bash
# Check what's missing
which copilot
which amplihack
which gh

# Install missing components
npm install -g @github/copilot  # Copilot CLI
pip install git+https://github.com/rysweet/amplihack  # amplihack
brew install gh  # GitHub CLI (macOS)
```

## Debug Techniques

### Enable Debug Logging

```bash
# Set debug environment variables
export DEBUG=*
export LOG_LEVEL=DEBUG

# Launch Copilot
copilot --allow-all-tools
```

### Verify Installation

```bash
# Check all components
echo "=== Node.js ==="
node --version

echo "=== npm ==="
npm --version

echo "=== Copilot CLI ==="
copilot --version

echo "=== amplihack ==="
amplihack --version

echo "=== GitHub CLI ==="
gh --version

echo "=== Git ==="
git --version

echo "=== Python ==="
python --version
```

### Test Agent Conversion

```bash
# Dry run to see what would be converted
amplihack convert-agents --dry-run

# Convert and check output
amplihack convert-agents --force

# Verify registry
cat .github/agents/REGISTRY.json

# Check specific agent
cat .github/agents/core/architect.md
```

### Validate Context Files

```bash
# Check all context files exist
ls .claude/context/

# Verify key files
cat .claude/context/PHILOSOPHY.md | head -20
cat .claude/context/PATTERNS.md | head -20
cat .claude/context/TRUST.md | head -20

# Check Copilot instructions
cat .github/copilot-instructions.md | head -50
```

### Test Agent Invocation

In Copilot CLI session:

```
> List available amplihack agents

> What is the amplihack philosophy?

> Show me amplihack patterns

> @architect: Design a simple caching module
  (Test actual agent invocation)
```

### Check File Permissions

```bash
# Verify read permissions on context files
ls -la .claude/context/
ls -la .github/copilot-instructions.md

# Fix permissions if needed
chmod -R u+r .claude/
chmod u+r .github/copilot-instructions.md
```

### Diagnose Context Issues

```markdown
In Copilot CLI session:

> Can you see the file .claude/context/PHILOSOPHY.md?
  (Test file access)

> What are the three core amplihack principles?
  (Test context understanding)

> Which agent should I use for architecture design?
  (Test agent awareness)
```

### Network Diagnostics

```bash
# Check GitHub connectivity
ping api.github.com

# Check npm registry
npm ping

# Check GitHub status
curl https://www.githubstatus.com/api/v2/status.json
```

### Clear Caches

```bash
# Clear npm cache
npm cache clean --force

# Clear pip cache
pip cache purge

# Reinstall
npm install -g @github/copilot
pip install --force-reinstall git+https://github.com/rysweet/amplihack
```

## Getting More Help

### Documentation

- [Getting Started Guide](./GETTING_STARTED.md)
- [Complete User Guide](./USER_GUIDE.md)
- [Migration Guide](./MIGRATION_FROM_CLAUDE.md)
- [FAQ](./FAQ.md)
- [API Reference](./API_REFERENCE.md)

### Community Support

- **GitHub Discussions:** https://github.com/rysweet/amplihack/discussions
- **Issue Tracker:** https://github.com/rysweet/amplihack/issues
- **Documentation:** https://rysweet.github.io/amplihack/

### Reporting Bugs

When reporting issues, include:

```markdown
**Environment:**
- OS: [macOS/Linux/Windows]
- Node.js version: [output of `node --version`]
- Copilot CLI version: [output of `copilot --version`]
- amplihack version: [output of `amplihack --version`]

**Problem:**
[Clear description of the issue]

**Steps to Reproduce:**
1. [First step]
2. [Second step]
3. [...]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happens]

**Error Messages:**
```
[Paste complete error output]
```

**Additional Context:**
[Any other relevant information]
```

### Emergency Fixes

#### Complete Reinstall

```bash
# Remove everything
npm uninstall -g @github/copilot
pip uninstall amplihack
rm -rf .github/agents/

# Reinstall
npm install -g @github/copilot
pip install git+https://github.com/rysweet/amplihack

# Reinitialize
amplihack init
amplihack convert-agents

# Test
copilot --version
amplihack --version
```

#### Reset Configuration

```bash
# Backup existing config
cp .github/copilot-instructions.md .github/copilot-instructions.md.bak

# Reinitialize
amplihack init --force

# Test
cat .github/copilot-instructions.md
```

## Preventive Measures

### Regular Maintenance

```bash
# Weekly: Update Copilot CLI
npm update -g @github/copilot

# Monthly: Update amplihack
pip install --upgrade git+https://github.com/rysweet/amplihack

# After updating agents, reconvert
amplihack convert-agents --force
```

### Best Practices

1. **Always provide context** - Reference philosophy and patterns explicitly
2. **Test agents after conversion** - Verify behavior after converting
3. **Keep documentation updated** - Update custom agents when changing
4. **Use version control** - Commit `.github/agents/` changes
5. **Monitor token usage** - Break large tasks into smaller requests

### Health Check Script

Create `check-amplihack.sh`:

```bash
#!/bin/bash
echo "=== amplihack Health Check ==="

echo "✓ Checking Copilot CLI..."
copilot --version || echo "❌ Copilot CLI not found"

echo "✓ Checking amplihack..."
amplihack --version || echo "❌ amplihack not found"

echo "✓ Checking agents..."
[ -d ".github/agents" ] && echo "✓ Agents directory exists" || echo "❌ Agents missing"

echo "✓ Checking context..."
[ -f ".claude/context/PHILOSOPHY.md" ] && echo "✓ Philosophy exists" || echo "❌ Philosophy missing"

echo "✓ Checking instructions..."
[ -f ".github/copilot-instructions.md" ] && echo "✓ Instructions exist" || echo "❌ Instructions missing"

echo "=== Health Check Complete ==="
```

Run periodically:

```bash
chmod +x check-amplihack.sh
./check-amplihack.sh
```

## Remember

Most issues come from:

1. **Missing context** - Provide explicit references
2. **Wrong agent names** - Check REGISTRY.json for exact names
3. **Unconverted agents** - Run `amplihack convert-agents`
4. **Path issues** - Ensure tools are in PATH
5. **Authentication** - Verify GitHub authentication

When in doubt, start with the basics: verify installation, check context files, test with simple agents.

Still having trouble? Open an issue with full diagnostic output!
