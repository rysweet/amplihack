# Amplihack → Amplifier Feature Mapping

This document maps all amplihack features to their Amplifier equivalents.

---

## Executive Summary

| Amplihack Feature | Count | Amplifier Equivalent | Strategy |
|-------------------|-------|---------------------|----------|
| SlashCommands | 25+ | Recipes + Agents | Convert interactive commands to recipes, delegate to agents |
| Skills | 100+ | Context files + Skills | Curate essential skills, most as context @mentions |
| Workflows | 8 | Recipes | Direct port to recipe YAML format |
| Agents | 35+ | Agents | Port unique agents, use foundation for overlaps |
| Hooks | 5 | Hooks | Map to Amplifier hook events |
| Context Files | 16 | Context files | Direct port to context/ directory |
| Templates | 8 | Context files | Templates as @mentionable context |
| Scenarios | 6 | Recipes or Tools | Complex scenarios → recipes |
| Profiles | 3 | Bundle variants | Different bundle.md files or behaviors |

---

## 1. SlashCommands → Recipes + Agents

### Strategy
- **Workflow commands** (ddd/*, modular-build) → **Recipes**
- **Specialist invocations** (expert-panel, debate) → **Agents** 
- **Session management** (lock, unlock, reflect) → **Hooks** or deprecate (Amplifier handles differently)

### Mapping

| Command | Type | Amplifier Implementation |
|---------|------|-------------------------|
| `/analyze` | Workflow | Recipe: `recipes/analyze.yaml` |
| `/auto` | Mode | Not needed - Amplifier is autonomous by default |
| `/cascade` | Workflow | Recipe: `recipes/cascade-fallback.yaml` |
| `/customize` | Config | User preferences in `~/.amplifier/` |
| `/debate` | Workflow | Recipe: `recipes/debate.yaml` |
| `/expert-panel` | Workflow | Recipe: `recipes/expert-panel.yaml` |
| `/fix` | Workflow | Recipe: `recipes/smart-fix.yaml` |
| `/improve` | Workflow | Recipe: `recipes/self-improvement.yaml` |
| `/ingest-code` | Tool | Could be a tool or recipe |
| `/install` | Setup | Documentation / README |
| `/knowledge-builder` | Workflow | Recipe: `recipes/knowledge-builder.yaml` |
| `/lock` / `/unlock` | Session | Deprecate - not needed in Amplifier |
| `/modular-build` | Workflow | Recipe: `recipes/modular-build.yaml` |
| `/n-version` | Workflow | Recipe: `recipes/n-version.yaml` |
| `/ps-diagnose` | Tool | Agent: `diagnostics` |
| `/reflect` | Workflow | Recipe: `recipes/reflect.yaml` |
| `/remote` | Mode | Not applicable |
| `/skill-builder` | Tool | Documentation |
| `/socratic` | Mode | Recipe: `recipes/socratic-inquiry.yaml` |
| `/transcripts` | Tool | Amplifier handles sessions natively |
| `/ultrathink` | Mode | Bundle default behavior |
| `/uninstall` | Setup | Documentation |
| `/xpia` | Security | Agent: `security` |

### DDD Commands → Recipe Suite

| Command | Recipe |
|---------|--------|
| `/ddd/0-help` | Documentation only |
| `/ddd/1-plan` | `recipes/ddd/planning.yaml` |
| `/ddd/2-docs` | `recipes/ddd/documentation.yaml` |
| `/ddd/3-code-plan` | `recipes/ddd/implementation-plan.yaml` |
| `/ddd/4-code` | `recipes/ddd/implementation.yaml` |
| `/ddd/5-finish` | `recipes/ddd/finalization.yaml` |
| `/ddd/prime` | Context file: `context/ddd-overview.md` |
| `/ddd/status` | Built into recipe state |

---

## 2. Skills → Curated Context + Skills

### Strategy
100+ skills is too many. Curate to essential categories:

### Tier 1: Essential (Include in bundle)
| Skill Category | Skills to Include | Format |
|----------------|-------------------|--------|
| **Workflows** | cascade-workflow, debate-workflow, default-workflow, investigation-workflow | Recipes |
| **Development** | code-smell-detector, design-patterns-expert, test-gap-analyzer | Skills |
| **Meta** | ultrathink-orchestrator, documentation-writing | Context files |

### Tier 2: Domain (Optional loading)
| Skill Category | Strategy |
|----------------|----------|
| Domain Analysts (23 analysts) | Skills directory - load on demand |
| Azure/DevOps | Skills directory - load on demand |
| Document formats | Skip - Amplifier has different approach |

### Tier 3: Deprecated
| Skill | Reason |
|-------|--------|
| Session management | Amplifier handles natively |
| MCP manager | Different architecture |
| Agent SDK | Different architecture |

---

## 3. Workflows → Recipes

### Direct Mapping

| Workflow | Recipe | Priority |
|----------|--------|----------|
| DEFAULT_WORKFLOW.md | `recipes/default-workflow.yaml` | HIGH - already created |
| INVESTIGATION_WORKFLOW.md | `recipes/investigation.yaml` | HIGH - already created |
| Q&A_WORKFLOW.md | `recipes/qa-flow.yaml` | HIGH - already created |
| CONSENSUS_WORKFLOW.md | `recipes/consensus.yaml` | MEDIUM |
| DEBATE_WORKFLOW.md | `recipes/debate.yaml` | MEDIUM |
| N_VERSION_WORKFLOW.md | `recipes/n-version.yaml` | LOW |
| CASCADE_WORKFLOW.md | `recipes/cascade-fallback.yaml` | LOW |

### Workflow Selector
Already created: `recipes/workflow-selector.yaml`

---

## 4. Agents → Amplifier Agents

### Overlap Analysis

| Amplihack Agent | Foundation Equivalent | Decision |
|-----------------|----------------------|----------|
| `architect` | `foundation:zen-architect` | USE FOUNDATION (richer) |
| `builder` | `foundation:modular-builder` | USE FOUNDATION |
| `reviewer` | - | CREATE AMPLIHACK (unique) |
| `tester` | `foundation:test-coverage` | USE FOUNDATION + enhance |
| `optimizer` | - | CREATE AMPLIHACK (unique) |
| `api-designer` | - | CREATE AMPLIHACK (unique) |
| `analyzer` | `foundation:explorer` | USE FOUNDATION for exploration, CREATE for analysis modes |
| `cleanup` | `foundation:post-task-cleanup` | USE FOUNDATION |
| `security` | `foundation:security-guardian` | USE FOUNDATION |
| `documentation-writer` | - | CREATE AMPLIHACK (unique Diataxis approach) |
| `integration` | `foundation:integration-specialist` | USE FOUNDATION |
| `database` | - | CREATE AMPLIHACK (unique) |
| `ambiguity` | - | CREATE AMPLIHACK (unique) |
| `patterns` | - | CREATE AMPLIHACK (unique) |
| `prompt-writer` | - | CREATE AMPLIHACK (unique) |
| `worktree-manager` | - | CREATE AMPLIHACK (unique) |
| `pre-commit-diagnostic` | - | CREATE AMPLIHACK (unique) |
| `ci-diagnostic` | - | CREATE AMPLIHACK (unique) |
| `zen-architect` | `foundation:zen-architect` | USE FOUNDATION |
| `philosophy-guardian` | - | MERGE INTO context/philosophy.md |

### Unique Amplihack Agents to Create (16 already exist)
All 16 specialized agents are already created in `.amplifier/agents/`.

### Agents to Use from Foundation (via delegation)
```yaml
# In bundle, don't recreate - just delegate to foundation agents
foundation:zen-architect      # Instead of amplihack architect
foundation:modular-builder    # Instead of amplihack builder
foundation:explorer           # Instead of amplihack analyzer (for exploration)
foundation:post-task-cleanup  # Instead of amplihack cleanup (mostly)
foundation:security-guardian  # Instead of amplihack security
foundation:integration-specialist  # Instead of amplihack integration
foundation:test-coverage      # Complements amplihack tester
foundation:git-ops            # For all git operations
foundation:bug-hunter         # For debugging
```

---

## 5. Hooks → Amplifier Hooks

### Mapping

| Amplihack Hook | Event | Amplifier Equivalent |
|----------------|-------|---------------------|
| `session_start.py` | SessionStart | `session:start` hook |
| `stop.py` | Stop | `session:end` hook |
| `pre_tool_use.py` | PreToolUse | `tool:before` hook |
| `post_tool_use.py` | PostToolUse | `tool:after` hook |
| `pre_compact.py` | PreCompact | Not directly supported |

### Implementation Strategy
Use foundation's hooks for now. The main hooks needed are already in foundation:
- `hooks-logging` - Session logging
- `hooks-streaming-ui` - Real-time UI
- `hooks-todo-reminder` - Todo reminders
- `hooks-status-context` - Git/environment context

Custom hooks (session_start context injection, reflection on stop) can be added later.

---

## 6. Context Files → Direct Port

| Amplihack File | Amplifier Location |
|----------------|-------------------|
| PHILOSOPHY.md | `context/philosophy.md` |
| PATTERNS.md | `context/patterns.md` |
| PROJECT.md | Per-project `.amplifier/AGENTS.md` |
| DISCOVERIES.md | Project runtime data |
| USER_PREFERENCES.md | `~/.amplifier/settings.yaml` |
| TRUST.md | `context/trust.md` |
| AGENT_INPUT_VALIDATION.md | Merge into agent instructions |

---

## 7. Proposed Bundle Structure

```
amplifier-amplihack/
├── bundle.md                        # THIN bundle entry point
├── behaviors/
│   └── amplihack.yaml               # Main behavior (agents + context)
├── agents/                          # 16 unique agents (DONE)
│   ├── reviewer.md
│   ├── tester.md
│   ├── optimizer.md
│   ├── api-designer.md
│   ├── analyzer.md
│   ├── ambiguity.md
│   ├── cleanup.md
│   ├── security.md
│   ├── documentation-writer.md
│   ├── worktree-manager.md
│   ├── integration.md
│   ├── database.md
│   ├── patterns.md
│   ├── pre-commit-diagnostic.md
│   ├── ci-diagnostic.md
│   └── zen-architect.md
├── context/
│   ├── instructions.md              # Main consolidated instructions
│   ├── philosophy.md                # Core philosophy from CLAUDE.md
│   ├── patterns.md                  # Development patterns
│   └── trust.md                     # Anti-sycophancy guidelines
├── recipes/                         # 7 core workflows
│   ├── workflow-selector.yaml       # DONE - Routes to correct workflow
│   ├── default-workflow.yaml        # DONE - Standard dev workflow
│   ├── investigation.yaml           # DONE - Research workflow
│   ├── qa-flow.yaml                 # DONE - Simple Q&A
│   ├── consensus.yaml               # TODO - Multi-agent consensus
│   ├── debate.yaml                  # TODO - Structured debate
│   └── n-version.yaml               # TODO - N-version programming
├── skills/                          # Essential domain knowledge
│   ├── code-smell-detector.md
│   ├── design-patterns-expert.md
│   └── test-gap-analyzer.md
├── docs/
│   ├── GETTING_STARTED.md
│   └── FEATURE_MAPPING.md
├── README.md
├── LICENSE
└── SECURITY.md
```

---

## 8. Resolution Decisions

### Use Foundation (Don't Duplicate)
- Orchestrator (foundation provides this)
- Core tools (filesystem, bash, web, search)
- Core hooks (logging, streaming-ui, status-context)
- zen-architect → Use `foundation:zen-architect`
- explorer → Use `foundation:explorer`
- bug-hunter → Use `foundation:bug-hunter`
- git-ops → Use `foundation:git-ops`
- modular-builder → Use `foundation:modular-builder`
- post-task-cleanup → Use `foundation:post-task-cleanup`
- security-guardian → Use `foundation:security-guardian`
- integration-specialist → Use `foundation:integration-specialist`

### Create Amplihack-Specific
- reviewer (code review specialist)
- tester (testing pyramid expert)
- optimizer (performance specialist)
- api-designer (API contracts)
- analyzer (TRIAGE/DEEP/SYNTHESIS modes)
- ambiguity (requirements clarification)
- documentation-writer (Diataxis framework)
- database (schema design)
- patterns (emergence detection)
- worktree-manager (git worktrees)
- pre-commit-diagnostic (hook failures)
- ci-diagnostic (CI failures)

### Deprecate (Not Needed in Amplifier)
- Session locking/unlocking
- Remote execution mode
- MCP manager (different architecture)
- Transcript management (Amplifier handles natively)
- Install/uninstall commands

---

## 9. Implementation Priority

### Phase 1: Bundle Structure (CURRENT)
1. ✅ Create agents (16 created)
2. ✅ Create initial recipes (4 created)
3. ⬜ Create context files (philosophy, patterns, trust)
4. ⬜ Create bundle.md and behaviors/amplihack.yaml
5. ⬜ Test basic bundle loading

### Phase 2: Recipe Completion
1. ⬜ consensus.yaml
2. ⬜ debate.yaml
3. ⬜ n-version.yaml (lower priority)

### Phase 3: Skills & Polish
1. ⬜ Essential skills
2. ⬜ Documentation
3. ⬜ Testing & validation

---

## 10. Open Questions

1. **Skills location**: Should skills be in the bundle or in `.amplifier/skills/`?
   - Recommendation: In bundle for portability

2. **Hook customization**: Do we need custom hooks for amplihack-specific behavior?
   - Recommendation: Start without, add later if needed

3. **Recipe approval gates**: Keep or remove?
   - User preference: Remove (autonomous execution focus)

4. **Profile system**: How to handle different loading profiles?
   - Recommendation: Different bundle variants or behaviors
