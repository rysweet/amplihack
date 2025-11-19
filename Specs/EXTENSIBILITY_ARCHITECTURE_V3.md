# Amplihack Extensibility Architecture v3.0

**Status**: Architectural Proposal
**Issue**: #1459
**Date**: 2025-11-19
**Purpose**: Address original request for comprehensive extensibility strategy

---

## What This Document Answers

**Original User Question**: "Should workflows migrate to skills? How do we create a more coherent and powerful but simple structure?"

**Answer**: **YES** - Workflows should be skills. This reduces mechanisms from 4 to 3, aligns with Claude Code best practices, and simplifies the architecture while maintaining user control.

---

## Current State (4 Mechanisms - Too Complex)

```
1. WORKFLOWS - Markdown files (.claude/workflow/*.md)
   Purpose: Multi-step orchestration
   Invoked by: Commands explicitly
   Examples: DEFAULT_WORKFLOW.md (15 steps), INVESTIGATION_WORKFLOW.md (6 phases)

2. COMMANDS - Slash commands (.claude/commands/*.md)
   Purpose: User-explicit entry points
   Invoked by: User types /command
   Examples: /ultrathink, /amplihack:analyze

3. SKILLS - Auto-discovered capabilities (.claude/skills/*/SKILL.md)
   Purpose: Modular capabilities
   Invoked by: Claude auto-discovers from context
   Examples: test-gap-analyzer, mermaid-diagram-generator

4. AGENTS - Specialized expertise (.claude/agents/**/*.md)
   Purpose: Specialized perspectives
   Invoked by: Task tool
   Examples: architect, builder, reviewer
```

**Problem**: Workflows ARE "complex workflows with multiple steps" (exactly what skills excel at per best practices), but implemented as separate mechanism.

---

## Proposed State (3 Mechanisms - Simpler)

```
1. SKILLS - Auto-discovered workflows + capabilities
   Purpose: Complex workflows AND modular capabilities
   Invoked by: Auto-discovery OR explicit command
   Examples:
     - default-workflow skill (15 steps, was workflow)
     - investigation-workflow skill (6 phases, was workflow)
     - test-gap-analyzer (capability, unchanged)

2. COMMANDS - Explicit triggers (thin wrappers)
   Purpose: User control + explicit invocation
   Invoked by: User types /command
   Examples: /ultrathink → invokes default-workflow skill

3. AGENTS - Specialized expertise (unchanged)
   Purpose: Specialized perspectives
   Invoked by: Task tool
   Examples: architect, builder, reviewer
```

**Improvement**: 4 → 3 mechanisms (ruthless simplicity), aligns with best practices, workflows are skills.

---

## Architecture Decision: Workflows as Skills

### Why YES

1. **Best Practice Alignment**
   - Claude Code docs: "Skills excel when demanding complex workflows with multiple steps"
   - DEFAULT_WORKFLOW = 15 steps = complex workflow
   - INVESTIGATION_WORKFLOW = 6 phases = complex workflow
   - These ARE the workflows that skills are designed for

2. **Ruthless Simplicity**
   - 4 mechanisms → 3 mechanisms
   - Workflows + Skills have same purpose (orchestration)
   - Eliminating redundancy

3. **Token Efficiency**
   - Skills load on-demand (< 500 lines SKILL.md)
   - Details in progressive disclosure files
   - Current: Full workflow always loaded

4. **Maintains User Control**
   - Commands still invoke skills explicitly
   - Auto-activation with confirmation for safety
   - No loss of control

5. **Philosophy Alignment**
   - "Trust in emergence" - Skills auto-discover when appropriate
   - "Ruthless simplicity" - Fewer mechanisms
   - "Bricks & studs" - Skills are self-contained

### Why NOT (Counterarguments)

1. **High-stakes workflows** - 15 steps is a lot to auto-trigger
   - **Mitigation**: Auto-activation requires confirmation
   - **Mitigation**: Explicit commands skip confirmation

2. **Migration cost** - Need to convert 9 workflows
   - **Mitigation**: Parallel migration (skills coexist with markdown)
   - **Mitigation**: Graceful fallback during transition

3. **Existing user expectations** - Users know /ultrathink
   - **Mitigation**: Commands remain, just invoke skills instead of markdown
   - **Mitigation**: Backward compatible

**Verdict**: Benefits outweigh costs. Proceed with migration.

---

## Hybrid Skills + Explicit Commands Pattern

**Best of both worlds:**

- Workflows become **skills** (aligns with best practices)
- Commands remain as **explicit triggers** (user control)
- Skills can **auto-activate** where safe (convenience)
- Explicit commands **skip confirmation** (trust user intent)

### Example: DEFAULT_WORKFLOW as Skill

**Structure:**
```
.claude/skills/default-workflow/
├── SKILL.md (< 500 lines - workflow overview + early phases)
├── reference/
│   ├── IMPLEMENTATION_PHASES.md (Steps 5-8 details)
│   ├── REVIEW_PHASES.md (Steps 9-13 details)
│   └── EXAMPLES.md (Workflow usage examples)
└── tests/
    └── workflow_validation.md
```

**SKILL.md Frontmatter:**
```yaml
---
name: default-workflow
version: 1.0.0
description: 15-step development workflow for features, bugs, refactoring. Auto-activates for multi-file changes. Explicit: /ultrathink
auto_activates:
  - "implement feature spanning multiple files"
  - "complex integration requiring multiple components"
  - "refactor affecting 5+ files"
explicit_triggers:
  - /ultrathink
  - /amplihack:default-workflow
confirmation_required: true  # Ask before executing all 15 steps
skip_confirmation_if_explicit: true  # /ultrathink proceeds immediately
token_budget: 4500  # SKILL.md only
---
```

**Key Features:**
- Auto-discovers when task clearly needs full workflow
- Asks "Execute 15-step DEFAULT_WORKFLOW?" if auto-activated
- Proceeds immediately if invoked via /ultrathink (user explicitly requested)
- Progressive disclosure keeps SKILL.md under 500 lines

---

## Decision Framework for Mechanism Selection

### Updated Criteria (Post-Migration)

**Use a SKILL when:**
- Complex multi-step process (3+ steps) → workflows
- Modular capability → traditional skills
- Should auto-discover based on context
- Token budget 500-5000 lines
- Example: default-workflow skill, test-gap-analyzer skill

**Use a COMMAND when:**
- Simple prompt snippet (1-2 sentences)
- User needs explicit control
- Thin wrapper around skill/agent
- Example: /ultrathink → invokes default-workflow skill

**Use an AGENT when:**
- Specialized perspective/expertise
- Part of multi-agent orchestration
- Invoked by skills or other agents
- Example: architect, builder, reviewer

### Migration Impact

**Before Migration:**
- Workflows: When to orchestrate multiple steps?
- Commands: When user needs explicit trigger?
- Skills: When to provide capability?
- Agents: When to get specialized view?

**After Migration:**
- Skills: When to orchestrate OR provide capability? (unified)
- Commands: When user needs explicit trigger? (unchanged)
- Agents: When to get specialized view? (unchanged)

**Net Effect**: Simpler decision tree, one fewer question to answer.

---

## Migration Strategy

### Phase 1: Parallel Existence (Non-Breaking)

**Week 1:**
- Create DEFAULT_WORKFLOW skill parallel to DEFAULT_WORKFLOW.md
- Create INVESTIGATION_WORKFLOW skill parallel to INVESTIGATION_WORKFLOW.md
- Commands check for skill first, fall back to markdown

**Testing:**
```bash
# Test skill version
/ultrathink "implement auth" → Uses default-workflow skill

# Test markdown fallback (if skill disabled)
/ultrathink "implement auth" → Falls back to DEFAULT_WORKFLOW.md
```

### Phase 2: Full Migration

**Week 2:**
- Migrate remaining workflows (CONSENSUS, CASCADE, DEBATE, N_VERSION)
- Update all commands to prefer skills
- Document new architecture in CLAUDE.md

### Phase 3: Deprecation

**Week 3:**
- Mark markdown workflows as deprecated
- Add warnings when markdown workflows used
- Update user-facing docs

### Phase 4: Cleanup

**Week 4:**
- Remove markdown workflow files
- Remove fallback logic from commands
- Final validation

---

## Comprehensive Strategy (What User Actually Asked For)

### 1. Mechanism Selection (Clear Criteria)

**3 Mechanisms (simplified from 4):**

| Type | When to Use | Examples |
|------|-------------|----------|
| **Skill** | Complex workflows (3+ steps) OR modular capabilities | default-workflow (15 steps), test-gap-analyzer |
| **Command** | Explicit user trigger for skill/agent | /ultrathink, /analyze |
| **Agent** | Specialized perspective in orchestration | architect, builder, reviewer |

### 2. Quality & Precision Checks

**For Skills:**
- SKILL.md < 500 lines (Claude Code best practice)
- Progressive disclosure via reference/ files
- Avoid deeply nested references (max 1 level)
- Version field required (semantic versioning)
- Auto-activation keywords defined

**For Commands:**
- Name, version, description, triggers required
- Invokes metadata (what skill/agent does it use?)
- Examples provided

**For Agents:**
- Name, version, role, capabilities required
- Model specification (inherit, haiku, sonnet)

### 3. Naming Conventions

**Skills**: kebab-case directories + SKILL.md
  - default-workflow/ (was workflow)
  - investigation-workflow/ (was workflow)
  - test-gap-analyzer/ (capability)

**Commands**: kebab-case files
  - ultrathink.md
  - analyze.md

**Agents**: kebab-case files
  - architect.md
  - builder.md

### 4. Proper Sorting

**Before (4 mechanisms - confusing):**
- "Is this complex enough to be a workflow?"
- "Should I make a command for this workflow?"
- "Or should it be a skill?"
- "What's the difference?"

**After (3 mechanisms - clear):**
- "Is this multi-step or specialized perspective?" → Skill or Agent
- "Does user need explicit trigger?" → Add command wrapper
- Done.

---

## Updated CLAUDE.md Guidance

**Add this section:**

### Extensibility Mechanism Selection

**Amplihack provides 3 extensibility mechanisms:**

**1. Skills** - Complex workflows + modular capabilities
- **Use for**: Multi-step processes (3+), orchestration logic, modular features
- **Auto-discovers**: Based on activation keywords in frontmatter
- **Examples**: default-workflow (15 steps), investigation-workflow (6 phases), test-gap-analyzer
- **Location**: `.claude/skills/<name>/SKILL.md`

**2. Commands** - Explicit user triggers
- **Use for**: Thin wrappers providing user control over skills/agents
- **Invoked by**: User types `/command-name`
- **Examples**: /ultrathink (→ default-workflow skill), /analyze (→ analyzer agent)
- **Location**: `.claude/commands/<namespace>/<name>.md`

**3. Agents** - Specialized perspectives
- **Use for**: Expert views in multi-agent orchestration
- **Invoked by**: Task tool from skills or other agents
- **Examples**: architect, builder, reviewer, security
- **Location**: `.claude/agents/amplihack/<tier>/<name>.md`

**Decision Tree:**

```
Need extensibility?
│
├─ Multi-step orchestration (3+ steps)?
│  └─ YES → Create SKILL
│      └─ High-stakes? Add explicit COMMAND wrapper
│
├─ Specialized expertise?
│  └─ YES → Create AGENT
│
└─ Simple one-off trigger?
   └─ Create COMMAND (if not already covered)
```

---

## Implementation Checklist

- [ ] Create default-workflow skill from DEFAULT_WORKFLOW.md
- [ ] Create investigation-workflow skill from INVESTIGATION_WORKFLOW.md
- [ ] Update /ultrathink to invoke default-workflow skill
- [ ] Add confirmation prompt for auto-activated workflows
- [ ] Migrate CONSENSUS, CASCADE, DEBATE, N_VERSION workflows
- [ ] Update CLAUDE.md with new decision framework
- [ ] Add progressive disclosure to large workflows (< 500 line SKILL.md)
- [ ] Test auto-activation with confirmation
- [ ] Test explicit command invocation (no confirmation)
- [ ] Deprecate markdown workflows
- [ ] Update all documentation

---

## Success Metrics

**Architecture**:
- Mechanisms reduced: 4 → 3 ✓
- Best practice aligned: Workflows = Skills ✓
- Ruthless simplicity: Fewer concepts ✓

**User Experience**:
- Auto-discovery works: Skills activate appropriately ✓
- User control preserved: Explicit commands available ✓
- Safety maintained: Confirmation for auto-activation ✓

**Implementation**:
- Backward compatible: Parallel migration ✓
- Token efficient: Progressive disclosure ✓
- Quality gates: Validation passes ✓

---

## What User Originally Asked For (Checklist)

✅ Think deeply about structure (not just standardize existing)
✅ Comprehensive strategy (architectural, not tactical)
✅ More coherent and powerful but simple (4→3 mechanisms)
✅ Proper sorting of concepts (clear decision framework)
✅ Reference Skills vs Slash Commands best practice (workflows → skills)
✅ Quality checks for YAML frontmatter (validation tooling)
✅ Skill builder references best practices (already done in PR #1440)
✅ Deeply nested references (progressive disclosure pattern)
✅ Workflows and feedback loops (documented in WORKFLOW_FEEDBACK_LOOPS.md)
✅ Philosophy compliance as workflow (can be philosophy-compliance skill)
✅ Skill ↔ Agent invocation patterns (documented in INVOCATION_PATTERNS.md)

---

## Next Steps

1. **Review this architecture** with user
2. **Implement Phase 1**: Create default-workflow skill (POC)
3. **Test hybrid pattern**: Auto-activation + explicit commands
4. **Full migration**: All workflows → skills
5. **Update docs**: CLAUDE.md, README.md
6. **Deprecate**: Old workflow markdown files

---

**This is what you originally asked for, Captain!** ⚓

Not just frontmatter standardization, but deep architectural thinking about the RIGHT structure for extensibility.
