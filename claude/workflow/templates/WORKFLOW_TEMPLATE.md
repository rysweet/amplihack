# [Your Workflow Name] Workflow

<!--
  TEMPLATE INSTRUCTIONS:
  - Replace [Your Workflow Name] with your workflow name
  - Fill in all sections below
  - Remove these template instruction comments when done
  - Keep the structure and section headings
  - Add/remove steps as needed for your workflow
  - Document agent assignments clearly
-->

This workflow [brief description of what makes this workflow unique].

## How This Workflow Works

**This workflow is the single source of truth for:**

<!-- Define what this workflow controls -->

- The order of operations (steps must be followed sequentially)
- [Any special process characteristics]
- [Agent coordination strategy]
- [Git workflow if different from default]

**Execution approach:**

<!-- How to invoke this workflow -->

- Start with `/ultrathink` with this workflow selected in USER_PREFERENCES.md
- UltraThink reads this workflow and orchestrates agents to execute it
- [Any special execution characteristics]

## When This Workflow Applies

<!-- Define when to use this workflow -->

This workflow should be followed for:

- [Use case 1]
- [Use case 2]
- [Use case 3]
- [Any specific conditions or requirements]

## The [N]-Step Workflow

<!--
  STEP STRUCTURE GUIDE:
  Each step should follow this format:

  ### Step N: Step Name

  [Optional: Special triggers or conditions]

  **Agent Orchestration:**
  - [ ] List of agents to deploy
  - [ ] How agents should coordinate (parallel/sequential)

  **Tasks:**
  - [ ] Specific tasks to complete
  - [ ] Success criteria
  - [ ] Validation requirements

  **Output:** [What this step produces]
-->

### Step 1: [First Step Name]

<!-- Example of a simple step -->

**Agent Orchestration:**

- [ ] **Use** [agent-name] agent to [specific task]
- [ ] **Use** [agent-name] agent to [specific task]

**Tasks:**

- [ ] [Specific task with clear success criteria]
- [ ] [Another task]
- [ ] [Validation task]

**Output:** [Deliverable from this step]

### Step 2: [Second Step Name]

<!-- Example of a step with parallel agent execution -->

**PARALLEL EXECUTION:** This step deploys multiple agents in parallel

**Agent Orchestration:**

- [ ] **Deploy** [agent1], [agent2], [agent3] in parallel
- [ ] **Round 1**: [What each agent does]
- [ ] **Round 2**: [Next phase of coordination]
- [ ] **Orchestrator**: [How to synthesize results]

**Tasks:**

- [ ] [Task 1]
- [ ] [Task 2]
- [ ] [Task 3]

**Output:** [Deliverable from this step]

### Step 3: [Third Step Name with Conditional Logic]

<!-- Example of a step with conditional execution -->

**CONDITIONAL TRIGGER**: [Condition that determines if extra work is needed]

**Standard Tasks:**

- [ ] [Always-executed task 1]
- [ ] [Always-executed task 2]

**IF [CONDITION] → Special Process:**

- [ ] [Additional steps if condition met]
- [ ] [More conditional work]
- [ ] [Validation of conditional outcome]

**Output:** [Deliverable from this step]

### Step 4: [Git Operation Step]

<!-- Example of a git workflow step -->

**Agent Orchestration:**

- [ ] [Any agent assistance needed]

**Git Tasks:**

- [ ] [Git command 1]
- [ ] [Git command 2]
- [ ] [Verification]

**Output:** [Git state change]

### Step 5: [Implementation Step]

<!-- Example of an implementation step -->

**Agent Orchestration:**

- [ ] **Always use** [builder-agent] to implement from specifications
- [ ] **Use** [integration-agent] for [specific integration work]

**Implementation Tasks:**

- [ ] [Follow design/spec]
- [ ] [Make tests pass]
- [ ] [Document code]
- [ ] [Ensure quality]

**Output:** [Working implementation]

### Step 6: [Review Step]

<!-- Example of a review/validation step -->

**REVIEW MECHANISM**: [Describe review approach]

**Agent Orchestration:**

- [ ] **Deploy review panel**: [agent1], [agent2], [agent3]
- [ ] **Parallel reviews**: Each agent reviews from their perspective
- [ ] **Consolidate findings**: Orchestrator synthesizes feedback

**Review Tasks:**

- [ ] [Review criteria 1]
- [ ] [Review criteria 2]
- [ ] [Review criteria 3]

**Output:** [Review findings and required actions]

### Step 7: [Testing Step]

<!-- Example of a testing/validation step -->

**Agent Orchestration:**

- [ ] **Use** [test-diagnostic-agent] if tests fail

**Testing Tasks:**

- [ ] [Run test suite]
- [ ] [Run pre-commit hooks]
- [ ] [Fix any issues]
- [ ] [Iterate until passing]

**Output:** [All checks passing]

### Step 8: [Final Step]

<!-- Example of final validation/cleanup step -->

**Agent Orchestration:**

- [ ] **Use** [cleanup-agent] for final pass
- [ ] **Validation**: All agents confirm completion

**Final Tasks:**

- [ ] [Verify all requirements met]
- [ ] [Clean up any artifacts]
- [ ] [Document completion]

**Output:** [Completed, validated work]

## Agent Assignment Patterns

<!-- Document your agent coordination strategy -->

### Parallel Execution

Use parallel execution when:

- [Condition 1]
- [Condition 2]

Example agents for parallel execution: [list]

### Sequential Execution

Use sequential execution when:

- [Hard dependency 1]
- [Hard dependency 2]

Example agent chains: [agent1] → [agent2] → [agent3]

### Conditional Agent Deployment

Deploy additional agents when:

- [Trigger condition 1]: Use [agent-set-1]
- [Trigger condition 2]: Use [agent-set-2]

## Special Mechanisms

<!-- Document any unique aspects of your workflow -->

### [Mechanism 1 Name]

**When to use**: [Conditions]

**Process**:

1. [Step 1]
2. [Step 2]
3. [Step 3]

**Output**: [What this mechanism produces]

### [Mechanism 2 Name]

**When to use**: [Conditions]

**Process**:

1. [Step 1]
2. [Step 2]
3. [Step 3]

**Output**: [What this mechanism produces]

## Customization

<!-- Explain how to customize this workflow -->

To customize this workflow:

1. [Step to customize]
2. [How to modify]
3. [Save and use]

## Performance Characteristics

<!-- Document performance trade-offs -->

**This workflow is [faster/slower] than default because:**

- [Characteristic 1]
- [Characteristic 2]

**Use when**: [Optimization for specific scenarios]

## Philosophy Integration

<!-- Show how workflow aligns with project philosophy -->

This workflow maintains core philosophy principles:

- **Ruthless Simplicity**: [How this is enforced]
- **Bricks & Studs**: [How this is validated]
- **Zero-BS**: [How this is verified]
- **Regeneratable**: [How this is ensured]
- **Test-Driven**: [How this is applied]

## Success Metrics

<!-- Define what success looks like -->

This workflow succeeds when:

- [Success criterion 1]
- [Success criterion 2]
- [Success criterion 3]
- [Overall outcome]

## Examples

<!-- Provide concrete examples of when to use this workflow -->

### Example 1: [Scenario]

**When**: [Specific situation]

**Why this workflow**: [Reason this workflow fits]

**Expected outcome**: [What will be achieved]

### Example 2: [Scenario]

**When**: [Specific situation]

**Why this workflow**: [Reason this workflow fits]

**Expected outcome**: [What will be achieved]

## Tips and Best Practices

<!-- Share wisdom about using this workflow -->

- **Tip 1**: [Practical advice]
- **Tip 2**: [What to watch out for]
- **Tip 3**: [Common pitfalls to avoid]

## Integration with Other Workflows

<!-- Explain relationship to other workflows -->

**Relationship to DEFAULT_WORKFLOW.md**:

- [How this differs]
- [What's shared]
- [When to switch]

**Relationship to CONSENSUS_WORKFLOW.md**:

- [How this differs]
- [What's shared]
- [When to switch]

---

<!-- Final notes or references -->

**Remember**: [Key takeaway about this workflow]

## Template Checklist

<!-- Remove this section after completing your workflow -->

Before publishing your workflow, ensure:

- [ ] All [placeholder text] replaced with actual content
- [ ] All template instruction comments removed
- [ ] Step count in title matches actual steps
- [ ] Agent assignments are clear and specific
- [ ] Success criteria are measurable
- [ ] Examples are concrete and helpful
- [ ] Philosophy alignment is documented
- [ ] Performance characteristics are honest
- [ ] Customization instructions are clear
- [ ] All sections are complete (no "TODO" or empty sections)
