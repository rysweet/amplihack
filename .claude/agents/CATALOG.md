# Agent Catalog

Complete reference guide for all agents in the Amplihack agentic coding framework.

## Quick Reference Table

| Agent | Category | Purpose | When to Use |
|-------|----------|---------|-------------|
| architect | Core | System design and specifications | New features, architecture decisions |
| builder | Core | Code implementation from specs | Building modules from specifications |
| reviewer | Core | Code review and debugging | Bug hunting, quality assurance |
| tester | Core | Test coverage analysis | Writing tests, identifying gaps |
| optimizer | Core | Performance optimization | Bottleneck analysis, speed improvements |
| api-designer | Core | API contract design | REST/GraphQL API design and review |
| analyzer | Specialized | Multi-mode analysis engine | Any analysis task (auto-selects mode) |
| security | Specialized | Security hardening | Authentication, authorization, vulnerabilities |
| database | Specialized | Database design and optimization | Schema design, query optimization |
| integration | Specialized | System integration | APIs, services, system connections |
| patterns | Specialized | Pattern emergence orchestration | Detecting patterns from diverse perspectives |
| cleanup | Specialized | Post-task hygiene | After task completion, removing artifacts |
| ambiguity | Specialized | Preserving productive contradictions | Paradoxes, competing theories, uncertainty |
| prompt-writer | Specialized | Structured prompt generation | Converting requirements to prompts |
| fix-agent | Specialized | Intelligent fix workflows | Quick fixes, diagnostics, comprehensive repairs |
| pre-commit-diagnostic | Workflow | Pre-commit hook failures | Local issues before pushing |
| ci-diagnostic-workflow | Workflow | CI/CD failure resolution | After push, making PR mergeable |
| amplihack-improvement-workflow | Workflow | Progressive validation workflow | Improving the amplihack project only |
| prompt-review-workflow | Workflow | Prompt review coordination | PromptWriter + Architect integration |
| n-version-validator | Fault Tolerance | N-version programming | Critical security/algorithm implementations |
| multi-agent-debate | Fault Tolerance | Structured debate pattern | Architectural trade-offs, decision-making |
| fallback-cascade | Fault Tolerance | Graceful degradation | Operations with fallback alternatives |
| worktree-manager | Specialized | Git worktree management | Creating/managing isolated dev environments |
| memory-manager | Specialized | Context and persistence | Session continuity, cross-session memory |
| knowledge-archaeologist | Specialized | Deep knowledge excavation | Understanding system evolution, buried insights |
| preference-reviewer | Specialized | User preference analysis | Identifying upstream contribution patterns |
| rust-programming-expert | Language | Rust expertise | Ownership, borrowing, memory safety |
| azure-kubernetes-expert | Platform | AKS production deployments | Azure Kubernetes operations and security |
| visualization-architect | Specialized | Visual documentation | Architecture diagrams, workflow visualization |
| zen-architect | Specialized | Philosophy compliance | Ensuring ruthless simplicity, brick philosophy |
| xpia-defense | Security | Prompt injection defense | Real-time threat protection, AI security |
| amplifier-cli-architect | Specialized | CLI architecture expertise | Hybrid code/AI systems, ccsdk_toolkit integration |

## Core Agents

Core agents form the foundation of the development workflow.

### Architect

**Role**: Primary architecture and design agent

**Description**: Embodies ruthless simplicity and creates specifications for implementation. Analyzes problems, designs solutions, and reviews code for philosophy compliance.

**Key Capabilities**:
- Problem decomposition and analysis
- Module specifications with clear contracts
- Code review for simplicity and modularity
- Pre-commit setup validation

**When to Use**:
- New feature design
- System architecture decisions
- Code review for philosophy
- Problem analysis before implementation

**Integration**: Works with builder (provides specs), reviewer (validates design), tester (defines test requirements)

---

### Builder

**Role**: Primary implementation agent

**Description**: Builds code from specifications following the modular brick philosophy. Creates self-contained, regeneratable modules with clear contracts.

**Key Capabilities**:
- Zero-BS implementation (no stubs/placeholders)
- Module structure creation
- Working code only
- Regeneratable from specification

**When to Use**:
- Implementing specifications
- Creating new modules
- Building features
- Converting designs to code

**Integration**: Receives specs from architect, coordinates with tester for test creation

---

### Reviewer

**Role**: Code review and debugging specialist

**Description**: Systematically finds issues, suggests improvements, and ensures philosophy compliance. Debugging expert with systematic approaches.

**Key Capabilities**:
- User requirement compliance checking (HIGHEST PRIORITY)
- Code quality review
- Bug hunting with hypothesis testing
- Root cause analysis

**When to Use**:
- Code review
- Bug investigation
- Quality assessment
- Philosophy compliance check

**Critical Feature**: Always checks explicit user requirements FIRST before suggesting simplifications

**Integration**: Reviews architect designs, builder implementations; posts reviews as PR comments

---

### Tester

**Role**: Test coverage expert

**Description**: Analyzes test gaps and suggests comprehensive test cases following the testing pyramid (60% unit, 30% integration, 10% E2E).

**Key Capabilities**:
- Coverage assessment (happy path, edge cases, errors)
- Testing pyramid compliance
- Parametrized test suggestions
- Strategic coverage over 100%

**When to Use**:
- Writing new features
- Fixing bugs (add regression tests)
- Reviewing test coverage
- Ensuring quality

**Integration**: Works with builder for test implementation, reviewer for quality validation

---

### Optimizer

**Role**: Performance optimization specialist

**Description**: Follows "measure twice, optimize once" principle. Analyzes bottlenecks, optimizes algorithms, and improves system performance.

**Key Capabilities**:
- Profiling and baseline metrics
- Algorithm optimization (O(n²) → O(n))
- Caching strategies
- Database query optimization

**When to Use**:
- Performance issues
- Bottleneck analysis
- Query optimization
- Speed improvements

**Integration**: Works with database for query optimization, analyzer for profiling data

---

### API Designer

**Role**: API contract specialist

**Description**: Designs minimal, clear REST/GraphQL APIs following bricks & studs philosophy. Creates OpenAPI specs and versioning strategies.

**Key Capabilities**:
- Contract-first design
- RESTful pragmatism
- OpenAPI specification
- Versioning strategy

**When to Use**:
- API design
- Endpoint review
- Integration contracts
- API refactoring

**Integration**: Works with architect for system design, security for auth patterns

---

## Specialized Agents

Specialized agents handle specific domains or cross-cutting concerns.

### Analyzer

**Role**: Multi-mode analysis engine

**Description**: Automatically selects TRIAGE (rapid filtering), DEEP (thorough analysis), or SYNTHESIS (combining sources) based on context.

**Modes**:
- **TRIAGE**: Large document sets, rapid filtering (>10 documents)
- **DEEP**: Single/small sets, detailed analysis (<5 documents)
- **SYNTHESIS**: Multiple sources, multi-source integration (3-10 documents)

**When to Use**:
- Any analysis task (auto-selects mode)
- Document filtering
- Deep investigation
- Combining multiple perspectives

**Integration**: Parallel-ready, works with all agents for multi-dimensional analysis

---

### Security

**Role**: Security specialist

**Description**: Ensures robust protection without over-engineering. Never compromises on security fundamentals.

**Key Capabilities**:
- Authentication and authorization
- Input validation
- Secure defaults
- Vulnerability prevention (injection, XSS)

**When to Use**:
- Security-sensitive code
- Authentication implementation
- Vulnerability assessment
- Security review

**Integration**: Works with api-designer for auth patterns, architect for security design

---

### Database

**Role**: Database design and optimization specialist

**Description**: Embodies ruthless simplicity in data architecture. Designs pragmatic schemas that evolve with needs.

**Key Capabilities**:
- Flexible schema design
- Query optimization with EXPLAIN
- Migration strategies
- Storage class selection

**When to Use**:
- Schema design
- Query performance issues
- Database selection
- Migration planning

**Integration**: Works with optimizer for query performance, architect for data modeling

---

### Integration

**Role**: Integration specialist

**Description**: Connects systems with minimal coupling and maximum reliability. Creates clean interfaces between components.

**Key Capabilities**:
- API client patterns
- Message queue patterns
- Retry with backoff
- Circuit breaker implementation

**When to Use**:
- External service integration
- Inter-service communication
- API design
- Reliability patterns

**Integration**: Works with api-designer for contracts, security for auth flows

---

### Patterns

**Role**: Pattern emergence orchestrator

**Description**: Coordinates diverse perspectives AND detects emergent patterns from that diversity. Finds patterns that emerge FROM diversity.

**Key Capabilities**:
- Orchestrate diversity (multiple perspectives)
- Detect emergence (unexpected patterns)
- Manage productive tensions
- Meta-pattern recognition

**When to Use**:
- Analyzing diverse outputs
- Identifying unexpected patterns
- Managing productive contradictions
- Cross-cutting pattern discovery

**Integration**: Parallel-ready, orchestrates multiple agent perspectives

---

### Cleanup

**Role**: Post-task cleanup specialist

**Description**: Reviews git status, removes temporary artifacts, eliminates unnecessary complexity, ensures philosophy compliance.

**Key Capabilities**:
- Git status analysis
- Philosophy compliance checking
- Artifact removal
- Documentation placement validation

**Critical Feature**: Checks user requirements FIRST - never removes explicitly requested items

**When to Use**:
- After task completion
- After todo list completion
- Before PR submission
- Repository hygiene

**Integration**: Works with reviewer for philosophy checks, proactively invoked after tasks

---

### Ambiguity

**Role**: Ambiguity guardian

**Description**: Preserves productive contradictions and navigates uncertainty as valuable knowledge features, not bugs to fix.

**Key Capabilities**:
- Tension maps (competing viewpoints)
- Uncertainty cartography
- Paradox preservation
- Knowledge boundary mapping

**When to Use**:
- Paradoxes and competing theories
- Mapping unknowns
- Premature certainty would lose insights
- Multiple valid perspectives exist

**Integration**: Works with patterns for diverse perspectives, architect for design trade-offs

---

### Prompt Writer

**Role**: Structured prompt generation specialist

**Description**: Transforms requirements into clear, actionable prompts with complexity assessment and quality validation.

**Key Capabilities**:
- Template-based prompt generation (feature/bug/refactor)
- Complexity assessment (Simple/Medium/Complex)
- Quality validation (80% threshold)
- Architect review integration

**When to Use**:
- Converting requirements to prompts
- Creating GitHub issues
- Structured task definition
- Quality-checked specifications

**Integration**: Works with architect for complex prompts, integrates with GitHub issue creation

---

### Fix Agent

**Role**: Intelligent fix workflow optimization

**Description**: Automatically selects QUICK (rapid fixes), DIAGNOSTIC (root cause), or COMPREHENSIVE (full workflow) based on context.

**Modes**:
- **QUICK**: Single file, obvious solutions, <5 minutes
- **DIAGNOSTIC**: Unclear errors, investigation needed
- **COMPREHENSIVE**: Architecture issues, breaking changes

**Common Patterns**: Import errors (15%), CI/CD (20%), tests (18%), config (12%), quality (25%), logic (10%)

**When to Use**:
- Any fix request (auto-selects mode)
- Quick import/format fixes
- Complex debugging
- Template-based common fixes

**Integration**: Works with pre-commit-diagnostic, ci-diagnostic-workflow, builder for fixes

---

### Pre-Commit Diagnostic

**Role**: Pre-commit workflow specialist

**Description**: Resolves all local issues BEFORE pushing to repository. Handles hook failures, formatting, linting.

**Key Capabilities**:
- Auto-fix with formatters (prettier, black, ruff)
- Manual fix guidance
- Environment verification
- Iteration until all pass

**When to Use**:
- Pre-commit hooks failing
- Can't commit code
- Before any git push
- Local quality issues

**Integration**: Hands off to ci-diagnostic-workflow after successful push

---

### CI Diagnostic Workflow

**Role**: CI workflow orchestrator

**Description**: Manages full CI diagnostic and fix cycle after code is pushed. Iterates until CI passes, never auto-merges.

**Key Capabilities**:
- CI status monitoring
- Failure diagnosis
- Fix and push loop
- Smart waiting and polling

**When to Use**:
- After git push
- CI failing
- Making PR mergeable
- Automated CI fixes

**Critical Feature**: NEVER auto-merges, stops at mergeable state

**Integration**: Receives from pre-commit-diagnostic, iterates until mergeable

---

### Worktree Manager

**Role**: Git worktree management specialist

**Description**: Manages git worktrees consistently and safely. Ensures worktrees are created in correct location (`./worktrees/`).

**Key Capabilities**:
- Standardized worktree creation
- Branch naming conventions
- Stale worktree cleanup
- Path validation

**When to Use**:
- Creating feature branches
- Isolated development environments
- Parallel work streams
- Worktree cleanup

**Integration**: Used in workflow Step 3 (Setup Worktree and Branch)

---

### Memory Manager

**Role**: Agent memory and persistence specialist

**Description**: Manages contextual memory, session continuity, and intelligent information retention across agent interactions.

**Key Capabilities**:
- 3-tier memory (session, working, knowledge)
- Context preservation and restoration
- Pattern recognition
- Relevance scoring

**When to Use**:
- Cross-session continuity
- Context preservation
- Pattern learning
- User preference tracking

**Integration**: Background service, transparent to all agents

---

### Knowledge Archaeologist

**Role**: Deep research and knowledge excavation specialist

**Description**: Uncovers hidden patterns, historical context, and buried insights from codebases and documentation.

**Key Capabilities**:
- Git history analysis
- Pattern discovery
- Context reconstruction
- Documentation archaeology

**When to Use**:
- Understanding system evolution
- Finding design rationale
- Uncovering hidden patterns
- Historical context needed

**Integration**: Works with analyzer for deep analysis, architect for design context

---

### Preference Reviewer

**Role**: User preference analysis for upstream contribution

**Description**: Analyzes user preferences to identify patterns worth contributing to Claude Code upstream.

**Key Capabilities**:
- Pattern analysis and scoring
- Generalizability assessment (0-30 pts)
- Implementation complexity (0-30 pts)
- User impact and philosophy alignment
- GitHub issue generation

**Contribution Threshold**: 60+ points

**When to Use**:
- Monthly preference audit
- Significant new preferences added
- Contribution drive active
- Analyzing preference value

**Integration**: Reads USER_PREFERENCES.md, generates GitHub issues

---

### Rust Programming Expert

**Role**: Rust language specialist

**Description**: Comprehensive knowledge of memory safety, ownership, borrowing, and systems programming in Rust.

**Key Capabilities**:
- Ownership system expertise
- Borrowing and references
- Lifetime annotations
- Zero-copy string parsing
- Error handling patterns

**Knowledge Base**: `amplihack-logparse/.claude/data/rust_focused_for_log_parser/`

**When to Use**:
- Rust compilation errors
- Ownership/borrowing issues
- Performance optimization
- Rust design questions

---

### Azure Kubernetes Expert

**Role**: AKS production deployment specialist

**Description**: Comprehensive knowledge of deploying, securing, and operating production workloads on Azure Kubernetes Service.

**Key Capabilities**:
- AKS architecture and control plane
- Node pools and scaling
- Networking (CNI, ingress)
- Identity and RBAC
- Monitoring and logging

**Knowledge Base**: `.claude/data/azure_aks_expert/`

**When to Use**:
- AKS cluster deployment
- Production hardening
- Troubleshooting AKS issues
- Cost optimization
- CI/CD integration

---

### Visualization Architect

**Role**: Visual communication specialist

**Description**: Creates ASCII diagrams, mermaid charts, and visual documentation to make complex systems understandable.

**Key Capabilities**:
- ASCII architecture diagrams
- Mermaid flowcharts
- Data flow visualization
- Brick-based visual thinking

**When to Use**:
- Architecture documentation
- Workflow visualization
- System communication
- Module structure diagrams

**Integration**: Works with architect for system visualization, knowledge-archaeologist for evolution diagrams

---

### Zen Architect

**Role**: Philosophy compliance guardian

**Description**: Ensures code aligns with amplihack's ruthless simplicity, brick philosophy, and Zen-like minimalism.

**Key Capabilities**:
- Philosophy validation
- Simplicity assessment
- Regeneration readiness check
- Red flag detection

**When to Use**:
- Architecture reviews
- Philosophy validation
- Simplicity enforcement
- Module design review

**Integration**: Works with architect for design validation, reviewer for philosophy compliance

---

### XPIA Defense

**Role**: Cross-Prompt Injection Attack defense specialist

**Description**: Provides transparent AI security protection with sub-100ms processing for prompt injection detection and prevention.

**Key Capabilities**:
- 3-tier threat detection (critical, suspicious, allowed)
- Context intelligence
- Zero false positives for dev work
- Transparent operation

**Operating Modes**: Standard, Strict, Learning

**When to Use**:
- Real-time threat protection
- AI security monitoring
- Prompt injection prevention
- Security compliance

**Integration**: Background service, transparent to all operations

---

### Amplifier CLI Architect

**Role**: Expert CLI architecture for hybrid code/AI systems

**Description**: Auto-selects CONTEXTUALIZE, GUIDE, or VALIDATE modes based on request type. Focuses on ccsdk_toolkit integration.

**Modes**:
- **CONTEXTUALIZE**: Architecture analysis
- **GUIDE**: Decision guidance and recommendations
- **VALIDATE**: Architecture validation

**When to Use**:
- CLI architecture decisions
- ccsdk_toolkit integration
- System design guidance
- Architecture validation

**Integration**: Works with all core agents, coordinates parallel analysis

---

## Workflow Agents

Workflow agents orchestrate multi-step processes.

### Amplihack Improvement Workflow

**Role**: Progressive validation workflow for amplihack project improvements

**Description**: Enforces 5-stage validation to prevent complexity creep. ONLY for improving the amplihack project itself.

**5 Stages**:
1. Problem Validation (check user requirements FIRST)
2. Minimal Solution Design
3. Implementation Validation
4. Integrated Review
5. Final Validation

**When to Use**: ONLY when improving the amplihack project (https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding)

**Critical Feature**: Checks user requirements at Stage 1 before any action

---

### Prompt Review Workflow

**Role**: Prompt review and refinement coordination

**Description**: Defines integration pattern between PromptWriter and Architect agents for complex prompts.

**Workflow**:
1. PromptWriter generates prompt
2. Architect reviews (if complex)
3. PromptWriter refines based on feedback
4. Optional GitHub issue creation

**When to Use**:
- Complex prompt generation
- Architecture-sensitive prompts
- Quality-checked specifications

---

## Fault Tolerance Agents

Fault tolerance agents implement resilience patterns for critical operations.

### N-Version Validator

**Role**: N-version programming fault-tolerance pattern

**Description**: Generates N independent implementations and selects the best through comparison and voting.

**Cost-Benefit**: 3-4x execution time, 30-65% error reduction

**When to Use**:
- Security-sensitive code (auth, encryption)
- Core algorithms (payment calculations)
- Mission-critical features

**Command**: `/amplihack:n-version "task description"`

**Integration**: Uses multiple builder agents in parallel, reviewer for comparison

---

### Multi-Agent Debate

**Role**: Structured debate pattern for decision-making

**Description**: Multiple agents with different perspectives debate a solution, converge through argument rounds, and reach consensus.

**Cost-Benefit**: 2-3x execution time, 40-70% better decision quality

**When to Use**:
- Architectural trade-offs
- Algorithm selection
- Security vs usability decisions
- Performance vs maintainability

**Command**: `/amplihack:debate "decision question"`

**Agent Profiles**: Security, Performance, Simplicity (default)

---

### Fallback Cascade

**Role**: Graceful degradation pattern for resilient operations

**Description**: Attempts primary approach, falls back to secondary/tertiary strategies if failures occur.

**Cost-Benefit**: 1.1-2x execution time (only on failures), 95%+ reliability

**When to Use**:
- External API calls (with fallbacks)
- Code generation (AI → templates → boilerplate)
- Data retrieval (DB → cache → defaults)
- Complex computations with approximations

**Command**: `/amplihack:cascade "operation description"`

**Pattern**: Primary (best) → Secondary (degraded) → Tertiary (minimal but reliable)

---

## Capability Matrix

| Agent | Parallel Execution | Sequential Required | Auto-Selects Mode | User Requirement Aware |
|-------|-------------------|---------------------|-------------------|----------------------|
| architect | ✓ | | | ✓ |
| builder | ✓ | ✓ (after architect) | | |
| reviewer | ✓ | | | ✓ (CRITICAL) |
| tester | ✓ | | | |
| optimizer | ✓ | | | |
| api-designer | ✓ | | | |
| analyzer | ✓ | | ✓ (TRIAGE/DEEP/SYNTHESIS) | |
| security | ✓ | | | |
| database | ✓ | | | |
| integration | ✓ | | | |
| patterns | ✓ | | | |
| cleanup | | | | ✓ (CRITICAL) |
| ambiguity | ✓ | | | |
| prompt-writer | | ✓ (→ architect) | | |
| fix-agent | | | ✓ (QUICK/DIAGNOSTIC/COMPREHENSIVE) | |
| pre-commit-diagnostic | | ✓ | | |
| ci-diagnostic-workflow | | ✓ | | |
| n-version-validator | ✓ (N parallel) | ✓ (phases) | | |
| multi-agent-debate | ✓ (debate) | ✓ (rounds) | | |
| fallback-cascade | | ✓ (cascade) | | |
| worktree-manager | | | | |
| visualization-architect | ✓ | | | |
| zen-architect | ✓ | | | |
| amplifier-cli-architect | ✓ | | ✓ (CONTEXTUALIZE/GUIDE/VALIDATE) | |

## Agent Coordination Patterns

### Standard Development Flow

```
User Request
    │
    ▼
architect (design) ──► builder (implement) ──► reviewer (validate) ──► tester (verify)
    │                       │                        │                      │
    ├─► api-designer        ├─► security            ├─► cleanup            └─► Done
    └─► database            └─► integration         └─► zen-architect
```

### Parallel Analysis Template

```
Task: Comprehensive Feature Review

Parallel Execution:
├─► analyzer (codebase structure)
├─► security (vulnerability scan)
├─► optimizer (performance analysis)
├─► patterns (pattern detection)
└─► reviewer (quality assessment)

Synthesis:
└─► Combine results for holistic view
```

### Sequential Workflow Template

```
Task: New Feature Implementation

Sequential Steps:
1. prompt-writer (structured spec) ──► architect (review if complex)
2. worktree-manager (setup branch)
3. architect (design solution)
4. builder (implement)
5. tester (create tests)
6. pre-commit-diagnostic (local validation)
7. git push
8. ci-diagnostic-workflow (CI validation)
9. reviewer (code review)
10. cleanup (post-task hygiene)
```

### Fault Tolerance Pattern

```
Critical Security Implementation:

/amplihack:n-version "Implement JWT token validation"
    │
    ├─► builder-1 (PyJWT approach)
    ├─► builder-2 (manual decode)
    └─► builder-3 (hybrid security)
         │
         ▼
    reviewer (compare all 3)
         │
         ▼
    Select best approach
```

## Usage Guidelines

### When to Use Parallel Execution

✓ **Independent analysis tasks**: Multiple agents analyzing same target
✓ **Multiple perspectives**: Security + performance + patterns
✓ **Separate components**: Different modules or systems
✓ **Batch operations**: Multiple files or resources

### When to Use Sequential Execution

✓ **Hard dependencies**: Output of A needed for input to B
✓ **State mutations**: Operations that modify shared state
✓ **User-specified order**: Explicit sequential requirements
✓ **Workflow phases**: Distinct stages that build on each other

### Microsoft Amplifier Parallel Execution Templates

**Template 1: Comprehensive Feature Development**
```
[architect, security, database, api-designer, tester]
```

**Template 2: Multi-Dimensional Code Analysis**
```
[analyzer, security, optimizer, patterns, reviewer]
```

**Template 3: Comprehensive Problem Diagnosis**
```
[analyzer, environment, patterns, logs]
```

**Template 4: System Preparation and Validation**
```
[environment, validator, tester, ci-checker]
```

**Template 5: Research and Discovery**
```
[analyzer, patterns, explorer, documenter]
```

## Philosophy and Principles

All agents follow amplihack's core philosophy:

### Ruthless Simplicity
- Start with simplest solution that works
- Add complexity only when justified
- Question every abstraction

### Modular Design (Bricks & Studs)
- **Brick** = Self-contained module with ONE responsibility
- **Stud** = Public contract others connect to
- **Regeneratable** = Can be rebuilt from specification

### Zero-BS Implementation
- No stubs or placeholders
- No dead code
- Every function works or doesn't exist

### User Requirement Priority (MANDATORY)

**Priority Hierarchy**:
1. **EXPLICIT USER REQUIREMENTS** (HIGHEST - NEVER OVERRIDE)
2. **IMPLICIT USER PREFERENCES**
3. **PROJECT PHILOSOPHY**
4. **DEFAULT BEHAVIORS** (LOWEST)

**Critical for**: reviewer, cleanup, amplihack-improvement-workflow

## Agent Catalog Statistics

- **Total Agents**: 38
- **Core Agents**: 6
- **Specialized Agents**: 25
- **Workflow Agents**: 4
- **Fault Tolerance Agents**: 3

**By Capability**:
- Parallel-Ready Agents: 18
- Sequential-Required Agents: 10
- Auto-Mode Selection: 4
- User Requirement Aware: 3 (CRITICAL)

**By Domain**:
- Architecture & Design: 4
- Implementation & Building: 2
- Quality & Testing: 3
- Performance & Optimization: 2
- Security: 2
- Integration & APIs: 3
- Analysis & Research: 4
- Workflow Orchestration: 7
- Language/Platform Specific: 2
- Philosophy & Compliance: 2
- Utilities & Support: 7

## Getting Help

- **Review Philosophy**: `.claude/context/PHILOSOPHY.md`
- **Check Patterns**: `.claude/context/PATTERNS.md`
- **Agent Capabilities**: This catalog
- **Update Learnings**: `.claude/context/DISCOVERIES.md`

## Remember

You are the orchestrator working with specialized agents. Delegate liberally, execute in parallel when possible, and continuously learn. The catalog is your guide to the right agent for every task.

---

*Last Updated: 2025-11-05*
*Agents Cataloged: 38*
*Categories: Core (6), Specialized (25), Workflow (4), Fault Tolerance (3)*
