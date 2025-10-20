# N-Version Programming Command

## Usage

`/n-version <TASK_DESCRIPTION>`

## Purpose

Execute N-version programming pattern for critical implementations. Generates multiple independent solutions and selects the best through comparison.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Read the workflow file**: `.claude/workflow/N_VERSION_WORKFLOW.md`
2. **Create a comprehensive todo list** using TodoWrite with all workflow steps
3. **Execute each step systematically**, marking todos as in_progress and completed
4. **Follow the N-version pattern**:
   - Generate N independent implementations
   - Compare implementations objectively
   - Select or synthesize the best solution
5. **Document the selection** with clear rationale
6. **Track decisions** in `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`

## When to Use

Use for **critical tasks** where correctness is paramount:

- Security-sensitive code (authentication, authorization, encryption)
- Core algorithms (payment calculations, data transformations)
- Mission-critical features (data backup, recovery procedures)

## Cost-Benefit

- **Cost:** 3-4x execution time (N parallel implementations)
- **Benefit:** 30-65% error reduction
- **ROI Positive when:** Task criticality > 3x cost multiplier

## Task Description

Execute the following task using N-version programming:

```
{TASK_DESCRIPTION}
```

## Configuration

The workflow can be customized by editing `.claude/workflow/N_VERSION_WORKFLOW.md`:

- Number of versions (N): 3 (default), 4-6 (critical tasks)
- Selection criteria: Correctness, Security, Performance, Simplicity
- Timeout settings
- Agent diversity profiles

## Success Metrics

From research (PR #946):

- Error Reduction: 30-65% for critical tasks
- Best Practices Alignment: 90%+ when N ≥ 3
- Defect Detection: 80%+ of security issues caught
