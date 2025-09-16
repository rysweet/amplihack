# Improve Command

## Usage
`/improve [target]`

Target can be:
- `self` - Improve the AI system itself
- `agents` - Enhance agent definitions
- `patterns` - Update pattern library
- `<path>` - Improve specific code

## Purpose
Continuous self-improvement and learning from experience.

## Self-Improvement Process

### 1. Analyze Current State
- Review `.claude/runtime/metrics/`
- Check `.claude/runtime/logs/`
- Examine DISCOVERIES.md
- Assess agent effectiveness

### 2. Identify Improvements
- Performance bottlenecks
- Repeated failures
- Missing capabilities
- Inefficient patterns

### 3. Generate Updates
- New agent definitions
- Updated patterns
- Enhanced commands
- Improved workflows

### 4. Document Learning
- Update DISCOVERIES.md
- Add to PATTERNS.md
- Enhance agent descriptions
- Create new tools

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

## Example Improvements

### New Agent Creation
```yaml
name: test-generator
purpose: Automatically generate comprehensive tests
trigger: After builder creates new module
capability: Analyze code and create test cases
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

## Remember

- Every failure is a learning opportunity
- Document what works and what doesn't
- Small improvements compound over time
- The system should get smarter with use
- Share learnings through documentation

Self-improvement is not a task, it's a continuous process.