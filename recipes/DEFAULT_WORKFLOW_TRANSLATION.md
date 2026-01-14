# DEFAULT_WORKFLOW Translation Guide

**Source:** `.amplifier/context/source-workflows/DEFAULT_WORKFLOW.md` (v1.1.0)
**Target:** `.amplifier/recipes/default-workflow.yaml` (v1.0.0)

This document explains how the original 22-step Claude Code workflow was translated into an Amplifier staged recipe.

---

## Translation Summary

| Aspect | Original | Amplifier Recipe |
|--------|----------|------------------|
| Steps | 22 sequential steps (0-21) | 32 recipe steps across 6 stages |
| Phases | 6 phases | 6 stages with approval gates |
| Mandatory Checkpoints | Steps 0, 10, 16, 17 | Approval gates at all stages, MANDATORY flags at stages 5-6 |
| Agents | ~20 specialized agents | 6 foundation agents with modes |
| Execution Model | Interactive with TodoWrite | Automated with human approval gates |

---

## Stage Mapping

### Stage 1: setup (Steps 0-1)

| Original Step | Recipe Step ID | Purpose |
|---------------|----------------|---------|
| Step 0: Workflow Preparation | `step-0-workflow-init` | Create work plan and tracking |
| Step 1: Prepare Workspace | `step-1-workspace-prep` | Git clean state verification |

**Approval Gate:** Review work plan before proceeding

### Stage 2: requirements (Steps 2-4)

| Original Step | Recipe Step ID | Purpose |
|---------------|----------------|---------|
| Step 2: Rewrite/Clarify Requirements | `step-2-clarify-requirements` | Requirements analysis |
| Step 3: Create GitHub Issue | `step-3-create-issue`, `step-3-execute-issue-creation` | Issue specification and creation |
| Step 4: Setup Worktree/Branch | `step-4-setup-branch`, `step-4-execute-branch-setup` | Branch planning and setup |

**Approval Gate:** Review requirements and issue before design

### Stage 3: design (Steps 5-6)

| Original Step | Recipe Step ID | Purpose |
|---------------|----------------|---------|
| Step 5: Research and Design | `step-5-architecture`, `step-5-security-requirements` | Architecture and security design |
| Step 6: Retcon Documentation | `step-6-write-documentation`, `step-6-design-review` | Pre-implementation docs |

**Approval Gate:** Review design before implementation

### Stage 4: implementation (Steps 7-9)

| Original Step | Recipe Step ID | Purpose |
|---------------|----------------|---------|
| Step 7: TDD - Write Tests | `step-7-write-tests`, `step-7-verify-tests-fail` | Test-first development |
| Step 8: Implement Solution | `step-8-implement`, `step-8-integration` | Implementation and integration |
| Step 9: Refactor/Simplify | `step-9-refactor`, `step-9-verify-no-placeholders` | Cleanup and zero-BS verification |

**Approval Gate:** Review implementation before mandatory review stage

### Stage 5: pre-commit-review (Steps 10-13) - MANDATORY

| Original Step | Recipe Step ID | Purpose |
|---------------|----------------|---------|
| Step 10: Review Pass (MANDATORY) | `step-10-code-review`, `step-10-security-review`, `step-10-philosophy-check` | Comprehensive review |
| Step 11: Incorporate Feedback | `step-11-assess-feedback`, `step-11-implement-feedback` | Address review items |
| Step 12: Run Tests/Pre-commit | `step-12-run-tests`, `step-12-diagnose-failures` | Test execution guidance |
| Step 13: Local Testing | `step-13-test-plan` | Manual test plan |

**Approval Gate:** MANDATORY - Must pass before PR creation

### Stage 6: pr-and-merge (Steps 14-21) - MANDATORY

| Original Step | Recipe Step ID | Purpose |
|---------------|----------------|---------|
| Step 14: Commit and Push | `step-14-commit-message`, `step-14-git-commands` | Commit preparation |
| Step 15: Open Draft PR | `step-15-pr-description` | PR creation |
| Step 16: Review PR (MANDATORY) | `step-16-pr-review`, `step-16-security-final` | Final PR review |
| Step 17: Implement Feedback (MANDATORY) | `step-17-final-feedback` | Address final feedback |
| Step 18: Philosophy Check | `step-18-final-philosophy` | Final philosophy verification |
| Step 19: Final Cleanup | `step-19-cleanup` | Remove artifacts |
| Step 20: Ready for Review | `step-20-ready-pr` | Convert draft to ready |
| Step 21: Ensure Mergeable | `step-21-check-mergeable`, `step-21-ci-diagnostics`, `workflow-complete` | Merge readiness |

**Approval Gate:** MANDATORY - Final gate before merge

---

## Agent Mapping

### Primary Mappings

| Original Agent | Amplifier Agent | Mode | Usage |
|----------------|-----------------|------|-------|
| architect | `foundation:zen-architect` | ARCHITECT | System design, architecture |
| zen-architect | `foundation:zen-architect` | ARCHITECT | High-level review |
| builder | `foundation:modular-builder` | - | Implementation |
| reviewer | `foundation:zen-architect` | REVIEW | Code review |
| tester | `foundation:test-coverage` | - | Test writing |
| security | `foundation:security-guardian` | - | Security analysis |
| cleanup | `foundation:post-task-cleanup` | - | Code cleanup |

### Consolidated Mappings

These original agents were consolidated into foundation agents with specific prompts:

| Original Agent | Mapped To | Rationale |
|----------------|-----------|-----------|
| prompt-writer | `foundation:explorer` | Requirements clarification |
| analyzer | `foundation:explorer` | Codebase analysis |
| ambiguity | `foundation:explorer` | Ambiguity detection |
| api-designer | `foundation:zen-architect` (ARCHITECT) | API design is architecture |
| database | `foundation:zen-architect` (ARCHITECT) | Data model is architecture |
| documentation-writer | `foundation:zen-architect` (ARCHITECT) | Doc structure is architecture |
| philosophy-guardian | `foundation:zen-architect` (REVIEW) | Philosophy is review concern |
| patterns | `foundation:zen-architect` (REVIEW) | Pattern compliance is review |
| optimizer | `foundation:performance-optimizer` | Direct mapping |
| integration | `foundation:integration-specialist` | Direct mapping |

### Operations Handled by Bash Steps

| Original Agent | Implementation | Rationale |
|----------------|----------------|-----------|
| worktree-manager | Bash steps with git commands | Direct shell operations |
| ci-diagnostic-workflow | `foundation:bug-hunter` + bash | Diagnostics need investigation |
| pre-commit-diagnostic | `foundation:bug-hunter` + bash | Pre-commit is shell-based |

---

## Philosophy Alignment

### How Philosophy Principles Are Enforced

| Principle | Enforcement Mechanism |
|-----------|----------------------|
| **Ruthless Simplicity** | `step-9-refactor` cleanup, `step-10-philosophy-check`, `step-18-final-philosophy` |
| **Zero-BS Implementation** | `step-9-verify-no-placeholders`, explicit checks in implementation prompts |
| **Test-Driven Development** | `step-7-write-tests` runs BEFORE `step-8-implement` |
| **Modular Design** | Architecture review in `step-5`, boundary checks in `step-19-cleanup` |

### Mandatory Steps Translation

| Original Mandatory | Recipe Enforcement |
|--------------------|-------------------|
| Step 0 | Stage 1 approval gate |
| Step 10 | Stage 5 marked as MANDATORY, explicit gate |
| Step 16 | Stage 6 marked as MANDATORY |
| Step 17 | Stage 6 marked as MANDATORY |

---

## Key Design Decisions

### 1. Staged vs Flat Recipe

**Decision:** Use staged recipe with approval gates

**Rationale:**
- Original workflow has mandatory checkpoints (Steps 0, 10, 16, 17)
- Human oversight is essential for code review quality
- Staged mode allows pausing and resuming
- Approval gates enforce mandatory review points

### 2. Step Splitting

**Decision:** Some original steps split into multiple recipe steps

**Examples:**
- Step 5 → `step-5-architecture` + `step-5-security-requirements`
- Step 10 → `step-10-code-review` + `step-10-security-review` + `step-10-philosophy-check`

**Rationale:**
- Single-responsibility principle for steps
- Different agents handle different concerns
- Better observability and debugging
- Parallel execution potential (future)

### 3. Bash Steps for Git Operations

**Decision:** Use `type: "bash"` for git operations instead of agents

**Rationale:**
- Git operations are deterministic (no LLM needed)
- Faster execution
- More reliable (exact commands)
- Easier to debug

### 4. Context Flow

**Decision:** Extensive use of output variables for context passing

**Key Outputs:**
```
work_plan → refined_requirements → architecture_design → test_code → 
implementation_code → refactored_code → feedback_implemented_code → 
final_implementation → final_output
```

**Rationale:**
- Each step builds on previous results
- Clear data flow through workflow
- Enables resumption from any point
- Full audit trail

### 5. Error Handling Strategy

**Decision:** Mix of fail-fast and continue-on-error

| Step Type | Strategy | Rationale |
|-----------|----------|-----------|
| Critical steps | `on_error: "fail"` (default) | Must succeed for workflow to continue |
| Git/bash operations | `on_error: "continue"` | Informational, manual fallback available |
| Optional validations | `on_error: "continue"` | Nice-to-have but not blocking |

---

## Differences from Original

### What's Different

1. **Execution Model**
   - Original: Interactive, uses TodoWrite for tracking
   - Recipe: Automated with approval gates for human checkpoints

2. **Agent Granularity**
   - Original: ~20 specialized agents
   - Recipe: 6 foundation agents with modes and specific prompts

3. **Git Operations**
   - Original: Dedicated worktree-manager agent
   - Recipe: Bash steps with git commands (more direct)

4. **Issue/PR Creation**
   - Original: Agents create directly
   - Recipe: Generates specs/commands for human execution (safer)

5. **Testing Execution**
   - Original: Agents run tests
   - Recipe: Provides test plans and commands (human executes)

### What's Preserved

1. **22-Step Structure** - All steps are represented
2. **6 Phases** - Mapped to 6 stages
3. **Mandatory Checkpoints** - Enforced via approval gates
4. **Philosophy Alignment** - Explicit verification steps
5. **TDD Order** - Tests before implementation
6. **Review Depth** - Multiple review passes

---

## Usage Guide

### Running the Workflow

```bash
# Basic execution
amplifier run "execute default-workflow.yaml with task_description='Add user authentication'"

# With options
amplifier run "execute default-workflow.yaml with task_description='Fix login bug' target_branch='develop' use_worktree='true'"
```

### Approval Workflow

When a stage completes:
1. Recipe pauses at approval gate
2. Review the stage outputs
3. Approve or deny:
   ```bash
   # List pending approvals
   amplifier run "list pending approvals"
   
   # Approve to continue
   amplifier run "approve recipe session <session-id> stage <stage-name>"
   
   # Deny to stop
   amplifier run "deny recipe session <session-id> stage <stage-name>"
   
   # Resume after approval
   amplifier run "resume recipe session <session-id>"
   ```

### Context Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `task_description` | Yes | - | What to implement |
| `target_branch` | No | `main` | Base branch |
| `use_worktree` | No | `false` | Use git worktrees |
| `auto_create_issue` | No | `true` | Create GitHub issue |
| `severity_threshold` | No | `high` | Security scan threshold |

---

## Future Improvements

### Potential Enhancements

1. **Parallel Execution**
   - Security and performance reviews could run in parallel
   - Multiple file analysis with `foreach`

2. **Sub-Recipe Extraction**
   - Security audit as reusable sub-recipe
   - PR workflow as sub-recipe

3. **CI Integration**
   - Actual test execution (not just commands)
   - CI status polling

4. **Issue/PR Automation**
   - Direct GitHub API integration
   - Auto-linking issues to PRs

5. **Metrics Collection**
   - Time per stage
   - Review iteration count
   - Philosophy compliance scores

---

## Troubleshooting

### Common Issues

**Stage approval timeout:**
- Default timeout is 1-4 hours depending on stage
- Resume with `amplifier run "resume recipe session <id>"`

**Agent not found:**
- Ensure `foundation` bundle is loaded
- Check agent names match exactly

**Git operations fail:**
- Recipe provides commands but doesn't execute destructive operations
- Run git commands manually if bash steps fail

**Context variable undefined:**
- Check spelling in prompts
- Verify previous step has `output` field
- Check step order (dependencies)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024 | Initial translation from DEFAULT_WORKFLOW v1.1.0 |

---

**See Also:**
- Original workflow: `.amplifier/context/source-workflows/DEFAULT_WORKFLOW.md`
- Recipe schema: `@recipes:docs/RECIPE_SCHEMA.md`
- Best practices: `@recipes:docs/BEST_PRACTICES.md`
