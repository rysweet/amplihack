---
name: philosophy-workflow
version: 1.0.0
description: Execute PHILOSOPHY_COMPLIANCE_WORKFLOW directly for code validation against amplihack philosophy
triggers:
  - "run philosophy workflow"
  - "check philosophy compliance"
  - "validate philosophy"
invokes:
  - type: workflow
    path: .claude/workflow/PHILOSOPHY_COMPLIANCE_WORKFLOW.md
---

# Philosophy Compliance Workflow Command

Directly executes the PHILOSOPHY_COMPLIANCE_WORKFLOW.md to validate code against amplihack's core philosophy: ruthless simplicity, brick philosophy, and zero-BS implementation.

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/amplihack:philosophy-workflow [target-path]`

If no target path is provided, validates current changes or full codebase depending on context.

## Purpose

Execute the 5-phase philosophy compliance workflow explicitly to validate code against amplihack principles. Use this for deep philosophy validation beyond a quick review.

## When to Use This Command

Use this command instead of `/analyze` when:

- You need deep philosophy validation with detailed report
- Code requires comprehensive compliance analysis across multiple principles
- You want remediation guidance with specific fixes
- Pre-merge validation for critical changes
- Architecture decisions need philosophy alignment verification

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Inform user** which workflow is being used:

   ```
   Executing PHILOSOPHY_COMPLIANCE_WORKFLOW.md (5-phase validation workflow)
   Target: [path or "current changes"]
   ```

2. **Read the workflow file** using the Read tool:
   - `.claude/workflow/PHILOSOPHY_COMPLIANCE_WORKFLOW.md`

3. **Create a comprehensive todo list** using TodoWrite with all 5 phases
   - Format: `Phase N: [Phase Name] - [Specific Action]`
   - Example: `Phase 1: Scope Identification - Define target scope and applicable principles`

4. **Execute each phase systematically**, marking todos as in_progress and completed

5. **Use the specified agents** for each phase (marked with "**Use**" or "**Deploy**")

6. **Track decisions** by creating `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`

7. **Mandatory: Generate philosophy score** (A/B/C/D/F) in Phase 3

## The 5-Phase Compliance Workflow

1. **Scope Identification** - Define what to analyze and which principles apply
   - Identify target scope (file, module, directory, full codebase)
   - Check for explicit user requirements that override simplification
   - Set compliance threshold (A/B/C/D/F grading)

2. **Principle Loading** - Load and prepare philosophy principles
   - Read PHILOSOPHY.md for core principles
   - Prepare validation rules: Ruthless Simplicity, Brick Philosophy, Zero-BS Implementation
   - Set priority hierarchy: User requirements > Philosophy > Defaults

3. **Compliance Analysis** - Deploy agents for parallel analysis
   - PARALLEL EXECUTION: [philosophy-guardian, reviewer, patterns, analyzer]
   - Assign philosophy score (A/B/C/D/F) based on findings
   - Generate compliance report with specific violations

4. **Violation Remediation** - Generate specific fixes for philosophy violations
   - Check if violations relate to explicit user requirements
   - Use cleanup agent for simplification suggestions
   - Use architect agent for structural redesign if needed
   - Prioritize fixes: Critical → Important → Nice-to-have

5. **Verification** - Validate compliance or document deferred improvements
   - Re-run Phase 3 if fixes applied
   - Update philosophy score
   - Optional: Update DISCOVERIES.md with patterns found

See `.claude/workflow/PHILOSOPHY_COMPLIANCE_WORKFLOW.md` for complete phase details.

## Critical: Parallel Execution in Phase 3

**Phase 3 (Compliance Analysis) MUST use parallel agent execution for comprehensive analysis.**

Example parallel agent deployment:

```
Target: ./src/auth/
→ [philosophy-guardian(auth), reviewer(auth), patterns(auth), analyzer(auth)]
```

Each agent validates specific aspects:

- **philosophy-guardian**: Necessity, simplicity, modularity, regenerability, value
- **reviewer**: Zero-BS compliance (no stubs, TODOs, dead code)
- **patterns**: Brick philosophy (module boundaries, contracts)
- **analyzer**: Complexity metrics and abstraction layers

## Philosophy Score Rubric

Phase 3 assigns a philosophy score based on compliance:

- **A**: Exemplary alignment, zero violations
- **B**: Strong alignment, minor concerns only
- **C**: Acceptable but needs improvement
- **D**: Multiple violations, refactoring required
- **F**: Critical philosophy violations, major redesign needed

## Task Management

Always use TodoWrite to:

- Track all 5 compliance phases
- Mark progress (pending → in_progress → completed)
- Coordinate parallel agent execution in Phase 3
- Document compliance findings and remediation

## Example Flow

```
User: "/amplihack:philosophy-workflow ./src/auth"

1. Inform: "Executing PHILOSOPHY_COMPLIANCE_WORKFLOW.md (5-phase validation workflow)"
2. Read workflow: `.claude/workflow/PHILOSOPHY_COMPLIANCE_WORKFLOW.md`
3. Create TodoWrite list with all 5 phases
4. Execute Phase 1: Identify scope (./src/auth), check user requirements
5. Execute Phase 2: Load philosophy principles from PHILOSOPHY.md
6. Execute Phase 3: Deploy parallel agents for compliance analysis
   → [philosophy-guardian(auth), reviewer(auth), patterns(auth), analyzer(auth)]
   → Assign philosophy score: B (strong alignment, minor concerns)
7. Execute Phase 4: Generate remediation for identified violations
   → Cleanup agent suggests simplifying helper functions
   → No violations of explicit user requirements found
8. Execute Phase 5: Verify compliance, finalize score
   → Philosophy score: B (before) → A (after cleanup)
```

## Integration with DEFAULT_WORKFLOW

This workflow integrates with development workflow at specific steps:

- **Step 6**: Refactor and Simplify → Use Phase 4 (Violation Remediation)
- **Step 13**: Philosophy Compliance Check → Use this workflow
- **Step 15**: Final Cleanup and Verification → Run this workflow for verification

## Comparison to /analyze

| Feature                 | /analyze                  | /amplihack:philosophy-workflow |
| ----------------------- | ------------------------- | ------------------------------ |
| **Depth**               | Quick compliance check    | Deep 5-phase validation        |
| **Report Detail**       | Summary with key findings | Comprehensive report + fixes   |
| **Remediation**         | General guidance          | Specific fixes with examples   |
| **Agent Orchestration** | Single agent (reviewer)   | Multi-agent parallel (Phase 3) |
| **Philosophy Score**    | Optional                  | Mandatory (A/B/C/D/F)          |
| **Use When**            | Quick pre-commit check    | Deep pre-merge validation      |

## Critical: User Requirements Override

**MANDATORY**: Phase 1 must identify explicit user requirements that CANNOT be optimized away.

Priority hierarchy:

1. **EXPLICIT USER REQUIREMENTS** (HIGHEST - NEVER OVERRIDE)
2. **USER_PREFERENCES.md** (MANDATORY - MUST FOLLOW)
3. **PROJECT PHILOSOPHY** (Strong guidance)
4. **DEFAULT BEHAVIORS** (LOWEST - Override when needed)

Example:

```
User requested: "Keep all logging statements for debugging"
→ Phase 4 remediation MUST NOT suggest removing logs
→ Document as intentional complexity with justification
```

## Deliverables

This workflow produces:

1. **Phase 3**: Compliance report with philosophy score and specific violations
2. **Phase 4**: Remediation plan with prioritized fixes and code examples
3. **Phase 5**: Final compliance certificate or improvement roadmap
4. **Optional**: Updated DISCOVERIES.md with patterns found

## Remember

- This command provides deep philosophy validation beyond quick `/analyze` checks
- Phase 3 MUST use parallel agent execution for comprehensive analysis
- User requirements are MANDATORY and cannot be "optimized away"
- Philosophy score (A/B/C/D/F) is mandatory output
- Use for pre-merge validation of critical changes

**When in doubt**: Use `/analyze` for quick checks. Use this command for comprehensive philosophy validation with detailed reports and remediation guidance.

## Philosophy Principles Validated

This workflow validates against:

- **Ruthless Simplicity**: Unnecessary abstractions, future-proofing, over-engineering
- **Brick Philosophy**: Module boundaries, single responsibility, clear contracts
- **Zero-BS Implementation**: No stubs, TODOs, dead code, or swallowed exceptions
- **Library vs Custom**: Justified complexity decisions
- **Regeneratable Modules**: Can be rebuilt from specification
