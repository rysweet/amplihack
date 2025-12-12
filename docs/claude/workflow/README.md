# Amplihack Workflow System

The Amplihack workflow system provides customizable, multi-agent orchestration for software development tasks. Workflows define the authoritative process for how tasks are executed, including step order, agent assignments, and quality gates.

## Overview

**What is a Workflow?**

A workflow is a structured, step-by-step process that defines:

- The sequence of operations for completing a task
- Which agents to deploy at each step
- How agents coordinate (parallel vs. sequential)
- Quality gates and validation requirements
- Git workflow and CI/CD integration points

**Why Use Workflows?**

- **Consistency**: Same process every time, reducing errors
- **Quality**: Built-in review and validation steps
- **Efficiency**: Multi-agent orchestration and parallel execution
- **Adaptability**: Customize workflows for different scenarios
- **Traceability**: Clear documentation of what was done and why

## Available Workflows

### DEFAULT_WORKFLOW.md

**Purpose**: Standard workflow for most development tasks

**When to use**:

- New features
- Bug fixes
- Refactoring
- Standard development work

**Characteristics**:

- Well-defined workflow steps from requirements to merge
- Balanced speed and quality
- Agent deployment at appropriate steps
- TDD approach with pre-commit validation
- Standard CI/CD integration

**Best for**: Day-to-day development where speed and quality balance is optimal

### CONSENSUS_WORKFLOW.md

**Purpose**: Enhanced workflow with consensus mechanisms for critical tasks

**When to use**:

- Ambiguous or complex requirements
- Architecturally significant designs
- Mission-critical code
- Security-sensitive implementations
- Performance-critical components
- Public APIs with long-term commitments

**Characteristics**:

- Same multi-step structure as default
- Multi-Agent Debate for requirements and design (Steps 1 & 4)
- N-Version Programming for critical code (Step 5)
- Expert Panel reviews for refactoring and PR review (Steps 6, 11, 13, 15)
- Consensus-driven decision making
- Higher quality but slower execution

**Best for**: Tasks where correctness and quality justify extra time investment

### Custom Workflows

Create your own workflows using the template in `templates/WORKFLOW_TEMPLATE.md`

## How Workflows Work

### Workflow Execution with UltraThink

**For any non-trivial task:**

1. Start with `/ultrathink [task description]`
2. UltraThink reads your selected workflow from USER_PREFERENCES.md
3. UltraThink executes each workflow step in order
4. Agents are deployed according to workflow specifications
5. Progress is tracked with TodoWrite
6. Completion is verified against workflow success criteria

**Workflow Selection:**

```bash
# Show available workflows
/amplihack:customize list-workflows

# View a specific workflow
/amplihack:customize show-workflow CONSENSUS_WORKFLOW

# Switch to a different workflow
/amplihack:customize set-workflow CONSENSUS_WORKFLOW

# Return to default
/amplihack:customize set-workflow DEFAULT_WORKFLOW
```

### Workflow Discovery

**Method 1: Via Command**

```bash
/amplihack:customize list-workflows
```

Lists all available workflows in `.claude/workflow/` with descriptions.

**Method 2: Via File System**

Browse `.claude/workflow/` directory:

```
.claude/workflow/
├── README.md                    # This file
├── DEFAULT_WORKFLOW.md          # Standard workflow
├── CONSENSUS_WORKFLOW.md        # Consensus-augmented workflow
└── templates/
    └── WORKFLOW_TEMPLATE.md     # Template for custom workflows
```

**Method 3: Via USER_PREFERENCES.md**

Check your current workflow setting:

```bash
/amplihack:customize show
```

Look for the `workflow` section.

### Workflow Structure

All workflows follow a consistent structure:

```markdown
# [Workflow Name]

## How This Workflow Works

[What makes this workflow unique]

## When This Workflow Applies

[Scenarios where this workflow is optimal]

## The [N]-Step Workflow

### Step 1: [Step Name]

- [ ] Agent orchestration instructions
- [ ] Tasks to complete
- [ ] Success criteria

[... more steps ...]

## Customization

[How to modify this workflow]

## Success Metrics

[What success looks like]
```

## Creating Custom Workflows

### Step 1: Copy the Template

```bash
cp .claude/workflow/templates/WORKFLOW_TEMPLATE.md .claude/workflow/MY_WORKFLOW.md
```

### Step 2: Customize Your Workflow

Edit `MY_WORKFLOW.md`:

1. Replace `[Your Workflow Name]` with your workflow name
2. Fill in all sections:
   - When to use this workflow
   - Step-by-step process
   - Agent assignments
   - Success criteria
3. Remove template instruction comments
4. Validate structure is complete

### Step 3: Test Your Workflow

```bash
# Switch to your workflow
/amplihack:customize set-workflow MY_WORKFLOW

# Test with a simple task
/ultrathink "Add a simple function to utils.py"
```

### Step 4: Iterate and Refine

- Observe how UltraThink executes your workflow
- Identify bottlenecks or missing steps
- Refine agent assignments
- Adjust parallelization strategy
- Document lessons learned

### Step 5: Share (Optional)

If your workflow is valuable to others:

1. Ensure comprehensive documentation
2. Add examples and use cases
3. Test thoroughly
4. Submit PR to add to standard workflows
5. Update this README with new workflow

## Workflow Selection Guide

### Decision Tree

```
Is the task trivial (< 5 minutes)?
├─ YES → Just do it, don't use a workflow
└─ NO → Continue

Is correctness more important than speed?
├─ YES → CONSENSUS_WORKFLOW
└─ NO → Continue

Are requirements ambiguous or complex?
├─ YES → CONSENSUS_WORKFLOW
└─ NO → Continue

Is this architecturally significant?
├─ YES → CONSENSUS_WORKFLOW
└─ NO → Continue

Is this mission-critical code?
├─ YES → CONSENSUS_WORKFLOW
└─ NO → DEFAULT_WORKFLOW (fast, balanced)
```

### Comparison Matrix

| Factor                   | DEFAULT_WORKFLOW | CONSENSUS_WORKFLOW |
| ------------------------ | ---------------- | ------------------ |
| Speed                    | Fast             | Slower             |
| Quality                  | High             | Highest            |
| Agent Invocations        | Moderate         | Many               |
| Consensus Mechanisms     | None             | 3 types            |
| Best for                 | Most tasks       | Critical tasks     |
| Requirements Clarity     | Good             | Excellent          |
| Design Validation        | Standard         | Multi-agent debate |
| Critical Code Validation | Standard         | N-Version          |
| Review Thoroughness      | Comprehensive    | Expert Panel       |
| Philosophy Compliance    | Validated        | Unanimous          |
| Decision Documentation   | Good             | Extensive          |
| Suitable for Public APIs | Yes              | Preferred          |
| Suitable for Security    | Yes              | Preferred          |
| Suitable for Performance | Yes              | Preferred          |

## Agent Coordination in Workflows

### Sequential Agent Execution

**When**: Hard dependencies exist (output of Agent A is input to Agent B)

**Example**:

```
architect → builder → reviewer
```

**Workflow Syntax**:

```markdown
### Step 4: Design

- [ ] **Use** architect agent to create specifications

### Step 5: Implement

- [ ] **Always use** builder agent to implement from specifications

### Step 6: Review

- [ ] **Always use** reviewer agent to validate implementation
```

### Parallel Agent Execution

**When**: Independent analysis, multiple perspectives needed

**Example**:

```
[analyzer, security, optimizer, patterns] → orchestrator synthesizes
```

**Workflow Syntax**:

```markdown
### Step 4: Design (PARALLEL)

- [ ] **Deploy** architect, api-designer, database, security, tester in parallel
- [ ] Each agent analyzes independently
- [ ] **Orchestrator**: Synthesize results
```

### Consensus Mechanisms

**Multi-Agent Debate**: Multiple rounds of proposal, challenge, synthesis

**N-Version Programming**: Independent implementations validated against each other

**Expert Panel**: Parallel reviews consolidated into unanimous decision

See `CONSENSUS_WORKFLOW.md` for detailed examples.

## Workflow Configuration

### In USER_PREFERENCES.md

```yaml
workflow:
  selected: "DEFAULT_WORKFLOW" # or "CONSENSUS_WORKFLOW" or custom
  consensus_depth: "balanced" # quick, balanced, comprehensive
```

### Configuration Options

**selected**: Name of workflow file (without .md extension)

- `DEFAULT_WORKFLOW` - Standard workflow (default)
- `CONSENSUS_WORKFLOW` - Consensus-augmented workflow
- `MY_CUSTOM_WORKFLOW` - Your custom workflow

**consensus_depth**: (Only applies to CONSENSUS_WORKFLOW)

- `quick` - Minimal consensus (2 agents, 2 rounds)
- `balanced` - Standard consensus (3-4 agents, 3 rounds) [default]
- `comprehensive` - Maximum consensus (5+ agents, 4+ rounds)

### Modifying Configuration

```bash
# Change workflow
/amplihack:customize set-workflow CONSENSUS_WORKFLOW

# Set consensus depth (for CONSENSUS_WORKFLOW only)
/amplihack:customize set consensus_depth comprehensive
```

## UltraThink Integration

UltraThink automatically integrates with the workflow system:

1. **Workflow Loading**: UltraThink reads workflow from USER_PREFERENCES.md
2. **Fallback**: If workflow not found, uses DEFAULT_WORKFLOW.md
3. **Parsing**: Extracts agent assignments from each step
4. **Orchestration**: Deploys agents according to workflow specifications
5. **Progress Tracking**: TodoWrite tracks workflow step completion
6. **Validation**: Verifies workflow success criteria at end

**How UltraThink Uses Workflows:**

```
User: /ultrathink "Add authentication to API"

UltraThink:
1. Reads USER_PREFERENCES.md → selected: "CONSENSUS_WORKFLOW"
2. Loads .claude/workflow/CONSENSUS_WORKFLOW.md
3. Parses workflow steps with agent assignments
4. Creates TodoWrite with all workflow steps
5. Executes Step 1:
   - Reads: "Deploy prompt-writer, analyzer, ambiguity"
   - If ambiguous: "Deploy Multi-Agent Debate"
   - Invokes agents as specified
6. Continues through all workflow steps
7. Validates: PR is mergeable, all requirements met
```

## Best Practices

### Workflow Design

1. **Start Simple**: Begin with DEFAULT_WORKFLOW, customize incrementally
2. **Clear Steps**: Each step should have one clear purpose
3. **Explicit Agents**: Specify which agents to deploy at each step
4. **Measurable Success**: Define concrete success criteria
5. **Document Rationale**: Explain why your workflow differs from default

### Workflow Usage

1. **Match to Task**: Use decision tree to select appropriate workflow
2. **Trust the Process**: Follow workflow steps in order
3. **Let Agents Work**: Don't skip agent deployment steps
4. **Document Changes**: If you modify mid-workflow, document why
5. **Learn and Improve**: Update workflows based on experience

### Workflow Maintenance

1. **Review Regularly**: Workflows should evolve with project needs
2. **Measure Effectiveness**: Track workflow success rates
3. **Gather Feedback**: Ask developers which workflows work best
4. **Consolidate Learning**: Update workflows based on discoveries
5. **Version Control**: Commit workflow changes with clear explanations

## Common Patterns

### Pattern 1: TDD-First Workflow

```markdown
### Step 4: Write Tests

- [ ] **Always use** tester agent to write failing tests
- [ ] Define success criteria through tests

### Step 5: Implement

- [ ] **Always use** builder agent to make tests pass
```

### Pattern 2: Security-First Workflow

```markdown
### Step 4: Design

- [ ] **Always use** security agent first to identify threats
- [ ] **Then use** architect agent to design with security in mind
```

### Pattern 3: Performance-Critical Workflow

```markdown
### Step 5: Implement

- [ ] **Always use** N-Version Programming for hot paths
- [ ] Benchmark each implementation

### Step 6: Optimize

- [ ] **Always use** optimizer agent with profiling data
```

## Troubleshooting

### Workflow Not Loading

**Problem**: UltraThink uses DEFAULT_WORKFLOW even though you selected different

**Solutions**:

1. Check workflow name in USER_PREFERENCES.md (exact match, no .md extension)
2. Verify workflow file exists in `.claude/workflow/`
3. Ensure workflow file is valid markdown with required structure

### Agents Not Deploying

**Problem**: Workflow step specifies agents but they aren't invoked

**Solutions**:

1. Check agent assignment syntax: "**Use** agent-name agent"
2. Verify agent exists in `.claude/agents/amplihack/`
3. Ensure TodoWrite is tracking workflow steps

### Workflow Taking Too Long

**Problem**: CONSENSUS_WORKFLOW is too slow for current task

**Solutions**:

1. Switch to DEFAULT_WORKFLOW for this task: `/amplihack:customize set-workflow DEFAULT_WORKFLOW`
2. Reduce consensus_depth: `/amplihack:customize set consensus_depth quick`
3. Create custom workflow with selective consensus

### Workflow Incomplete

**Problem**: Workflow has missing steps or unclear instructions

**Solutions**:

1. Review against WORKFLOW_TEMPLATE.md checklist
2. Add missing agent assignments
3. Clarify success criteria
4. Test with simple task to validate

## Examples

### Example 1: Using Default Workflow

```bash
# Verify workflow selection
/amplihack:customize show
# Output: workflow: selected: "DEFAULT_WORKFLOW"

# Execute task with workflow
/ultrathink "Add password reset functionality to auth service"

# UltraThink will:
# 1. Load DEFAULT_WORKFLOW.md
# 2. Execute all workflow steps
# 3. Deploy agents as specified in each step
# 4. Produce mergeable PR
```

### Example 2: Switching to Consensus Workflow

```bash
# Switch workflow
/amplihack:customize set-workflow CONSENSUS_WORKFLOW

# Execute architecturally significant task
/ultrathink "Redesign authentication system to support OAuth2 and SAML"

# UltraThink will:
# 1. Load CONSENSUS_WORKFLOW.md
# 2. Step 1: Multi-Agent Debate on requirements (ambiguous)
# 3. Step 4: Multi-Agent Debate on architecture (ALWAYS)
# 4. Step 5: N-Version for critical auth logic
# 5. Steps 6, 11, 13, 15: Expert Panel reviews
# 6. Produce high-quality, consensus-validated PR
```

### Example 3: Creating Custom Workflow

```bash
# Copy template
cp .claude/workflow/templates/WORKFLOW_TEMPLATE.md .claude/workflow/HOTFIX_WORKFLOW.md

# Edit for fast hotfixes:
# - Reduce to 8 steps
# - Skip comprehensive design (trust developer judgment)
# - Focus on rapid testing and deployment
# - Maintain safety gates (tests, pre-commit, CI)

# Use for emergency fixes
/amplihack:customize set-workflow HOTFIX_WORKFLOW
/ultrathink "Fix critical production bug in payment processing"
```

## Advanced Topics

### Dynamic Workflow Selection

You can programmatically select workflows based on task characteristics:

```bash
# For simple tasks
/amplihack:customize set-workflow DEFAULT_WORKFLOW
/ultrathink "Add logging to function X"

# For complex tasks
/amplihack:customize set-workflow CONSENSUS_WORKFLOW
/ultrathink "Redesign data pipeline architecture"
```

### Workflow Composition

Combine aspects of multiple workflows by creating custom workflow that references others:

```markdown
### Step 4: Design

**IF architecturally significant:**

- [ ] Use design process from CONSENSUS_WORKFLOW.md Step 4

**ELSE:**

- [ ] Use design process from DEFAULT_WORKFLOW.md Step 4
```

### Workflow Metrics

Track workflow effectiveness:

- Time to completion
- Number of iterations required
- Issues found in review
- Post-merge defects
- Developer satisfaction

Use metrics to guide workflow refinement.

## Integration with Project Philosophy

All workflows must maintain Amplihack core principles:

- **Ruthless Simplicity**: Workflows enforce simplification steps
- **Bricks & Studs**: Architecture review validates module boundaries
- **Zero-BS**: Review steps verify no stubs or placeholders
- **Regeneratable**: Design steps ensure specifications are complete
- **Test-Driven**: TDD steps come before implementation

Workflows are the mechanism for consistently applying philosophy.

## Contributing

### Adding New Workflows

1. Create workflow using WORKFLOW_TEMPLATE.md
2. Test thoroughly with real tasks
3. Document use cases and benefits
4. Add to this README's "Available Workflows" section
5. Submit PR with examples

### Improving Existing Workflows

1. Identify issue or improvement opportunity
2. Propose change with rationale
3. Test modified workflow
4. Update documentation
5. Submit PR with before/after comparison

## Resources

- **DEFAULT_WORKFLOW.md**: Standard workflow implementation
- **CONSENSUS_WORKFLOW.md**: Consensus-augmented workflow implementation
- **WORKFLOW_TEMPLATE.md**: Template for creating custom workflows
- **CLAUDE.md**: Project-level workflow integration
- **.claude/agents/CATALOG.md**: Available agents for workflow steps
- **USER_PREFERENCES.md**: Workflow configuration storage

## Summary

The Amplihack workflow system provides:

- **Structure**: Clear, repeatable processes
- **Quality**: Built-in validation and review gates
- **Flexibility**: Multiple workflows for different scenarios
- **Customization**: Create workflows for your specific needs
- **Integration**: Seamless UltraThink orchestration
- **Philosophy Alignment**: Consistent application of core principles

Start with DEFAULT_WORKFLOW for most tasks. Use CONSENSUS_WORKFLOW for critical work. Create custom workflows as you discover patterns in your development process.

---

**Remember**: Workflows are the authoritative process definition. Trust the workflow, execute the steps, and let specialized agents do their work.
