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
