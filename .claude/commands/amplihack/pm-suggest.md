# PM:Suggest - Smart Backlog Recommendations

Get AI-powered recommendations for what backlog item to work on next.

## What This Command Does

Phase 2 AI assistance: Analyzes all ready backlog items using multi-criteria scoring to recommend the best work to tackle next.

**Scoring Formula:**
- Priority (40%): HIGH=1.0, MEDIUM=0.6, LOW=0.3
- Blocking Impact (30%): How many items this unblocks
- Ease (20%): Inverse of complexity (simple=quick win)
- Goal Alignment (10%): Business value from project goals

**Features:**
- Multi-criteria analysis
- Dependency detection (skips items with unmet dependencies)
- Complexity estimation (simple/medium/complex)
- Confidence scores (how certain the AI is)
- Clear rationale (why this item now)

## Usage

```bash
/pm:suggest
```

Shows top 3 recommendations by default.

## Example Output

```
============================================================
🤖 PM ARCHITECT RECOMMENDATIONS
============================================================

#1 | BL-003: Add authentication API
    Priority: HIGH | Score: 87.5/100
    Complexity: medium | Confidence: 80%

    Recommended because: HIGH priority, unblocks 2 other item(s), high business value

#2 | BL-001: Fix login bug
    Priority: HIGH | Score: 82.0/100
    Complexity: simple | Confidence: 75%

    Recommended because: HIGH priority, quick win (simple)

#3 | BL-005: Refactor user service
    Priority: MEDIUM | Score: 65.0/100
    Complexity: medium | Confidence: 70%

    Recommended because: unblocks 1 other item(s), good next step

============================================================
💡 TIP: Use /pm:prepare <id> to create rich delegation package
```

## Next Steps

After seeing recommendations:

1. **Prepare delegation package**: `/pm:prepare BL-003`
   - Creates comprehensive AI-generated context
   - Finds relevant files to examine
   - Identifies similar patterns
   - Generates test requirements

2. **Start workstream**: `/pm:start BL-003`
   - Begins work with chosen item
   - Uses rich delegation package if prepared

## Implementation

Implemented in: `.claude/tools/amplihack/pm/cli.py::cmd_suggest()`

Uses:
- `intelligence.py::RecommendationEngine` - Multi-criteria scoring
- `intelligence.py::BacklogAnalyzer` - Item categorization
- `intelligence.py::DependencyAnalyzer` - Dependency detection
- `intelligence.py::ComplexityEstimator` - Effort estimation

## Philosophy

**Practical AI Assistance:**
- Transparent reasoning (always explain why)
- Honest uncertainty (confidence scores)
- Multi-criteria optimization (not just one factor)
- Skip blocked items (only recommend doable work)

**Ruthless Simplicity:**
- No ML models or complex algorithms
- Rule-based scoring with clear weights
- Simple keyword analysis
- Fast execution (< 1 second)

## Phase 2 Integration

Part of PM Architect Phase 2 (AI Assistance):
- `/pm:suggest` - This command (recommendations)
- `/pm:prepare` - Rich delegation packages
- Enhanced workstream context

See Phase 1 commands: `/pm:init`, `/pm:add`, `/pm:start`, `/pm:status`
