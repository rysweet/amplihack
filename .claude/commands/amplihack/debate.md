# Multi-Agent Debate Command

## Usage

`/debate <QUESTION_OR_DECISION>`

## Purpose

Execute multi-agent debate pattern for complex decisions. Structured debate with multiple perspectives converges on best decision through argument and synthesis.

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked, you MUST:

1. **Read the workflow file**: `.claude/workflow/DEBATE_WORKFLOW.md`
2. **Create a comprehensive todo list** using TodoWrite with all workflow steps
3. **Execute each step systematically**, marking todos as in_progress and completed
4. **Follow the debate pattern**:
   - Initialize perspectives (security, performance, simplicity, etc.)
   - Conduct debate rounds (challenge, respond, synthesize)
   - Identify convergence or best argument
   - Make recommendation with confidence level
5. **Document the debate** with all positions and rationale
6. **Track decisions** in `.claude/runtime/logs/<session_timestamp>/DECISIONS.md`

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
