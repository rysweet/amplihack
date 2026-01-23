# Module: Improvement Workflow

## Purpose

Enforce progressive validation throughout the improvement process to prevent complexity creep and catch issues early when they're cheap to fix.

## Contract

### Inputs

- **Improvement Request**: Description of what needs improvement
- **Context**: Current state of the system
- **Constraints**: Time, scope, or resource limits

### Outputs

- **Validated Implementation**: Code that passes all gates
- **Validation Report**: Record of all checks performed
- **Learning Capture**: Updates to DISCOVERIES.md

### Side Effects

- Creates validation logs in `~/.amplihack/.claude/runtime/logs/`
- Updates DISCOVERIES.md with patterns
- May invoke other agents for validation
- May reject and restart improvements

## Dependencies

### Required Agents

- architect (design validation)
- reviewer (philosophy compliance)
- security (vulnerability scanning)
- analyzer (redundancy detection)
- tester (test validation)

### Required Tools

- Task (parallel agent execution)
- Read/Write (code inspection)
- TodoWrite (progress tracking)

## Implementation Notes

### Key Design Decisions

1. **5-Stage Pipeline**: Each stage has a gate that must pass before proceeding
2. **50 LOC Increments**: Forces continuous validation during coding
3. **Parallel Validation**: Stage 4 runs multiple agents simultaneously
4. **Hard Stops**: Security and philosophy violations halt immediately
5. **Automatic Triggers**: Complexity detection is automatic, not optional

### Stage Gates

```
Stage 1 (Problem) → STOP if not simplest approach
Stage 2 (Design) → STOP if > 200 LOC or > 3 components
Stage 3 (Code) → STOP every 50 LOC for validation
Stage 4 (Review) → STOP if any agent finds issues
Stage 5 (Final) → STOP if checklist incomplete
```

### Enforcement Rules

- **Cannot skip stages**: Must complete in order
- **Cannot ignore failures**: Must fix or redesign
- **Cannot exceed limits**: Without architect approval
- **Cannot merge**: Without all validations passing

## Test Requirements

### Behavior Tests

1. **Gate Enforcement**
   - Verify stops at complexity threshold
   - Verify stops at security issues
   - Verify stops at philosophy violations

2. **Progressive Validation**
   - Verify 50 LOC increment checks
   - Verify parallel agent execution
   - Verify validation report generation

3. **Learning Capture**
   - Verify DISCOVERIES.md updates
   - Verify metrics collection
   - Verify pattern recognition

### Test Scenarios

```python
# Scenario 1: Simple improvement passes all gates
def test_simple_improvement_flow():
    # 50 lines, 1 component, no security issues
    # Should complete all 5 stages

# Scenario 2: Complex improvement triggers redesign
def test_complexity_gate_trigger():
    # 300+ lines or 4+ components
    # Should stop at Stage 2 and require decomposition

# Scenario 3: Security issue forces fix
def test_security_gate_enforcement():
    # Vulnerability detected at Stage 3
    # Should halt and require fix before continuing
```

## Integration Points

### With CLAUDE.md

Updates main orchestrator to use improvement-workflow for all improvements:

```markdown
When user requests improvement:

1. Delegate to improvement-workflow agent
2. Monitor stage progression
3. Handle gate failures appropriately
```

### With Other Workflows

- **prompt-review-workflow**: Can trigger improvement-workflow for implementation
- **ci-diagnostic-workflow**: Uses validation patterns from improvement-workflow

### With Metrics System

Feeds data to `~/.amplihack/.claude/runtime/metrics/`:

- Validation failure rates
- Common failure patterns
- Time spent at each stage
- Complexity trends over time

## Success Criteria

An implementation is successful when:

1. **Zero PR rejections** due to preventable issues
2. **< 300 LOC** for 90% of improvements
3. **< 3 components** for 85% of features
4. **Zero security issues** reaching review
5. **< 5% redundant code** in final implementation

## Rollout Strategy

1. **Phase 1**: Use for new feature development
2. **Phase 2**: Apply to bug fixes and refactoring
3. **Phase 3**: Mandatory for all code changes
4. **Phase 4**: Analyze metrics and optimize gates

## Lessons from PR #44

This workflow specifically prevents:

| PR #44 Issue               | How This Workflow Prevents It       |
| -------------------------- | ----------------------------------- |
| 7 agents created           | Stage 2 gate limits to 3 components |
| 915-line test file         | Stage 3 stops at 50 LOC increments  |
| Security issues late       | Stage 2 security pre-check          |
| 2000+ redundant lines      | Stage 3 continuous redundancy check |
| Force push slipped through | Stage 5 checklist requirement       |

## Future Enhancements (NOT NOW)

- Machine learning for complexity prediction
- Automatic decomposition suggestions
- Historical analysis for gate tuning
- IDE integration for real-time validation

Remember: **The best bug is the one that never gets written.**
