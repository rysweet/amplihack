# Ultrathink Orchestrator

Deep analysis orchestration for complex tasks requiring systematic, multi-step reasoning.

## When to Use

- Complex problems requiring structured analysis
- Tasks with unclear scope or approach
- Multi-faceted investigations
- Keywords: "analyze deeply", "think through", "investigate", "complex problem"

## Task Type Detection

### Type 1: Q&A (Quick Answer)

**Triggers:**
- "What is...", "How do I...", "Why does..."
- Single-concept questions
- Factual lookups
- Syntax questions

**Workflow:** Direct answer with optional brief explanation

### Type 2: Investigation

**Triggers:**
- "Why is this happening...", "Debug...", "Find the cause..."
- "Investigate...", "Analyze...", "What's wrong with..."
- Error messages or unexpected behavior
- Performance issues

**Workflow:** Full investigation protocol

### Type 3: Development

**Triggers:**
- "Build...", "Create...", "Implement..."
- "Add feature...", "Refactor...", "Fix..."
- Code changes requested
- New functionality needed

**Workflow:** Structured development protocol

## Keyword Classification

| Category | High-Confidence Triggers |
|----------|-------------------------|
| **Immediate** | "quick", "just", "simply", "fast" |
| **Investigation** | "why", "debug", "trace", "root cause", "investigate" |
| **Development** | "implement", "build", "create", "add", "refactor" |
| **Deep Analysis** | "analyze", "evaluate", "compare", "assess", "review" |
| **Planning** | "plan", "design", "architect", "strategy" |

## Workflow Routing Logic

```
START
  │
  ├─ Is it a simple factual question?
  │   YES → Q&A Mode (direct answer)
  │   NO ↓
  │
  ├─ Does it involve understanding existing behavior?
  │   YES → Investigation Mode
  │   NO ↓
  │
  ├─ Does it involve creating/changing code?
  │   YES → Development Mode
  │   NO ↓
  │
  └─ Default → Deep Analysis Mode
```

## Mandatory Steps by Mode

### Investigation Mode

1. **Symptom Collection** - Gather all observable behaviors
2. **Hypothesis Formation** - Generate 3+ possible causes
3. **Evidence Gathering** - Collect data for each hypothesis
4. **Root Cause Identification** - Eliminate hypotheses systematically
5. **Solution Proposal** - Address root cause, not symptoms
6. **Verification Plan** - How to confirm fix works

### Development Mode

1. **Requirements Clarification** - What exactly needs to be built
2. **Impact Assessment** - What existing code is affected
3. **Design Decision** - Approach selection with rationale
4. **Implementation Plan** - Ordered steps
5. **Test Strategy** - How to verify correctness
6. **Execution** - Actual implementation
7. **Validation** - Run tests, verify behavior

### Deep Analysis Mode

1. **Problem Framing** - Define scope and constraints
2. **Information Gathering** - Collect relevant data
3. **Multi-Perspective Analysis** - View from different angles
4. **Synthesis** - Combine insights
5. **Conclusions** - Clear findings
6. **Recommendations** - Actionable next steps

## Orchestration Output Format

```markdown
## Task Analysis

**Type Detected:** [Q&A | Investigation | Development | Deep Analysis]
**Confidence:** [High | Medium | Low]
**Reasoning:** [Why this type was selected]

## Workflow Activation

**Mode:** [Selected workflow]
**Mandatory Steps:**
1. [ ] Step 1
2. [ ] Step 2
...

## Execution

### Step 1: [Name]
[Content]

### Step 2: [Name]
[Content]

...

## Summary

**Findings:** [Key discoveries]
**Outcome:** [Result of analysis/work]
**Next Steps:** [If any]
```

## Complexity Escalation

| Complexity | Indicators | Response |
|------------|-----------|----------|
| **Low** | Single file, clear fix, known pattern | Execute directly |
| **Medium** | Multiple files, design choice needed | Plan then execute |
| **High** | Architectural impact, multiple systems | Full analysis first |
| **Critical** | Data integrity, security, production | Pause for confirmation |

## Anti-Patterns

- Jumping to solutions before understanding the problem
- Skipping investigation steps when debugging
- Not documenting reasoning for complex decisions
- Treating all tasks as same complexity
- Ignoring type detection and using one-size-fits-all approach
