# Microsoft Amplifier Parallel Execution Engine

**PARALLEL BY DEFAULT**: Always execute operations in parallel unless
dependencies require sequential order.

## Comprehensive Parallel Detection Framework

### RULE 1: File Operations

Batch all file operations in single tool call when multiple files are involved.

### RULE 2: Multi-Perspective Analysis

Deploy relevant agents in parallel when multiple viewpoints are needed.

### RULE 3: Independent Components

Analyze separate modules or systems in parallel.

### RULE 4: Information Gathering

Parallel information collection when multiple data sources are needed.

### RULE 5: Development Lifecycle Tasks

Execute parallel operations for testing, building, and validation phases.

### RULE 6: Cross-Cutting Concerns

Apply security, performance, and quality analysis in parallel.

## Execution Templates

### Template 1: Comprehensive Feature Development

```
[architect, security, database, api-designer, tester] for new feature
```

### Template 2: Multi-Dimensional Code Analysis

```
[analyzer, security, optimizer, patterns, reviewer] for comprehensive review
```

### Template 3: Comprehensive Problem Diagnosis

```
[analyzer, environment, patterns, logs] for issue investigation
```

### Template 4: System Preparation and Validation

```
[environment, validator, tester, ci-checker] for deployment readiness
```

### Template 5: Research and Discovery

```
[analyzer, patterns, explorer, documenter] for knowledge gathering
```

## Advanced Execution Patterns

**Parallel (Default)**

```
[analyzer(comp1), analyzer(comp2), analyzer(comp3)]
```

**Sequential (Exception - Hard Dependencies Only)**

```
architect → builder → reviewer
```

## Coordination Protocols

**Agent Guidelines:**

- Context sharing: Each agent receives full task context
- Output integration: Orchestrator synthesizes parallel results
- Progress tracking: TodoWrite manages parallel task completion

**PARALLEL-READY Agents**: `analyzer`, `security`, `optimizer`, `patterns`,
`reviewer`, `architect`, `api-designer`, `database`, `tester`, `integration`,
`cleanup`, `ambiguity`

**SEQUENTIAL-REQUIRED Agents**: `architect` → `builder` → `reviewer`,
`pre-commit-diagnostic`, `ci-diagnostic-workflow`

## Decision Framework

### When to Use Parallel Execution

- Independent analysis tasks
- Multiple perspectives on same target
- Separate components
- Batch operations

### When to Use Sequential Execution

- Hard dependencies (A output → B input)
- State mutations
- User-specified order

### Decision Matrix

| Scenario           | Use Parallel | Use Sequential |
| ------------------ | ------------ | -------------- |
| File analysis      | ✓            |                |
| Multi-agent review | ✓            |                |
| Dependencies exist |              | ✓              |

## Anti-Patterns

- **Unnecessary Sequencing**: Avoid sequential execution when tasks are independent.
- **False Dependencies**: Don't create artificial sequential dependencies.
- **Over-Sequencing**: Break complex tasks into parallel components when possible.

## Template Responses for Common Scenarios

- **New Feature Request**: Deploy parallel feature development template with architect, security, database, api-designer, and tester.
- **Bug Investigation**: Use parallel diagnostic template with analyzer, environment, patterns, and logs.
- **Code Review Request**: Apply multi-dimensional analysis with analyzer, security, optimizer, patterns, and reviewer.
- **System Analysis**: Execute comprehensive system review with all relevant agents in parallel.

## Performance Optimization

- Minimize agent overlap
- Optimize context sharing
- Track execution metrics
- Monitor parallel execution performance
- Measure time savings vs sequential
