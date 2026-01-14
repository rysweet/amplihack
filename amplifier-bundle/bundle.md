---
bundle:
  name: amplihack
  version: 1.0.0
  description: "Amplihack development framework - Amplifier bundle packaging"

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-recipes@main

behaviors:
  amplihack:
    path: behaviors/amplihack.yaml

# Reference existing Claude Code components via relative paths - NO DUPLICATION
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
  
  # Workflow skills (6)
  cascade-workflow: { path: ../.claude/skills/cascade-workflow/SKILL.md }
  consensus-voting: { path: ../.claude/skills/consensus-voting/SKILL.md }
  debate-workflow: { path: ../.claude/skills/debate-workflow/SKILL.md }
  default-workflow: { path: ../.claude/skills/default-workflow/SKILL.md }
  investigation-workflow: { path: ../.claude/skills/investigation-workflow/SKILL.md }
  n-version-workflow: { path: ../.claude/skills/n-version-workflow/SKILL.md }
  
  # Technical skills (18)
  agent-sdk: { path: ../.claude/skills/agent-sdk/SKILL.md }
  azure-admin: { path: ../.claude/skills/azure-admin/SKILL.md }
  azure-devops: { path: ../.claude/skills/azure-devops/SKILL.md }
  azure-devops-cli: { path: ../.claude/skills/azure-devops-cli/skill.md }
  code-smell-detector: { path: ../.claude/skills/code-smell-detector/SKILL.md }
  context_management: { path: ../.claude/skills/context_management/SKILL.md }
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

agents:
  # Top-level agents (3)
  concept-extractor: { path: ../.claude/agents/concept-extractor.md }
  insight-synthesizer: { path: ../.claude/agents/insight-synthesizer.md }
  knowledge-archaeologist: { path: ../.claude/agents/knowledge-archaeologist.md }
  
  # Core agents (6)
  api-designer: { path: ../.claude/agents/amplihack/core/api-designer.md }
  architect: { path: ../.claude/agents/amplihack/core/architect.md }
  builder: { path: ../.claude/agents/amplihack/core/builder.md }
  optimizer: { path: ../.claude/agents/amplihack/core/optimizer.md }
  reviewer: { path: ../.claude/agents/amplihack/core/reviewer.md }
  tester: { path: ../.claude/agents/amplihack/core/tester.md }
  
  # Specialized agents (25)
  ambiguity: { path: ../.claude/agents/amplihack/specialized/ambiguity.md }
  amplifier-cli-architect: { path: ../.claude/agents/amplihack/specialized/amplifier-cli-architect.md }
  analyzer: { path: ../.claude/agents/amplihack/specialized/analyzer.md }
  azure-kubernetes-expert: { path: ../.claude/agents/amplihack/specialized/azure-kubernetes-expert.md }
  ci-diagnostic-workflow: { path: ../.claude/agents/amplihack/specialized/ci-diagnostic-workflow.md }
  cleanup: { path: ../.claude/agents/amplihack/specialized/cleanup.md }
  database: { path: ../.claude/agents/amplihack/specialized/database.md }
  documentation-writer: { path: ../.claude/agents/amplihack/specialized/documentation-writer.md }
  fallback-cascade: { path: ../.claude/agents/amplihack/specialized/fallback-cascade.md }
  fix-agent: { path: ../.claude/agents/amplihack/specialized/fix-agent.md }
  integration: { path: ../.claude/agents/amplihack/specialized/integration.md }
  knowledge-archaeologist-specialized: { path: ../.claude/agents/amplihack/specialized/knowledge-archaeologist.md }
  memory-manager: { path: ../.claude/agents/amplihack/specialized/memory-manager.md }
  multi-agent-debate: { path: ../.claude/agents/amplihack/specialized/multi-agent-debate.md }
  n-version-validator: { path: ../.claude/agents/amplihack/specialized/n-version-validator.md }
  patterns: { path: ../.claude/agents/amplihack/specialized/patterns.md }
  philosophy-guardian: { path: ../.claude/agents/amplihack/specialized/philosophy-guardian.md }
  pre-commit-diagnostic: { path: ../.claude/agents/amplihack/specialized/pre-commit-diagnostic.md }
  preference-reviewer: { path: ../.claude/agents/amplihack/specialized/preference-reviewer.md }
  prompt-writer: { path: ../.claude/agents/amplihack/specialized/prompt-writer.md }
  rust-programming-expert: { path: ../.claude/agents/amplihack/specialized/rust-programming-expert.md }
  security: { path: ../.claude/agents/amplihack/specialized/security.md }
  visualization-architect: { path: ../.claude/agents/amplihack/specialized/visualization-architect.md }
  worktree-manager: { path: ../.claude/agents/amplihack/specialized/worktree-manager.md }
  xpia-defense: { path: ../.claude/agents/amplihack/specialized/xpia-defense.md }
  
  # Workflow agents (2)
  amplihack-improvement-workflow: { path: ../.claude/agents/amplihack/workflows/amplihack-improvement-workflow.md }
  prompt-review-workflow: { path: ../.claude/agents/amplihack/workflows/prompt-review-workflow.md }

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
    - modules/hook-session-start     # Version check, preferences, context injection
    - modules/hook-session-stop      # Learning capture, memory storage
    - modules/hook-post-tool-use     # Tool registry, metrics, error detection
    
    # Feature hooks
    - modules/hook-power-steering    # Session completion verification
    - modules/hook-memory            # Agent memory injection/extraction
    - modules/hook-pre-tool-use      # Dangerous operation blocking
    - modules/hook-pre-compact       # Transcript export before compaction
    - modules/hook-user-prompt       # User preferences injection

# Note: workflow_tracker functionality is covered by hooks-todo-reminder from foundation
---

# Amplihack - Amplifier Bundle

This is the Amplifier bundle packaging of amplihack, a development framework that uses specialized AI agents to accelerate software development.

## Overview

This bundle provides a thin Amplifier packaging layer that references the existing Claude Code components in `.claude/` without duplication.

## What's Included

### From Claude Code (referenced, not duplicated)
- **62 Skills** - Domain expertise, workflow patterns, technical capabilities
- **36 Agents** - Core, specialized, and workflow agents
- **Context** - Philosophy, patterns, trust guidelines
- **Workflows** - Q&A, Investigation, Default development workflows

### Amplifier-Specific (in this bundle)
- **8 Hook Modules** - Wrappers around Claude Code hooks for Amplifier compatibility
- **Behaviors** - Amplihack behavior configuration with workflow selection
- **Context** - Amplifier-specific instructions

## Hook Mapping

| Amplifier Module | Wraps Claude Code Hook | Purpose |
|------------------|----------------------|---------|
| `hook-session-start` | `session_start.py` | Version check, preferences, context injection, Neo4j startup |
| `hook-session-stop` | `session_stop.py` | Learning capture, memory storage via MemoryCoordinator |
| `hook-post-tool-use` | `post_tool_use.py` | Tool registry, metrics tracking, error detection |
| `hook-power-steering` | `power_steering_*.py` | Session completion verification (21 considerations) |
| `hook-memory` | `agent_memory_hook.py` | Persistent memory injection/extraction across sessions |
| `hook-pre-tool-use` | `pre_tool_use.py` | Block dangerous operations (--no-verify, rm -rf) |
| `hook-pre-compact` | `pre_compact.py` | Export transcript before context compaction |
| `hook-user-prompt` | `user_prompt_submit.py` | Inject user preferences on every prompt |

**Note:** `workflow_tracker` functionality is covered by `hooks-todo-reminder` from foundation.

## Usage

```bash
# Use with Amplifier
amplifier run --bundle amplihack

# Or include in another bundle
includes:
  - bundle: git+https://github.com/rysweet/amplihack@main#amplifier-bundle
```

## Philosophy

This bundle follows the "thin bundle" pattern:
- Lightweight overlay enabling Amplifier compatibility
- References existing Claude Code components (no duplication)
- Wrapper modules delegate to existing Claude Code implementations
- Same components work in both Claude Code and Amplifier
