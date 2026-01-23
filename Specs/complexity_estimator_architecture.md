# Investigation Complexity Estimator - Architecture Specification

## Overview

Pre-flight complexity assessment system that analyzes investigation requests and routes them to appropriate execution paths, preventing over-engineering of simple questions while maintaining thoroughness for complex investigations.

## Problem Statement

Ultra-Think command currently deploys full multi-agent orchestration for ALL investigation tasks without assessing if simpler approaches would suffice. This creates:

- Unnecessary overhead for straightforward questions (50+ messages for simple queries)
- Slower response times for users with simple needs
- Resource waste on over-engineered solutions

## Solution Architecture

### Design Principles

1. **Ruthless Simplicity**: Embedded heuristics in command file, no external dependencies
2. **Zero-BS**: Complete working logic, no stubs or placeholders
3. **Backward Compatible**: No breaking changes to existing workflow
4. **Transparent**: Always announce routing decision to user

### Component Design

#### Component 1: Complexity Assessment Engine (Embedded)

**Location**: `~/.amplihack/.claude/commands/amplihack/ultrathink.md` (Step 0)

**Responsibility**: Analyze investigation request and classify complexity

**Inputs**:

- User's task description (string)
- Task type detection (investigation vs implementation)

**Outputs**:

- Complexity classification: Simple | Medium | Complex
- Routing decision: Explore-Quick | Explore-Thorough | UltraThink-2Agents | UltraThink-Full
- Announcement message (string)

**Algorithm**:

```
1. Task Type Detection
   IF task contains imperative verbs ("add", "implement", "fix", "create")
      THEN skip assessment → proceed to Step 1

   IF task contains investigation keywords ("how", "explain", "what is", "describe")
      THEN proceed with assessment

2. Scope Scoring (Systems Involved)
   Count unique system/module mentions in task description
   Keywords: file names, module names, "integrate", "between"

   Score:
   - 1 system/concept → Simple (1 point)
   - 2-3 systems → Medium (2 points)
   - 4+ systems OR "entire"/"all" → Complex (3 points)

3. Depth Scoring (Analysis Level)
   Detect depth keywords:
   - "overview", "what is", "describe" → Overview → Simple (1 point)
   - "how does X work", "integrate", "connection" → Detailed → Medium (2 points)
   - "comprehensive", "entire", "all aspects", "deep dive" → Comprehensive → Complex (3 points)

4. Breadth Scoring (Coverage Area)
   Detect breadth keywords:
   - "specific", "just", "only", single question → Narrow → Simple (1 point)
   - Multiple questions, "and" connectors → Moderate → Medium (2 points)
   - "all", "entire", "cross-cutting", "every" → Broad → Complex (3 points)

5. Final Classification
   Average Score = (Scope + Depth + Breadth) / 3

   IF Average >= 2.5 OR any dimension = 3 → Complex
   ELSE IF Average >= 1.5 → Medium
   ELSE → Simple

   Edge Case: If depth = 1 (overview) but scope = 1 → Simple (quick mode)
              If depth >= 2 and scope = 1 → Simple (thorough mode)

6. Routing Decision
   Simple + Overview → Explore-Quick (15-25 messages)
   Simple + Detailed → Explore-Thorough (25-40 messages)
   Medium → UltraThink-2Agents (70-120 messages)
   Complex → UltraThink-Full (120-250 messages)
```

**Heuristic Examples**:

| Task                                        | Scope | Depth | Breadth | Avg  | Classification |
| ------------------------------------------- | ----- | ----- | ------- | ---- | -------------- |
| "How does lock system work?"                | 1     | 2     | 1       | 1.33 | Simple         |
| "Explain preferences and hooks integration" | 2     | 2     | 2       | 2.0  | Medium         |
| "How does entire agent orchestration work?" | 3     | 3     | 3       | 3.0  | Complex        |
| "What are pre-commit hooks?"                | 1     | 1     | 1       | 1.0  | Simple (quick) |

#### Component 2: Routing Dispatcher (Embedded)

**Location**: `~/.amplihack/.claude/commands/amplihack/ultrathink.md` (Step 0)

**Responsibility**: Execute appropriate path based on classification

**Routing Logic**:

```markdown
ROUTE: Explore-Quick (Simple + Overview)
└─> Deploy single Explore agent with focused scope - Limit: Documentation and overview only - Expected messages: 15-25 - Skip todo list creation - Announce: "Using quick Explore for overview"

ROUTE: Explore-Thorough (Simple + Detailed)
└─> Deploy single Explore agent with deeper analysis - Include: Code review + documentation - Expected messages: 25-40 - Create minimal todo list - Announce: "Using thorough Explore for detailed analysis"

ROUTE: UltraThink-2Agents (Medium)
└─> Execute Ultra-Think workflow with targeted agents - Deploy 2-3 specific agents (typically analyzer + patterns) - Follow workflow Steps 1-15 with limited orchestration - Expected messages: 70-120 - Announce: "Using targeted Ultra-Think with 2 agents"

ROUTE: UltraThink-Full (Complex)
└─> Execute standard Ultra-Think orchestration - Deploy all relevant agents at each step - Full workflow Steps 1-15 - Expected messages: 120-250 - Announce: "Using full Ultra-Think orchestration"
```

#### Component 3: User Announcement (Embedded)

**Location**: `~/.amplihack/.claude/commands/amplihack/ultrathink.md` (Step 0)

**Responsibility**: Provide transparency about routing decision

**Message Template**:

```
I've assessed this as a [COMPLEXITY] investigation focusing on [KEY_TOPICS].
I'll use [APPROACH] for optimal efficiency!

Examples:
- "I've assessed this as a Simple investigation focusing on the lock system. I'll use quick Explore for optimal efficiency!"
- "I've assessed this as a Complex investigation focusing on agent orchestration, workflow execution, and decision logging. I'll use full Ultra-Think orchestration for comprehensive coverage!"
```

### Integration Architecture

```
User Input
    ↓
ultrathink.md invoked
    ↓
┌─────────────────────────────────────┐
│  Step 0: Assess Complexity          │
│                                     │
│  1. Detect task type                │
│     - Investigation? → Continue     │
│     - Implementation? → Skip to Step 1│
│                                     │
│  2. Score: Scope + Depth + Breadth  │
│                                     │
│  3. Classify: Simple/Medium/Complex │
│                                     │
│  4. Announce decision to user       │
│                                     │
│  5. Route to appropriate path       │
└─────────────────────────────────────┘
    ↓
┌─────────┬──────────┬───────────┬──────────┐
│ Explore │ Explore  │UltraThink │UltraThink│
│ Quick   │Thorough  │ 2 Agents  │   Full   │
└─────────┴──────────┴───────────┴──────────┘
```

### Data Flow

1. **Input**: User task description → ultrathink.md
2. **Detection**: Check for investigation keywords
3. **Scoring**: Calculate scope/depth/breadth scores
4. **Classification**: Determine Simple/Medium/Complex
5. **Announcement**: Generate and display message to user
6. **Routing**: Invoke appropriate execution path
7. **Execution**: Selected path runs to completion
8. **Output**: Results returned to user

### File Structure

```
.claude/commands/amplihack/
└── ultrathink.md
    ├── [NEW] Step 0: Assess Investigation Complexity
    │   ├── Task type detection
    │   ├── Complexity scoring heuristics
    │   ├── Classification logic
    │   ├── User announcement
    │   └── Routing dispatcher
    ├── Step 1: Rewrite and Clarify Requirements (unchanged)
    ├── Step 2: Create GitHub Issue (unchanged)
    └── ... (Steps 3-15 unchanged)

Specs/
├── complexity_estimator_architecture.md (this file)
└── complexity_estimator_tests.md (test specification)
```

## Implementation Strategy

### Phase 1: Core Assessment Logic

1. Add Step 0 section to ultrathink.md
2. Implement task type detection
3. Implement scoring heuristics (scope, depth, breadth)
4. Implement classification logic

### Phase 2: Routing Integration

1. Add announcement message generation
2. Implement routing for each complexity level
3. Integrate with existing workflow steps
4. Ensure backward compatibility

### Phase 3: Testing & Validation

1. Test all classification test cases
2. Verify announcement messages
3. Validate routing decisions
4. Check message count expectations
5. Confirm no regressions

## Non-Functional Requirements

### Performance

- Assessment must complete in < 1 second
- No noticeable latency added to workflow start

### Accuracy

- Target 85%+ classification accuracy in practice
- Conservative routing (when in doubt, route higher)

### Maintainability

- All logic in single location (ultrathink.md Step 0)
- Clear comments explaining heuristics
- Easy to modify scoring thresholds

### Backward Compatibility

- Zero breaking changes to existing workflow
- Non-investigation tasks unaffected
- Users can override routing by being more specific

## Success Metrics

### Primary Metrics

- Simple investigations: 60% message reduction (50+ → 15-25)
- Classification accuracy: 85%+
- Zero regressions in complex investigation quality

### Secondary Metrics

- User satisfaction with routing decisions
- Average message count per investigation type
- Time to complete investigations by complexity

## Risk Assessment

### Risk 1: Misclassification

**Impact**: Medium
**Mitigation**: Conservative routing (when ambiguous, route to higher complexity)

### Risk 2: Keyword Brittleness

**Impact**: Low
**Mitigation**: Comprehensive keyword lists, can be tuned based on usage

### Risk 3: User Confusion

**Impact**: Low
**Mitigation**: Clear announcement messages explain routing decision

### Risk 4: False Negatives (Missing Investigations)

**Impact**: Low
**Mitigation**: Broad investigation keyword detection, implementation tasks naturally skip

## Future Enhancements

### Phase 2 (Post-MVP)

1. Machine learning-based classification
2. User feedback loop for classification tuning
3. Detailed analytics on routing accuracy
4. Custom routing rules per user/project

### Phase 3 (Advanced)

1. Dynamic agent selection based on question content
2. Predictive message count estimates
3. Cost optimization for LLM usage
4. A/B testing of routing strategies

## Dependencies

### Required (Existing)

- ultrathink.md command file
- Explore agent (core agents)
- Ultra-Think workflow (Steps 1-15)

### Optional (Future)

- Analytics collection (for accuracy metrics)
- User feedback mechanism (for tuning)

## Philosophy Alignment

**Ruthless Simplicity**: Solves the problem with minimal added complexity
**Zero-BS**: Complete, working logic from day one
**Modular Design**: Clear separation between assessment and execution
**Trust in Emergence**: Simple heuristics create intelligent routing
**Analysis First**: Assess before executing

## Decision Log

### Decision 1: Embedded vs Separate Module

**Choice**: Embedded in ultrathink.md
**Rationale**: Command files are prompt-based; avoiding Python module complexity
**Alternatives Considered**: Separate .py module (rejected: harder to invoke from markdown)

### Decision 2: Heuristics vs ML

**Choice**: Keyword-based heuristics
**Rationale**: Simpler, more transparent, sufficient for MVP
**Alternatives Considered**: ML classifier (rejected: over-engineering for MVP)

### Decision 3: Three Tiers vs Continuous Scale

**Choice**: Three discrete tiers (Simple/Medium/Complex)
**Rationale**: Easier to reason about, clearer routing decisions
**Alternatives Considered**: Continuous score (rejected: harder to map to routes)

### Decision 4: Conservative vs Aggressive Routing

**Choice**: Conservative (when in doubt, route higher)
**Rationale**: Better to over-analyze than under-analyze
**Alternatives Considered**: Aggressive routing (rejected: risk of missing details)

## Acceptance Criteria

- [ ] Step 0 added to ultrathink.md with complete assessment logic
- [ ] All test cases from complexity_estimator_tests.md pass
- [ ] Announcement messages are clear and informative
- [ ] Routing decisions match expected complexity levels
- [ ] Message counts within expected ranges for each route
- [ ] Zero breaking changes to existing workflow
- [ ] Non-investigation tasks skip assessment correctly
- [ ] Documentation updated with new Step 0 behavior

## Related Documents

- `Specs/complexity_estimator_tests.md` - Test specification
- `~/.amplihack/.claude/commands/amplihack/ultrathink.md` - Implementation file
- Issue #1108 - Original feature request
- Reflection session 20251104 - Source of recommendation
