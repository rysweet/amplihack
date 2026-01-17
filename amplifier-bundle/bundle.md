---
bundle:
  name: amplihack
  version: 1.0.0
  description: "A set of recipes, agents, tools, hooks, and skills from the amplihack toolset which are designed to provide a more complete engineering system on top of Amplifier."

includes:
  # Note: foundation is NOT explicitly included here because:
  # 1. Amplifier CLI already loads foundation as the default bundle
  # 2. amplifier-bundle-recipes includes foundation transitively
  # Including it again causes a "circular dependency" warning
  - bundle: git+https://github.com/microsoft/amplifier-bundle-recipes@main

# Configure tool-skills to find skills
# The amplihack launcher copies skills to .claude/skills in cwd during setup
tools:
  - module: tool-skills
    config:
      skills_dirs:
        - .claude/skills # Amplihack skills (copied by launcher during setup)
        - .amplifier/skills # Standard workspace location
        - ~/.amplifier/skills # User skills

# Reference existing Claude Code components via relative paths - NO DUPLICATION
# Note: The skills section below documents what's available but tool-skills
# discovers them via skills_dirs config above
skills:
  # Domain analyst skills (23)
  anthropologist-analyst: { path: ../.claude/skills/anthropologist-analyst/SKILL.md }
  biologist-analyst: { path: ../.claude/skills/biologist-analyst/SKILL.md }
  chemist-analyst: { path: ../.claude/skills/chemist-analyst/SKILL.md }
  computer-scientist-analyst: { path: ../.claude/skills/computer-scientist-analyst/SKILL.md }
  cybersecurity-analyst: { path: ../.claude/skills/cybersecurity-analyst/SKILL.md }
  economist-analyst: { path: ../.claude/skills/economist-analyst/SKILL.md }
  engineer-analyst: { path: ../.claude/skills/engineer-analyst/SKILL.md }
  environmentalist-analyst: { path: ../.claude/skills/environmentalist-analyst/SKILL.md }
  epidemiologist-analyst: { path: ../.claude/skills/epidemiologist-analyst/SKILL.md }
  ethicist-analyst: { path: ../.claude/skills/ethicist-analyst/SKILL.md }
  futurist-analyst: { path: ../.claude/skills/futurist-analyst/SKILL.md }
  historian-analyst: { path: ../.claude/skills/historian-analyst/SKILL.md }
  indigenous-leader-analyst: { path: ../.claude/skills/indigenous-leader-analyst/SKILL.md }
  journalist-analyst: { path: ../.claude/skills/journalist-analyst/SKILL.md }
  lawyer-analyst: { path: ../.claude/skills/lawyer-analyst/SKILL.md }
  novelist-analyst: { path: ../.claude/skills/novelist-analyst/SKILL.md }
  philosopher-analyst: { path: ../.claude/skills/philosopher-analyst/SKILL.md }
  physicist-analyst: { path: ../.claude/skills/physicist-analyst/SKILL.md }
  poet-analyst: { path: ../.claude/skills/poet-analyst/SKILL.md }
  political-scientist-analyst: { path: ../.claude/skills/political-scientist-analyst/SKILL.md }
  psychologist-analyst: { path: ../.claude/skills/psychologist-analyst/SKILL.md }
  sociologist-analyst: { path: ../.claude/skills/sociologist-analyst/SKILL.md }
  urban-planner-analyst: { path: ../.claude/skills/urban-planner-analyst/SKILL.md }

  # Workflow skills (11)
  cascade-workflow: { path: ../.claude/skills/cascade-workflow/SKILL.md }
  consensus-voting: { path: ../.claude/skills/consensus-voting/SKILL.md }
  debate-workflow: { path: ../.claude/skills/debate-workflow/SKILL.md }
  default-workflow: { path: ../.claude/skills/default-workflow/SKILL.md }
  eval-recipes-runner: { path: ../.claude/skills/eval-recipes-runner/SKILL.md }
  investigation-workflow: { path: ../.claude/skills/investigation-workflow/SKILL.md }
  n-version-workflow: { path: ../.claude/skills/n-version-workflow/SKILL.md }
  philosophy-compliance-workflow:
    { path: ../.claude/skills/philosophy-compliance-workflow/SKILL.md }
  quality-audit-workflow: { path: ../.claude/skills/quality-audit-workflow/SKILL.md }
  ultrathink-orchestrator: { path: ../.claude/skills/ultrathink-orchestrator/SKILL.md }

  # Technical skills (19)
  agent-sdk: { path: ../.claude/skills/agent-sdk/SKILL.md }
  azure-admin: { path: ../.claude/skills/azure-admin/SKILL.md }
  azure-devops: { path: ../.claude/skills/azure-devops/SKILL.md }
  azure-devops-cli: { path: ../.claude/skills/azure-devops-cli/skill.md }
  code-smell-detector: { path: ../.claude/skills/code-smell-detector/SKILL.md }
  context-management: { path: ../.claude/skills/context-management/SKILL.md }
  design-patterns-expert: { path: ../.claude/skills/design-patterns-expert/SKILL.md }
  documentation-writing: { path: ../.claude/skills/documentation-writing/SKILL.md }
  dynamic-debugger: { path: ../.claude/skills/dynamic-debugger/SKILL.md }
  email-drafter: { path: ../.claude/skills/email-drafter/SKILL.md }
  goal-seeking-agent-pattern: { path: ../.claude/skills/goal-seeking-agent-pattern/SKILL.md }
  mcp-manager: { path: ../.claude/skills/mcp-manager/SKILL.md }
  mermaid-diagram-generator: { path: ../.claude/skills/mermaid-diagram-generator/SKILL.md }
  microsoft-agent-framework: { path: ../.claude/skills/microsoft-agent-framework/skill.md }
  module-spec-generator: { path: ../.claude/skills/module-spec-generator/SKILL.md }
  outside-in-testing: { path: ../.claude/skills/outside-in-testing/SKILL.md }
  remote-work: { path: ../.claude/skills/remote-work/SKILL.md }
  skill-builder: { path: ../.claude/skills/skill-builder/SKILL.md }
  test-gap-analyzer: { path: ../.claude/skills/test-gap-analyzer/SKILL.md }

  # Document processing (4)
  docx: { path: ../.claude/skills/docx/SKILL.md }
  pdf: { path: ../.claude/skills/pdf/SKILL.md }
  pptx: { path: ../.claude/skills/pptx/SKILL.md }
  xlsx: { path: ../.claude/skills/xlsx/SKILL.md }

  # Meta skills (11)
  backlog-curator: { path: ../.claude/skills/backlog-curator/skill.md }
  knowledge-extractor: { path: ../.claude/skills/knowledge-extractor/SKILL.md }
  learning-path-builder: { path: ../.claude/skills/learning-path-builder/SKILL.md }
  meeting-synthesizer: { path: ../.claude/skills/meeting-synthesizer/SKILL.md }
  model-evaluation-benchmark: { path: ../.claude/skills/model-evaluation-benchmark/SKILL.md }
  pm-architect: { path: ../.claude/skills/pm-architect/skill.md }
  pr-review-assistant: { path: ../.claude/skills/pr-review-assistant/SKILL.md }
  roadmap-strategist: { path: ../.claude/skills/roadmap-strategist/skill.md }
  storytelling-synthesizer: { path: ../.claude/skills/storytelling-synthesizer/SKILL.md }
  work-delegator: { path: ../.claude/skills/work-delegator/skill.md }
  workstream-coordinator: { path: ../.claude/skills/workstream-coordinator/skill.md }

  # Nested skills - collaboration (1)
  creating-pull-requests: { path: ../.claude/skills/collaboration/creating-pull-requests/SKILL.md }

  # Nested skills - development (2)
  architecting-solutions: { path: ../.claude/skills/development/architecting-solutions/SKILL.md }
  setting-up-projects: { path: ../.claude/skills/development/setting-up-projects/SKILL.md }

  # Nested skills - meta-cognitive (1)
  analyzing-deeply: { path: ../.claude/skills/meta-cognitive/analyzing-deeply/SKILL.md }

  # Nested skills - quality (2)
  reviewing-code: { path: ../.claude/skills/quality/reviewing-code/SKILL.md }
  testing-code: { path: ../.claude/skills/quality/testing-code/SKILL.md }

  # Nested skills - research (1)
  researching-topics: { path: ../.claude/skills/research/researching-topics/SKILL.md }

agents:
  # Core agents (6)
  api-designer: { path: ../.claude/agents/amplihack/core/api-designer.md }
  architect: { path: ../.claude/agents/amplihack/core/architect.md }
  builder: { path: ../.claude/agents/amplihack/core/builder.md }
  optimizer: { path: ../.claude/agents/amplihack/core/optimizer.md }
  reviewer: { path: ../.claude/agents/amplihack/core/reviewer.md }
  tester: { path: ../.claude/agents/amplihack/core/tester.md }

  # Specialized agents (27)
  ambiguity: { path: ../.claude/agents/amplihack/specialized/ambiguity.md }
  amplifier-cli-architect:
    { path: ../.claude/agents/amplihack/specialized/amplifier-cli-architect.md }
  analyzer: { path: ../.claude/agents/amplihack/specialized/analyzer.md }
  concept-extractor:
    { path: ../.claude/agents/amplihack/specialized/concept-extractor.md }
  azure-kubernetes-expert:
    { path: ../.claude/agents/amplihack/specialized/azure-kubernetes-expert.md }
  ci-diagnostic-workflow:
    { path: ../.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md }
  cleanup: { path: ../.claude/agents/amplihack/specialized/cleanup.md }
  database: { path: ../.claude/agents/amplihack/specialized/database.md }
  documentation-writer: { path: ../.claude/agents/amplihack/specialized/documentation-writer.md }
  fallback-cascade: { path: ../.claude/agents/amplihack/specialized/fallback-cascade.md }
  fix-agent: { path: ../.claude/agents/amplihack/specialized/fix-agent.md }
  insight-synthesizer:
    { path: ../.claude/agents/amplihack/specialized/insight-synthesizer.md }
  integration: { path: ../.claude/agents/amplihack/specialized/integration.md }
  knowledge-archaeologist:
    { path: ../.claude/agents/amplihack/specialized/knowledge-archaeologist.md }
  memory-manager: { path: ../.claude/agents/amplihack/specialized/memory-manager.md }
  multi-agent-debate: { path: ../.claude/agents/amplihack/specialized/multi-agent-debate.md }
  n-version-validator: { path: ../.claude/agents/amplihack/specialized/n-version-validator.md }
  patterns: { path: ../.claude/agents/amplihack/specialized/patterns.md }
  philosophy-guardian: { path: ../.claude/agents/amplihack/specialized/philosophy-guardian.md }
  pre-commit-diagnostic: { path: ../.claude/agents/amplihack/specialized/pre-commit-diagnostic.md }
  preference-reviewer: { path: ../.claude/agents/amplihack/specialized/preference-reviewer.md }
  prompt-writer: { path: ../.claude/agents/amplihack/specialized/prompt-writer.md }
  rust-programming-expert:
    { path: ../.claude/agents/amplihack/specialized/rust-programming-expert.md }
  security: { path: ../.claude/agents/amplihack/specialized/security.md }
  visualization-architect:
    { path: ../.claude/agents/amplihack/specialized/visualization-architect.md }
  worktree-manager: { path: ../.claude/agents/amplihack/specialized/worktree-manager.md }
  xpia-defense: { path: ../.claude/agents/amplihack/specialized/xpia-defense.md }

  # Workflow agents (2)
  amplihack-improvement-workflow:
    { path: ../.claude/agents/amplihack/workflows/amplihack-improvement-workflow.md }
  prompt-review-workflow: { path: ../.claude/agents/amplihack/workflows/prompt-review-workflow.md }

# Amplifier recipes (converted from Claude Code workflows)
recipes:
  qa-workflow: { path: recipes/qa-workflow.yaml }
  cascade-workflow: { path: recipes/cascade-workflow.yaml }
  consensus-workflow: { path: recipes/consensus-workflow.yaml }
  debate-workflow: { path: recipes/debate-workflow.yaml }
  default-workflow: { path: recipes/default-workflow.yaml }
  investigation-workflow: { path: recipes/investigation-workflow.yaml }
  n-version-workflow: { path: recipes/n-version-workflow.yaml }
  verification-workflow: { path: recipes/verification-workflow.yaml }

context:
  include:
    # Reference existing Claude Code context
    - ../.claude/context/PHILOSOPHY.md
    - ../.claude/context/PATTERNS.md
    - ../.claude/context/TRUST.md
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

## MANDATORY: Workflow Classification (ALWAYS FIRST)

**CRITICAL**: You MUST classify every user request into a workflow and execute the corresponding recipe BEFORE taking any other action. No exceptions.

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
