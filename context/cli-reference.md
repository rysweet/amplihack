# Amplihack CLI Reference

This reference covers using Amplifier with the amplihack bundle for systematic AI-powered development.

## Quick Start

```bash
# Install amplifier (if not already)
uv tool install git+https://github.com/microsoft/amplifier

# Run with amplihack bundle
amplifier run --bundle amplihack "your task here"
```

## Core Commands

### Interactive Session

```bash
# Start interactive session with amplihack
amplifier run --bundle amplihack

# With specific provider
amplifier run --bundle amplihack --provider anthropic

# With custom model
amplifier run --bundle amplihack --model claude-sonnet-4-20250514
```

### Auto Mode (Autonomous Execution)

```bash
# Run autonomously with turn limit
amplifier run --bundle amplihack --max-turns 20 "Implement the feature"

# With timeout
amplifier run --bundle amplihack --timeout 1h "Complete the audit"
```

### Recipe Execution

```bash
# Run a workflow recipe
amplifier tool invoke recipes \
  operation=execute \
  recipe_path=amplihack:recipes/default-workflow.yaml \
  context='{"task": "Build authentication module"}'

# List available recipes
ls $(amplifier bundle path amplihack)/recipes/

# Validate a recipe
amplifier tool invoke recipes operation=validate recipe_path=amplihack:recipes/my-recipe.yaml
```

### Session Management

```bash
# List recent sessions
amplifier sessions

# Resume a session
amplifier resume <session-id>

# View session logs
amplifier logs <session-id>

# Export session transcript
amplifier session export <session-id> --format markdown
```

## Workflow Commands

### UltraThink Mode

Within a session, trigger deep analysis:

```
/ultrathink Analyze the authentication architecture
```

Or as initial prompt:

```bash
amplifier run --bundle amplihack "/ultrathink Design the caching layer"
```

### Workflow Selection

The bundle automatically selects appropriate workflows:

- **Simple tasks** → Default workflow (lightweight)
- **Investigations** → Investigation workflow (6 phases)
- **Decisions** → Debate workflow (multi-perspective)
- **Critical code** → N-version workflow (multiple implementations)

Override with explicit selection:

```
/workflow debate "Should we use microservices or monolith?"
```

### Goal Agent Generation

Create specialized agents for complex objectives:

```bash
# Via tool invocation
amplifier tool invoke goal-agent-generator \
  goal="Create automated security scanner" \
  name="security-scanner-agent" \
  output_path="./agents"
```

## Skill Loading

Load skills for specialized knowledge:

```bash
# Within session - load a skill
@amplihack:skills/azure-devops/SKILL.md

# Load multiple related skills
@amplihack:skills/development/SKILL.md
@amplihack:skills/testing/SKILL.md
```

## Agent Delegation

Delegate to specialized agents:

```
# Spawn architect for design
[task agent=amplihack:architect prompt="Design the API structure"]

# Spawn security for audit
[task agent=amplihack:security prompt="Review auth implementation"]

# Spawn tester for coverage
[task agent=amplihack:tester prompt="Create test plan for user module"]
```

## Configuration

### Bundle Override

Create local customizations:

```bash
# Create local AGENTS.md
echo "# Local Overrides
- Prefer TypeScript over JavaScript
- Always use PostgreSQL for databases
" > .amplifier/AGENTS.md
```

### Provider Configuration

```bash
# Set API key
export ANTHROPIC_API_KEY=your-key

# Or via settings
amplifier config set providers.anthropic.api_key your-key
```

### Model Selection

```bash
# Use specific model
amplifier run --model claude-sonnet-4-20250514

# Or configure default
amplifier config set providers.anthropic.default_model claude-sonnet-4-20250514
```

## Common Patterns

### Feature Development

```bash
amplifier run --bundle amplihack --max-turns 25 "
Implement user profile management:
- CRUD operations for profiles
- Avatar upload to blob storage
- Profile privacy settings
- Tests for all endpoints
"
```

### Bug Investigation

```bash
amplifier run --bundle amplihack "
/workflow investigation
Bug: Users intermittently get 500 errors on checkout
Symptoms: Happens ~5% of the time, no pattern in logs
"
```

### Code Review

```bash
amplifier run --bundle amplihack "
Review PR #142 for:
- Security vulnerabilities
- Philosophy compliance (ruthless simplicity)
- Test coverage gaps
- Performance issues
"
```

### Architecture Decision

```bash
amplifier run --bundle amplihack "
/workflow debate
Decision: Choose between REST and GraphQL for our public API
Constraints: Must support mobile clients, need good caching
"
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API authentication |
| `AMPLIFIER_LOG_LEVEL` | Logging verbosity (DEBUG, INFO, WARN, ERROR) |
| `AMPLIFIER_SESSION_DIR` | Custom session storage location |
| `AMPLIFIER_MAX_TURNS` | Default max turns for auto mode |

## Troubleshooting

### Common Issues

**Session won't start:**
```bash
# Check provider configuration
amplifier config list

# Verify API key
echo $ANTHROPIC_API_KEY
```

**Recipe execution fails:**
```bash
# Validate recipe first
amplifier tool invoke recipes operation=validate recipe_path=your-recipe.yaml

# Check recipe syntax
cat your-recipe.yaml | yq .
```

**Bundle not found:**
```bash
# List installed bundles
amplifier bundle list

# Install amplihack bundle
amplifier bundle install git+https://github.com/your-org/amplifier-amplihack
```

### Getting Help

```bash
# General help
amplifier --help

# Command-specific help
amplifier run --help
amplifier tool --help

# Within session
/help
```
