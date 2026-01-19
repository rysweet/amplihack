# Frontmatter Standards

**Version**: 2.0.0
**Status**: Active
**Last Updated**: 2025-11-19

## Purpose

YAML frontmatter provides **machine-readable metadata** for all amplihack extensibility mechanisms. This enables:

1. **Automatic discovery** - Tools can find and catalog all commands, skills, workflows, and subagents
2. **Dependency tracking** - Understand what invokes what and why
3. **Philosophy validation** - Verify alignment with core principles
4. **Version management** - Track breaking changes and compatibility
5. **Auto-documentation** - Generate comprehensive guides from metadata

**Why This Matters**: Frontmatter turns the amplihack ecosystem from scattered files into a queryable, validated, self-documenting system.

## Standards by Component Type

### Commands

**Purpose**: User-invokable entry points via `/command-name`

**Required Fields:**

```yaml
---
name: command-name # Kebab-case, matches /command-name
version: 1.0.0 # Semantic versioning (MAJOR.MINOR.PATCH)
description: One-line summary # Under 80 characters
triggers: # User request patterns
  - "Pattern that suggests this command"
---
```

**Optional Fields:**

```yaml
invokes: # What this command uses
  - type: workflow
    path: .claude/workflow/WORKFLOW_NAME.md
  - type: command
    name: /other-command
  - type: skill
    name: skill-name
  - type: subagent
    path: .claude/agents/amplihack/agent.md
philosophy:
  - principle: Ruthless Simplicity
    application: How command embodies principle
dependencies:
  required:
    - "Tool or file that must exist"
  optional:
    - "Tool or file that enhances functionality"
examples: # Usage examples
  - "/command-name basic usage"
  - "/command-name advanced mode"
```

**Complete Example:**

```yaml
---
name: ultrathink
version: 2.1.0
description: Orchestrates workflow-driven multi-agent execution for complex tasks
triggers:
  - "Non-trivial task requiring planning"
  - "Multi-step feature implementation"
  - "When workflow orchestration needed"
invokes:
  - type: workflow
    path: .claude/workflow/DEFAULT_WORKFLOW.md
  - type: subagent
    path: .claude/agents/amplihack/architect.md
  - type: subagent
    path: .claude/agents/amplihack/builder.md
  - type: command
    name: /fix
philosophy:
  - principle: Trust in Emergence
    application: Complex solutions emerge from simple workflow steps
  - principle: Ruthless Simplicity
    application: Each step is simple, complexity is in composition
dependencies:
  required:
    - ".claude/workflow/DEFAULT_WORKFLOW.md"
  optional:
    - "GitHub CLI (gh) for PR creation"
examples:
  - "/ultrathink Add authentication to API"
  - "/ultrathink Refactor database layer"
---
```

### Skills

**Purpose**: Reusable, token-efficient capabilities loaded on-demand

**Required Fields:**

```yaml
---
name: skill-name # Kebab-case
version: 1.0.0
description: One-line purpose # Under 80 characters
auto_activates: # Patterns triggering auto-load
  - "Pattern for auto-activation"
priority_score: 42.5 # 0-50 scale from evaluation
---
```

**Optional Fields:**

```yaml
evaluation_criteria: # How priority_score calculated
  frequency: HIGH # HIGH|MEDIUM|LOW
  impact: HIGH
  complexity: LOW
  reusability: HIGH
  philosophy_alignment: HIGH
  uniqueness: HIGH
invokes:
  - type: command
    name: /command-name
  - type: skill
    name: other-skill
  - type: subagent
    path: .claude/agents/amplihack/agent.md
dependencies:
  tools: # Claude Code tools needed
    - Read
    - Edit
  external: # External dependencies
    - "GitHub CLI (gh)"
philosophy:
  - principle: Modular Design
    application: Self-contained with clear interface
maturity: production # experimental|production
```

**Complete Example:**

```yaml
---
name: test-gap-analyzer
version: 1.2.0
description: Identifies untested code paths and missing test coverage
auto_activates:
  - "Analyze test coverage"
  - "Find missing tests"
  - "Test gap analysis"
priority_score: 44.5
evaluation_criteria:
  frequency: HIGH
  impact: HIGH
  complexity: MEDIUM
  reusability: HIGH
  philosophy_alignment: HIGH
  uniqueness: MEDIUM
invokes:
  - type: skill
    name: code-smell-detector
  - type: subagent
    path: .claude/agents/amplihack/tester.md
dependencies:
  tools:
    - Read
    - Grep
    - Glob
  external:
    - "pytest (for Python projects)"
philosophy:
  - principle: Zero-BS Implementation
    application: No untested code survives analysis
  - principle: Modular Design
    application: Works with any test framework
maturity: production
---
```

### Workflows

**Purpose**: Multi-step process templates that define execution order

**Required Fields:**

```yaml
---
name: WORKFLOW_NAME # SCREAMING_SNAKE_CASE
version: 1.0.0
description: What this workflow orchestrates
steps: 13 # Total number of steps
---
```

**Optional Fields:**

```yaml
entry_points: # Commands/skills using this workflow
  - /command-name
  - skill-name
phases: # Logical groupings of steps
  - name: Phase Name
    steps: [1, 2, 3]
    description: What this phase accomplishes
references: # What this workflow mentions
  workflows:
    - OTHER_WORKFLOW.md
  commands:
    - /command-name
  skills:
    - skill-name
  subagents:
    - .claude/agents/amplihack/agent.md
philosophy:
  - principle: Trust in Emergence
    application: How workflow enables emergent solutions
customizable: true # Can users modify this workflow?
```

**Complete Example:**

```yaml
---
name: CI_DIAGNOSTIC_WORKFLOW
version: 2.0.0
description: Diagnoses and fixes CI failures until PR is mergeable
steps: 8
entry_points:
  - /fix
  - ci-diagnostic-workflow.md
phases:
  - name: Assessment
    steps: [1, 2]
    description: Understand failure context and CI status
  - name: Diagnosis
    steps: [3, 4]
    description: Identify root causes and affected systems
  - name: Resolution
    steps: [5, 6, 7]
    description: Fix issues and verify resolution
  - name: Completion
    steps: [8]
    description: Update documentation and close loop
references:
  commands:
    - /fix
  subagents:
    - .claude/agents/amplihack/ci-diagnostic-workflow.md
  tools:
    - ".claude/tools/ci_status.py"
philosophy:
  - principle: Ruthless Simplicity
    application: Each step is minimal and focused
  - principle: Trust in Emergence
    application: Complex fixes emerge from simple diagnostics
customizable: false
---
```

### Subagents

**Purpose**: Specialized roles with deep domain expertise and full context

**Required Fields:**

```yaml
---
role: agent-role-name # Kebab-case
purpose: Single responsibility # One clear statement
triggers: # When to use this agent
  - "Situation requiring this agent"
---
```

**Optional Fields:**

```yaml
invokes:
  - type: command
    name: /command-name
  - type: skill
    name: skill-name
  - type: subagent
    path: .claude/agents/amplihack/other-agent.md
boundaries: # What agent does NOT do
  - "Explicitly excluded responsibility"
philosophy:
  - principle: Single Responsibility
    application: How agent maintains focus
dependencies:
  required_context: # Files to import
    - "@.claude/context/PHILOSOPHY.md"
  tools:
    - Read
    - Bash
expertise: # Domain knowledge
  - "Area of deep knowledge"
delegation_pattern: parallel # parallel|sequential|adaptive
```

**Complete Example:**

```yaml
---
role: architect
purpose: Designs system architecture and module specifications
triggers:
  - "Design new feature or system"
  - "Create module specification"
  - "Problem decomposition needed"
invokes:
  - type: skill
    name: module-spec-generator
  - type: subagent
    path: .claude/agents/amplihack/builder.md
  - type: command
    name: /fix
boundaries:
  - "Does not implement code (delegates to builder)"
  - "Does not test implementations (delegates to tester)"
philosophy:
  - principle: Analysis First
    application: Always design before implementation
  - principle: Modular Design
    application: Creates self-contained module specs
dependencies:
  required_context:
    - "@.claude/context/PHILOSOPHY.md"
    - "@.claude/context/PATTERNS.md"
  tools:
    - Read
    - Write
    - Edit
expertise:
  - "System architecture"
  - "Module boundaries"
  - "API design"
  - "Contract definition"
delegation_pattern: sequential
---
```

## Validation Rules

### Version Format

```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes to invocation interface
MINOR: New features, backward-compatible
PATCH: Bug fixes, clarifications
```

### Naming Conventions

- **Commands**: `kebab-case` (file: `kebab-case.md`, invoke: `/kebab-case`)
- **Skills**: `kebab-case` (file: `kebab-case`, invoke: `skill-name`)
- **Workflows**: `SCREAMING_SNAKE_CASE` (file: `WORKFLOW_NAME.md`)
- **Subagents**: `kebab-case` (file: `kebab-case.md`)

### Required Field Validation

```python
# Commands must have
assert frontmatter['name']
assert frontmatter['version']
assert frontmatter['description']
assert frontmatter['triggers']

# Skills must have
assert frontmatter['name']
assert frontmatter['version']
assert frontmatter['description']
assert frontmatter['auto_activates']
assert frontmatter['priority_score']

# Workflows must have
assert frontmatter['name']
assert frontmatter['version']
assert frontmatter['description']
assert frontmatter['steps']

# Subagents must have
assert frontmatter['role']
assert frontmatter['purpose']
assert frontmatter['triggers']
```

### Philosophy Alignment

Every mechanism SHOULD document alignment with at least one core principle:

- Ruthless Simplicity
- Trust in Emergence
- Modular Design
- Zero-BS Implementation
- Analysis First

## Migration Checklist

### For Existing Files Without Frontmatter

1. **Identify file type** (command, skill, workflow, or subagent)
2. **Extract metadata** from content and filename
3. **Add YAML block** at top of file between `---` delimiters
4. **Fill required fields** based on file type
5. **Document invocations** (what does this file call?)
6. **Add philosophy alignment** (how does it embody principles?)
7. **Validate format** (YAML syntax, required fields)
8. **Test invocation** (ensure file still works)

### Example Migration

**Before:**

```markdown
# Ultra Think Command

This command orchestrates workflow-driven execution...
```

**After:**

```markdown
---
name: ultrathink
version: 2.1.0
description: Orchestrates workflow-driven multi-agent execution
triggers:
  - "Complex multi-step tasks"
invokes:
  - type: workflow
    path: .claude/workflow/DEFAULT_WORKFLOW.md
philosophy:
  - principle: Trust in Emergence
    application: Complex solutions from simple steps
---

# Ultra Think Command

This command orchestrates workflow-driven execution...
```

## References

- **Revised Architecture**: `.claude/runtime/logs/session_20251119_024338/REVISED_ARCHITECTURE.md`
- **Claude Code Best Practices**: https://docs.anthropic.com/claude/docs/claude-code
- **Semantic Versioning**: https://semver.org/

---

**Remember**: Frontmatter is MANDATORY for all new mechanisms and should be added to existing files during natural updates.
