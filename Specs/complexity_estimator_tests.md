# Complexity Estimator Test Specification

## Test Coverage Analysis

### Current Coverage

- Lines: 0% (new feature)
- Functions: 0% (new feature)
- Critical gaps: All functionality needs testing

### Testing Strategy

Following testing pyramid:

- 80% Manual verification (embedded heuristics in markdown)
- 20% Integration testing (full workflow execution)

## High Priority Test Cases

### 1. Simple Investigation - Single System

**Test: Lock System Question**

```
Input: "How does the lock system work?"
Expected Classification: Simple
Expected Route: Single Explore agent (quick mode)
Expected Message Count: 15-25

Heuristics Check:
- Scope: 1 system mentioned ("lock system") → Simple
- Depth: "how does X work" → Detailed → Medium
- Breadth: Single focused topic → Narrow → Simple
- Final: 2/3 Simple → Simple
```

**Test: Overview Question**

```
Input: "Explain what the pre-commit hooks are"
Expected Classification: Simple
Expected Route: Single Explore agent (quick mode)
Expected Message Count: 15-25

Heuristics Check:
- Scope: 1 concept → Simple
- Depth: "explain what" → Overview → Simple
- Breadth: Single topic → Narrow → Simple
- Final: 3/3 Simple → Simple
```

### 2. Medium Investigation - Multiple Systems

**Test: Integration Question**

```
Input: "How do preferences and hooks integrate?"
Expected Classification: Medium
Expected Route: Ultra-Think with 2 agents
Expected Message Count: 70-120

Heuristics Check:
- Scope: 2 systems ("preferences", "hooks") → Medium
- Depth: "integrate" → Detailed → Medium
- Breadth: Two systems → Moderate → Medium
- Final: 3/3 Medium → Medium
```

**Test: Two-Component Question**

```
Input: "Describe the connection between worktrees and agents"
Expected Classification: Medium
Expected Route: Ultra-Think with 2 agents
Expected Message Count: 70-120

Heuristics Check:
- Scope: 2 systems → Medium
- Depth: "connection between" → Detailed → Medium
- Breadth: Two areas → Moderate → Medium
- Final: 3/3 Medium → Medium
```

### 3. Complex Investigation - Multiple Systems

**Test: Orchestration Question**

```
Input: "How does the entire agent orchestration system work?"
Expected Classification: Complex
Expected Route: Full Ultra-Think orchestration
Expected Message Count: 120-250

Heuristics Check:
- Scope: "entire system" → 4+ components → Complex
- Depth: "how does X work" + "entire" → Comprehensive → Complex
- Breadth: "entire system" → Broad → Complex
- Final: 3/3 Complex → Complex
```

**Test: Cross-Cutting Question**

```
Input: "Explain all aspects of the workflow execution, agent delegation, and decision logging"
Expected Classification: Complex
Expected Route: Full Ultra-Think orchestration
Expected Message Count: 120-250

Heuristics Check:
- Scope: 3 major systems explicitly mentioned → Complex
- Depth: "all aspects" → Comprehensive → Complex
- Breadth: Multiple topics → Broad → Complex
- Final: 3/3 Complex → Complex
```

### 4. Edge Cases

**Test: Ambiguous Scope**

```
Input: "How does the workflow system work?"
Expected Classification: Medium
Expected Route: Ultra-Think with 2 agents

Heuristics Check:
- Scope: "workflow system" could be 1 or multiple → Medium (conservative)
- Depth: "how does X work" → Detailed → Medium
- Breadth: Single topic but broad implications → Moderate → Medium
- Final: 3/3 Medium → Medium
```

**Test: Non-Investigation Task**

```
Input: "Add authentication to the API"
Expected: Skip Step 0, proceed to Step 1
Route: Standard Ultra-Think workflow

Detection:
- No investigation keywords ("how", "explain", "what is")
- Imperative verb ("Add") → Implementation task
- Should skip complexity assessment
```

**Test: Mixed Investigation and Implementation**

```
Input: "Explain how authentication works and then add it to the API"
Expected Classification: Complex (investigation + implementation)
Expected Route: Full Ultra-Think orchestration

Heuristics Check:
- Contains investigation + implementation → Complex by default
- Multiple phases required → Complex
```

### 5. Boundary Conditions

**Test: Minimal Question**

```
Input: "Lock?"
Expected Classification: Simple
Expected Route: Single Explore agent

Heuristics Check:
- Single word → Simple
- No complexity indicators → Simple
```

**Test: Maximum Verbosity**

```
Input: "I need a comprehensive deep-dive analysis covering all aspects of how the entire agent orchestration system integrates with workflows, preferences, hooks, and the Ultra-Think command, including all cross-cutting concerns and edge cases"
Expected Classification: Complex
Expected Route: Full Ultra-Think orchestration

Heuristics Check:
- "comprehensive", "deep-dive", "entire", "all aspects" → Complex
- 5+ systems mentioned → Complex
- "cross-cutting concerns" → Broad → Complex
```

## Integration Test Cases

### 1. Announcement Message Verification

**Test: Message Format**

```
For any complexity level, verify message includes:
- Complexity level (Simple/Medium/Complex)
- Key topics identified
- Approach being used
- Format: "I've assessed this as a [COMPLEXITY] investigation..."
```

### 2. Agent Invocation Verification

**Test: Simple Route**

```
After Simple classification:
- Verify single Explore agent is invoked
- Verify no Ultra-Think workflow steps created
- Verify message count stays under 40
```

**Test: Medium Route**

```
After Medium classification:
- Verify Ultra-Think workflow begins
- Verify 2-3 agents are deployed (not full orchestration)
- Verify message count in 70-120 range
```

**Test: Complex Route**

```
After Complex classification:
- Verify full Ultra-Think workflow executes
- Verify all relevant agents deployed
- Verify comprehensive coverage
```

### 3. Workflow Integration

**Test: Non-Investigation Skip**

```
For implementation tasks:
- Verify Step 0 is skipped
- Verify workflow proceeds directly to Step 1
- Verify no announcement about complexity
```

### 4. Backward Compatibility

**Test: Existing Behavior Preserved**

```
For tasks not using new assessment:
- Verify existing Ultra-Think behavior unchanged
- Verify no breaking changes to workflow
- Verify all existing features still work
```

## Manual Testing Checklist

- [ ] Test all 5 simple investigation examples
- [ ] Test all 4 medium investigation examples
- [ ] Test all 3 complex investigation examples
- [ ] Test all 4 edge cases
- [ ] Verify announcement messages are clear
- [ ] Confirm routing decisions are correct
- [ ] Check message counts are in expected ranges
- [ ] Validate non-investigation tasks skip assessment
- [ ] Ensure no regressions in existing workflow

## Success Criteria

- [ ] 100% of test cases classify correctly
- [ ] Announcement messages are clear and informative
- [ ] 60% time reduction for simple investigations (vs full Ultra-Think)
- [ ] No regressions in medium/complex investigation quality
- [ ] Zero breaking changes to existing workflow
- [ ] User feedback indicates improved efficiency

## Red Flags to Watch For

- Misclassification (Simple marked as Complex or vice versa)
- Missing announcement messages
- Wrong agent deployed for complexity level
- Message count outside expected ranges
- Breaking changes to existing behavior
- Confusion in edge cases (ambiguous questions)

## Performance Metrics

Target improvements from issue #1108:

- Simple investigations: 50+ messages → 15-25 messages (60% reduction)
- Medium investigations: No change (already appropriate)
- Complex investigations: No change (already appropriate)
- Overall efficiency: 30-40% average message reduction across all investigations

## Notes

- This is a heuristics-based system, not ML-based
- Some edge cases will require judgment calls
- Conservative routing (when in doubt, route to higher complexity) is acceptable
- User can always override by providing more specific instructions
- Classification accuracy target: 85%+ in practice
