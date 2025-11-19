---
# REQUIRED FIELDS - Fill these in for every workflow

name: [FILL: WORKFLOW_NAME]             # SCREAMING_SNAKE_CASE (e.g., DEFAULT_WORKFLOW, CI_DIAGNOSTIC_WORKFLOW)
version: 1.0.0                          # Semantic versioning (MAJOR.MINOR.PATCH)
description: [FILL: What this workflow orchestrates - one line under 80 chars]
steps: [FILL: number]                   # Total number of steps in this workflow

# OPTIONAL FIELDS - Include for better integration and documentation

entry_points:                           # Commands or skills that use this workflow
  - [FILL: /command-name]
  - [FILL: skill-name]

phases:                                 # Logical groupings of steps
  - name: [FILL: Phase 1 Name]
    steps: [FILL: [1, 2, 3]]           # Array of step numbers in this phase
    description: [FILL: What this phase accomplishes]
  - name: [FILL: Phase 2 Name]
    steps: [FILL: [4, 5, 6]]
    description: [FILL: What this phase accomplishes]

references:                             # Components this workflow mentions
  workflows:
    - [FILL: OTHER_WORKFLOW.md]
  commands:
    - [FILL: /command-name]
  skills:
    - [FILL: skill-name]
  subagents:
    - [FILL: .claude/agents/amplihack/agent-name.md]
  tools:
    - "[FILL: .claude/tools/tool-name.py]"

philosophy:                             # How workflow embodies amplihack principles
  - principle: [FILL: Ruthless Simplicity|Trust in Emergence|Modular Design|Zero-BS Implementation|Analysis First]
    application: [FILL: How this workflow embodies the principle]
  - principle: [FILL: Another principle if applicable]
    application: [FILL: Application description]

customizable: [FILL: true|false]        # Can users modify this workflow for their needs?
---

# [FILL: Workflow Title in Title Case]

## Overview

[FILL: 2-3 sentences describing what this workflow orchestrates, when to use it, and what outcomes it produces]

## When to Use This Workflow

[FILL: Scenarios where this workflow is the right choice]

- [FILL: Scenario 1]
- [FILL: Scenario 2]
- [FILL: Scenario 3]

## Workflow Phases

### Phase 1: [FILL: Phase Name]

**Steps: [FILL: 1-3]**

[FILL: Description of what this phase accomplishes and why it's important]

### Phase 2: [FILL: Phase Name]

**Steps: [FILL: 4-6]**

[FILL: Description of what this phase accomplishes and why it's important]

### Phase 3: [FILL: Phase Name]

**Steps: [FILL: 7-9]**

[FILL: Description of what this phase accomplishes and why it's important]

## Detailed Step-by-Step Process

### Step 1: [FILL: Step Name]

**Objective**: [FILL: What this step achieves]

**Actions**:

1. [FILL: Action 1]
2. [FILL: Action 2]
3. [FILL: Action 3]

**Agents**: [FILL: Which agents should be invoked? e.g., `architect`, `analyzer`]

**Output**: [FILL: What artifacts or decisions this step produces]

---

### Step 2: [FILL: Step Name]

**Objective**: [FILL: What this step achieves]

**Actions**:

1. [FILL: Action 1]
2. [FILL: Action 2]
3. [FILL: Action 3]

**Agents**: [FILL: Which agents should be invoked?]

**Dependencies**: [FILL: What must be complete before this step? e.g., "Step 1 output"]

**Output**: [FILL: What artifacts or decisions this step produces]

---

### Step 3: [FILL: Step Name]

**Objective**: [FILL: What this step achieves]

**Actions**:

1. [FILL: Action 1]
2. [FILL: Action 2]
3. [FILL: Action 3]

**Agents**: [FILL: Which agents should be invoked?]

**Output**: [FILL: What artifacts or decisions this step produces]

---

[FILL: Continue pattern for all remaining steps...]

---

### Step [FILL: N]: [FILL: Final Step Name]

**Objective**: [FILL: What this step achieves - typically cleanup or validation]

**Actions**:

1. [FILL: Action 1]
2. [FILL: Action 2]
3. [FILL: Action 3]

**Agents**: [FILL: Which agents should be invoked?]

**Output**: [FILL: Final deliverables and completion criteria]

## Success Criteria

[FILL: How do we know this workflow completed successfully?]

- [FILL: Success criterion 1]
- [FILL: Success criterion 2]
- [FILL: Success criterion 3]

## Failure Handling

[FILL: What happens if a step fails?]

- [FILL: Failure scenario 1 and how to handle]
- [FILL: Failure scenario 2 and how to handle]

## Customization Guide

[FILL: If customizable=true, explain how users can adapt this workflow]

Users can customize this workflow by:

1. [FILL: Customization option 1]
2. [FILL: Customization option 2]
3. [FILL: Customization option 3]

## Integration Points

[FILL: How this workflow integrates with other components]

- **Commands**: [FILL: Which commands invoke this workflow?]
- **Skills**: [FILL: Which skills might be used during execution?]
- **Agents**: [FILL: Key agents orchestrated by this workflow]

## Philosophy Alignment

[FILL: Explain how this workflow embodies amplihack philosophy]

This workflow demonstrates:

- **[FILL: Principle 1]**: [FILL: How workflow embodies it]
- **[FILL: Principle 2]**: [FILL: How workflow embodies it]

## Examples

### Example 1: [FILL: Basic Workflow Execution]

```
[FILL: Show example of workflow in action with concrete task]
```

**Steps Executed:**

1. [FILL: Step 1 result]
2. [FILL: Step 2 result]
3. [FILL: Continue through steps...]

**Outcome**: [FILL: Final result]

### Example 2: [FILL: Complex Workflow Execution]

```
[FILL: Show more complex example]
```

**Outcome**: [FILL: Final result]

## Notes and Limitations

[FILL: Important considerations when using this workflow]

- [FILL: Note 1]
- [FILL: Note 2]

## Related Workflows

- **[FILL: RELATED_WORKFLOW.md]**: [Brief description of relationship]
- **[FILL: ANOTHER_WORKFLOW.md]**: [Brief description of relationship]

## Version History

- **1.0.0** (YYYY-MM-DD): Initial release
