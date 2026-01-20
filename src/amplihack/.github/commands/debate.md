# GitHub Copilot Command Reference: debate

**Source**: `.claude/commands/amplihack/debate.md`

---

## Command Metadata

- **name**: /fix
- **version**: 1.0.0
- **description**: Multi-agent debate for complex decisions and trade-offs
- **triggers**: 
- **invokes**: 
- **- type**: command
- **path**: .claude/workflow/DEBATE_WORKFLOW.md
- **philosophy**: 
- **- principle**: Analysis First
- **application**: Explores all perspectives before deciding
- **dependencies**: 
- **required**: 
- **optional**: 
- **examples**: 
- **- "/amplihack**: debate Microservices vs monolith for this service"

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/debate.md

# Use patterns from this command
gh copilot suggest --context .github/commands/debate.md "your task"
```

---

## Original Command Documentation


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
