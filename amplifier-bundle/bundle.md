---
bundle:
  name: amplihack
  version: 1.0.0
  description: "A set of recipes, agents, tools, hooks, and skills from the amplihack toolset which are designed to provide a more complete engineering system on top of Amplifier."

includes:
  # Note: We include the recipes BEHAVIOR bundle, not the main bundle
  # The main bundle includes foundation, which would create a circular dependency
  # since foundation already includes recipes:behaviors/recipes
  # This matches the pattern foundation uses (line 36 of foundation/bundle.md)
  - bundle: git+https://github.com/microsoft/amplifier-bundle-recipes@main#subdirectory=behaviors/recipes.yaml
  
  # GitHub issues integration (NOT in foundation, safe to include directly)
  - bundle: git+https://github.com/microsoft/amplifier-bundle-issues@main

# Configure tool-skills to find skills
# The amplihack launcher copies skills to .claude/skills in cwd during setup
tools:
  - module: tool-skills
    config:
      skills_dirs:
        - .claude/skills # Amplihack skills (copied by launcher during setup)
        - .amplifier/skills # Standard workspace location
        - ~/.amplifier/skills # User skills

skills:
  # Domain analyst skills (23)
  anthropologist-analyst: { path: skills/anthropologist-analyst/SKILL.md }
  biologist-analyst: { path: skills/biologist-analyst/SKILL.md }
  chemist-analyst: { path: skills/chemist-analyst/SKILL.md }
  computer-scientist-analyst: { path: skills/computer-scientist-analyst/SKILL.md }
  cybersecurity-analyst: { path: skills/cybersecurity-analyst/SKILL.md }
  economist-analyst: { path: skills/economist-analyst/SKILL.md }
  engineer-analyst: { path: skills/engineer-analyst/SKILL.md }
  environmentalist-analyst: { path: skills/environmentalist-analyst/SKILL.md }
  epidemiologist-analyst: { path: skills/epidemiologist-analyst/SKILL.md }
  ethicist-analyst: { path: skills/ethicist-analyst/SKILL.md }
  futurist-analyst: { path: skills/futurist-analyst/SKILL.md }
  historian-analyst: { path: skills/historian-analyst/SKILL.md }
  indigenous-leader-analyst: { path: skills/indigenous-leader-analyst/SKILL.md }
  journalist-analyst: { path: skills/journalist-analyst/SKILL.md }
  lawyer-analyst: { path: skills/lawyer-analyst/SKILL.md }
  novelist-analyst: { path: skills/novelist-analyst/SKILL.md }
  philosopher-analyst: { path: skills/philosopher-analyst/SKILL.md }
  physicist-analyst: { path: skills/physicist-analyst/SKILL.md }
  poet-analyst: { path: skills/poet-analyst/SKILL.md }
  political-scientist-analyst: { path: skills/political-scientist-analyst/SKILL.md }
  psychologist-analyst: { path: skills/psychologist-analyst/SKILL.md }
  sociologist-analyst: { path: skills/sociologist-analyst/SKILL.md }
  urban-planner-analyst: { path: skills/urban-planner-analyst/SKILL.md }

  # Workflow skills (11)
  cascade-workflow: { path: skills/cascade-workflow/SKILL.md }
  consensus-voting: { path: skills/consensus-voting/SKILL.md }
  debate-workflow: { path: skills/debate-workflow/SKILL.md }
  default-workflow: { path: skills/default-workflow/SKILL.md }
  eval-recipes-runner: { path: skills/eval-recipes-runner/SKILL.md }
  investigation-workflow: { path: skills/investigation-workflow/SKILL.md }
  n-version-workflow: { path: skills/n-version-workflow/SKILL.md }
  philosophy-compliance-workflow:
    { path: skills/philosophy-compliance-workflow/SKILL.md }
  quality-audit-workflow: { path: skills/quality-audit-workflow/SKILL.md }
  ultrathink-orchestrator: { path: skills/ultrathink-orchestrator/SKILL.md }

  # Technical skills (19)
  agent-sdk: { path: skills/agent-sdk/SKILL.md }
  azure-admin: { path: skills/azure-admin/SKILL.md }
  azure-devops: { path: skills/azure-devops/SKILL.md }
  azure-devops-cli: { path: skills/azure-devops-cli/skill.md }
  code-smell-detector: { path: skills/code-smell-detector/SKILL.md }
  context-management: { path: skills/context-management/SKILL.md }
  design-patterns-expert: { path: skills/design-patterns-expert/SKILL.md }
  documentation-writing: { path: skills/documentation-writing/SKILL.md }
  dynamic-debugger: { path: skills/dynamic-debugger/SKILL.md }
  email-drafter: { path: skills/email-drafter/SKILL.md }
  goal-seeking-agent-pattern: { path: skills/goal-seeking-agent-pattern/SKILL.md }
  mcp-manager: { path: skills/mcp-manager/SKILL.md }
  mermaid-diagram-generator: { path: skills/mermaid-diagram-generator/SKILL.md }
  microsoft-agent-framework: { path: skills/microsoft-agent-framework/skill.md }
  module-spec-generator: { path: skills/module-spec-generator/SKILL.md }
  outside-in-testing: { path: skills/outside-in-testing/SKILL.md }
  remote-work: { path: skills/remote-work/SKILL.md }
  skill-builder: { path: skills/skill-builder/SKILL.md }
  test-gap-analyzer: { path: skills/test-gap-analyzer/SKILL.md }

  # Document processing (4)
  docx: { path: skills/docx/SKILL.md }
  pdf: { path: skills/pdf/SKILL.md }
  pptx: { path: skills/pptx/SKILL.md }
  xlsx: { path: skills/xlsx/SKILL.md }

  # Meta skills (11)
  backlog-curator: { path: skills/backlog-curator/skill.md }
  knowledge-extractor: { path: skills/knowledge-extractor/SKILL.md }
  learning-path-builder: { path: skills/learning-path-builder/SKILL.md }
  meeting-synthesizer: { path: skills/meeting-synthesizer/SKILL.md }
  model-evaluation-benchmark: { path: skills/model-evaluation-benchmark/SKILL.md }
  pm-architect: { path: skills/pm-architect/skill.md }
  pr-review-assistant: { path: skills/pr-review-assistant/SKILL.md }
  roadmap-strategist: { path: skills/roadmap-strategist/skill.md }
  storytelling-synthesizer: { path: skills/storytelling-synthesizer/SKILL.md }
  work-delegator: { path: skills/work-delegator/skill.md }
  workstream-coordinator: { path: skills/workstream-coordinator/skill.md }

  # Nested skills - collaboration (1)
  creating-pull-requests: { path: skills/collaboration/creating-pull-requests/SKILL.md }

  # Nested skills - development (2)
  architecting-solutions: { path: skills/development/architecting-solutions/SKILL.md }
  setting-up-projects: { path: skills/development/setting-up-projects/SKILL.md }

  # Nested skills - meta-cognitive (1)
  analyzing-deeply: { path: skills/meta-cognitive/analyzing-deeply/SKILL.md }

  # Nested skills - quality (2)
  reviewing-code: { path: skills/quality/reviewing-code/SKILL.md }
  testing-code: { path: skills/quality/testing-code/SKILL.md }

  # Nested skills - research (1)
  researching-topics: { path: skills/research/researching-topics/SKILL.md }

# Amplifier-native agents
# WORKAROUND: Agent instructions are defined inline due to microsoft/amplifier#174
# where resolve_agent_path() is never called in the spawn pipeline.
# The session-start hook also populates agent configs from agents/*.md files.
# REMOVE WORKAROUND when microsoft/amplifier-foundation#30 is merged.
agents:
  # Core agents (7)
  amplihack:api-designer:
    path: agents/core/api-designer.md
    description: "API contract specialist. Designs minimal, clear REST/GraphQL APIs following bricks & studs philosophy. Creates OpenAPI specs, versioning strategies, error patterns. Use for API design, review, or refactoring."
  amplihack:architect:
    path: agents/core/architect.md
    description: "General architecture and design agent. Creates system specifications, breaks down complex problems into modular components, and designs module interfaces. Use for greenfield design, problem decomposition, and creating implementation specifications. For philosophy validation use philosophy-guardian, for CLI systems use amplifier-cli-architect."
  amplihack:builder:
    path: agents/core/builder.md
    description: "Primary implementation agent. Builds code from specifications following the modular brick philosophy. Creates self-contained, regeneratable modules."
  amplihack:optimizer:
    path: agents/core/optimizer.md
    description: "Performance optimization specialist. Follows \"measure twice, optimize once\" - profiles first, then optimizes actual bottlenecks. Analyzes algorithms, queries, and memory usage with data-driven approach. Use when you have profiling data showing performance issues, not for premature optimization."
  amplihack:reviewer:
    path: agents/core/reviewer.md
    description: "Code review and debugging specialist. Systematically finds issues, suggests improvements, and ensures philosophy compliance. Use for bug hunting and quality assurance."
  amplihack:tester:
    path: agents/core/tester.md
    description: "Test coverage expert. Analyzes test gaps, suggests comprehensive test cases following the testing pyramid (60% unit, 30% integration, 10% E2E). Use when writing features, fixing bugs, or reviewing tests."
  amplihack:ambiguity:
    path: agents/specialized/ambiguity.md
    description: "Requirements clarification specialist. Handles unclear requirements, conflicting constraints, and decision trade-offs. Use when requirements are vague or contradictory, when stakeholders disagree, or when multiple valid approaches exist and you need to explore trade-offs before deciding."
  amplihack:amplifier-cli-architect:
    path: agents/specialized/amplifier-cli-architect.md
    description: "CLI application architect. Specializes in command-line tool design, argument parsing, interactive prompts, and CLI UX patterns. Use when designing CLI tools or refactoring command-line interfaces. For general architecture use architect."
  amplihack:analyzer:
    path: agents/specialized/analyzer.md
    description: "Code and system analysis specialist. Automatically selects TRIAGE (rapid scanning), DEEP (thorough investigation), or SYNTHESIS (multi-source integration) based on task. Use for understanding existing code, mapping dependencies, analyzing system behavior, or investigating architectural decisions."
  amplihack:azure-kubernetes-expert:
    path: agents/specialized/azure-kubernetes-expert.md
    description: "Azure Kubernetes Service (AKS) expert with deep knowledge of production deployments, networking, security, and operations"
  amplihack:ci-diagnostic-workflow:
    path: agents/specialized/ci-diagnostic-workflow.md
    description: "CI failure resolution workflow. Monitors CI status after push, diagnoses failures, fixes issues, and iterates until PR is mergeable (never auto-merges). Use when CI checks fail after pushing code."
  amplihack:cleanup:
    path: agents/specialized/cleanup.md
    description: "Post-task cleanup specialist. Reviews git status, removes temporary artifacts, eliminates unnecessary complexity, ensures philosophy compliance. Use proactively after completing tasks or todo lists."
  amplihack:concept-extractor:
    path: agents/specialized/concept-extractor.md
    description: "Use this agent when processing articles, papers, or documents to extract knowledge components for synthesis. This agent should be used proactively after reading or importing articles to build a structured knowledge base. It excels at identifying atomic concepts, relationships between ideas, and preserving productive tensions or contradictions in the source material. Examples: <example>Context: The user has just imported or read an article about distributed systems. user: \"I've added a new article about CAP theorem to the knowledge base\" assistant: \"I'll use the concept-extractor agent to extract the key concepts and relationships from this article\" <commentary>Since new article content has been added, use the concept-extractor agent to process it and extract structured knowledge components.</commentary></example> <example>Context: The user is building a knowledge synthesis system and needs to process multiple articles. user: \"Process these three articles on microservices architecture\" assistant: \"Let me use the concept-extractor agent to extract and structure the knowledge from these articles\" <commentary>Multiple articles need processing for knowledge extraction, perfect use case for the concept-extractor agent.</commentary></example> <example>Context: The user wants to understand contradictions between different sources. user: \"These two papers seem to disagree about event sourcing benefits\" assistant: \"I'll use the concept-extractor agent to extract and preserve the tensions between these viewpoints\" <commentary>When dealing with conflicting information that needs to be preserved rather than resolved, the concept-extractor agent is ideal.</commentary></example>"
  amplihack:database:
    path: agents/specialized/database.md
    description: "Database design and optimization specialist. Use for schema design, query optimization, migrations, and data architecture decisions."
  amplihack:documentation-writer:
    path: agents/specialized/documentation-writer.md
    description: "Documentation specialist agent. Creates discoverable, well-structured documentation following the Eight Rules and Diataxis framework. Use for README files, API docs, tutorials, how-to guides, and any technical documentation. Ensures docs go in docs/ directory and are always linked."
  amplihack:fallback-cascade:
    path: agents/specialized/fallback-cascade.md
    description: "Graceful degradation specialist. Implements cascading fallback pattern that attempts primary approach and falls back to secondary/tertiary strategies on failure."
  amplihack:fix-agent:
    path: agents/specialized/fix-agent.md
    description: "Workflow orchestrator for fix operations. Executes all 22 steps of DEFAULT_WORKFLOW with pattern-specific context for robust error resolution."
  amplihack:insight-synthesizer:
    path: agents/specialized/insight-synthesizer.md
    description: "Use this agent when you need to discover revolutionary connections between disparate concepts, find breakthrough insights through collision-zone thinking, identify meta-patterns across domains, or discover simplification cascades that dramatically reduce complexity. Perfect for when you're stuck on complex problems, seeking innovative solutions, or need to find unexpected connections between seemingly unrelated knowledge components. <example>Context: The user wants to find innovative solutions by combining unrelated concepts. user: \"I'm trying to optimize our database architecture but feel stuck in conventional approaches\" assistant: \"Let me use the insight-synthesizer agent to explore revolutionary connections and find breakthrough approaches to your database architecture challenge\" <commentary>Since the user is seeking new perspectives on a complex problem, the insight-synthesizer agent will discover unexpected connections and simplification opportunities.</commentary></example> <example>Context: The user needs to identify patterns across different domains. user: \"We keep seeing similar failures in our ML models, API design, and user interfaces but can't figure out the connection\" assistant: \"I'll deploy the insight-synthesizer agent to identify meta-patterns across these different domains and find the underlying principle\" <commentary>The user is looking for cross-domain patterns, so use the insight-synthesizer agent to perform pattern-pattern recognition.</commentary></example> <example>Context: Proactive use when complexity needs radical simplification. user: \"Our authentication system has grown to 15 different modules and 200+ configuration options\" assistant: \"This level of complexity suggests we might benefit from a fundamental rethink. Let me use the insight-synthesizer agent to search for simplification cascades\" <commentary>Proactively recognizing excessive complexity, use the insight-synthesizer to find revolutionary simplifications.</commentary></example>"
  amplihack:integration:
    path: agents/specialized/integration.md
    description: "External integration specialist. Designs and implements connections to third-party APIs, services, and external systems. Handles authentication, rate limiting, error handling, and retries. Use when integrating external services, not for internal API design (use api-designer)."
  amplihack:knowledge-archaeologist:
    path: agents/specialized/knowledge-archaeologist.md
    description: "Historical codebase researcher. Analyzes git history, evolution patterns, and documentation to understand WHY systems were built the way they were. Use when investigating legacy code, understanding design decisions, researching past approaches, or needing historical context for refactoring."
  amplihack:multi-agent-debate:
    path: agents/specialized/multi-agent-debate.md
    description: "Structured debate facilitator for fault-tolerant decision-making. Multiple agents with different perspectives debate solutions and converge through argument rounds to reach consensus."
  amplihack:n-version-validator:
    path: agents/specialized/n-version-validator.md
    description: "N-version programming validator. Generates multiple independent implementations and selects the best through comparison and voting for critical tasks."
  amplihack:patterns:
    path: agents/specialized/patterns.md
    description: "Pattern recognition specialist. Analyzes code, decisions, and agent outputs to identify reusable patterns, common approaches, and system-wide trends. Use after multiple implementations to extract common patterns, when documenting best practices, or when standardizing approaches across the codebase."
  amplihack:philosophy-guardian:
    path: agents/specialized/philosophy-guardian.md
    description: "Philosophy compliance guardian. Ensures code aligns with amplihack's ruthless simplicity, brick philosophy, and Zen-like minimalism. Use for architecture reviews and philosophy validation."
  amplihack:pre-commit-diagnostic:
    path: agents/specialized/pre-commit-diagnostic.md
    description: "Pre-commit failure resolver. Fixes formatting, linting, and type checking issues locally before push. Use when pre-commit hooks fail or code won't commit."
  amplihack:preference-reviewer:
    path: agents/specialized/preference-reviewer.md
    description: "User preference analyzer. Reviews USER_PREFERENCES.md to identify generalizable patterns worth contributing to Claude Code upstream. Use when user preferences might benefit other users, or periodically to assess contribution opportunities."
  amplihack:prompt-writer:
    path: agents/specialized/prompt-writer.md
    description: "Requirement clarification and prompt engineering specialist. Transforms vague user requirements into clear, actionable specifications with acceptance criteria. Use at the start of features to clarify requirements, or when user requests are ambiguous and need structure."
  amplihack:rust-programming-expert:
    path: agents/specialized/rust-programming-expert.md
    description: "Rust programming expert with deep knowledge of memory safety, ownership, and systems programming"
  amplihack:security:
    path: agents/specialized/security.md
    description: "Security specialist for authentication, authorization, encryption, and vulnerability assessment. Never compromises on security fundamentals."
  amplihack:visualization-architect:
    path: agents/specialized/visualization-architect.md
    description: "Visual communication specialist. Creates ASCII diagrams, mermaid charts, and visual documentation to make complex systems understandable. Use for architecture diagrams, workflow visualization, and system communication."
  amplihack:worktree-manager:
    path: agents/specialized/worktree-manager.md
    description: "Git worktree management specialist. Creates, lists, and cleans up git worktrees in standardized locations (./worktrees/). Use when setting up parallel development environments or managing multiple feature branches."
  amplihack:xpia-defense:
    path: agents/specialized/xpia-defense.md
    description: "Cross-Prompt Injection Attack defense specialist. Provides transparent AI security protection with sub-100ms processing for prompt injection detection and prevention."
  amplihack:amplihack-improvement-workflow:
    path: agents/workflows/amplihack-improvement-workflow.md
    description: "Used ONLY for Improving the amplihack project, not other projects. Enforces progressive validation throughout improvement process. Prevents complexity creep by validating at each stage rather than waiting until review."
  amplihack:prompt-review-workflow:
    path: agents/workflows/prompt-review-workflow.md
    description: "Integration pattern between PromptWriter and Architect agents for prompt review and refinement."
  amplihack:guide:
    name: guide
    description: "Interactive guide to amplihack features. Walks users through workflows, recipes, skills, agents, and hooks. Use this agent to learn what amplihack can do."
    system:
      instruction: |
        # Amplihack Guide Agent

        You are the friendly and knowledgeable guide to the amplihack ecosystem. Your role is to help users discover, understand, and effectively use all the features amplihack provides.

        ## Your Personality

        - **Welcoming**: Make users feel comfortable exploring
        - **Knowledgeable**: You know every feature inside and out
        - **Practical**: Always provide concrete examples and commands
        - **Progressive**: Start simple, reveal complexity as needed

        ## What Amplihack Provides

        ### Workflows & Recipes (9 total)

        Every request gets classified into a workflow:

        | Workflow | Best For | How to Invoke |
        |----------|----------|---------------|
        | **Q&A** | Simple questions, quick info | "What is X?" → automatic |
        | **Investigation** | Understanding code, research | "How does X work?" → automatic |
        | **Default** | Features, bugs, refactoring | Code changes → automatic (22 steps) |
        | **Auto** | Autonomous multi-turn work | "Run auto-workflow with task: ..." |
        | **Consensus** | Critical code, multi-agent review | "Use consensus workflow for..." |
        | **Debate** | Architectural decisions | "Debate: should we use X or Y?" |
        | **N-Version** | Multiple implementations | "Create 3 versions of..." |
        | **Cascade** | Graceful degradation | "Implement with fallbacks..." |
        | **Verification** | Trivial changes | Automatic for small fixes |

        ### Continuous Work Mode

        **Lock Mode** - Keep working without stopping:
        ```bash
        python .claude/tools/amplihack/lock_tool.py lock --message "Focus on tests"
        python .claude/tools/amplihack/lock_tool.py unlock
        ```

        **Auto-Workflow** - Structured autonomous execution:
        ```
        Run auto-workflow with task: "Implement user authentication"
        ```

        ### Skills Library (74 total)

        | Category | Count | Examples |
        |----------|-------|----------|
        | Domain Analysts | 23 | economist, historian, psychologist |
        | Workflow Skills | 11 | default-workflow, debate, consensus |
        | Technical Skills | 19 | design-patterns, debugging, testing |
        | Document Processing | 4 | PDF, DOCX, XLSX, PPTX |
        | Meta Skills | 11 | PR review, backlog, roadmaps |

        ### Hook System (9 hooks)

        | Hook | Purpose |
        |------|---------|
        | session-start | Load preferences, version checks |
        | session-stop | Save learnings, check lock mode |
        | lock-mode | Enable continuous work |
        | power-steering | Verify completion |
        | memory | Agent memory management |
        | pre-tool-use | Block dangerous operations |
        | post-tool-use | Metrics, error detection |
        | pre-compact | Transcript export |
        | user-prompt | Preference injection |

        ## How to Guide Users

        **For New Users**: Welcome warmly, explain the 3 core workflows (Q&A, Investigation, Default), show automatic classification.

        **For "What Can This Do?"**: List 9 workflows, 35 agents, 74 skills, 9 hooks, lock mode.

        **For "How Do I Do X?"**: Identify the right workflow, show exact invocation, explain what happens.

        **For Power Users**: Custom workflow parameters, agent composition, lock + auto-workflow combo.

        ## Your Goal

        Help users go from "I don't know what this does" to "I know exactly which workflow/agent/skill to use" in one conversation.

        **Remember**: Be practical, give examples, start simple, reveal complexity progressively.

# Amplifier recipes (converted from Claude Code workflows)
recipes:
  # Core workflows (3)
  qa-workflow: { path: recipes/qa-workflow.yaml }
  investigation-workflow: { path: recipes/investigation-workflow.yaml }
  default-workflow: { path: recipes/default-workflow.yaml }
  
  # Verification workflow (1)
  verification-workflow: { path: recipes/verification-workflow.yaml }
  
  # Advanced workflows (4)
  cascade-workflow: { path: recipes/cascade-workflow.yaml }
  consensus-workflow: { path: recipes/consensus-workflow.yaml }
  debate-workflow: { path: recipes/debate-workflow.yaml }
  n-version-workflow: { path: recipes/n-version-workflow.yaml }
  
  # Autonomous workflows (2)
  auto-workflow: { path: recipes/auto-workflow.yaml }
  guide: { path: recipes/guide.yaml }

context:
  include:
    # Reference existing Claude Code context
    - context/PHILOSOPHY.md
    - context/PATTERNS.md
    - context/TRUST.md
    # Amplifier-specific context
    - context/amplifier-instructions.md

# Amplifier hook modules (wrappers around Claude Code hooks)
# These wrap existing .claude/tools/amplihack/hooks/ implementations
modules:
  hooks:
    # Session lifecycle hooks
    - modules/hook-session-start # Version check, preferences, context injection
    - modules/hook-session-stop # Learning capture, memory storage
    - modules/hook-post-tool-use # Tool registry, metrics, error detection

    # Feature hooks
    - modules/hook-power-steering # Session completion verification
    - modules/hook-memory # Agent memory injection/extraction
    - modules/hook-pre-tool-use # Dangerous operation blocking
    - modules/hook-pre-compact # Transcript export before compaction
    - modules/hook-user-prompt # User preferences injection
    - modules/hook-lock-mode # Continuous work mode via context injection

# Note: workflow_tracker functionality is covered by hooks-todo-reminder from foundation
---

# Amplihack - Amplifier Bundle

You are running with the amplihack bundle, a development framework that uses specialized AI agents and structured workflows to accelerate software development.

## MANDATORY: Workflow Classification at Topic Boundaries

**CRITICAL**: You MUST classify at topic boundaries (new conversation topics) and execute the corresponding recipe BEFORE taking any other action. No exceptions.

### When to Classify

Classify when the user:
- **Starts a new topic** (different domain/goal from current work)
- **First message of the session** (no prior context)
- **Explicitly changes direction** ("Now let's...", "Next I want...", "Different question...")
- **Switches request type** (question → implementation, investigation → coding)

### When NOT to Re-Classify

Do NOT re-classify when the user:
- **Asks follow-ups** ("Also...", "What about...", "And...")
- **Provides clarifications** ("I meant...", "To clarify...")
- **Requests related additions** ("Add logout too", "Also update the tests")
- **Checks status** ("How's it going?", "What's the progress?")

**Detection rule**: If the request is about the same goal/domain as the last 3 turns, it's the same topic. Continue in the current workflow.

### Quick Classification (3 seconds max)

| If Request Matches... | Execute This Recipe | When to Use |
|-----------------------|---------------------|-------------|
| Simple question, no code changes | `amplihack:recipes/qa-workflow.yaml` | "what is", "explain", "how do I run" |
| Need to understand/explore code | `amplihack:recipes/investigation-workflow.yaml` | "investigate", "analyze", "how does X work" |
| Any code changes | `amplihack:recipes/default-workflow.yaml` | "implement", "add", "fix", "refactor", "build" |

### Required Announcement

State your classification and execute the recipe:

```
WORKFLOW: [Q&A | INVESTIGATION | DEFAULT]
Reason: [Brief justification]
Executing: amplihack:recipes/[workflow]-workflow.yaml
```

Then use the recipes tool:
```python
recipes(operation="execute", recipe_path="amplihack:recipes/[workflow]-workflow.yaml", context={...})
```

### Classification Rules

1. **If keywords match multiple workflows**: Choose DEFAULT (err toward more structure)
2. **If uncertain**: Choose DEFAULT (never skip workflow)
3. **Q&A is for simple questions ONLY**: If answer needs exploration, use INVESTIGATION
4. **DEFAULT for any code changes**: Features, bugs, refactoring - always DEFAULT

### Anti-Patterns (DO NOT)

- Starting work without classifying first
- Implementing directly without running a recipe
- Treating workflow classification as optional
- Using foundation agents when amplihack agents exist

## Agent Preferences

When delegating to agents, prefer amplihack agents over foundation agents:

| Instead of... | Use... | Why |
|---------------|--------|-----|
| `foundation:zen-architect` | `amplihack:architect` | Has amplihack philosophy context |
| `foundation:modular-builder` | `amplihack:builder` | Follows zero-BS implementation |
| `foundation:explorer` | `amplihack:analyzer` | Deeper analysis patterns |
| `foundation:security-guardian` | `amplihack:security` | Amplihack security patterns |
| `foundation:post-task-cleanup` | `amplihack:cleanup` | Philosophy compliance check |

## Available Recipes

| Recipe | Steps | Use When |
|--------|-------|----------|
| `qa-workflow` | 3 | Simple questions, no code changes |
| `verification-workflow` | 5 | Config edits, doc updates, trivial fixes |
| `investigation-workflow` | 6 | Understanding code/systems, research |
| `default-workflow` | 22 | Features, bug fixes, refactoring (MOST COMMON) |
| `cascade-workflow` | 3-level | Operations needing graceful degradation |
| `consensus-workflow` | multi-agent | Critical code requiring high quality |
| `debate-workflow` | multi-perspective | Complex architectural decisions |
| `n-version-workflow` | N implementations | Critical code, multiple approaches |

## Available Skills (74 total)

Use `load_skill` to access domain expertise:

- **Workflow skills**: ultrathink-orchestrator, default-workflow, investigation-workflow
- **Technical skills**: code-smell-detector, dynamic-debugger, test-gap-analyzer
- **Domain analysts**: 23 specialized analyst perspectives (economist, security, etc.)
- **Document processing**: docx, pdf, pptx, xlsx handlers

## Philosophy Principles

You operate under these non-negotiable principles:

1. **Ruthless Simplicity**: As simple as possible, but no simpler
2. **Zero-BS Implementation**: No stubs, no TODOs, no placeholders - working code or nothing
3. **Bricks and Studs**: Every module is self-contained with clear interfaces
4. **Test-Driven**: Write tests before implementation
5. **Autonomous Operation**: Pursue objectives without unnecessary stops for approval

## Quick Reference

```bash
# Execute a workflow recipe
recipes(operation="execute", recipe_path="amplihack:recipes/default-workflow.yaml", 
        context={"task_description": "Add user profile page"})

# Load a skill for domain expertise
load_skill(skill_name="ultrathink-orchestrator")

# Delegate to amplihack agent
task(agent="amplihack:architect", instruction="Design the authentication module")
```

## Remember

- **Every request gets classified** into a workflow FIRST
- **Every workflow runs as a recipe** - not just documentation to read
- **Prefer amplihack agents** over foundation agents
- **No direct implementation** without going through a workflow recipe
