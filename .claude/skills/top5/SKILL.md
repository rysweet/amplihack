---
name: top5
description: "Aggregates priorities from backlog-curator, workstream-coordinator, roadmap-strategist, and work-delegator into a strict Top 5 ranked list. Quick executive summary of what matters most right now."
explicit_triggers:
  - /top5
---

# Top 5 Priorities

## Role

You aggregate priorities across the four PM sub-skills (backlog-curator, workstream-coordinator, roadmap-strategist, work-delegator) and produce a strict Top 5 ranked list of what to focus on right now. This is the executive summary view of project state.

## When to Activate

- User invokes `/top5`
- User asks "What are the top priorities?"
- User asks "What should I focus on?"
- User asks "Give me the highlights" or "What matters most?"

## How It Works

Run the aggregation script:

```bash
python .claude/skills/top5/scripts/generate_top5.py --project-root .
```

The script:

1. **Reads backlog** (`.pm/backlog/items.yaml`) - extracts READY items with priority scores
2. **Reads workstreams** (`.pm/workstreams/ws-*.yaml`) - identifies stalled/blocked work needing attention
3. **Reads roadmap** (`.pm/roadmap.md`) - extracts strategic goals for alignment scoring
4. **Reads delegation state** (`.pm/delegations/`) - identifies pending delegations needing action

Each source contributes scored candidates. The script applies weighted aggregation:

- **Backlog priority** (35%): Multi-criteria score from backlog-curator
- **Workstream urgency** (25%): Stalled/blocked workstreams get high urgency
- **Strategic alignment** (25%): How well items align with roadmap goals
- **Delegation readiness** (15%): Items ready for delegation get a boost

Output is a strict Top 5 ranked JSON list.

## Presenting Results

Present the Top 5 as a numbered list with:

1. **Rank and title** (bold)
2. **Source** (which sub-skill surfaced it)
3. **Score** (aggregated priority score)
4. **Why** (one-line rationale)

Example output format:

```
## Top 5 Priorities

1. **Fix authentication bug** (backlog, score: 92.3)
   Bug fix blocking 3 other items, HIGH priority

2. **Investigate stalled API workstream** (workstream, score: 87.1)
   No activity for 4.2 hours, may need intervention

3. **Implement config parser** (backlog, score: 78.5)
   Aligned with Q1 goal "Core Infrastructure", quick win

4. **Delegate test suite to agent** (delegation, score: 71.2)
   Ready for delegation, estimated 2 hours

5. **Update roadmap milestone** (roadmap, score: 65.0)
   Q1 milestone approaching, needs status update
```

## Integration with PM Architect

This skill is invoked by pm-architect as an additional orchestration pattern:

### Pattern 5: Quick Priority View

User asks for priorities → invoke `/top5` → present ranked list.

## Philosophy Alignment

- **Ruthless Simplicity**: One script, one output, five items
- **Single Responsibility**: Aggregate and rank, nothing else
- **Zero-BS**: Real scores from real data, no placeholders

## Remember

You are the executive summary. Cut through noise. Five items, ranked, with reasons. Nothing more.
