---
name: amplihack:debate
version: 1.0.0
description: Multi-agent debate for complex decisions and trade-offs
triggers:
  - "need multiple perspectives"
  - "complex decision needed"
  - "debate trade-offs"
  - "architectural choice"
invokes:
  - type: workflow
    path: .claude/workflow/DEBATE_WORKFLOW.md
  - type: command
    name: /fix
philosophy:
  - principle: Trust in Emergence
    application: Best decisions emerge from structured debate
  - principle: Analysis First
    application: Explores all perspectives before deciding
dependencies:
  required:
    - .claude/workflow/DEBATE_WORKFLOW.md
  optional:
    - .claude/tools/amplihack/orchestration/patterns/debate.py
examples:
  - "/amplihack:debate Should we use PostgreSQL or Redis?"
  - "/amplihack:debate Microservices vs monolith for this service"
---

# Multi-Agent Debate Command

## Usage

`/amplihack:debate <QUESTION_OR_DECISION>`

## Purpose

Execute multi-agent debate pattern for complex decisions. Structured debate with multiple perspectives converges on best decision through argument and synthesis.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Import the orchestrator**:

   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path.cwd() / ".claude/tools/amplihack"))
   from orchestration.patterns.debate import run_debate
   ```

2. **Execute the pattern**:

   ```python
   result = run_debate(
       decision_question="{QUESTION_OR_DECISION}",
       perspectives=["security", "performance", "simplicity"],  # or custom
       rounds=3,
       working_dir=Path.cwd()
   )
   ```

3. **Display results**:
   - Show synthesis and recommendation
   - Explain confidence level (HIGH/MEDIUM/LOW)
   - Summarize key debate points
   - Report session_id for traceability
   - Link to logs: `.claude/runtime/logs/debate_<timestamp>/`

4. **Manual fallback** (if orchestrator unavailable):
   - Read workflow: `.claude/workflow/DEBATE_WORKFLOW.md`
   - Execute steps manually with TodoWrite tracking

## When to Use

Use for **decisions with multiple valid approaches**:

- Architectural trade-offs (microservices vs monolith)
- Algorithm selection (quick vs accurate)
- Security vs usability decisions
- Performance vs maintainability choices

## Cost-Benefit

- **Cost:** 2-3x execution time (debate rounds + synthesis)
- **Benefit:** 40-70% better decision quality
- **ROI Positive when:** Decision impact > 3x implementation cost

## Decision Question

Execute debate for the following decision:

```
{QUESTION_OR_DECISION}
```

## Configuration

The workflow can be customized by editing `.claude/workflow/DEBATE_WORKFLOW.md`:

- Agent perspectives: 3 (default), 5 (extended), custom profiles
- Debate rounds: 2-3 (standard), 4-5 (deep analysis)
- Convergence criteria: 100% (strong), 2/3 (majority), synthesis
- Facilitation rules

## Success Metrics

From research (PR #946):

- Decision Quality: 40-70% improvement vs single perspective
- Blind Spot Detection: 85%+ of overlooked concerns surfaced
- Stakeholder Alignment: 90%+ when diverse perspectives included
