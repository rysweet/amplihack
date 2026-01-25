# How to Verify .claude/ Staging

Quick guide to verify that amplihack properly staged agents, skills, and tools to `~/.amplihack/.claude/`.

## When You Need This

- After running any amplihack command for the first time
- When agents/skills aren't working as expected
- After upgrading amplihack package

## Verify Staging Worked

Check that the directory exists and contains expected files:

```bash
# Check directory exists
ls -la ~/.amplihack/.claude/

# Verify agents are staged
ls ~/.amplihack/.claude/agents/amplihack/core/
# Expected: architect.md, builder.md, reviewer.md, tester.md

# Verify skills are staged
ls ~/.amplihack/.claude/skills/
# Expected: documentation-writing, mermaid-diagram-generator, test-gap-analyzer, etc.

# Verify tools are staged
ls ~/.amplihack/.claude/tools/
# Expected: github_issue.py, ci_status.py, etc.
```

## Expected Output

After running `amplihack copilot` (or any command), you should see:

```
Staging amplihack to ~/.amplihack/.claude/...
✓ Agents staged (38 agents)
✓ Skills staged (73 skills)
✓ Tools staged (24 commands)
✓ Hooks staged
```

## Quick Test

Test that an agent works:

```bash
# With amplihack copilot
gh copilot explain --agent architect "design a simple REST API"

# With amplihack amplifier
amplifier --agent architect "design a simple REST API"

# With amplihack rustyclawd
rustyclawd --agent architect "design a simple REST API"
```

If the agent responds with design guidance, staging worked correctly.

## Troubleshooting

### Directory Missing

If `~/.amplihack/.claude/` doesn't exist:

```bash
# Run any amplihack command - staging happens automatically
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot

# Staging runs before the command launches
```

### Old/Stale Files

If you upgraded amplihack but still see old behavior:

```bash
# Remove old staged files
rm -rf ~/.amplihack/.claude/

# Re-run command - will re-stage automatically
uvx --from git+https://github.com/rysweet/amplihack amplihack copilot
```

### Permission Errors

If staging fails with permission errors:

```bash
# Check directory ownership
ls -la ~/.amplihack/

# Fix permissions if needed
chmod -R u+w ~/.amplihack/
```

## What Gets Staged

The staging process copies:

- **Agents** (38): `~/.amplihack/.claude/agents/`
- **Skills** (73): `~/.amplihack/.claude/skills/`
- **Commands** (24): `~/.amplihack/.claude/commands/`
- **Tools**: `~/.amplihack/.claude/tools/`
- **Hooks**: `~/.amplihack/.claude/hooks/`
- **Context**: `~/.amplihack/.claude/context/`
- **Workflows**: `~/.amplihack/.claude/workflow/`

## Related

- [Unified Staging Architecture](../concepts/unified-staging-architecture.md) - Why this approach
- [Staging API Reference](../reference/staging-api.md) - Developer details
- [Prerequisites](../PREREQUISITES.md) - System requirements
