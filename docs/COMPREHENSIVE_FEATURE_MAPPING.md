# Comprehensive Amplihack → Amplifier Feature Mapping

This document provides a complete capability-by-capability mapping from the amplihack Claude Code framework to an Amplifier bundle.

## Summary Statistics

| Category | Amplihack Count | Amplifier Equivalent | Status |
|----------|-----------------|---------------------|--------|
| **Agents** | 34 | Agents (34) | Port all |
| **Skills** | 64+ | Skills (64+) | Port all by category |
| **Hooks** | 4 configured + infrastructure | Hooks (4) | Port with simplification |
| **Tools** | 15+ Python modules | Tools/Recipes | Selective port |
| **Context Files** | 16 | Context files (16) | Port all |
| **Commands** | 32 | Recipes + Agent invocation | Port as recipes |
| **Workflows** | 8 + 6 fix templates | Recipes (14) | Port all |
| **Special Modes** | 3 (Lock/Auto/Ultrathink) | Recipes + Hooks | Port with adaptation |

---

## 1. AGENTS (34 Total)

### 1.1 Root-Level Agents (3)

| Agent | Purpose | Amplifier Equivalent |
|-------|---------|---------------------|
| `concept-extractor` | Extract structured knowledge from documents | `amplihack:concept-extractor` |
| `insight-synthesizer` | Discover revolutionary cross-domain connections | `amplihack:insight-synthesizer` |
| `knowledge-archaeologist` | Trace evolution of ideas over time | `amplihack:knowledge-archaeologist` |

### 1.2 Core Agents (6)

| Agent | Purpose | Notes |
|-------|---------|-------|
| `api-designer` | API contract design | Unique to amplihack |
| `architect` | System design, problem decomposition | Similar to `foundation:zen-architect` but keep for philosophy |
| `builder` | Implementation from specs | Similar to `foundation:modular-builder` but keep for philosophy |
| `optimizer` | Performance optimization | Unique profiling focus |
| `reviewer` | Code review, quality assurance | Unique PR comment patterns |
| `tester` | Test coverage, testing pyramid | Unique 60/30/10 methodology |

### 1.3 Specialized Agents (26)

| Agent | Purpose | Foundation Overlap? |
|-------|---------|---------------------|
| `ambiguity` | Requirements clarification, preserve contradictions | Unique |
| `amplifier-cli-architect` | CLI hybrid code/AI systems | Unique |
| `analyzer` | TRIAGE/DEEP/SYNTHESIS modes | Unique auto-mode |
| `azure-kubernetes-expert` | AKS expertise | Unique domain |
| `ci-diagnostic-workflow` | CI failure resolution loop | Unique state machine |
| `cleanup` | Post-task codebase hygiene | Similar to `foundation:post-task-cleanup` |
| `database` | Schema design, pragmatic DB choices | Unique |
| `documentation-writer` | Diataxis framework docs | Unique methodology |
| `fallback-cascade` | Graceful degradation patterns | Unique fault tolerance |
| `fix-agent` | Rapid diagnosis with mode selection | Unique quick/diagnostic/comprehensive |
| `integration` | External integrations | Similar to `foundation:integration-specialist` |
| `knowledge-archaeologist` | Historical codebase research | Unique git archaeology |
| `memory-manager` | Session state persistence | Unique memory tiers |
| `multi-agent-debate` | Structured debate facilitation | Unique consensus building |
| `n-version-validator` | N-version programming | Unique fault tolerance |
| `patterns` | Pattern emergence detection | Unique meta-patterns |
| `philosophy-guardian` | Philosophy compliance enforcement | Unique to amplihack |
| `pre-commit-diagnostic` | Pre-commit failure resolution | Unique local fix flow |
| `preference-reviewer` | Analyze user preferences for upstream | Unique contribution analysis |
| `prompt-writer` | Requirements → clear specs | Unique templates |
| `rust-programming-expert` | Rust ownership/borrowing expertise | Unique domain |
| `security` | Security review, OWASP | Similar to `foundation:security-guardian` |
| `visualization-architect` | Architecture diagrams, ASCII art | Unique visual communication |
| `worktree-manager` | Git worktree management | Unique git workflow |
| `xpia-defense` | Prompt injection detection | Unique AI security |

### 1.4 Workflow Agents (2)

| Agent | Purpose |
|-------|---------|
| `amplihack-improvement-workflow` | 5-stage progressive validation for self-improvement |
| `prompt-review-workflow` | PromptWriter ↔ Architect integration |

### Agent Mapping Decision

**Keep all 34 agents** - Even where foundation has similar agents, the amplihack versions have:
- Amplihack-specific philosophy integration
- Different methodologies (e.g., tester's 60/30/10 pyramid)
- Unique output formats and workflows

Users can choose foundation OR amplihack agents based on preference.

---

## 2. SKILLS (64+ Total)

### 2.1 Domain Analyst Skills (20)

Multi-disciplinary analysis frameworks. Each provides theoretical foundations, frameworks, methodology.

| Skill | Domain |
|-------|--------|
| `anthropologist-analyst` | Cultural analysis, ethnographic methods |
| `economist-analyst` | Supply/demand, game theory, behavioral economics |
| `ethicist-analyst` | Consequentialism, deontology, virtue ethics |
| `futurist-analyst` | Horizon scanning, trend analysis, scenario planning |
| `game-theorist-analyst` | Nash equilibrium, mechanism design |
| `geopolitical-analyst` | International relations, power dynamics |
| `historian-analyst` | Primary sources, periodization, historiography |
| `journalist-analyst` | 5W1H, source verification, bias detection |
| `legal-analyst` | Statutory interpretation, case law |
| `military-strategist-analyst` | Clausewitz, Sun Tzu, OODA loops |
| `philosopher-analyst` | Epistemology, metaphysics, logic |
| `political-scientist-analyst` | Comparative politics, institutionalism |
| `psychologist-analyst` | Cognitive, developmental, social frameworks |
| `public-health-analyst` | Epidemiology, health policy |
| `religious-studies-analyst` | Theology, comparative religion |
| `science-studies-analyst` | Philosophy of science, STS |
| `sociologist-analyst` | Structural-functionalism, conflict theory |
| `systems-theorist-analyst` | Feedback loops, emergence, complexity |
| `urban-planner-analyst` | Zoning, transit-oriented development |
| `environmental-analyst` | Sustainability, ecosystem services |

### 2.2 Azure Cloud Skills (16)

| Skill | Focus |
|-------|-------|
| `azure-ai` | Cognitive Services, OpenAI, ML Studio |
| `azure-app-service` | Web app hosting, deployment slots |
| `azure-architecture-patterns` | Landing zones, hub-spoke, WAF |
| `azure-cli-az` | CLI command reference |
| `azure-container-apps` | Serverless containers, Dapr |
| `azure-cosmos-db` | NoSQL, partitioning, consistency |
| `azure-devops` | Pipelines, repos, artifacts |
| `azure-functions` | Serverless, triggers, bindings |
| `azure-governance` | Policy, RBAC, blueprints |
| `azure-identity` | Entra ID, managed identities |
| `azure-integration` | Logic Apps, Service Bus, Event Grid |
| `azure-kubernetes` | AKS, Helm, GitOps |
| `azure-networking` | VNets, NSGs, firewalls |
| `azure-quickstarts` | Common deployment patterns |
| `azure-security` | Defender, Key Vault, compliance |
| `azure-storage` | Blob, files, queues, tables |

### 2.3 Development Skills (10)

| Skill | Focus |
|-------|-------|
| `architecting-solutions` | System design, module specs |
| `setting-up-projects` | Project setup automation |
| `code-reviewer` | Security, performance, maintainability |
| `debugging` | Systematic methodology, root cause |
| `git-master` | Advanced Git workflows |
| `test-gap-analyzer` | Coverage analysis, missing tests |
| `pr-reviewer` | Structured PR feedback |
| `refactoring` | Patterns, tech debt reduction |
| `performance-optimization` | Analysis and optimization |
| `security-review` | Vulnerability detection |

### 2.4 Workflow/Orchestration Skills (8)

| Skill | Focus |
|-------|-------|
| `ultrathink-orchestrator` | Auto-invoke deep analysis |
| `skill-builder` | Create new Claude Code skills |
| `multi-perspective-analyzer` | Cross-discipline synthesis |
| `meta-analyst` | Meta-cognitive reasoning analysis |
| `parallel-hypothesis-tester` | Test multiple hypotheses |
| `decision-framework` | Structured decision-making |
| `planning-horizon` | Short/medium/long-term planning |
| `consensus-builder` | Facilitate multi-perspective consensus |

### 2.5 Document Processing Skills (4)

| Skill | Capabilities |
|-------|-------------|
| `pdf` | Create, merge, split, extract |
| `pptx` | PowerPoint creation and editing |
| `xlsx` | Excel formulas, formatting |
| `docx` | Word documents, templates |

### 2.6 Communication Skills (4)

| Skill | Focus |
|-------|-------|
| `storytelling-synthesizer` | Convert technical work to demos/blogs |
| `prompt-writer` | Effective AI prompts |
| `technical-writer` | API docs, user guides |
| `presentation-designer` | Visual presentation structure |

### 2.7 Infrastructure Skills (2)

| Skill | Focus |
|-------|-------|
| `mcp-manager` | MCP server configuration |
| `infrastructure` | IaC, deployment automation |

---

## 3. HOOKS (4 + Infrastructure)

### 3.1 Configured Hooks

| Hook | Event | Amplifier Equivalent |
|------|-------|---------------------|
| `session_start.py` | SessionStart | `amplihack:session-start` hook |
| `stop.py` | Stop | `amplihack:stop` hook (simplified) |
| `post_tool_use.py` | PostToolUse | `amplihack:post-tool-use` hook |
| `pre_compact.py` | PreCompact | `amplihack:pre-compact` hook |

### 3.2 Hook Features to Port

| Feature | Original | Amplifier Approach |
|---------|----------|-------------------|
| Context injection | `session_start.py` | Hook injects philosophy + preferences |
| Lock mode blocking | `stop.py` | Hook checks lock state file |
| Power steering | `stop.py` | Simplified consideration checker |
| Reflection analysis | `stop.py` | Optional Claude SDK analysis |
| Tool metrics | `post_tool_use.py` | Metrics logging |
| Transcript export | `pre_compact.py` | Context preservation |

### 3.3 Infrastructure Modules

| Module | Purpose | Port? |
|--------|---------|-------|
| `hook_processor.py` | Base class with JSON I/O | Adapt for Amplifier hooks |
| `power_steering_checker.py` | Completion analysis | Simplify significantly |
| `shutdown_context.py` | Graceful shutdown | May not be needed |
| `error_protocol.py` | Structured errors | Adapt for Amplifier |

---

## 4. PYTHON TOOLS (15+ Modules)

### 4.1 Fault Tolerance Patterns

| Tool | Purpose | Amplifier Approach |
|------|---------|-------------------|
| `n_version.py` | N-version programming | Recipe + parallel agent spawning |
| `debate.py` | Multi-agent debate | Recipe + parallel perspectives |
| `cascade.py` | Fallback cascade | Recipe with error handling |
| `expert_panel.py` | Expert voting | Recipe + aggregation |

### 4.2 Memory System

| Tool | Purpose | Amplifier Approach |
|------|---------|-------------------|
| `interface.py` | AgentMemory API | Context persistence tool |
| `core.py` | SQLite backend | Amplifier session storage |

### 4.3 Session Management

| Tool | Purpose | Amplifier Approach |
|------|---------|-------------------|
| `session_manager.py` | Session persistence | Use Amplifier sessions |
| `reflection.py` | AI-powered analysis | Recipe for reflection |

### 4.4 CI/CD Tools

| Tool | Purpose | Amplifier Approach |
|------|---------|-------------------|
| `ci_status.py` | Check CI status | Tool or bash wrapper |
| `github_issue.py` | Create issues | gh CLI wrapper |

### 4.5 Security

| Tool | Purpose | Amplifier Approach |
|------|---------|-------------------|
| `xpia_defense.py` | Prompt injection defense | Hook + patterns |

---

## 5. CONTEXT FILES (16)

### 5.1 Core Context (Loaded at Startup)

| File | Size | Purpose |
|------|------|---------|
| `PHILOSOPHY.md` | 8KB | Zen minimalism, brick philosophy |
| `PROJECT.md` | 2KB | Project-specific template |
| `PATTERNS.md` | 28KB | 14 proven patterns |
| `TRUST.md` | 1KB | Anti-sycophancy (7 rules) |
| `USER_PREFERENCES.md` | 9KB | User-specific settings |
| `USER_REQUIREMENT_PRIORITY.md` | 5KB | Priority hierarchy |

### 5.2 Supplementary Context

| File | Size | Purpose |
|------|------|---------|
| `FRONTMATTER_STANDARDS.md` | 11KB | YAML frontmatter specs |
| `AGENT_INPUT_VALIDATION.md` | 1KB | Input validation rules |
| `ORIGINAL_REQUEST_PRESERVATION.md` | 2KB | Context compaction rules |
| `PROJECT_AMPLIHACK.md` | 6KB | Amplihack self-description |
| `TOOL_VS_SKILL_CLASSIFICATION.md` | 4KB | Tool vs skill guidance |
| `PM_PATTERNS.md` | 11KB | PM cognitive offloading |

### 5.3 Knowledge Base

| File | Size | Purpose |
|------|------|---------|
| `DISCOVERIES.md` | 76KB | Living knowledge base |
| `DISCOVERIES_ARCHIVE.md` | 5KB | Archived discoveries |
| `REFLECTION_FEATURES_2025_11.md` | 41KB | Reflection system docs |

---

## 6. COMMANDS (32)

### 6.1 Orchestration Commands

| Command | Amplifier Equivalent |
|---------|---------------------|
| `/ultrathink` | Recipe: `workflow-selector.yaml` |
| `/auto` | Recipe: `auto-mode.yaml` |

### 6.2 Session Management

| Command | Amplifier Equivalent |
|---------|---------------------|
| `/lock` | Recipe + hook state |
| `/unlock` | Recipe + hook state |

### 6.3 Fault Tolerance

| Command | Amplifier Equivalent |
|---------|---------------------|
| `/debate` | Recipe: `debate-workflow.yaml` |
| `/cascade` | Recipe: `cascade-workflow.yaml` |
| `/n-version` | Recipe: `n-version-workflow.yaml` |
| `/expert-panel` | Recipe: `expert-panel-workflow.yaml` |

### 6.4 DDD Suite (8)

| Command | Amplifier Equivalent |
|---------|---------------------|
| `/ddd:0-help` | Skill: `ddd-help` |
| `/ddd:prime` | Recipe: context loading |
| `/ddd:status` | Agent: check DDD state |
| `/ddd:1-plan` | Recipe: `ddd-1-plan.yaml` |
| `/ddd:2-docs` | Recipe: `ddd-2-docs.yaml` |
| `/ddd:3-code-plan` | Recipe: `ddd-3-code-plan.yaml` |
| `/ddd:4-code` | Recipe: `ddd-4-code.yaml` |
| `/ddd:5-finish` | Recipe: `ddd-5-finish.yaml` |

### 6.5 Utility Commands

| Command | Amplifier Equivalent |
|---------|---------------------|
| `/fix` | Agent: `amplihack:fix-agent` |
| `/analyze` | Agent: `amplihack:analyzer` |
| `/improve` | Recipe: `improvement-workflow.yaml` |
| `/reflect` | Recipe: `reflect.yaml` |
| `/socratic` | Agent: `amplihack:socratic` |
| `/customize` | Recipe: preferences management |
| `/modular-build` | Recipe: `modular-build.yaml` |
| `/skill-builder` | Recipe: `skill-builder.yaml` |
| `/knowledge-builder` | Recipe: `knowledge-builder.yaml` |
| `/remote` | Recipe: remote execution |
| `/transcripts` | Agent: transcript management |
| `/ingest-code` | Tool: Neo4j integration |
| `/xpia` | Agent: security status |
| `/ps-diagnose` | Agent: power steering diagnostics |

---

## 7. WORKFLOWS (8 + 6 Fix Templates)

### 7.1 Primary Workflows

| Workflow | Steps | Amplifier Recipe |
|----------|-------|------------------|
| `DEFAULT_WORKFLOW.md` | 22 | `default-workflow.yaml` |
| `CONSENSUS_WORKFLOW.md` | 21 | `consensus-workflow.yaml` |
| `DEBATE_WORKFLOW.md` | 8 | `debate-workflow.yaml` |
| `N_VERSION_WORKFLOW.md` | 7 | `n-version-workflow.yaml` |
| `CASCADE_WORKFLOW.md` | 7 | `cascade-workflow.yaml` |
| `INVESTIGATION_WORKFLOW.md` | 6 | `investigation-workflow.yaml` |
| `Q&A_WORKFLOW.md` | 3 | `qa-workflow.yaml` |

### 7.2 Fix Templates

| Template | Usage | Amplifier Approach |
|----------|-------|-------------------|
| `ci-fix-template.md` | 20% | Skill: `ci-fix` |
| `code-quality-fix-template.md` | 25% | Skill: `code-quality-fix` |
| `config-fix-template.md` | 12% | Skill: `config-fix` |
| `import-fix-template.md` | 15% | Skill: `import-fix` |
| `logic-fix-template.md` | 10% | Skill: `logic-fix` |
| `test-fix-template.md` | 18% | Skill: `test-fix` |

---

## 8. SPECIAL MODES

### 8.1 Lock Mode

| Aspect | Original | Amplifier |
|--------|----------|-----------|
| Activation | `/lock [message]` | Recipe sets state file |
| State | `.claude/runtime/locks/.lock_active` | `.amplifier/state/lock_active` |
| Blocking | `stop.py` hook | `amplihack:stop` hook |
| Deactivation | `/unlock` | Recipe clears state |

### 8.2 Auto Mode

| Aspect | Original | Amplifier |
|--------|----------|-----------|
| Activation | `/auto --max-turns N` | Recipe with loop |
| Turns | 10 default | Configurable |
| Mid-injection | `--append` | Recipe context update |
| State | `.claude/runtime/logs/auto_*` | Session logs |

### 8.3 Ultrathink Mode

| Aspect | Original | Amplifier |
|--------|----------|-----------|
| Activation | `/ultrathink` (default) | `workflow-selector.yaml` |
| Detection | Keyword analysis | Recipe classifier step |
| Workflows | Q&A, Investigation, Development | Route to appropriate recipe |

---

## Implementation Priority

### Phase 1: Core Structure
1. Bundle entry point (`bundle.md`)
2. Core context files (6)
3. Core agents (6)

### Phase 2: Agents & Skills
4. All 34 agents
5. Development skills (10)
6. Workflow skills (8)

### Phase 3: Workflows & Commands
7. Primary workflows (8 recipes)
8. Command equivalents
9. Fix templates as skills

### Phase 4: Advanced Features
10. Hooks (4)
11. Special modes
12. Domain analyst skills (20)
13. Azure skills (16)
14. Document/Communication skills (8)

### Phase 5: Testing & Validation
15. Outside-in testing
16. Documentation
17. Examples

---

## Notes

### What We're NOT Porting

1. **Neo4j memory system** - Complex, optional, not core to workflow
2. **Remote execution** - Azure VM provisioning is out of scope
3. **Power steering complexity** - Simplify to basic consideration checking
4. **Profile filtering** - Amplifier handles this differently

### Amplifier Advantages

1. **Recipe system** - Better workflow orchestration than markdown
2. **Agent delegation** - Native `task` tool for sub-agents
3. **Session management** - Built-in persistence
4. **Bundle composition** - Inherits foundation capabilities

### Philosophy Alignment

The amplihack philosophy perfectly aligns with Amplifier's:
- Ruthless simplicity
- Modular design (bricks & studs)
- Zero-BS implementations
- Mechanism over policy
