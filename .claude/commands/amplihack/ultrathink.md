# Ultra-Think Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/ultrathink <TASK_DESCRIPTION>`

## Purpose

Deep analysis mode for complex tasks. Orchestrates multiple agents to break down, analyze, and solve challenging problems.

## Process

### Phase 1: Analysis

Use the architect agent to:

- Decompose the problem
- Identify components
- Design solution architecture
- Create specifications

### Phase 2: Implementation

Use the builder agent to:

- Implement modules from specifications
- Create self-contained components
- Write tests and documentation

### Phase 3: Review

Use the reviewer agent to:

- Check philosophy compliance
- Verify correctness
- Suggest improvements
- Ensure quality

## Agent Orchestration

### When to Use Sequential

- Architecture → Implementation → Review
- Each step depends on previous
- Building progressive context

### When to Use Parallel

- Multiple independent analyses
- Different perspectives needed
- Gathering diverse solutions

## Task Management

Always use TodoWrite to:

- Break down complex tasks
- Track progress
- Coordinate agents
- Document decisions

## Example Flow

```
1. Analyze problem with architect
2. Create specifications
3. Build with builder agent
4. Review with reviewer agent
5. Iterate if needed
```

Remember: Ultra-thinking means thorough analysis before action.
