# Complete Amplihack Feature Inventory

**Generated:** 2026-01-12
**Source:** Comprehensive multi-agent survey of ~/src/amplihack

## Executive Summary

| Category | Count | Lines | Status |
|----------|-------|-------|--------|
| **CLI + Auto Mode** | 1 main + 12 launcher | ~4,300 | NOT PORTED |
| **Goal Agent Generator** | 7 files | ~1,800 | NOT PORTED |
| **Bundle Generator** | 14 files | ~5,000 | NOT PORTED |
| **Memory System** | 35+ files | ~8,500 | PARTIAL |
| **Proxy System** | 18 files | ~8,800 | NOT PORTED |
| **Orchestration Patterns** | 9 files | ~3,100 | NOT PORTED |
| **Security (XPIA)** | 9 files | ~2,400 | PARTIAL |
| **Skills** | 74 | ~500KB | NOT PORTED |
| **Agents** | 37 | ~250KB | PARTIAL (38 ported) |
| **Workflows** | 9 | ~140KB | NOT PORTED |
| **Commands** | 32 | ~200KB | NOT PORTED |
| **Hooks** | 17+ | ~8,000 | PARTIAL |
| **Utils** | 19 files | ~4,200 | NOT PORTED |
| **TOTAL** | 300+ files | ~85,000+ lines | ~15% PORTED |

---

## 1. CLI System (/src/amplihack/cli.py + launcher/)

### Main CLI (786 lines, 29KB)

**Commands:**
| Command | Description | Priority |
|---------|-------------|----------|
| `amplihack launch` | Launch Claude with proxy/Docker | HIGH |
| `amplihack auto` | Autonomous agentic loop | HIGH |
| `amplihack install` | Install to ~/.claude | MEDIUM |
| `amplihack memory tree` | Visualize memory graph | MEDIUM |
| `amplihack RustyClawd` | Rust Claude implementation | LOW |
| `amplihack copilot` | GitHub Copilot launcher | LOW |
| `amplihack codex` | OpenAI Codex launcher | LOW |

### Auto-Mode System (launcher/auto_mode.py - 1,432 lines)

**Features:**
- `--auto` flag with `--max-turns N` (default 10)
- Agentic loop: clarify → plan → execute → evaluate
- `--append` for mid-session instruction injection
- `--ui` for Rich-based interactive UI
- Session forking after 60 minutes
- Multi-SDK support: Claude, Copilot, Codex

**Key Classes:**
- `AutoMode` - Main orchestrator
- `ClaudeLauncher` - Session management
- `ForkManager` - 60-min threshold forking
- `AppendHandler` - Mid-session prompts

---

## 2. Goal Agent Generator (/src/amplihack/goal_agent_generator/)

**Purpose:** Generate specialized agents from natural language goals

### Pipeline
```
Prompt → PromptAnalyzer → ObjectivePlanner → SkillSynthesizer → AgentAssembler → Packager
```

### Files (7 files, ~1,800 lines)
| File | Lines | Purpose |
|------|-------|---------|
| `models.py` | 159 | GoalDefinition, ExecutionPlan, SkillDefinition, GoalAgentBundle |
| `prompt_analyzer.py` | 235 | Extract goals from prompts |
| `objective_planner.py` | 253 | Create multi-phase execution plans |
| `skill_synthesizer.py` | 219 | Match existing skills to requirements |
| `agent_assembler.py` | 202 | Assemble final agent bundles |
| `packager.py` | 310 | Package for deployment |
| `cli.py` | 162 | CLI interface |

**Key Classes:**
- `GoalDefinition` - User goal with domain, constraints, success criteria
- `ExecutionPlan` - Multi-phase plan with parallel opportunities
- `GoalAgentBundle` - Complete bundle with auto_mode_config

---

## 3. Bundle Generator (/src/amplihack/bundle_generator/)

**Purpose:** Generate, test, and package AI agent bundles from natural language

### Pipeline
```
Prompt → Parser → Extractor → Generator → Builder → Packager → Distributor
```

### Files (14 files, ~5,000 lines)
| File | Lines | Purpose |
|------|-------|---------|
| `generator.py` | 556 | AgentGenerator - create agent content |
| `repackage_generator.py` | 658 | Regenerate existing bundles |
| `distributor.py` | 577 | GitHubDistributor - deploy to GitHub |
| `filesystem_packager.py` | 575 | Package to filesystem |
| `cli.py` | 502 | CLI for bundle operations |
| `packager.py` | 503 | UVXPackager - UVX packaging |
| `builder.py` | 437 | BundleBuilder - assemble structure |
| `extractor.py` | 417 | IntentExtractor - extract requirements |
| `parser.py` | 397 | PromptParser - NLP parsing |
| `repository_creator.py` | 392 | Create GitHub repos |
| `documentation_generator.py` | 332 | Generate docs |
| `exceptions.py` | 299 | Custom exceptions |
| `update_manager.py` | 252 | Manage bundle updates |
| `models.py` | 238 | Data models |

---

## 4. Orchestration Patterns (tools/amplihack/orchestration/)

**Purpose:** Multi-agent orchestration for parallel Claude processes

### Patterns (4 main patterns, ~2,500 lines)
| Pattern | Lines | Description |
|---------|-------|-------------|
| `expert_panel.py` | 696 | Parallel domain experts + moderator synthesis |
| `debate.py` | 409 | Thesis/antithesis/synthesis rounds |
| `cascade.py` | 399 | Progressive fallback chain |
| `n_version.py` | 335 | Parallel variants with voting |

### Infrastructure
| File | Lines | Purpose |
|------|-------|---------|
| `claude_process.py` | 333 | Claude subprocess with timeout |
| `execution.py` | 241 | Parallel/sequential execution |
| `session.py` | 180 | Session with logging/metrics |

---

## 5. Memory System (/src/amplihack/memory/ - 35+ files, ~8,500 lines)

### Backends
| Backend | Lines | Description |
|---------|-------|-------------|
| `kuzu_backend.py` | 1,265 | Kùzu embedded graph DB |
| `sqlite_backend.py` | 172 | SQLite fallback |
| Neo4j (20+ files) | ~6,000 | Full graph database |

### Core Components
| File | Lines | Purpose |
|------|-------|---------|
| `coordinator.py` | 722 | MemoryCoordinator - main interface |
| `database.py` | 693 | MemoryDatabase - SQLite |
| `manager.py` | 364 | MemoryManager - high-level API |
| `maintenance.py` | 328 | Memory maintenance tasks |

### Memory Types
- Basic: CONVERSATION, DECISION, PATTERN, CONTEXT, LEARNING, ARTIFACT
- Extended: EPISODIC, SEMANTIC, PROCEDURAL, STRATEGIC, REFLECTIVE

---

## 6. Proxy System (/src/amplihack/proxy/ - 18 files, ~8,800 lines)

**Purpose:** API proxy for Azure OpenAI, GitHub Models, LiteLLM routing

### Core Files
| File | Lines | Purpose |
|------|-------|---------|
| `integrated_proxy.py` | 4,168 | LiteLLM router proxy |
| `server.py` | 2,377 | FastAPI with Responses API |
| `manager.py` | 789 | ProxyManager lifecycle |
| `azure_unified_integration.py` | 698 | Azure model routing |
| `config.py` | 581 | ProxyConfig |

### Features
- LiteLLM Router with fallbacks
- Azure deployment name mapping
- GitHub Models via Copilot
- SSE streaming
- Tool handling with retry

---

## 7. Skills (74 total)

### Domain Expert Analysts (25)
- anthropologist, biologist, chemist, computer-scientist, cybersecurity
- economist, engineer, environmentalist, epidemiologist, ethicist
- futurist, historian, indigenous-leader, journalist, lawyer
- novelist, philosopher, physicist, poet, political-scientist
- psychologist, sociologist, urban-planner, and more

### Workflow Skills (11)
- cascade-workflow, consensus-voting, debate-workflow, default-workflow
- goal-seeking-agent-pattern, investigation-workflow, n-version-workflow
- philosophy-compliance-workflow, quality-audit-workflow
- ultrathink-orchestrator, eval-recipes-runner

### Technical Skills (22)
- agent-sdk, azure-admin, azure-devops, code-smell-detector
- context_management, design-patterns-expert, docx, documentation-writing
- dynamic-debugger, email-drafter, mcp-manager, mermaid-diagram-generator
- microsoft-agent-framework, module-spec-generator, outside-in-testing
- pdf, pptx, xlsx, remote-work, test-gap-analyzer, skill-builder

### Meta Skills (16)
- backlog-curator, knowledge-extractor, learning-path-builder
- meeting-synthesizer, model-evaluation-benchmark, pm-architect
- pr-review-assistant, roadmap-strategist, storytelling-synthesizer
- work-delegator, workstream-coordinator, and quality/dev/research skills

---

## 8. Agents (37 total)

### Core (5)
architect, reviewer, tester, optimizer, api-designer

### Specialized (28)
amplifier-cli-architect, analyzer, azure-kubernetes-expert, ci-diagnostic-workflow
cleanup, database, documentation-writer, fallback-cascade, fix-agent
integration, knowledge-archaeologist, memory-manager, multi-agent-debate
n-version-validator, patterns, philosophy-guardian, pre-commit-diagnostic
preference-reviewer, prompt-writer, rust-programming-expert, security
visualization-architect, worktree-manager, xpia-defense, ambiguity

### Workflow Agents (2)
amplihack-improvement-workflow, prompt-review-workflow

### Synthesis Agents (2)
insight-synthesizer, concept-extractor

---

## 9. Workflows (9 total)

| Workflow | Size | Steps |
|----------|------|-------|
| DEFAULT_WORKFLOW.md | 20KB | 22 steps |
| CASCADE_WORKFLOW.md | 21KB | 7 steps |
| CONSENSUS_WORKFLOW.md | 21KB | 21 steps |
| DEBATE_WORKFLOW.md | 20KB | 8 steps |
| INVESTIGATION_WORKFLOW.md | 17KB | 6 phases |
| N_VERSION_WORKFLOW.md | 13KB | 7 steps |
| Q&A_WORKFLOW.md | 3KB | 3 steps |

---

## 10. Commands (32 total)

### Amplihack Commands (24)
- `/amplihack:fix`, `/amplihack:expert-panel`, `/amplihack:debate`
- `/amplihack:customize`, `/amplihack:cascade`, `/amplihack:auto`
- `/amplihack:analyze`, `/amplihack:xpia`, `/amplihack:ultrathink`
- `/amplihack:transcripts`, `/amplihack:socratic`, `/amplihack:skill-builder`
- `/amplihack:remote`, `/amplihack:reflect`, `/amplihack:ps-diagnose`
- `/amplihack:n-version`, `/amplihack:modular-build`, `/amplihack:lock`
- `/amplihack:knowledge-builder`, `/amplihack:install`, `/amplihack:ingest-code`
- `/amplihack:improve`

### DDD Commands (8)
- `/ddd:0-help`, `/ddd:1-plan`, `/ddd:2-docs`, `/ddd:3-code-plan`
- `/ddd:4-code`, `/ddd:5-finish`, `/ddd:status`, `/ddd:prime`

---

## 11. Power Steering (8,015 lines in hooks/)

### Components
| File | Lines | Purpose |
|------|-------|---------|
| `power_steering_checker.py` | 2,830 | 21-consideration completeness |
| `stop.py` | 868 | Stop hook with power steering |
| `claude_power_steering.py` | 298 | SDK-based analysis |

### 21 Considerations
1. Objective completion
2. TODO items addressed
3. Next steps defined
4. Philosophy compliance
5. Local testing done
6. Dev workflow complete
7. Documentation updated
8. CI status checked
9. Code quality verified
10. Error handling complete
11. Edge cases addressed
... (11 more)

---

## 12. Security/XPIA (9 files, ~2,400 lines)

### Components
| File | Lines | Purpose |
|------|-------|---------|
| `xpia_defender.py` | 689 | Core validation |
| `xpia_defense_interface.py` | 486 | Interface definitions |
| `xpia_patterns.py` | 476 | Attack patterns |
| `xpia_hooks.py` | 421 | Claude Code integration |

### Security Levels
STRICT, HIGH, MEDIUM/MODERATE, LOW/LENIENT

### Threat Types
INJECTION, EXFILTRATION, MANIPULATION

---

## 13. Utils (19 files, ~4,200 lines)

### Key Utilities
| File | Lines | Purpose |
|------|-------|---------|
| `prerequisites.py` | 917 | PrerequisiteChecker, InteractiveInstaller |
| `defensive.py` | 485 | JSON parsing, retry logic, file I/O |
| `uvx_staging_v2.py` | 433 | V2 staging system |
| `hook_merge_utility.py` | 411 | Merge hook configurations |
| `claude_md_preserver.py` | 391 | Preserve CLAUDE.md |
| `project_initializer.py` | 380 | Initialize PROJECT.md |
| `claude_cli.py` | 361 | get_claude_cli_path(), auto-install |

---

## What Has Been Ported (Current State)

### Modules Created
| Module | Lines | Status |
|--------|-------|--------|
| hook-power-steering | 959 | ✓ Working |
| tool-memory | 493 | ✓ Working |
| hook-agent-memory | 295 | ✓ Working |
| tool-session-utils | 478 | ✓ Working |
| tool-workflow | 814 | ✓ Working |
| tool-lock | 200 | ✓ Working |
| hook-xpia-defense | 150 | ✓ Working |
| **TOTAL PORTED** | ~3,389 | ~4% of source |

### Bundle Content Ported
- 38 agents (partial definitions)
- 66 skills (references only, not content)
- 10 recipes (references only)
- Context files (philosophy, instructions)

---

## Priority Port List

### P0 - Critical (Must Have)
1. **CLI + Auto Mode** - Core user interface
2. **Goal Agent Generator** - Key differentiating feature
3. **All 74 Skills** - Complete skill content
4. **All 9 Workflows as Recipes** - Workflow definitions

### P1 - High Priority
5. **Bundle Generator** - Agent creation from prompts
6. **Orchestration Patterns** - Expert Panel, Debate, Cascade, N-Version
7. **Full Power Steering** - All 21 considerations

### P2 - Medium Priority
8. **Proxy System** - Multi-provider support
9. **Full Memory System** - All backends
10. **All 32 Commands** - User commands

### P3 - Nice to Have
11. **Utils** - Defensive programming
12. **Remote Execution** - Azure VM support
13. **Knowledge Builder** - Socratic exploration

---

## Estimated Effort

| Phase | Files | Lines | Days |
|-------|-------|-------|------|
| CLI + Auto Mode | 13 | 4,300 | 2-3 |
| Goal Agent Generator | 7 | 1,800 | 1-2 |
| Skills (74) | 74 | ~15,000 | 3-4 |
| Workflows → Recipes | 9 | 3,000 | 1-2 |
| Bundle Generator | 14 | 5,000 | 2-3 |
| Orchestration Patterns | 9 | 3,100 | 2 |
| Commands | 32 | 5,000 | 2 |
| **TOTAL** | ~158 | ~37,200 | 13-18 days |

---

## Next Steps

1. Create skills/ directory with all 74 skills
2. Convert 9 workflows to Amplifier recipe format
3. Port CLI as behavior with tool integrations
4. Port Goal Agent Generator as tool module
5. Implement orchestration patterns as recipes
6. Run default-workflow for validation
7. Outside-in testing of complete bundle
