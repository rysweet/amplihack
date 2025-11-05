# Investigation Message Budget Guidelines

This document defines expected message ranges for investigation tasks to prevent runaway sessions and ensure efficient use of resources. Budgets are based on task complexity, scope, and depth, with checkpoint intervals for reassessment.

## Budget Matrix

| Complexity              | Scope         | Depth         | Expected Messages | Checkpoint Interval |
| ----------------------- | ------------- | ------------- | ----------------- | ------------------- |
| Simple (1-3/13)         | 1 system      | Overview only | 20-40             | 50                  |
| Simple (1-3/13)         | 1 system      | Detailed      | 30-60             | 75                  |
| Medium (4-7/13)         | 2-3 systems   | Overview      | 40-80             | 100                 |
| Medium (4-7/13)         | 2-3 systems   | Detailed      | 60-120            | 125                 |
| Complex (8-10/13)       | 4+ systems    | Overview      | 80-150            | 150                 |
| Complex (8-10/13)       | 4+ systems    | Detailed      | 100-200           | 200                 |
| Very Complex (11-13/13) | Cross-cutting | Comprehensive | 150-300           | 250                 |

## Complexity Scale Reference

**Simple (1-3/13)**: Single system or module investigation with clear boundaries

- Example: "Explain how user authentication works in this app"
- Characteristics: Well-defined scope, single responsibility, clear documentation

**Medium (4-7/13)**: Multi-system investigation requiring coordination analysis

- Example: "How does data flow from API to database to UI?"
- Characteristics: 2-3 interconnected systems, some ambiguity, moderate documentation

**Complex (8-10/13)**: Cross-cutting concerns or deep architectural analysis

- Example: "Analyze performance bottlenecks across the entire request lifecycle"
- Characteristics: 4+ systems, significant ambiguity, sparse documentation

**Very Complex (11-13/13)**: Comprehensive system understanding or major redesign planning

- Example: "Design migration strategy from monolith to microservices"
- Characteristics: Entire system scope, high ambiguity, architectural decisions required

## Scope Dimensions

**1 system**: Single module, service, or component
**2-3 systems**: Multiple coordinating components with defined interfaces
**4+ systems**: Broad cross-cutting analysis involving many moving parts
**Cross-cutting**: System-wide concerns affecting all components (security, performance, architecture)

## Depth Levels

**Overview**: High-level understanding, key concepts, main flows
**Detailed**: In-depth analysis, edge cases, implementation details
**Comprehensive**: Exhaustive examination, all variations, complete understanding

## Checkpoint Actions

At each checkpoint interval (50, 100, 150, 200, 250, 300 messages):

### 1. Count Current Messages

- Track message count throughout session
- Compare to budget matrix for task complexity
- Calculate percentage of budget used

### 2. Assess Progress Status

- **Core questions answered?** → Consider synthesis and wrap-up
- **Still exploring fundamentals?** → Justified to continue investigation
- **Over-investigating edge cases?** → Time to synthesize findings
- **Hitting diminishing returns?** → Prioritize synthesis over completeness

### 3. Decision Tree

```
IF message_count > expected_upper_bound:
    THEN prompt user:
        "We're at [N] messages for a [complexity] investigation.
         Expected range is [lower]-[upper] messages.

         Current status: [brief progress summary]

         Shall I:
         A) Continue investigation (please specify what areas need deeper analysis)
         B) Synthesize findings now with current information
         C) Switch to narrower focus (specify which aspects to prioritize)"

    WAIT for user decision
    LOG budget extension decision and justification

ELIF message_count >= checkpoint_interval:
    THEN log milestone:
        "Checkpoint: [N] messages, [progress_status], on track for [complexity] ([X]% of budget used)"

    CONTINUE investigation

ELSE:
    CONTINUE investigation silently
```

### 4. Budget Extension Protocol

When user chooses to continue beyond budget:

- **Document justification**: Why additional depth is valuable
- **Set new target**: "Extending to approximately [N] messages to cover [specific areas]"
- **User explicitly approved**: Record in session metadata
- **Add to session log**: `budget_extended: true, reason: [user request], new_target: [N]`

## Over-Budget Threshold

### When to Prompt User

**Immediate prompt** when investigation exceeds upper bound of expected range:

- Simple (1-3/13) Detailed: > 60 messages
- Medium (4-7/13) Detailed: > 120 messages
- Complex (8-10/13) Detailed: > 200 messages
- Very Complex (11-13/13) Comprehensive: > 300 messages

### User Prompt Template

```markdown
## Budget Checkpoint 🎯

**Current Status**: [N] messages ([X]% over expected budget)
**Task Complexity**: [Simple/Medium/Complex/Very Complex]
**Expected Range**: [lower]-[upper] messages

**Progress Summary**:
[2-3 sentences on what's been discovered and what remains]

**Your Options**:

**A) Continue Investigation**

- Specify areas needing deeper analysis
- Estimated additional messages: [N]

**B) Synthesize Now**

- Summarize findings with current information
- Estimated completion: [N] messages

**C) Adjust Focus**

- Narrow scope to specific aspects
- Specify priority areas

**Recommendation**: [Agent's suggestion based on progress and value]

What would you like me to do?
```

## Verbosity-Adjusted Budgets

User verbosity preference modifies budget ranges:

### Concise Preference

- **Adjustment**: -40% to all budget ranges
- **Example**: Medium/Detailed 60-120 → 36-72 messages
- **Philosophy**: User wants succinct explanations, fewer examples, faster results

### Balanced Preference (Default)

- **Adjustment**: 0% (use standard budgets from matrix)
- **Example**: Medium/Detailed remains 60-120 messages
- **Philosophy**: User wants appropriate detail without excess

### Detailed Preference

- **Adjustment**: +40% to all budget ranges
- **Example**: Medium/Detailed 60-120 → 84-168 messages
- **Philosophy**: User values comprehensive explanations, examples, thorough coverage

### Applying Adjustments

```python
def adjust_budget_for_verbosity(lower: int, upper: int, verbosity: str) -> tuple[int, int]:
    """Apply verbosity multiplier to budget range."""
    multipliers = {
        "concise": 0.6,   # -40%
        "balanced": 1.0,  # no change
        "detailed": 1.4   # +40%
    }
    multiplier = multipliers.get(verbosity, 1.0)
    return (int(lower * multiplier), int(upper * multiplier))
```

## Historical Data and Tuning

### Baseline Data (Issue #1106 Analysis)

From reflection-session-20251104_210400:

- Investigation task: 358 messages
- User preference: "balanced" verbosity
- Task complexity: ~6/13 (Medium)
- Expected range: 60-120 messages
- Actual overrun: 3x upper bound

### Session Progression Pattern

| Session        | Messages | Expected | Ratio          |
| -------------- | -------- | -------- | -------------- |
| 1st reflection | 51       | 60-120   | 0.43x (under)  |
| 2nd reflection | 72       | 60-120   | 0.60x (within) |
| 3rd reflection | 165      | 60-120   | 1.38x (over)   |
| 4th reflection | 210      | 60-120   | 1.75x (over)   |
| 5th reflection | 244      | 60-120   | 2.03x (over)   |
| 6th reflection | 358      | 60-120   | 2.98x (over)   |

**Observation**: Message counts increasing over time without budget awareness. This system addresses exactly this pattern.

### Quarterly Tuning Process

1. **Collect Usage Data**: Log actual message counts vs. budgets for all investigations
2. **Analyze Variance**: Identify patterns in over/under budget scenarios
3. **Adjust Ranges**: Modify budget matrix based on 80th percentile of actual usage
4. **Update Checkpoints**: Tune checkpoint intervals if too frequent/infrequent
5. **Refine Complexity**: Improve complexity estimation based on variance analysis

## Success Metrics

### Immediate (First Month)

- **Adoption**: Checkpoints fire in 100% of investigations exceeding thresholds
- **User Engagement**: User responds to checkpoint prompts > 80% of time
- **Message Reduction**: Average investigation length -40% overall
- **Budget Adherence**: > 70% of investigations stay within expected range

### Long-term (3 Months)

- **Budget Accuracy**: < 20% variance from actual needs
- **User Satisfaction**: "Investigation was appropriate length" > 85% (survey)
- **Efficiency Gains**: Time-to-insight improves by 30%
- **Complaint Reduction**: Issues about long investigations -80%

## Example Scenarios

### Scenario 1: Simple Investigation Stays Within Budget

**Task**: "Explain how the authentication module handles password reset"
**Complexity**: Simple (2/13), 1 system, detailed depth
**Expected Budget**: 30-60 messages (balanced verbosity)

**Timeline**:

- Message 25: Investigation proceeding normally
- Message 50: Checkpoint - "50 messages, 83% of budget used, investigation nearly complete"
- Message 55: Synthesis complete, findings delivered
- **Result**: Within budget ✅

### Scenario 2: Medium Investigation Triggers Checkpoint

**Task**: "Analyze data flow from API endpoint to database and back to UI"
**Complexity**: Medium (6/13), 2-3 systems, detailed depth
**Expected Budget**: 60-120 messages (balanced verbosity)

**Timeline**:

- Message 75: Checkpoint - "75 messages, 63% of budget used, API→DB flow complete, analyzing DB→UI"
- Message 100: Checkpoint - "100 messages, 83% of budget used, nearly complete"
- Message 115: Synthesis complete
- **Result**: Within budget ✅

### Scenario 3: Complex Investigation Requests Extension

**Task**: "Identify all performance bottlenecks in request lifecycle"
**Complexity**: Complex (9/13), 4+ systems, detailed depth
**Expected Budget**: 100-200 messages (balanced verbosity)

**Timeline**:

- Message 150: Checkpoint - "150 messages, 75% of budget used, frontend and API analyzed, database pending"
- Message 200: Checkpoint - "200 messages, at upper bound, database bottlenecks identified"
- Message 210: **OVER BUDGET** - Prompt user
  - User response: "Continue - also analyze caching layer"
  - Extension approved: target 250 messages
- Message 245: Synthesis with comprehensive findings
- **Result**: Budget extended with user approval ✅

### Scenario 4: Very Complex Investigation Stays on Track

**Task**: "Design migration strategy from monolith to microservices"
**Complexity**: Very Complex (12/13), cross-cutting, comprehensive
**Expected Budget**: 150-300 messages (balanced verbosity)

**Timeline**:

- Message 150: Checkpoint - "150 messages, 50% of budget used, current architecture analyzed"
- Message 200: Checkpoint - "200 messages, 67% of budget used, microservice boundaries identified"
- Message 250: Checkpoint - "250 messages, 83% of budget used, migration strategy drafted"
- Message 285: Synthesis complete with comprehensive migration plan
- **Result**: Within budget for very complex task ✅

## Integration with Existing Systems

### USER_PREFERENCES.md Integration

Read user verbosity preference:

```python
def get_user_verbosity() -> str:
    """Read verbosity preference from USER_PREFERENCES.md."""
    prefs_path = ".claude/context/USER_PREFERENCES.md"
    # Parse YAML frontmatter or structured content
    # Return: "concise" | "balanced" | "detailed"
    return "balanced"  # default
```

### INVESTIGATION_WORKFLOW.md Integration

This budget system is referenced in INVESTIGATION_WORKFLOW.md as an ongoing checkpoint step that runs throughout the investigation process.

### Session Logging

Log checkpoint events to `.claude/runtime/logs/{session_id}/budget_checkpoints.jsonl`:

```jsonl
{"timestamp": "2025-11-05T10:30:00Z", "message_count": 50, "complexity": 6, "budget_range": [60, 120], "status": "on_track", "percentage_used": 42}
{"timestamp": "2025-11-05T10:45:00Z", "message_count": 100, "complexity": 6, "budget_range": [60, 120], "status": "on_track", "percentage_used": 83}
{"timestamp": "2025-11-05T11:00:00Z", "message_count": 150, "complexity": 6, "budget_range": [60, 120], "status": "over_budget", "action": "prompted_user"}
```

## Related Issues and Documents

- **Issue #1106**: This issue (implementing message budget awareness)
- **Issue #1095**: INVESTIGATION_WORKFLOW.md creation (dependency)
- **Issue #1100**: Verbosity auto-adjustment (related)
- **Issue #1103**: Phase progress indicators (complementary)
- **USER_PREFERENCES.md**: Verbosity preference source
- **DEFAULT_WORKFLOW.md**: Standard workflow reference

## Philosophy Alignment

This budget system embodies core project principles:

- **Ruthless Simplicity**: Clear budgets, simple decision tree, no complex abstractions
- **User Trust**: User always has final decision on continuation
- **Transparency**: Budget status visible at checkpoints
- **Data-Driven**: Historical data informs budget ranges
- **Respect for User Time**: Prevents unnecessary overruns
- **Continuous Improvement**: Quarterly tuning based on actual usage

---

**Last Updated**: 2025-11-05
**Version**: 1.0
**Status**: Initial implementation
