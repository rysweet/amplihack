---
name: PHILOSOPHY_COMPLIANCE_WORKFLOW
version: 1.0.0
description: 5-phase workflow for validating code against amplihack philosophy principles
steps: 5
phases:
  - scope-identification
  - principle-loading
  - compliance-analysis
  - violation-remediation
  - verification
success_criteria:
  - "All philosophy principles validated"
  - "Violations identified with specific locations"
  - "Remediation guidance provided"
  - "Philosophy score assigned"
philosophy_alignment:
  - principle: Ruthless Simplicity
    application: Workflow checks for unnecessary complexity
  - principle: Brick Philosophy
    application: Validates module boundaries and contracts
  - principle: Zero-BS Implementation
    application: Detects stubs, TODOs, dead code
entry_points:
  - /analyze [path]
  - philosophy-guardian agent
  - reviewer agent with philosophy flag
references:
  workflows:
    - DEFAULT_WORKFLOW.md
  agents:
    - philosophy-guardian.md
    - reviewer.md
    - cleanup.md
customizable: true
---

# Philosophy Compliance Workflow

This workflow validates code against amplihack's core philosophy: ruthless simplicity, brick philosophy, and Zen-like minimalism.

## When This Workflow Applies

Use this workflow for:

- Philosophy compliance checks during code review (DEFAULT_WORKFLOW Step 13)
- Pre-merge validation (`/analyze` command)
- Refactoring quality assessment
- Architecture decision validation
- Any code requiring philosophy alignment verification

## The 5-Phase Compliance Workflow

### Phase 1: Scope Identification

**Purpose:** Define what code to analyze and which philosophy principles apply.

**Tasks:**

- [ ] Identify target scope (file, module, directory, or full codebase)
- [ ] Determine applicable philosophy principles (all or specific subset)
- [ ] Check for explicit user requirements that override simplification
- [ ] Set compliance threshold (A/B/C/D/F grading)
- [ ] Define output format (report, fixes, or both)

**Success Criteria:**

- Clear scope boundaries defined
- Philosophy principles selected
- User requirements documented
- Compliance threshold set

**Deliverables:**

- Scope definition with:
  - Target files/modules to analyze
  - Philosophy principles to validate
  - Explicit user requirements (CANNOT be optimized away)
  - Expected output format

### Phase 2: Principle Loading

**Purpose:** Load and prepare philosophy principles for validation.

**Tasks:**

- [ ] Read `.claude/context/PHILOSOPHY.md` for core principles
- [ ] Load decision framework (6 questions)
- [ ] Identify red flags and green patterns
- [ ] Prepare principle-specific validation rules:
  - Ruthless Simplicity: Unnecessary abstractions, future-proofing
  - Brick Philosophy: Module boundaries, single responsibility
  - Zero-BS Implementation: Stubs, TODOs, dead code, swallowed exceptions
  - Library vs Custom: Justified complexity decisions
- [ ] Set priority hierarchy: User requirements > Philosophy > Defaults

**Success Criteria:**

- Philosophy principles loaded and categorized
- Validation rules prepared for each principle
- Priority hierarchy established

**Deliverables:**

- Validation ruleset with:
  - Principle-specific checks
  - Red flag patterns
  - Green pattern expectations
  - User requirement overrides

### Phase 3: Compliance Analysis

**Purpose:** Deploy agents to analyze code against philosophy principles.

**CRITICAL: Use PARALLEL agent execution for comprehensive analysis.**

**Tasks:**

- [ ] **Deploy agents in PARALLEL:**
  - `philosophy-guardian` - Core philosophy validation
  - `reviewer` - Code quality and patterns
  - `patterns` - Identify anti-patterns and good patterns
  - `analyzer` - Deep code structure analysis (if scope is complex)
- [ ] Each agent validates specific aspects:
  - **philosophy-guardian**: Necessity, simplicity, modularity, regenerability, value
  - **reviewer**: Zero-BS compliance (no stubs, TODOs, dead code)
  - **patterns**: Brick philosophy (module boundaries, contracts)
  - **analyzer**: Complexity metrics and abstraction layers
- [ ] Collect findings from all parallel analyses
- [ ] Assign philosophy score (A/B/C/D/F) based on violations
- [ ] Generate compliance report with specific violations

**Parallel Agent Example:**

```
Target: ./src/auth/
→ [philosophy-guardian(auth), reviewer(auth), patterns(auth)]
```

**Philosophy Score Rubric:**

- **A**: Exemplary alignment, zero violations
- **B**: Strong alignment, minor concerns only
- **C**: Acceptable but needs improvement
- **D**: Multiple violations, refactoring required
- **F**: Critical philosophy violations, major redesign needed

**Success Criteria:**

- All agents completed analysis
- Violations identified with locations
- Philosophy score assigned
- Compliance report generated

**Deliverables:**

- Philosophy compliance report with:
  - Philosophy score (A/B/C/D/F)
  - Strengths (what aligns well)
  - Concerns (minor issues)
  - Violations (critical departures)
  - Specific file/line locations for each finding

### Phase 4: Violation Remediation

**Purpose:** Generate specific fixes for philosophy violations.

**Tasks:**

- [ ] **For each violation, determine fix strategy:**
  - **CRITICAL**: Check if violation relates to explicit user requirement
  - **If user required it**: Document as intentional, skip fix
  - **If not user required**: Generate remediation guidance
- [ ] **Use cleanup agent** to suggest simplifications (respecting user requirements)
- [ ] **Use architect agent** for structural redesign (if needed)
- [ ] Generate concrete fix recommendations:
  - What to remove (dead code, unnecessary abstractions)
  - What to simplify (complex logic, deep hierarchies)
  - What to restructure (module boundaries)
  - What to document (justified complexity)
- [ ] Prioritize fixes: Critical → Important → Nice-to-have
- [ ] Provide code examples for complex fixes

**Success Criteria:**

- All violations have remediation guidance
- User requirements respected and not "optimized away"
- Fixes prioritized by impact
- Code examples provided where helpful

**Deliverables:**

- Remediation plan with:
  - Immediate fixes (critical violations)
  - Structural improvements (module boundaries)
  - Simplification opportunities
  - Intentional complexity justifications
  - Code examples for key fixes

### Phase 5: Verification

**Purpose:** Validate that compliance is achieved or improvements documented.

**Tasks:**

- [ ] **If fixes were applied**, re-run Phase 3 analysis to verify improvement
- [ ] **If fixes not applied**, ensure all violations documented with:
  - Reason for deferral (user requirement, justified complexity, technical debt)
  - Issue tracking (GitHub issue if needed)
- [ ] Update philosophy score based on remediation
- [ ] Generate final compliance certificate or improvement roadmap
- [ ] **Optional**: Update `.claude/context/DISCOVERIES.md` with patterns found

**Success Criteria:**

- Compliance status verified (pass/fail/deferred)
- Philosophy score finalized
- All decisions documented
- Knowledge captured for future reference

**Deliverables:**

- Final compliance report with:
  - Before/after philosophy scores
  - Compliance status (pass/fail/in-progress)
  - Remaining violations with justifications
  - Knowledge capture (patterns, lessons learned)

## Integration Points

### With DEFAULT_WORKFLOW.md

- **Step 13**: Philosophy Compliance Check → Use this workflow
- **Step 6**: Refactor and Simplify → Use Phase 4 (Violation Remediation)
- **Step 15**: Final Cleanup → Run this workflow for verification

### With Commands

- `/analyze [path]` → Runs this workflow with default settings
- `/ultrathink` → Can invoke this workflow for philosophy validation
- `/improve` → Uses findings for self-improvement

### With Agents

- `philosophy-guardian` → Core agent for Phase 3
- `reviewer` → Supporting agent for Phase 3
- `cleanup` → Key agent for Phase 4
- `architect` → Used in Phase 4 for structural redesign

## Quick Invocation Examples

```bash
# Full codebase philosophy check
/analyze

# Specific module check
/analyze ./src/auth

# Within DEFAULT_WORKFLOW Step 13
→ Run PHILOSOPHY_COMPLIANCE_WORKFLOW.md on current changes

# After refactoring
→ Run Phase 3 (Compliance Analysis) to verify improvements
```

## Customization

To customize this workflow:

1. Edit Phase 3 to add project-specific validation rules
2. Adjust philosophy score rubric in Phase 3
3. Modify agent deployment strategy for your needs
4. Add project-specific red flags or green patterns

## Remember

- **User requirements are MANDATORY** - Never optimize away explicit user requests
- **Simplicity is the default** - Complexity needs justification
- **Bricks over monoliths** - Validate module boundaries aggressively
- **Zero-BS always** - No stubs, TODOs, or dead code tolerated
- **Philosophy is guidance** - Not dogma; justified violations are acceptable
