# GitHub Copilot Command Reference: n-version

**Source**: `.claude/commands/amplihack/n-version.md`

---

## Command Metadata

- **name**: amplihack:n-version
- **version**: 1.0.0
- **description**: N-version programming for Byzantine-robust critical implementations
- **triggers**: 
- **invokes**: 
- **- type**: workflow
- **path**: .claude/workflow/N_VERSION_WORKFLOW.md
- **philosophy**: 
- **- principle**: Analysis First
- **application**: Compares implementations to select best
- **dependencies**: 
- **required**: 
- **optional**: 
- **examples**: 
- **- "/amplihack**: n-version Create password hashing function"

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/n-version.md

# Use patterns from this command
gh copilot suggest --context .github/commands/n-version.md "your task"
```

---

## Original Command Documentation


# N-Version Programming Command

## Usage

`/amplihack:n-version <TASK_DESCRIPTION>`

## Purpose

Execute N-version programming pattern for critical implementations. Generates multiple independent solutions and selects the best through comparison.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Import the orchestrator**:

   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path.cwd() / ".claude/tools/amplihack"))
   from orchestration.patterns.n_version import run_n_version
   ```

2. **Execute the pattern**:

   ```python
   result = run_n_version(
       task_prompt="{TASK_DESCRIPTION}",
       n=3,  # or custom value
       working_dir=Path.cwd()
   )
   ```

3. **Display results**:
   - Show selected implementation
   - Explain rationale for selection
   - Report session_id for traceability
   - Link to logs: `.claude/runtime/logs/n_version_<timestamp>/`

4. **Manual fallback** (if orchestrator unavailable):
   - Read workflow: `.claude/workflow/N_VERSION_WORKFLOW.md`
   - Execute steps manually with TodoWrite tracking

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
