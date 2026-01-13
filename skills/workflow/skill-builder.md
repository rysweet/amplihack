# Skill Builder

Workflow for creating new skills, agents, commands, and scenarios in the amplifier ecosystem.

## When to Use

- Creating new amplifier skills
- Building agent definitions
- Designing scenario tools
- Keywords: "create skill", "new agent", "build command", "add scenario"

## Skill Types

| Type | Purpose | Location | Format |
|------|---------|----------|--------|
| **Skill** | Domain knowledge, workflows, patterns | `skills/` | Markdown |
| **Agent** | Specialized assistant with tools | `agents/` | YAML |
| **Command** | Quick action, shortcut | `commands/` | YAML |
| **Scenario** | Multi-step workflow template | `scenario-tools/` | Directory |

## Output Location Conventions

```
bundle/
├── skills/
│   ├── [domain]/           # Grouped by domain
│   │   └── [skill-name].md
│   └── [skill-name].md     # Or flat structure
├── agents/
│   └── [agent-name].yaml
├── commands/
│   └── [command-name].yaml
└── scenario-tools/
    └── [scenario-name]/
        ├── README.md
        ├── recipe.yaml
        └── templates/
```

## Workflow: Validate -> Clarify -> Design -> Implement -> Review

### Step 1: Validate Need

```markdown
## Need Validation

**Requested:** [What user asked for]
**Type:** [Skill | Agent | Command | Scenario]

**Validation Checklist:**
- [ ] Does this already exist in available bundles?
- [ ] Is this the right type for the need?
- [ ] Is the scope appropriate (not too broad/narrow)?
- [ ] Does it align with bundle purpose?

**Conclusion:** [Proceed | Adjust Type | Merge with Existing | Decline]
```

### Step 2: Clarify Requirements

```markdown
## Requirements Clarification

**Primary Purpose:** [Single sentence]

**Use Cases:**
1. [When would this be used?]
2. [What problem does it solve?]
3. [Who is the target user?]

**Scope Boundaries:**
- IN Scope: [What it will do]
- OUT of Scope: [What it won't do]

**Dependencies:**
- Required: [Must have]
- Optional: [Nice to have]
```

### Step 3: Design

```markdown
## Design

**Name:** [kebab-case name]
**Location:** [Full path]

**Structure:**
[Outline of content/sections]

**Integration Points:**
- [How it connects to other skills/agents]

**Keywords/Triggers:**
- [When this should be activated]
```

### Step 4: Implement

Create the artifact following the appropriate template.

### Step 5: Review

```markdown
## Review Checklist

- [ ] Name is clear and descriptive
- [ ] Purpose is immediately obvious
- [ ] "When to Use" section is accurate
- [ ] Content is complete but concise
- [ ] Follows bundle conventions
- [ ] No duplication with existing skills
- [ ] Examples are practical
- [ ] Output formats are clear
```

## Template: Skill

```markdown
# [Skill Name]

[One-line description of what this skill provides]

## When to Use

- [Situation 1]
- [Situation 2]
- Keywords: "[trigger1]", "[trigger2]"

## [Main Section 1]

[Content - tables, checklists, patterns]

## [Main Section 2]

[Content]

## Workflow/Process

1. Step 1
2. Step 2
...

## Output Format

```markdown
## [Output Title]

[Template for outputs]
```

## Anti-Patterns

- [What to avoid]
```

## Template: Agent

```yaml
name: [agent-name]
description: |
  [Multi-line description of agent purpose and capabilities]

instructions: |
  [Core instructions for the agent's behavior]
  
  ## Responsibilities
  - [Responsibility 1]
  - [Responsibility 2]

context:
  - "[skill-reference]"

tools:
  - [tool1]
  - [tool2]
```

## Template: Command

```yaml
name: [command-name]
description: "[Brief description]"

instructions: |
  [What to do when command is invoked]

# Optional: specific context or tools
context:
  - "[relevant-skill]"
```

## Template: Scenario

```
scenario-name/
├── README.md          # Usage instructions
├── recipe.yaml        # Workflow definition
└── templates/         # Output templates
    └── [template].md
```

## Quality Criteria

| Criterion | Good | Bad |
|-----------|------|-----|
| **Scope** | Single, clear purpose | Multiple unrelated concerns |
| **Name** | Descriptive, searchable | Vague, generic |
| **Triggers** | Specific, unique | Overlapping with others |
| **Content** | Actionable, practical | Theoretical, abstract |
| **Length** | Concise, scannable | Bloated, verbose |

## Common Mistakes

- Creating skills that are too narrow (should be section of larger skill)
- Creating skills that are too broad (should be multiple skills)
- Duplicating content from existing skills
- Missing "When to Use" section
- Vague or missing output formats
- No clear workflow or process
