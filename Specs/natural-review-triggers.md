# Module: Natural Review Triggers

## Purpose

Trigger code reviews at meaningful boundaries that respect developer flow while catching issues when they're easiest to fix.

## Contract

### Inputs

- **Code Changes**: Current implementation in progress
- **Context State**: Module boundaries, complexity metrics, risk indicators
- **Developer Intent**: What they're trying to accomplish

### Outputs

- **Review Decision**: Whether to trigger review now
- **Review Type**: Quick check vs deep analysis
- **Review Focus**: What specifically to examine

### Side Effects

- May pause implementation for review
- Creates review records in logs
- Updates complexity metrics

## Review Trigger Categories

### 1. Natural Completion Points

**When to trigger**: Code represents a complete thought

```yaml
triggers:
  - module_complete: "Finished implementing a complete module"
  - feature_complete: "Core functionality is working"
  - integration_point: "About to connect to external system"
  - abstraction_layer: "Just created a new abstraction"
```

**Review depth**: Full philosophy and design check

### 2. Complexity Thresholds

**When to trigger**: Complexity signals emerge

```yaml
early_warning_signals:
  - second_abstraction: "Adding 2nd layer of abstraction"
  - third_dependency: "Pulling in 3rd external dependency"
  - nested_depth_3: "Code nesting exceeds 3 levels"
  - multiple_responsibilities: "Function doing more than one thing"

hard_stops:
  - cyclomatic_complexity: "> 10 in single function"
  - file_count: "> 3 files in single feature"
  - coupling: "> 3 modules interdependent"
```

**Review depth**: Focused on simplification opportunities

### 3. Risk-Based Triggers

**When to trigger**: Touching sensitive areas

```yaml
immediate_review:
  - authentication: "Any auth/authz code"
  - file_system: "Direct file manipulation"
  - subprocess: "Spawning external processes"
  - network: "External API calls"
  - data_persistence: "Database/storage changes"
  - secrets: "Anything touching credentials" # pragma: allowlist secret

deferred_review:
  - ui_changes: "Pure presentation logic"
  - test_code: "Test implementations"
  - documentation: "Doc updates"
```

**Review depth**: Security and correctness focus

### 4. Domain Transitions

**When to trigger**: Crossing architectural boundaries

```yaml
boundary_crossings:
  - layer_transition: "Moving from business to data layer"
  - agent_boundary: "Crossing from one agent to another"
  - system_edge: "At system input/output points"
  - protocol_change: "Switching communication patterns"
```

**Review depth**: Contract and interface validation

## Smart Review Scheduling

### Adaptive Triggers

```python
def should_trigger_review(context):
    # Immediate triggers (always review)
    if context.has_security_risk:
        return ReviewType.IMMEDIATE

    # Accumulated risk score
    risk_score = (
        context.complexity_increase * 2 +
        context.dependencies_added * 3 +
        context.abstractions_created * 4
    )

    if risk_score > 10:
        return ReviewType.COMPREHENSIVE

    # Natural boundary
    if context.at_module_boundary:
        return ReviewType.STANDARD

    # Defer review
    return ReviewType.NONE
```

### Review Types

**Quick Check** (2 min)

- Philosophy alignment
- Obvious issues
- Security red flags

**Standard Review** (5 min)

- Design coherence
- Module boundaries
- Test coverage

**Comprehensive Review** (10+ min)

- Full architecture review
- Performance implications
- Edge case analysis

## Implementation Flow

### Pre-Implementation Review

```yaml
trigger: "Design complete, before coding"
focus:
  - Is this the simplest approach?
  - Are boundaries clear?
  - Any security considerations?
depth: "High-level, 5 minutes max"
```

### Mid-Implementation Review

```yaml
trigger: "Natural completion point OR risk signal"
focus:
  - Is complexity justified?
  - Can this be simpler?
  - Are we solving the right problem?
depth: "Proportional to risk"
```

### Pre-Integration Review

```yaml
trigger: "Before connecting to other systems"
focus:
  - Contract clarity
  - Error handling
  - Security implications
depth: "Deep at integration points"
```

### Final Review

```yaml
trigger: "Feature complete, before merge"
focus:
  - Philosophy compliance
  - No dead code
  - Documentation complete
depth: "Comprehensive"
```

## Developer Experience

### Flow-Preserving Principles

1. **Batch Reviews**: Group related changes for single review
2. **Async When Possible**: Non-blocking reviews for low-risk changes
3. **Context Aware**: Don't review scaffolding or boilerplate
4. **Progressive Depth**: Quick checks first, deep dives only when needed

### Review Fatigue Prevention

```yaml
strategies:
  - no_repeat_reviews: "Don't re-review unchanged code"
  - trust_building: "Less review as patterns prove safe"
  - focus_rotation: "Different aspect each review"
  - celebration: "Acknowledge good design choices"
```

## Metrics for Success

### Effectiveness Metrics

- Issues caught per review
- Time to fix vs time of discovery
- False positive rate

### Developer Experience Metrics

- Flow interruptions per day
- Review acceptance rate
- Time spent in review

### Optimization Signals

- If catching < 1 issue per 5 reviews: reduce frequency
- If fixing takes > 10x discovery time: review earlier
- If developers bypass: simplify triggers

## Integration with Existing Workflow

### Replace Line-Based Triggers

```diff
- Stage 3 (Code) → STOP every 50 LOC for validation
+ Stage 3 (Code) → STOP at natural boundaries per triggers
```

### Parallel Review Capability

```python
# When multiple aspects need review
parallel_reviews = [
    ("architect", "design_coherence"),
    ("security", "vulnerability_scan"),
    ("reviewer", "philosophy_check")
]
# Execute simultaneously, aggregate results
```

## Example Scenarios

### Scenario 1: Simple Feature Addition

```
1. Design review → Quick check (2 min)
2. Implementation → No interruption (< 50 lines, single file)
3. Pre-merge → Standard review (5 min)
Total interruptions: 2 (vs 3-4 with line counting)
```

### Scenario 2: Security-Sensitive Change

```
1. Design review → Comprehensive (involves auth)
2. First implementation → Immediate review (security checkpoint)
3. Integration point → Standard review
4. Pre-merge → Security-focused review
Total: 4 reviews, all meaningful
```

### Scenario 3: Complex Refactoring

```
1. Architecture review → Comprehensive
2. Module 1 complete → Standard review
3. Module 2 complete → Standard review
4. Integration → Comprehensive review
5. Pre-merge → Quick check
Total: 5 reviews at natural boundaries
```

## The Philosophy

Reviews should feel like:

- **Guardrails**, not roadblocks
- **Coaching**, not criticism
- **Learning opportunities**, not tests
- **Natural pauses**, not interruptions

Remember: The goal is to catch issues when they're cheap to fix, not to maximize review frequency.
