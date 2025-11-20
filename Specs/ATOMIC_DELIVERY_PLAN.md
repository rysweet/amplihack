# Atomic Delivery Plan - Option A (5 Sequential PRs)

**Strategy**: Break comprehensive extensibility work into 5 safe, reviewable PRs

---

## PR Sequence (Dependencies → Delivery Order)

### PR #1: Frontmatter Standardization & Validation
**Branch**: `feat/frontmatter-standardization`
**Base**: `main`
**Dependencies**: None
**Risk**: LOW

**Scope:**
- Add YAML frontmatter to ALL agents (35 files): name, version, role
- Add YAML frontmatter to ALL commands (30 files): name, version, description, triggers
- Add YAML frontmatter to ALL existing skills (41 files): version field
- Create FRONTMATTER_STANDARDS.md
- Create validate_frontmatter.py tool
- Add pre-commit hook for validation

**Deliverable**: 116 components with valid frontmatter, automated validation

**Review Time**: ~20 minutes (metadata only, no behavior changes)

**Value**: Foundation for all subsequent work, validation prevents future issues

---

### PR #2: Core Workflow Skills (DEFAULT + INVESTIGATION)
**Branch**: `feat/core-workflow-skills`
**Base**: `main` (merge after PR #1)
**Dependencies**: PR #1 (for frontmatter standards)
**Risk**: LOW

**Scope:**
- Create default-workflow skill from DEFAULT_WORKFLOW.md
- Create investigation-workflow skill from INVESTIGATION_WORKFLOW.md
- Keep markdown workflows (parallel existence)
- No command changes yet (commands still use markdown)

**Deliverable**: 2 workflow skills, parallel to existing workflows

**Review Time**: ~30 minutes (review skill structure, no behavior impact)

**Value**: Proves workflows-as-skills pattern, safe parallel migration

---

### PR #3: Command Updates (Use Skills Instead of Markdown)
**Branch**: `feat/commands-use-workflow-skills`
**Base**: `main` (merge after PR #2)
**Dependencies**: PR #2 (workflow skills must exist)
**Risk**: MEDIUM

**Scope:**
- Update /ultrathink to invoke default-workflow skill
- Update /amplihack:investigation-workflow to invoke skill
- Add fallback to markdown if skill not found (safety)
- Test skill invocation vs markdown fallback

**Deliverable**: Commands use skills, graceful degradation if issues

**Review Time**: ~25 minutes (review invocation changes, test fallback)

**Value**: Activates workflows-as-skills architecture

---

### PR #4: Specialized Workflow Skills
**Branch**: `feat/specialized-workflow-skills`
**Base**: `main` (merge after PR #3)
**Dependencies**: PR #1, PR #3 (patterns established)
**Risk**: LOW

**Scope:**
- Create consensus-workflow skill
- Create cascade-workflow skill
- Create debate-workflow skill
- Create n-version-workflow skill
- Create philosophy-compliance-workflow skill
- Update related commands to use skills

**Deliverable**: All workflows migrated to skills

**Review Time**: ~35 minutes (5 skills, less critical than core workflows)

**Value**: Complete migration, full architecture realized

---

### PR #5: Architecture Documentation & Cleanup
**Branch**: `feat/extensibility-architecture-docs`
**Base**: `main` (merge after PR #4)
**Dependencies**: PR #1-4 (all implementation complete)
**Risk**: LOW

**Scope:**
- Update CLAUDE.md with 3-mechanism architecture
- Deprecate markdown workflows (add warnings)
- Create migration guide
- Update README.md
- Generate component catalog
- Final validation pass

**Deliverable**: Complete documentation, deprecated old system

**Review Time**: ~20 minutes (docs only)

**Value**: Completes migration, guides users to new architecture

---

## PR #6 (Separate Experimental): Ultrathink as Default Skill
**Branch**: `experiment/ultrathink-as-default-skill`
**Base**: `main` (after PR #5, or independent)
**Dependencies**: PR #1-5 (or can be standalone experiment)
**Risk**: MEDIUM (changes fundamental behavior)

**Scope:**
- Create ultrathink-orchestrator skill
- Auto-activates on: "any work request not matching specific skill"
- LOW priority (other skills checked first)
- Add safeguards: confirmation required, complexity estimation
- Compare to current /ultrathink command approach

**Purpose**: Exploration, not guaranteed merge

**Deliverable**: Proof-of-concept of ultrathink auto-invocation

**Review Time**: ~40 minutes (controversial, needs discussion)

**Value**: Proves or disproves viability of "default fallback skill" concept

---

## Timeline (Option A)

**Week 1**:
- Monday: Create & merge PR #1 (frontmatter)
- Wednesday: Create & merge PR #2 (core workflow skills)
- Friday: Create PR #3 (command updates)

**Week 2**:
- Monday: Review & merge PR #3
- Wednesday: Create & merge PR #4 (specialized workflows)
- Friday: Create & merge PR #5 (docs)

**Week 3** (Optional):
- Create PR #6 (ultrathink-as-default experiment)
- Evaluate, decide to merge or close

**Total Timeline**: 2-3 weeks for full migration

---

## Benefits of Option A

**1. Reviewability**:
- Each PR < 100 files
- Single clear purpose
- 20-40 minute review time

**2. Safety**:
- Incremental changes
- Easy to revert
- Test at each stage

**3. Early Value**:
- PR #1 delivers validation immediately
- PR #2 proves architecture
- Don't wait for everything

**4. Flexibility**:
- Can stop after PR #3 if issues
- Can adjust based on feedback
- Not all-or-nothing

**5. Learning**:
- Each PR teaches lessons for next
- Refine approach iteratively

---

## Risks & Mitigation

**Risk 1**: Parallel existence of workflows + skills could confuse users
- **Mitigation**: Clear docs, commands prefer skills, warnings on markdown

**Risk 2**: 5 PRs might conflict if main moves forward
- **Mitigation**: Rebase each PR before merge, quick review cycle

**Risk 3**: PR #6 (ultrathink-as-default) might be rejected
- **Mitigation**: Clearly marked as experiment, user decides fate

---

## Comparison to Other Options

| Factor | Option A (5 PRs) | Option B (3 PRs) | Option C (1 PR) |
|--------|------------------|------------------|-----------------|
| Review Time | 20-40 min each | 40-60 min each | 90+ min |
| Risk Per PR | LOW | MEDIUM | HIGH |
| Revert Ease | EASY | MODERATE | HARD |
| Value Delivery | FAST | MODERATE | SLOW |
| Conflicts | LOW | MEDIUM | HIGH |
| User Recommended | ✅ YES | Maybe | No |

**User said**: "I want to review carefully" → Option A optimal for careful review

---

## Next Steps (Awaiting Confirmation)

**If approved:**
1. Close PR #1440
2. Create PR #1 (frontmatter) from current work
3. Get quick review & merge
4. Create PR #2 (core workflows)
5. Continue sequence...
6. Create PR #6 (ultrathink experiment) in parallel

**Awaiting**: Final confirmation to proceed with Option A

---

**Ready to execute, Captain!** ⚓

This plan gives ye 5 small, reviewable PRs (20-40 min each) plus an experimental PR fer ultrathink-as-default exploration.
