# Improve Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/improve [target]`

Target can be:

- `self` - Improve the AI system itself
- `agents` - Enhance agent definitions
- `patterns` - Update pattern library
- `<path>` - Improve specific code

## Purpose

Continuous self-improvement with built-in validation to prevent complexity creep.

## Stage 2: Reflection and Improvement

Use `/reflect` to analyze sessions for improvement opportunities. When high-priority patterns are detected:

1. GitHub issues are created automatically with context
2. UltraThink is delegated to create PRs
3. Links to issues and PRs are provided

See `/reflect` command for AI-powered session analysis.

## New Improvement Workflow (v2)

**ALWAYS use the improvement-workflow agent for improvements:**

```markdown
Task("improvement-workflow", {
"target": "[what to improve]",
"problem": "[specific issue]",
"constraints": "[must remain simple]"
})
```

The workflow enforces:

1. **Simplicity-first validation** before any code
2. **Progressive review** at each stage
3. **Security checks** built-in
4. **Redundancy prevention** automatic
5. **Philosophy compliance** continuous

## Self-Improvement Process

### Stage 1: Problem Validation ✓

- Validate simplest approach first
- Check for existing solutions
- Max 3 components rule
- Security pre-check

### Stage 2: Minimal Implementation ✓

- Start with < 200 LOC
- No more than 3 files
- Review at natural boundaries (module completion, security code)
- Automatic simplicity check

### Stage 3: Progressive Enhancement ✓

- Justify each addition
- Parallel review (reviewer + security)
- Continuous validation
- Stop at "good enough"

### Stage 4: Final Validation ✓

- Philosophy compliance check
- Security audit
- Redundancy scan
- Simplicity score

## Improvement Areas

### Agent Enhancement

```markdown
## Agent Analysis

- Usage frequency
- Success rates
- Common failures
- Missing capabilities

## Proposed Changes

- New agent: [purpose]
- Enhanced: [agent] with [capability]
- Deprecated: [agent] because [reason]
```

### Pattern Evolution

```markdown
## Pattern Review

- Applied successfully: X times
- Failed applications: Y times
- Variations discovered

## Pattern Update

- Original: [old pattern]
- Improved: [new pattern]
- Reason: [why better]
```

### Workflow Optimization

```markdown
## Current Workflow

1. Step A (30s avg)
2. Step B (45s avg)
3. Step C (15s avg)

## Optimized Workflow

1. Step B+C parallel (45s total)
2. Step A (30s avg)
   Total: 75s → 45s improvement
```

## Metrics to Track

### Effectiveness

- Task completion rate
- Error frequency
- Time to solution
- Code quality scores

### Learning

- Patterns discovered
- Agents created/modified
- Discoveries documented
- Improvements implemented

## Self-Assessment Questions

1. What failed that shouldn't have?
2. What took longer than expected?
3. What patterns keep appearing?
4. What tools are missing?
5. What knowledge gaps exist?

## Example Using New Workflow

### Creating New Agent (OLD WAY - Don't Do)

```yaml
name: test-generator
purpose: Generate tests
# Problem: No validation, could be redundant
```

### Creating New Agent (NEW WAY - Do This)

```markdown
Task("improvement-workflow", {
"target": "agents",
"problem": "Need automated test generation",
"constraints": "Check if tester.md already does this"
})

# Workflow will:

# 1. Check for existing test capabilities

# 2. Validate if new agent is needed

# 3. Enforce minimal implementation

# 4. Review at each stage
```

### Pattern Addition

```markdown
## Pattern: Parallel Agent Execution

When: Multiple independent analyses needed
How: Use Task tool with multiple agents
Benefit: 3x faster analysis
```

### Workflow Enhancement

```markdown
## Old: Sequential Review

1. Architect analyzes
2. Builder implements
3. Reviewer checks

## New: Parallel Review

1. Architect + Reviewer analyze together
2. Builder implements with both inputs
3. Final quick review
```

## Key Lessons from PR #44

**What went wrong:**

- Created 7 agents when 2 sufficed
- 915-line test file (violated Zero-BS)
- Security issues found late
- 2000+ lines removed in review

**Why the new workflow prevents this:**

- Stage 1 would reject 7-agent design
- Stage 2 would stop at line 200 of tests
- Security check happens BEFORE code
- Continuous validation prevents accumulation

## Remember

- **Simplicity is enforced, not suggested**
- **Review early and often, not just at end**
- **Validate at 50 LOC increments**
- **Stop when it works, not when it's perfect**
- **Built-in checks prevent human oversight**

The improvement-workflow agent ensures improvements actually improve.
