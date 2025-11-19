---
# REQUIRED FIELDS - Fill these in for every agent

role: [FILL: agent-role-name]           # Kebab-case (e.g., architect, builder, tester)
purpose: [FILL: Single clear responsibility statement - one sentence]
triggers:                               # When to use this agent
  - "[FILL: Situation 1 - e.g., 'Design new feature or system']"
  - "[FILL: Situation 2 - e.g., 'Create module specification']"
  - "[FILL: Situation 3 - e.g., 'Problem decomposition needed']"

# OPTIONAL FIELDS - Include based on agent complexity and specialization

invokes:                                # What this agent uses internally
  - type: command
    name: [FILL: /command-name]
  - type: skill
    name: [FILL: skill-name]
  - type: subagent
    path: [FILL: .claude/agents/amplihack/other-agent.md]

boundaries:                             # What this agent explicitly does NOT do
  - "[FILL: Excluded responsibility 1 - e.g., 'Does not implement code (delegates to builder)']"
  - "[FILL: Excluded responsibility 2]"

philosophy:                             # How agent embodies amplihack principles
  - principle: [FILL: Ruthless Simplicity|Trust in Emergence|Modular Design|Zero-BS Implementation|Analysis First|Single Responsibility]
    application: [FILL: How this agent embodies the principle]
  - principle: [FILL: Another principle if applicable]
    application: [FILL: Application description]

dependencies:
  required_context:                     # Files agent should import for context
    - "[FILL: @.claude/context/PHILOSOPHY.md]"
    - "[FILL: @.claude/context/PATTERNS.md]"
  tools:                                # Claude Code tools this agent needs
    - [FILL: Read]
    - [FILL: Write]
    - [FILL: Edit]
    - [FILL: Bash]

expertise:                              # Domain knowledge areas
  - "[FILL: Area of deep knowledge 1]"
  - "[FILL: Area of deep knowledge 2]"
  - "[FILL: Area of deep knowledge 3]"

delegation_pattern: [FILL: parallel|sequential|adaptive]  # How agent delegates to others
---

# [FILL: Agent Role Name in Title Case]

You are the **[FILL: agent role]** agent in the amplihack framework.

## Your Responsibility

[FILL: Detailed description of agent's single, focused responsibility - 2-3 sentences explaining what this agent does and why it exists]

## When You Are Invoked

You are called when:

- [FILL: Trigger scenario 1]
- [FILL: Trigger scenario 2]
- [FILL: Trigger scenario 3]

## What You Do

[FILL: Clear description of agent's workflow and process]

### Step 1: [FILL: First Major Step]

[FILL: Detailed description of what happens in this step]

**Actions:**

- [FILL: Specific action 1]
- [FILL: Specific action 2]
- [FILL: Specific action 3]

### Step 2: [FILL: Second Major Step]

[FILL: Detailed description of what happens in this step]

**Actions:**

- [FILL: Specific action 1]
- [FILL: Specific action 2]
- [FILL: Specific action 3]

### Step 3: [FILL: Third Major Step]

[FILL: Detailed description of what happens in this step]

**Actions:**

- [FILL: Specific action 1]
- [FILL: Specific action 2]
- [FILL: Specific action 3]

## What You Do NOT Do

[FILL: Clear boundaries to prevent scope creep]

- [FILL: Responsibility 1 you delegate to another agent]
- [FILL: Responsibility 2 you delegate to another agent]
- [FILL: Responsibility 3 outside your scope]

## Delegation Strategy

[FILL: Explain when and how this agent delegates to others]

**Pattern**: [FILL: parallel|sequential|adaptive]

- **[FILL: Agent/Tool 1]**: [When and why you delegate to it]
- **[FILL: Agent/Tool 2]**: [When and why you delegate to it]
- **[FILL: Agent/Tool 3]**: [When and why you delegate to it]

## Input Requirements

[FILL: What information or context does this agent need to function?]

- **[FILL: Input 1]**: [Description and format]
- **[FILL: Input 2]**: [Description and format]
- **[FILL: Input 3]**: [Description and format]

## Output Deliverables

[FILL: What artifacts or decisions does this agent produce?]

- **[FILL: Output 1]**: [Description and format]
- **[FILL: Output 2]**: [Description and format]
- **[FILL: Output 3]**: [Description and format]

## Core Principles

[FILL: How this agent embodies amplihack philosophy]

### [FILL: Principle 1 Name]

[FILL: Detailed explanation of how agent embodies this principle with concrete examples]

### [FILL: Principle 2 Name]

[FILL: Detailed explanation of how agent embodies this principle with concrete examples]

## Tools and Context

[FILL: What tools and context files does this agent use?]

**Required Context:**

```
[FILL: @.claude/context/FILE1.md]
[FILL: @.claude/context/FILE2.md]
```

**Tools Used:**

- **[FILL: Tool 1]**: [How and when used]
- **[FILL: Tool 2]**: [How and when used]
- **[FILL: Tool 3]**: [How and when used]

## Expertise Areas

[FILL: Domain knowledge this agent brings]

- **[FILL: Expertise 1]**: [Description of knowledge depth]
- **[FILL: Expertise 2]**: [Description of knowledge depth]
- **[FILL: Expertise 3]**: [Description of knowledge depth]

## Decision Framework

[FILL: How this agent makes decisions]

When faced with [FILL: common decision scenario]:

1. [FILL: Decision criterion 1]
2. [FILL: Decision criterion 2]
3. [FILL: Decision criterion 3]

## Examples

### Example 1: [FILL: Basic Scenario]

**User Request**: "[FILL: Example user request]"

**Agent Process**:

1. [FILL: Step 1 with concrete actions]
2. [FILL: Step 2 with concrete actions]
3. [FILL: Step 3 with concrete actions]

**Output**: [FILL: What the agent produces]

### Example 2: [FILL: Complex Scenario]

**User Request**: "[FILL: Example user request]"

**Agent Process**:

1. [FILL: Step 1 with concrete actions]
2. [FILL: Step 2 with concrete actions]
3. [FILL: Step 3 with concrete actions]

**Output**: [FILL: What the agent produces]

## Quality Checks

[FILL: How this agent ensures quality output]

Before completing work, verify:

- [ ] [FILL: Quality check 1]
- [ ] [FILL: Quality check 2]
- [ ] [FILL: Quality check 3]

## Common Patterns

[FILL: Reusable patterns this agent frequently uses]

### Pattern 1: [FILL: Pattern Name]

[FILL: Description and when to use]

```
[FILL: Example code or template]
```

### Pattern 2: [FILL: Pattern Name]

[FILL: Description and when to use]

```
[FILL: Example code or template]
```

## Error Handling

[FILL: How agent handles failures and edge cases]

- **[FILL: Error Type 1]**: [How to handle]
- **[FILL: Error Type 2]**: [How to handle]
- **[FILL: Error Type 3]**: [How to handle]

## Integration with Amplihack

[FILL: How this agent fits into the broader amplihack ecosystem]

- **Works with**: [FILL: Related agents, commands, workflows]
- **Called by**: [FILL: What invokes this agent]
- **Invokes**: [FILL: What this agent calls]

## Notes and Limitations

[FILL: Important considerations when using this agent]

- [FILL: Limitation 1]
- [FILL: Limitation 2]
- [FILL: Known edge case]

## Version History

- **1.0.0** (YYYY-MM-DD): Initial agent definition
