---
# REQUIRED FIELDS - Fill these in for every command

name: [FILL: command-name]              # Kebab-case, matches /command-name (e.g., ultrathink, analyze, fix)
version: 1.0.0                          # Semantic versioning (MAJOR.MINOR.PATCH)
description: [FILL: One-line summary under 80 characters describing what this command does]
triggers:                               # User request patterns that suggest using this command
  - "[FILL: Pattern 1 - e.g., 'Non-trivial task requiring planning']"
  - "[FILL: Pattern 2 - e.g., 'Multi-step feature implementation']"
  - "[FILL: Pattern 3 - e.g., 'When workflow orchestration needed']"

# OPTIONAL FIELDS - Include if relevant to your command

invokes:                                # What this command uses internally
  - type: workflow                      # Options: workflow, command, skill, subagent
    path: [FILL: .claude/workflow/WORKFLOW_NAME.md]
  - type: subagent
    path: [FILL: .claude/agents/amplihack/agent-name.md]
  - type: command
    name: [FILL: /other-command]
  - type: skill
    name: [FILL: skill-name]

philosophy:                             # How command embodies amplihack principles
  - principle: [FILL: Ruthless Simplicity|Trust in Emergence|Modular Design|Zero-BS Implementation|Analysis First]
    application: [FILL: How this command embodies the principle]
  - principle: [FILL: Another principle if applicable]
    application: [FILL: Application description]

dependencies:                           # External tools or files required
  required:
    - "[FILL: Required dependency 1]"
    - "[FILL: Required dependency 2]"
  optional:
    - "[FILL: Optional dependency that enhances functionality]"

examples:                               # Usage examples for users
  - "[FILL: /command-name basic usage example]"
  - "[FILL: /command-name advanced usage with options]"
---

# [FILL: Command Title in Title Case]

## Overview

[FILL: 2-3 sentences describing what this command does, when to use it, and what problems it solves]

## When to Use This Command

[FILL: Bullet list of scenarios where this command is the right choice]

- [FILL: Scenario 1]
- [FILL: Scenario 2]
- [FILL: Scenario 3]

## Usage

```bash
/command-name [FILL: arguments or options]
```

**Examples:**

```bash
# [FILL: Basic example]
/command-name simple task

# [FILL: Advanced example]
/command-name complex task with options
```

## How It Works

[FILL: Step-by-step explanation of command execution]

1. **[FILL: Step 1 name]**: [Description of what happens]
2. **[FILL: Step 2 name]**: [Description of what happens]
3. **[FILL: Step 3 name]**: [Description of what happens]

## Command Behavior

[FILL: Describe key behaviors, constraints, and expected outcomes]

- **Input**: [What the command accepts]
- **Output**: [What the command produces]
- **Side Effects**: [Any state changes, file modifications, etc.]

## Integration with Other Components

[FILL: Describe how this command works with workflows, agents, skills, or other commands]

## Notes and Limitations

[FILL: Important caveats, known limitations, or considerations]

- [FILL: Limitation 1]
- [FILL: Limitation 2]

## Related Commands

- [FILL: `/related-command`] - [Brief description of relationship]
- [FILL: `/another-command`] - [Brief description of relationship]
