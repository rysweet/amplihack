---
# REQUIRED FIELDS - Fill these in for every skill

name: [FILL: skill-name]                # Kebab-case (e.g., test-gap-analyzer, decision-logger)
version: 1.0.0                          # Semantic versioning (MAJOR.MINOR.PATCH)
description: [FILL: One-line purpose under 80 characters]
auto_activates:                         # Patterns that trigger automatic skill loading
  - "[FILL: Pattern 1 - e.g., 'Analyze test coverage']"
  - "[FILL: Pattern 2 - e.g., 'Find missing tests']"
  - "[FILL: Pattern 3 - e.g., 'Test gap analysis']"
priority_score: [FILL: 0-50]            # Score from evaluation (see criteria below)

# OPTIONAL FIELDS - Include based on skill complexity

evaluation_criteria:                    # How priority_score was calculated
  frequency: [FILL: HIGH|MEDIUM|LOW]    # How often is this skill needed?
  impact: [FILL: HIGH|MEDIUM|LOW]       # How valuable is this skill?
  complexity: [FILL: HIGH|MEDIUM|LOW]   # How complex is the skill? (LOW is better)
  reusability: [FILL: HIGH|MEDIUM|LOW]  # Can it be used in many contexts?
  philosophy_alignment: [FILL: HIGH|MEDIUM|LOW]  # Follows amplihack principles?
  uniqueness: [FILL: HIGH|MEDIUM|LOW]   # Does something other tools don't?

invokes:                                # What this skill uses internally
  - type: command
    name: [FILL: /command-name]
  - type: skill
    name: [FILL: other-skill-name]
  - type: subagent
    path: [FILL: .claude/agents/amplihack/agent-name.md]

dependencies:                           # Required tools and external dependencies
  tools:                                # Claude Code tools needed
    - [FILL: Read]
    - [FILL: Edit]
    - [FILL: Write]
    - [FILL: Grep]
    - [FILL: Bash]
  external:                             # External CLI tools or services
    - "[FILL: External dependency 1]"
    - "[FILL: External dependency 2]"

philosophy:                             # How skill embodies amplihack principles
  - principle: [FILL: Ruthless Simplicity|Trust in Emergence|Modular Design|Zero-BS Implementation|Analysis First]
    application: [FILL: How this skill embodies the principle]
  - principle: [FILL: Another principle if applicable]
    application: [FILL: Application description]

maturity: [FILL: experimental|production]  # Current maturity level
---

# [FILL: Skill Title in Title Case]

## Purpose

[FILL: 2-3 sentences describing what this skill does and what problems it solves]

## Auto-Activation Triggers

This skill automatically loads when Claude detects:

- [FILL: Trigger pattern 1]
- [FILL: Trigger pattern 2]
- [FILL: Trigger pattern 3]

## Manual Invocation

```
Claude, use the [FILL: skill-name] skill to [FILL: specific task]
```

**Examples:**

```
Claude, use the [FILL: skill-name] skill to [FILL: example 1]
Claude, analyze [FILL: target] using [FILL: skill-name]
```

## How It Works

[FILL: Step-by-step explanation of skill execution]

1. **[FILL: Step 1]**: [Description]
2. **[FILL: Step 2]**: [Description]
3. **[FILL: Step 3]**: [Description]

## Input Requirements

[FILL: What inputs does this skill need?]

- **[FILL: Input 1]**: [Description and format]
- **[FILL: Input 2]**: [Description and format]

## Output Format

[FILL: What does this skill produce?]

- **[FILL: Output 1]**: [Description and format]
- **[FILL: Output 2]**: [Description and format]

## Skill Implementation

[FILL: Detailed instructions for Claude on how to execute this skill]

### Phase 1: [FILL: Phase Name]

[FILL: What to do in this phase]

### Phase 2: [FILL: Phase Name]

[FILL: What to do in this phase]

### Phase 3: [FILL: Phase Name]

[FILL: What to do in this phase]

## Best Practices

[FILL: Guidelines for effective use of this skill]

- [FILL: Best practice 1]
- [FILL: Best practice 2]
- [FILL: Best practice 3]

## Limitations

[FILL: Known constraints or scenarios where this skill may not be suitable]

- [FILL: Limitation 1]
- [FILL: Limitation 2]

## Related Skills

- **[FILL: related-skill-name]**: [Brief description of relationship]
- **[FILL: another-skill-name]**: [Brief description of relationship]

## Examples

### Example 1: [FILL: Basic Usage]

```
[FILL: Show concrete example of skill in action]
```

**Result:**

```
[FILL: Show expected output]
```

### Example 2: [FILL: Advanced Usage]

```
[FILL: Show more complex example]
```

**Result:**

```
[FILL: Show expected output]
```

## Philosophy Alignment

[FILL: Explain how this skill embodies amplihack philosophy]

This skill demonstrates **[FILL: principle name]** by [FILL: explanation of how].

## Version History

- **1.0.0** (YYYY-MM-DD): Initial release
