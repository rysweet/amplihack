# Recipe CLI Quick Reference

One-page cheat sheet for the `amplihack recipe` CLI commands.

## Core Commands

```bash
# List recipes
amplihack recipe list                     # All recipes
amplihack recipe list --long              # With details
amplihack recipe list --format json       # JSON output

# Run recipe
amplihack recipe run <recipe> --context '{"key": "value"}'
amplihack recipe run <recipe> --context-file context.json
amplihack recipe run <recipe> --dry-run   # Preview only

# Validate recipe
amplihack recipe validate <file>          # Check syntax/structure
amplihack recipe validate <file> --strict # Warnings as errors

# Show recipe details
amplihack recipe show <recipe>            # Full details
amplihack recipe show <recipe> --format json
amplihack recipe show <recipe> --steps-only
```

## Common Recipes

| Recipe                  | Steps | Purpose                                 |
| ----------------------- | ----- | --------------------------------------- |
| `default-workflow`      | 22    | Full development (requirements → merge) |
| `quick-fix`             | 4     | Fast bug fixes                          |
| `investigation`         | 6     | Understand existing code                |
| `code-review`           | 5     | Multi-perspective review                |
| `security-audit`        | 7     | Security analysis                       |
| `verification-workflow` | 8     | Post-implementation testing             |

## Context Variables

Pass runtime values via JSON:

```bash
--context '{"task_description": "Add auth", "repo_path": "."}'
--context-file config.json
```

Common variables:

- `task_description` - What to implement (usually required)
- `repo_path` - Repository root (default: `.`)
- `branch_name` - Git branch override
- `pr_number` - Pull request number
- `focus_area` - Directory to analyze

## Run Options

```bash
--dry-run                  # Preview without executing
--adapter <name>           # Force adapter: claude, copilot, cli
--resume-from <step>       # Resume from step ID
--stop-at <step>           # Stop after step ID
--output <file>            # Save execution log
--interactive              # Approve each step
--verbose, -v              # Detailed output
```

## Exit Codes

| Code | Meaning                               |
| ---- | ------------------------------------- |
| 0    | Success                               |
| 1    | Validation failed or recipe not found |
| 2    | Missing context variable              |
| 3    | Step execution failed                 |
| 4    | Agent not found                       |
| 5    | Adapter not available                 |
| 130  | User interrupted (Ctrl+C)             |

## Environment Variables

```bash
export AMPLIHACK_RECIPE_PATH="/custom/recipes:/team/recipes"
export AMPLIHACK_ADAPTER=copilot
export AMPLIHACK_VERBOSE=1
export AMPLIHACK_DRY_RUN=1
```

## Quick Examples

### Development Workflow

```bash
# Full feature implementation
amplihack recipe run default-workflow \
  --context '{"task_description": "Add JWT auth", "repo_path": "."}'

# Fast bug fix
amplihack recipe run quick-fix \
  --context '{"task_description": "Fix null pointer in UserService"}'

# Code investigation
amplihack recipe run investigation \
  --context '{"task_description": "How does auth work?", "focus_area": "src/auth/"}'
```

### Testing & Validation

```bash
# Validate before running
amplihack recipe validate my-recipe.yaml

# Preview execution
amplihack recipe run my-recipe --dry-run \
  --context '{"target": "src/api"}'

# Run verification suite
amplihack recipe run verification-workflow --context '{"repo_path": "."}'
```

### CI/CD Integration

```bash
# Check exit code
amplihack recipe run verification-workflow --context '...'
if [ $? -eq 0 ]; then
  echo "Tests passed"
fi

# Save execution log
amplihack recipe run default-workflow \
  --context '...' \
  --output execution-log.json
```

## Recipe Discovery

Recipes discovered from (in priority order):

1. `amplifier-bundle/recipes/` - Bundled recipes
2. `src/amplihack/amplifier-bundle/recipes/` - Package recipes
3. `~/.amplihack/.claude/recipes/` - User recipes
4. `.claude/recipes/` - Project recipes
5. `$AMPLIHACK_RECIPE_PATH` - Custom paths

Later paths override earlier ones.

## Adapter Selection

Auto-detected based on available CLIs:

1. Claude Agent SDK (if `claude` CLI found)
2. GitHub Copilot SDK (if `copilot` CLI found)
3. CLI subprocess (fallback, always available)

Override with `--adapter <name>`.

## Common Patterns

### Resume after failure

```bash
# Initial run fails at step 15
amplihack recipe run default-workflow --context '...'

# Fix issue, resume from step 15
amplihack recipe run default-workflow --context '...' --resume-from step-15
```

### Partial execution

```bash
# Run only first 5 steps
amplihack recipe run default-workflow --context '...' --stop-at step-5
```

### Interactive approval

```bash
# Approve each step manually
amplihack recipe run security-audit --interactive
```

### Load context from file

```bash
# Create context file
cat > context.json <<EOF
{"task_description": "Add webhooks", "repo_path": "."}
EOF

# Use it
amplihack recipe run default-workflow --context-file context.json
```

### Override context variables

```bash
# Base context + overrides
amplihack recipe run default-workflow \
  --context-file base-context.json \
  --context '{"branch_name": "feat/custom-branch"}'
```

## Troubleshooting

### Recipe not found

```bash
# List available recipes
amplihack recipe list

# Check recipe paths
ls ~/.amplihack/.claude/recipes/*.yaml
ls .claude/recipes/*.yaml
```

### Missing context variable

```bash
# Show required context
amplihack recipe show <recipe>

# Provide all required variables
amplihack recipe run <recipe> --context '{"required_var": "value"}'
```

### Agent not found

```bash
# List available agents
ls ~/.amplihack/.claude/agents/amplihack/*.md

# Fix recipe to use valid agent name
# amplihack:architect (not amplihack:unknown-agent)
```

### Step fails

```bash
# Run with verbose output
amplihack recipe --verbose run <recipe> --context '...'

# Save execution log for debugging
amplihack recipe run <recipe> --context '...' --output debug.json
```

---

**See also**:

- [Recipe CLI Commands How-To](../howto/recipe-cli-commands.md) - Task-oriented usage guide
- [Recipe CLI Reference](../reference/recipe-cli-reference.md) - Complete command documentation
- [Recipe CLI Examples](cli-examples.md) - Real-world scenarios
- [Recipe Runner Overview](README.md) - Architecture and YAML format
