# PR #1461 Comprehensive Implementation Plan

**Based on User Requirements**: Synthesize best of #1440 + #1461 + new requirements

---

## User Requirements (Detailed)

1. **Keep useful items from PR #1440**
   - Frontmatter validation tool
   - Ensure ALL agents, commands, skills have valid frontmatter

2. **Review frontmatter descriptions for precision**
   - Not too broad (prevent wrong invocations)
   - Include specific triggers
   - Follow best practice: "Extract text from PDFs" not "Helps with documents"

3. **Skills should encourage subagent usage**
   - Workflow skills should delegate to architect, builder, reviewer
   - Document which agents to use at each phase

4. **Deep review of best practices + original prompt**
   - Skills < 500 lines (progressive disclosure)
   - Avoid deeply nested references (max 1 level)
   - Precise descriptions for auto-activation
   - Token-efficient loading

5. **Make ultrathink a DEFAULT skill**
   - Auto-invokes when user asks for work
   - Absent more specific skill match
   - Becomes fallback orchestrator

6. **Wrap all in PR #1461**
   - Single cohesive PR
   - Clean architecture
   - Fully implemented

7. **Propose atomic breakout**
   - How to split into smaller PRs?
   - What's the dependency order?
   - Incremental delivery strategy

---

## Implementation Checklist for PR #1461

### Phase 1: Foundation from #1440 (Useful Items)

- [ ] Add frontmatter validation tool (validate_frontmatter.py)
- [ ] Ensure ALL agents have: name, version, role frontmatter
- [ ] Ensure ALL commands have: name, version, description, triggers
- [ ] Ensure ALL skills have: name, version, description, auto_activates
- [ ] Create FRONTMATTER_STANDARDS.md (reference doc)

### Phase 2: Description Precision Review

- [ ] Review ALL workflow skill descriptions
  - [ ] default-workflow: Specific triggers (not "implement feature")
  - [ ] investigation-workflow: Specific triggers (not "understand code")
  - [ ] Each: "Use when [specific pattern]"

- [ ] Review ALL capability skill descriptions
  - [ ] test-gap-analyzer: "Identifies untested functions" (not "helps with testing")
  - [ ] mermaid-diagram-generator: "Converts descriptions to Mermaid" (not "creates diagrams")

- [ ] Add trigger keywords to frontmatter for each skill
  - Based on actual use cases
  - Not too broad (prevents false positives)

### Phase 3: Subagent Guidance in Skills

- [ ] default-workflow skill: Document agent usage at each step
  ```markdown
  ### Step 4: Research and Design
  - **Use** architect agent for solution architecture
  - **Use** api-designer for API contracts
  - **Use** database agent for data models
  ```

- [ ] investigation-workflow skill: Document parallel agent deployment
  ```markdown
  ### Phase 3: Deep Dives (Parallel)
  - Deploy analyzer, patterns, knowledge-archaeologist in parallel
  ```

- [ ] All workflow skills: Clear "When to invoke which agent" guidance

### Phase 4: Ultrathink as DEFAULT Skill

**Key Insight from Best Practices**: Skills should be specific. If ultrathink auto-invokes for "any work request", it's too broad.

**Better Approach**:
- Keep ultrathink as command (explicit orchestrator)
- Make default-workflow auto-invoke for "implement feature"
- Make investigation-workflow auto-invoke for "investigate X"
- Let skill auto-discovery choose the right workflow

**Rationale**: Per best practices, descriptions should be precise. "Auto-invoke for any work" is opposite of precise.

**Alternative** (if user insists):
- Create "work-orchestrator" skill that acts as fallback
- Auto-activates ONLY when no other skill matches
- Low priority (other skills checked first)

### Phase 5: Complete PR #1461

- [ ] All workflow skills created (DONE)
- [ ] Frontmatter validated for all components
- [ ] Descriptions precise and trigger-specific
- [ ] Subagent guidance added
- [ ] CLAUDE.md updated with 3-mechanism architecture
- [ ] Migration guide created
- [ ] Testing plan

---

## Atomic Breakout Proposal

### Option A: Sequential Delivery (Safest)

**PR 1**: Frontmatter Standardization (from #1440)
- Add frontmatter to agents, commands, existing skills
- Create validation tool
- No behavioral changes
- **Risk**: Low - metadata only

**PR 2**: Workflow Skills Creation
- Create 6 workflow skills parallel to markdown
- No deprecation yet
- **Risk**: Low - parallel existence

**PR 3**: Command Updates
- Update /ultrathink and related commands to use skills
- Fallback to markdown if skill not found
- **Risk**: Medium - changes invocation

**PR 4**: Architecture Documentation
- Update CLAUDE.md with 3-mechanism model
- Migration guides
- Deprecate markdown workflows
- **Risk**: Low - docs only

**PR 5**: Final Migration
- Remove markdown workflow files
- Remove fallback logic
- **Risk**: High - breaking if issues

### Option B: Feature-Based Delivery (Faster)

**PR 1**: Core Workflow Skills
- default-workflow + investigation-workflow skills
- Update /ultrathink
- Keep other workflows as markdown
- **Risk**: Medium - partial migration

**PR 2**: Specialized Workflow Skills
- consensus, cascade, debate, n-version, philosophy-compliance
- Complete migration
- **Risk**: Low - less commonly used

**PR 3**: Frontmatter + Validation
- Standardize across all components
- Validation tooling
- **Risk**: Low

### Option C: Big Bang (Current Approach)

**PR 1461**: Everything at once
- All workflows as skills
- All frontmatter
- Architecture docs
- **Risk**: High - large surface area for review

---

## Recommendation

Given user wants to "review carefully," recommend **Option A: Sequential Delivery**

**Advantages**:
- Each PR is reviewable in < 30 min
- Clear scope per PR
- Low risk incremental changes
- Easy to revert if issues
- Can ship value faster (frontmatter validation useful immediately)

**Timeline**:
- Week 1: PR1 (frontmatter) + PR2 (workflow skills)
- Week 2: PR3 (command updates) + PR4 (docs)
- Week 3: PR5 (final migration)

---

## Critical Questions for User

1. **Ultrathink as DEFAULT skill**: Do you want it to auto-invoke for "any work request"? (This violates "precise descriptions" best practice)

2. **Atomic breakout**: Option A (sequential, 5 PRs), Option B (feature-based, 3 PRs), or Option C (big bang, 1 PR)?

3. **Frontmatter scope**: All components or just workflows/skills?

4. **Migration timing**: Parallel coexistence (safe) or immediate replacement (risky)?

---

## Next Steps (Awaiting Decision)

**If Option A chosen**:
1. Close #1440
2. Split #1461 into 5 atomic PRs
3. Deliver sequentially

**If Option B chosen**:
1. Close #1440
2. Split #1461 into 3 feature PRs
3. Deliver in parallel where possible

**If Option C chosen**:
1. Close #1440
2. Complete all work in #1461
3. Single comprehensive review

**Awaiting your call, Captain!** ⚓
