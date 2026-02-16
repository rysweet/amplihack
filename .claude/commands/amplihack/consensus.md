---
name: amplihack:consensus
version: 1.0.0
description: Run the consensus workflow with multi-agent validation gates
triggers:
  - "critical implementation"
  - "need consensus"
  - "high-stakes code"
  - "multi-agent validation"
invokes:
  - type: recipe
    name: consensus-workflow
dependencies:
  required:
    - amplifier-bundle/recipes/consensus-workflow.yaml
examples:
  - "/amplihack:consensus Implement JWT token validation for public API"
  - "/amplihack:consensus Design database migration strategy"
---

# Consensus Workflow Command

## Usage

`/amplihack:consensus <TASK_DESCRIPTION>`

## Purpose

Directly invoke the consensus workflow recipe with multi-agent validation at 7 critical gates. Use for complex features with architectural implications, mission-critical code, security-sensitive implementations, or public APIs.

This is slower but produces significantly higher quality output than the default workflow.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Attempt Recipe Runner execution** (preferred):

   ```python
   from amplihack.recipes import run_recipe_by_name
   result = run_recipe_by_name(
       "consensus-workflow",
       adapter=sdk_adapter,
       user_context={
           "task_description": "{TASK_DESCRIPTION}",
           "repo_path": ".",
           "consensus_depth": "balanced"
       }
   )
   ```

2. **Fallback to Skill** (if Recipe Runner unavailable):
   - Read workflow directly and execute with multi-agent debate at each gate

3. **Create TodoWrite entries** for all 15 steps including 7 consensus gates.

## Consensus Gates

1. Requirements: Multi-Agent Debate (if ambiguous)
2. Design: Architecture debate (5 agents, 3 rounds)
3. Implementation: N-Version programming (2-3 builders)
4. Refactoring: Expert Panel (4 agents)
5. PR Review: Expert Panel (5 agents)
6. Philosophy: Compliance Panel (3 agents)
7. Final: Quality Panel (3 agents)

## When to Use

- Complex features with architectural implications
- Mission-critical code requiring high reliability
- Security-sensitive implementations
- Public APIs with long-term commitments

## Cost-Benefit

- **Cost:** 3-5x execution time vs default-workflow
- **Benefit:** Significantly higher quality through consensus validation

## Task Description

```
{TASK_DESCRIPTION}
```
