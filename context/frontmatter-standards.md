# Frontmatter Standards

YAML frontmatter specifications for Amplifier artifacts: commands, skills, workflows, agents, and recipes.

---

## General Rules

1. **Required fields must always be present** - Missing required fields cause load failures
2. **Use lowercase keys** - `name:` not `Name:`
3. **Quote strings with special characters** - Especially `:`, `#`, `[`, `]`, `{`, `}`
4. **Validate before committing** - Use `amplifier validate [path]`

---

## Commands

Commands are simple automations triggered by user input.

```yaml
---
# REQUIRED
name: command-name              # Unique identifier (kebab-case)
description: Brief description  # One line, shown in help

# OPTIONAL  
aliases:                        # Alternative names
  - cmd
  - c
args:                          # Positional arguments
  - name: target
    description: Target file or directory
    required: true
  - name: format
    description: Output format
    required: false
    default: json
options:                       # Named options (--flag)
  - name: verbose
    short: v                   # Single character shortcut
    description: Enable verbose output
    type: boolean
    default: false
  - name: output
    short: o
    description: Output file path
    type: string
tags:                          # For organization/filtering
  - utility
  - file-operations
---
```

### Command Example

```yaml
---
name: format-code
description: Format code files using project formatters
aliases: [fmt, f]
args:
  - name: paths
    description: Files or directories to format
    required: false
    default: "."
options:
  - name: check
    short: c
    description: Check formatting without changing files
    type: boolean
    default: false
  - name: diff
    short: d
    description: Show diff of changes
    type: boolean
    default: false
tags: [code-quality, formatting]
---
```

---

## Skills

Skills are knowledge modules loaded into agent context.

```yaml
---
# REQUIRED
name: skill-name               # Unique identifier (kebab-case)
description: What this skill provides
version: "1.0.0"               # Semantic version

# OPTIONAL
author: Author Name
license: MIT                   # SPDX identifier
tags:
  - category
  - subcategory
requires:                      # Other skills this depends on
  - base-skill
provides:                      # Capabilities this skill enables
  - capability-name
context_files:                 # Additional files to load
  - patterns.md
  - examples/
---
```

### Skill Example

```yaml
---
name: python-async
description: Best practices for async Python development
version: "2.1.0"
author: Amplihack Team
license: MIT
tags: [python, async, concurrency]
requires:
  - python-basics
provides:
  - asyncio-patterns
  - concurrent-programming
  - async-testing
context_files:
  - async-patterns.md
  - common-pitfalls.md
  - examples/
---
```

---

## Workflows

Workflows define multi-step processes for agents to follow.

```yaml
---
# REQUIRED
name: workflow-name            # Unique identifier (kebab-case)
description: What this workflow accomplishes
version: "1.0.0"

# OPTIONAL
trigger:                       # When to auto-activate
  keywords:                    # Keywords in user request
    - implement
    - build
    - create
  file_patterns:              # File types involved
    - "*.py"
    - "*.ts"
priority: 100                  # Higher = preferred when multiple match
agents:                        # Agents this workflow uses
  - foundation:modular-builder
  - amplihack:reviewer
tags:
  - development
  - implementation
---
```

### Workflow Example

```yaml
---
name: feature-development
description: Complete workflow for implementing new features
version: "1.2.0"
trigger:
  keywords:
    - implement
    - add feature
    - build
    - create
  file_patterns:
    - "*.py"
    - "*.ts"
    - "*.go"
priority: 100
agents:
  - foundation:zen-architect
  - foundation:modular-builder
  - amplihack:reviewer
  - amplihack:tester
tags: [development, features]
---
```

---

## Agents

Agents are specialized AI assistants with specific capabilities.

```yaml
---
# REQUIRED
name: agent-name               # Unique identifier (kebab-case)
description: What this agent specializes in
version: "1.0.0"

# OPTIONAL
model: claude-sonnet-4-20250514          # Model to use (default: claude-sonnet-4-20250514)
temperature: 0.1               # Creativity (0-1, default: 0.1 for code)
max_tokens: 4096              # Response limit

capabilities:                  # What this agent can do
  - code-review
  - security-analysis
tools:                        # Tools this agent can use
  - read_file
  - write_file
  - bash
  - grep
context:                      # Files always loaded for this agent
  - context/philosophy.md
  - context/patterns.md
delegation:                   # Agents this can delegate to
  - foundation:git-ops
  - amplihack:tester
tags:
  - review
  - security
---
```

### Agent Example

```yaml
---
name: security-reviewer
description: Specialized agent for security code review
version: "1.3.0"
model: claude-sonnet-4-20250514
temperature: 0.0
max_tokens: 8192
capabilities:
  - security-analysis
  - vulnerability-detection
  - dependency-audit
  - secrets-scanning
tools:
  - read_file
  - grep
  - bash
  - web_search
context:
  - context/security-patterns.md
  - context/owasp-top-10.md
delegation:
  - foundation:explorer
tags: [security, review, audit]
---
```

---

## Recipes

Recipes are declarative multi-step workflows executed by the recipe engine.

```yaml
---
# REQUIRED
name: recipe-name              # Unique identifier (kebab-case)
description: What this recipe accomplishes
version: "1.0.0"

# OPTIONAL
author: Author Name
tags:
  - category
inputs:                        # Required inputs from user
  - name: target_path
    description: Path to operate on
    required: true
  - name: dry_run
    description: Preview without changes
    required: false
    default: false
outputs:                       # What recipe produces
  - name: result
    description: Operation result
  - name: report
    description: Detailed report path
timeout: 300                   # Max execution time in seconds
retry:                        # Retry configuration
  max_attempts: 3
  backoff: exponential
---
```

### Recipe Example

```yaml
---
name: code-review-pipeline
description: Comprehensive code review with multiple specialized agents
version: "2.0.0"
author: Amplihack Team
tags: [review, quality, pipeline]
inputs:
  - name: file_paths
    description: Files to review (glob patterns supported)
    required: true
  - name: focus_areas
    description: Areas to focus on (security, performance, style)
    required: false
    default: [security, performance, style]
  - name: severity_threshold
    description: Minimum severity to report
    required: false
    default: warning
outputs:
  - name: issues
    description: List of issues found
  - name: summary
    description: Executive summary
  - name: report_path
    description: Full report location
timeout: 600
retry:
  max_attempts: 2
  backoff: linear
---
```

---

## Validation Rules

### Name Validation

```yaml
# VALID names
name: my-agent
name: code-review-v2
name: python-async-patterns

# INVALID names
name: My Agent          # No spaces
name: code_review       # Use kebab-case
name: CodeReview        # Use kebab-case
name: 2nd-agent         # Don't start with number
```

### Version Validation

```yaml
# VALID versions (semver)
version: "1.0.0"
version: "2.1.3"
version: "0.1.0-beta"
version: "1.0.0-rc.1"

# INVALID versions
version: 1.0            # Must be string, needs patch
version: v1.0.0         # No 'v' prefix
version: "1"            # Need major.minor.patch
```

### Description Guidelines

```yaml
# GOOD descriptions
description: Format Python code using ruff with project settings
description: Security-focused code review for OWASP Top 10 vulnerabilities
description: Multi-agent workflow for feature implementation

# BAD descriptions
description: Does stuff              # Too vague
description: This agent is really... # Too long, be concise
description: ""                      # Empty not allowed
```

---

## Quick Reference

| Artifact | Required Fields | Key Optional Fields |
|----------|-----------------|---------------------|
| Command | name, description | aliases, args, options |
| Skill | name, description, version | requires, provides, context_files |
| Workflow | name, description, version | trigger, agents, priority |
| Agent | name, description, version | capabilities, tools, context |
| Recipe | name, description, version | inputs, outputs, timeout |

---

## Template Files

Use these as starting points:

```bash
# Create from templates
cp templates/command.yaml commands/my-command.yaml
cp templates/skill.yaml skills/my-skill/skill.yaml
cp templates/agent.yaml agents/my-agent.yaml
cp templates/recipe.yaml recipes/my-recipe.yaml
```
