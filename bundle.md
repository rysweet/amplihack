---
bundle:
  name: amplihack
  version: 1.0.0
  description: |
    Amplihack development framework - systematic AI-powered development workflows
    with 38 specialized agents, 66 skills, 10 workflow recipes, and philosophy-driven design.

includes:
  # Inherit foundation capabilities (tools, hooks, core agents)
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  # Include recipes behavior for workflow execution
  - bundle: git+https://github.com/microsoft/amplifier-bundle-recipes@main
  # Amplihack-specific behavior (agents, context)
  - bundle: amplihack:behaviors/amplihack

# Spawn configuration for sub-agents
spawn:
  exclude_tools: [tool-task]  # Prevent recursive spawning

# Agent registry (38 agents)
agents:
  # Core Development Agents
  architect:
    path: amplihack:agents/architect.md
    description: System architecture and design decisions
  builder:
    path: amplihack:agents/builder.md
    description: Implementation from specifications
  reviewer:
    path: amplihack:agents/reviewer.md
    description: Code review and quality assessment
  tester:
    path: amplihack:agents/tester.md
    description: Test strategy and implementation
  analyzer:
    path: amplihack:agents/analyzer.md
    description: Deep code and problem analysis
  optimizer:
    path: amplihack:agents/optimizer.md
    description: Performance optimization
  security:
    path: amplihack:agents/security.md
    description: Security analysis and hardening
  documentation-writer:
    path: amplihack:agents/documentation-writer.md
    description: Documentation generation
  database:
    path: amplihack:agents/database.md
    description: Database design and optimization
  api-designer:
    path: amplihack:agents/api-designer.md
    description: API design and documentation
  
  # Diagnostic Agents
  diagnostics:
    path: amplihack:agents/diagnostics.md
    description: Problem diagnosis and debugging
  pre-commit-diagnostic:
    path: amplihack:agents/pre-commit-diagnostic.md
    description: Pre-commit validation
  ci-diagnostic:
    path: amplihack:agents/ci-diagnostic.md
    description: CI/CD failure resolution
  fix-agent:
    path: amplihack:agents/fix-agent.md
    description: Rapid diagnosis and fix
  
  # Specialized Technical Agents
  rust-programming-expert:
    path: amplihack:agents/rust-programming-expert.md
    description: Rust language expertise
  azure-kubernetes-expert:
    path: amplihack:agents/azure-kubernetes-expert.md
    description: AKS and Kubernetes expertise
  amplifier-cli-architect:
    path: amplihack:agents/amplifier-cli-architect.md
    description: Amplifier ecosystem expertise
  visualization-architect:
    path: amplihack:agents/visualization-architect.md
    description: Data visualization design
  
  # Workflow Agents
  improvement-workflow:
    path: amplihack:agents/improvement-workflow.md
    description: 5-stage progressive validation
  prompt-review-workflow:
    path: amplihack:agents/prompt-review-workflow.md
    description: Prompt optimization workflow
  worktree-manager:
    path: amplihack:agents/worktree-manager.md
    description: Git worktree management
  
  # Synthesis Agents
  socratic:
    path: amplihack:agents/socratic.md
    description: Socratic questioning methodology
  concept-extractor:
    path: amplihack:agents/concept-extractor.md
    description: Abstract concept identification
  insight-synthesizer:
    path: amplihack:agents/insight-synthesizer.md
    description: Cross-domain pattern synthesis
  knowledge-archaeologist:
    path: amplihack:agents/knowledge-archaeologist.md
    description: Knowledge extraction and organization
  knowledge-archaeologist-specialized:
    path: amplihack:agents/knowledge-archaeologist-specialized.md
    description: Domain-specific knowledge extraction
  ambiguity:
    path: amplihack:agents/ambiguity.md
    description: Ambiguity detection and resolution
  patterns:
    path: amplihack:agents/patterns.md
    description: Pattern identification
  
  # Quality Agents
  philosophy-guardian:
    path: amplihack:agents/philosophy-guardian.md
    description: Philosophy compliance enforcement
  preference-reviewer:
    path: amplihack:agents/preference-reviewer.md
    description: User preference alignment
  prompt-writer:
    path: amplihack:agents/prompt-writer.md
    description: Effective prompt engineering
  xpia-defense:
    path: amplihack:agents/xpia-defense.md
    description: Prompt injection defense
  
  # Advanced Pattern Agents
  cleanup:
    path: amplihack:agents/cleanup.md
    description: Post-task workspace hygiene
  fallback-cascade:
    path: amplihack:agents/fallback-cascade.md
    description: Graceful degradation design
  integration:
    path: amplihack:agents/integration.md
    description: External integrations specialist
  memory-manager:
    path: amplihack:agents/memory-manager.md
    description: Session state persistence
  multi-agent-debate:
    path: amplihack:agents/multi-agent-debate.md
    description: Multi-perspective analysis
  n-version-validator:
    path: amplihack:agents/n-version-validator.md
    description: N-version programming validation
---

# Amplihack Development Framework

You are configured with the Amplihack development framework - a systematic approach to AI-powered software development that emphasizes ruthless simplicity, modular design, and autonomous execution.

## Core Philosophy

@amplihack:context/philosophy.md

## Instructions

@amplihack:context/instructions.md

## Special Operating Modes

@amplihack:context/special-modes.md

## Skills Reference

### Development Skills (10)
Load with `@amplihack:skills/development/<skill>.md`:
- `code-quality` - Linting, formatting, type checking
- `dependency-management` - Package management best practices
- `error-handling` - Exception handling patterns
- `git` - Git workflow and operations
- `logging` - Structured logging patterns
- `python` - Python development standards
- `refactoring` - Code improvement patterns
- `testing` - Test strategy and implementation
- `tdd` - Test-driven development methodology
- `debugging` - Systematic debugging approaches

### Workflow Skills (8)
Load with `@amplihack:skills/workflow/<skill>.md`:
- `investigation` - Problem investigation methodology
- `progressive-validation` - 5-stage validation pattern
- `reasoning-modes` - Different reasoning approaches
- `structured-debate` - Multi-perspective analysis
- `task-detection` - Automatic task type identification
- `ultrathink-default` - Deep analysis workflow
- `verification-patterns` - Output verification methods
- `workflow-states` - State machine for workflows

### Fix Templates (6)
Load with `@amplihack:skills/fix-templates/<template>.md`:
- `build-fix` - Build failure resolution
- `ci-fix` - CI pipeline troubleshooting
- `dependency-fix` - Dependency conflict resolution
- `lint-fix` - Linting error fixes
- `test-fix` - Test failure diagnosis
- `type-fix` - Type error resolution

### Domain Analyst Skills (20)
Load with `@amplihack:skills/domain-analysts/<analyst>.md`:
- Multi-disciplinary analysis perspectives
- Each provides theoretical frameworks, methodology, core questions
- Available: anthropologist, economist, ethicist, futurist, game-theorist, geopolitical, historian, journalist, legal, military-strategist, philosopher, political-scientist, psychologist, public-health, religious-studies, science-studies, sociologist, systems-theorist, urban-planner, environmental

### Azure Cloud Skills (9)
Load with `@amplihack:skills/azure/<skill>.md`:
- `azure-ai` - Azure OpenAI, Cognitive Services
- `azure-kubernetes` - AKS deployment and management
- `azure-functions` - Serverless compute
- `azure-identity` - Entra ID, managed identities
- `azure-storage` - Blob, files, queues, tables
- `azure-networking` - VNets, NSGs, Private Link
- `azure-devops` - Pipelines, repos, boards
- `azure-container-apps` - Serverless containers
- `azure-cosmos-db` - Globally distributed NoSQL

### Document Processing Skills (4)
Load with `@amplihack:skills/documents/<skill>.md`:
- `pdf` - PDF creation, merging, extraction
- `xlsx` - Excel workbook operations
- `docx` - Word document operations
- `pptx` - PowerPoint operations

### Communication Skills (4)
Load with `@amplihack:skills/communication/<skill>.md`:
- `storytelling-synthesizer` - Technical narratives
- `technical-writer` - Documentation best practices
- `prompt-writer` - Prompt engineering patterns
- `presentation-designer` - Visual presentation design

### Infrastructure Skills (2)
Load with `@amplihack:skills/infrastructure/<skill>.md`:
- `mcp-manager` - MCP server management
- `infrastructure` - IaC and deployment automation

## Workflow Recipes (10)

Execute with `recipes` tool:
- `default-workflow.yaml` - Standard 22-step development workflow
- `consensus-workflow.yaml` - 21-step consensus building
- `debate-workflow.yaml` - 8-step structured debate
- `n-version-workflow.yaml` - 7-step N-version validation
- `cascade-workflow.yaml` - 7-step fallback cascade
- `investigation-workflow.yaml` - 6-phase investigation
- `qa-workflow.yaml` - 3-step Q&A
- `improvement-workflow.yaml` - 5-stage progressive validation
- `fix-workflow.yaml` - Fix template-based resolution
- `exploration-workflow.yaml` - Codebase exploration

## Hooks

- `auto-update-user-preferences` - Captures expressed preferences
- `xpia-defense` - Prompt injection detection
- `philosophy-guardian` - Philosophy compliance monitoring
- `auto-mode` - Autonomous operation control

---

@foundation:context/shared/common-system-base.md
