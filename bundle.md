---
bundle:
  name: amplihack
  version: 1.0.0
  description: |
    Amplihack development framework - systematic AI-powered development workflows
    with 40 specialized agents, 73 skills, 10 workflow recipes, and philosophy-driven design.

includes:
  # Inherit foundation capabilities (tools, hooks, core agents)
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  # Include recipes behavior for workflow execution
  - bundle: git+https://github.com/microsoft/amplifier-bundle-recipes@main
  # Amplihack-specific behavior (agents, context)
  - bundle: amplihack:behaviors/amplihack.yaml

# Provider configuration (defaults to Anthropic, user can override in settings)
providers:
  - module: provider-anthropic
    source: git+https://github.com/microsoft/amplifier-module-provider-anthropic@main
    config:
      api_key: ${ANTHROPIC_API_KEY}
      default_model: claude-sonnet-4-20250514

# Amplihack Custom Modules
# These modules are in modules/ directory and provide advanced capabilities:
#
# Tools:
#   - tool-lock: File locking with multi-model debate resolution
#   - tool-memory: SQLite-backed agent memory system
#   - tool-session-utils: Fork management and instruction appending
#   - tool-workflow: Workflow tracking and transcript management
#
# Hooks:
#   - hook-power-steering: 6,466 lines of advanced session quality checks
#   - hook-agent-memory: Automatic memory injection into agent context
#   - hook-xpia-defense: Prompt injection detection and defense
#
# To use locally, install with: pip install -e modules/<module-name>/

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
  amplihack-improvement-workflow:
    path: amplihack:agents/amplihack-improvement-workflow.md
    description: Amplihack-specific improvement workflow
  ci-diagnostic-workflow:
    path: amplihack:agents/ci-diagnostic-workflow.md
    description: CI/CD diagnostic workflow with full context
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

## Auto Mode & CLI

@amplihack:context/auto-mode.md
@amplihack:context/cli-reference.md

## Skills Reference (73 Skills)

Load skills with `@amplihack:skills/<skill-name>/SKILL.md`

### Workflow Skills (11)
- `cascade-workflow` - Graceful degradation workflow
- `consensus-voting` - Multi-agent consensus building
- `debate-workflow` - Structured multi-perspective debate
- `default-workflow` - Standard development workflow
- `goal-seeking-agent-pattern` - Goal-driven agent generation
- `investigation-workflow` - Systematic investigation
- `n-version-workflow` - N-version programming
- `philosophy-compliance-workflow` - Philosophy adherence checks
- `quality-audit-workflow` - Quality assessment
- `ultrathink-orchestrator` - Deep analysis orchestration
- `eval-recipes-runner` - Recipe evaluation runner

### Domain Analyst Skills (20)
Multi-disciplinary analysis perspectives with theoretical frameworks:
- `anthropologist-analyst`, `biologist-analyst`, `chemist-analyst`
- `computer-scientist-analyst`, `cybersecurity-analyst`, `economist-analyst`
- `engineer-analyst`, `environmentalist-analyst`, `epidemiologist-analyst`
- `ethicist-analyst`, `futurist-analyst`, `historian-analyst`
- `indigenous-leader-analyst`, `journalist-analyst`, `lawyer-analyst`
- `novelist-analyst`, `philosopher-analyst`, `physicist-analyst`
- `poet-analyst`, `political-scientist-analyst`, `psychologist-analyst`
- `sociologist-analyst`, `urban-planner-analyst`

### Technical Skills (22)
- `agent-sdk` - Agent SDK patterns
- `azure-admin` - Azure administration
- `azure-devops` - Azure DevOps pipelines
- `azure-devops-cli` - Azure DevOps CLI
- `code-smell-detector` - Code quality detection
- `context_management` - Context window management
- `design-patterns-expert` - Software design patterns
- `docx` - Word document processing
- `documentation-writing` - Technical documentation
- `dynamic-debugger` - Dynamic debugging
- `email-drafter` - Professional email composition
- `mcp-manager` - MCP server management
- `mermaid-diagram-generator` - Diagram generation
- `microsoft-agent-framework` - Microsoft AI agents
- `module-spec-generator` - Module specification
- `outside-in-testing` - Integration testing patterns
- `pdf` - PDF document processing
- `pptx` - PowerPoint processing
- `xlsx` - Excel processing
- `remote-work` - Remote execution patterns
- `test-gap-analyzer` - Test coverage analysis
- `skill-builder` - Skill creation patterns

### Meta/Collaboration Skills (16)
- `backlog-curator` - Backlog management
- `collaboration` - Team collaboration patterns
- `common` - Shared utilities
- `development` - Development workflow skills
- `knowledge-extractor` - Knowledge mining
- `learning-path-builder` - Learning paths
- `meeting-synthesizer` - Meeting summaries
- `meta-cognitive` - Meta-cognition patterns
- `model-evaluation-benchmark` - Model evaluation
- `pm-architect` - Project management
- `pr-review-assistant` - PR review automation
- `quality` - Quality assurance
- `research` - Research methodology
- `roadmap-strategist` - Strategic planning
- `storytelling-synthesizer` - Narrative construction
- `work-delegator` - Task delegation
- `workstream-coordinator` - Workstream management

## Workflow Recipes (10)

Execute with `recipes` tool using `amplihack:recipes/<recipe>.yaml`:

### Core Workflows
- `default-workflow.yaml` - Standard 22-step development workflow (staged with approval gates)
- `default-workflow-autonomous.yaml` - Autonomous version (no approval gates)
- `improvement-workflow.yaml` - 5-stage progressive validation

### Investigation & Research
- `investigation-workflow.yaml` - 6-phase systematic investigation
- `qa-workflow.yaml` - 3-step Q&A pattern

### Multi-Agent Patterns
- `debate-workflow.yaml` - 8-step structured multi-perspective debate
- `consensus-workflow.yaml` - 21-step consensus building (combines debate + n-version)
- `n-version-workflow.yaml` - 7-step N-version programming for critical code
- `cascade-workflow.yaml` - 7-step graceful degradation fallback

### Meta Workflows
- `workflow-selector.yaml` - Automatic workflow selection based on task analysis

### Documentation
- `DEFAULT_WORKFLOW_TRANSLATION.md` - Translation guide from amplihack to Amplifier

## Hooks

- `auto-update-user-preferences` - Captures expressed preferences
- `xpia-defense` - Prompt injection detection
- `philosophy-guardian` - Philosophy compliance monitoring
- `auto-mode` - Autonomous operation control

---

@foundation:context/shared/common-system-base.md
