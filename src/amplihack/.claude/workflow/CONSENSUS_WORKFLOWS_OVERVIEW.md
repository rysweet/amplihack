---
name: CONSENSUS_WORKFLOWS_OVERVIEW
version: 1.0.0
description: Documentation explaining the three consensus workflow patterns and when to use each
phases:
  - overview
  - comparison
  - selection-guidance
---

# Consensus Workflows Overview

This document explains the three consensus workflow patterns and when to use each.

## Architecture

**Hybrid Approach**: Workflows (markdown) + Minimal orchestrators (Python)

- **Workflow files** (this directory): Define WHAT to do, step-by-step
- **Python orchestrators** (to be built): Handle subprocess spawning, voting, collection
- **Commands** (to be built): Connect workflows to orchestrators via `/ultrathink`

## The Three Workflows

### 1. N-Version Workflow (`N_VERSION_WORKFLOW.md`)

**Pattern**: Generate N independent implementations, select best

**Use When**:

- Critical security features (authentication, authorization)
- Complex algorithms with multiple valid approaches
- High-risk refactoring of core components
- When correctness is paramount over speed

**Key Features**:

- N parallel implementations (typically 3-6)
- No context sharing (true independence)
- Systematic comparison and selection
- Can synthesize hybrid from best parts

**Example**:

```
Task: Implement JWT authentication
N = 4 (critical security)
→ 4 independent implementations generated
→ Comparison: correctness, security, simplicity
→ Selection: Hybrid of versions 2 and 3
→ Best security + cleanest API design
```

**Cost**: N times compute resources
**Benefit**: Significantly reduced risk of critical errors

---

### 2. Debate Workflow (`DEBATE_WORKFLOW.md`)

**Pattern**: Multi-perspective structured debate for decisions

**Use When**:

- Major architectural decisions (framework selection)
- Complex trade-offs with no clear winner
- Controversial changes affecting multiple teams
- High-impact decisions requiring buy-in

**Key Features**:

- Multiple agent perspectives (security, performance, simplicity, etc.)
- Structured debate rounds (2-5 rounds)
- Challenge and response format
- Facilitator synthesis with dissenting views

**Example**:

```
Decision: PostgreSQL vs MongoDB for analytics
Perspectives: Performance, Cost, Maintainability, Scalability
Rounds: 3 (position, challenge, synthesis)
→ Debate reveals trade-offs clearly
→ Synthesis: PostgreSQL with migration path to ClickHouse
→ Consensus achieved, dissent documented
```

**Cost**: Multiple agent cycles, longer decision time
**Benefit**: Well-reasoned decisions, surface hidden risks

---

### 3. Cascade Workflow (`CASCADE_WORKFLOW.md`)

**Pattern**: Graceful degradation with fallbacks

**Use When**:

- External service dependencies (APIs, databases)
- Time-sensitive operations with acceptable degraded modes
- Operations where partial results better than no results
- High-availability requirements

**Key Features**:

- Primary (optimal) → Secondary (acceptable) → Tertiary (guaranteed)
- Timeout-based fallback triggers
- Configurable degradation notification
- Always completes, never fully fails

**Example**:

```
Task: Code analysis with AI
PRIMARY: GPT-4 comprehensive (30s) → TIMEOUT
SECONDARY: GPT-3.5 standard (10s) → SUCCESS
TERTIARY: Static regex (5s) → (not needed)
→ User gets standard analysis instead of comprehensive
→ Better than error message or long wait
```

**Cost**: Complexity of maintaining multiple fallback levels
**Benefit**: System always responds, better UX

## Integration with DEFAULT_WORKFLOW

Each consensus workflow replaces specific steps in DEFAULT_WORKFLOW:

| Consensus Workflow | Replaces DEFAULT_WORKFLOW Steps                  |
| ------------------ | ------------------------------------------------ |
| N-Version          | Steps 4-5 (Research & Implementation)            |
| Debate             | Step 4 (Research and Design)                     |
| Cascade            | Step 5 (Implementation) - for resilient features |

All other steps (requirements, testing, CI/CD, PR process) remain unchanged.

## Usage Patterns

### Via UltraThink (Recommended)

```bash
# Use n-version for critical implementation
/ultrathink --workflow n-version "Implement authentication system"

# Use debate for architectural decision
/ultrathink --workflow debate "Should we use REST or GraphQL?"

# Use cascade for resilient feature
/ultrathink --workflow cascade "Implement external API integration"
```

### Manual Execution

Follow the steps in each workflow file manually when:

- You want fine-grained control over each step
- Testing workflow modifications
- Learning how the workflow operates

### Customization

All workflows are user-customizable:

1. Edit configuration section in workflow file
2. Adjust parameters (N, perspectives, timeouts)
3. Modify steps to match your needs
4. Save changes
5. Updated workflow applies automatically

## When to Use Which Workflow

### Decision Matrix

| Scenario                  | N-Version | Debate | Cascade |
| ------------------------- | --------- | ------ | ------- |
| Security-critical code    | ✓✓✓       | ✓      |         |
| Architectural decision    |           | ✓✓✓    |         |
| External API integration  |           |        | ✓✓✓     |
| Complex algorithm         | ✓✓        | ✓      |         |
| High-availability feature |           |        | ✓✓✓     |
| Framework selection       |           | ✓✓✓    |         |
| Core refactoring          | ✓✓        | ✓✓     |         |
| Time-sensitive operation  |           |        | ✓✓      |

✓✓✓ = Primary use case
✓✓ = Good fit
✓ = Can help

### Anti-Patterns (Don't Use For)

**N-Version**: Don't use for

- Simple CRUD operations
- Minor bug fixes
- Documentation updates
- Time-sensitive quick fixes

**Debate**: Don't use for

- Decisions with obvious correct answer
- Simple implementation choices
- Hot fixes
- Routine feature additions

**Cascade**: Don't use for

- Operations requiring exact correctness
- Security-critical operations (authentication)
- Financial transactions
- When failures must surface to user

## Cost-Benefit Summary

### N-Version Programming

- **Cost**: 3-6x compute resources, longer execution time
- **Benefit**: Dramatically reduced risk of critical bugs
- **ROI**: High for security and core infrastructure
- **Typical N**: 3 (standard), 4-6 (critical)

### Debate Workflow

- **Cost**: Multiple agent cycles, 2-5x time for decision
- **Benefit**: Better decisions, buy-in, documented rationale
- **ROI**: High for decisions expensive to reverse
- **Typical Perspectives**: 3-5, rarely 7

### Cascade Workflow

- **Cost**: Complexity of maintaining fallback levels
- **Benefit**: Always completes, better user experience
- **ROI**: High for user-facing, time-sensitive features
- **Typical Levels**: Always 3 (primary, secondary, tertiary)

## Combining Workflows

Workflows can be combined for complex scenarios:

### Example: Critical External Service Integration

```
Step 1: DEBATE - Decide which external service to use
→ Result: Service A chosen

Step 2: N-VERSION - Implement integration 3 ways
→ Result: Best implementation selected

Step 3: CASCADE - Add fallback levels to implementation
→ Result: Resilient integration with graceful degradation
```

### Example: Complex Feature Development

```
Step 1: DEBATE - Architectural approach
→ Result: Microservices with event sourcing

Step 2: N-VERSION - Implement core service (critical)
→ Result: Best of 3 implementations

Step 3: DEFAULT_WORKFLOW - Implement supporting services
→ Result: Standard implementation (non-critical)

Step 4: CASCADE - Add resilience to all services
→ Result: High-availability system
```

## Next Steps

### For Implementers

To implement orchestrators for these workflows:

1. **Read**: Review all three workflow files thoroughly
2. **Design**: Plan Python orchestrator architecture (see `ORCHESTRATOR_DESIGN.md`)
3. **Build**: Implement minimal orchestrators (subprocess spawning, collection)
4. **Test**: Validate each workflow independently
5. **Integrate**: Connect to UltraThink via command flags
6. **Document**: Update this overview with usage examples

### For Users

To use these workflows:

1. **Learn**: Read workflow files to understand each pattern
2. **Experiment**: Try on non-critical features first
3. **Customize**: Adjust configurations for your project
4. **Measure**: Track metrics (cost, quality, time saved)
5. **Optimize**: Refine based on results
6. **Share**: Document learnings in DISCOVERIES.md

## Philosophy Alignment

These workflows enforce Amplihack principles:

- **Ruthless Simplicity**: Workflows are simple, orchestrators minimal
- **Bricks & Studs**: Each workflow is self-contained, clear interface
- **Zero-BS**: No stubs, all workflows complete and actionable
- **Evidence-Based**: Decisions backed by systematic analysis
- **Continuous Improvement**: Metrics drive optimization
- **User-Centric**: Customizable for different needs

## Metrics to Track

Monitor these metrics to optimize workflow usage:

### N-Version Metrics

- Selection rate by version number (is one profile consistently better?)
- Synthesis frequency (how often do we combine versions?)
- Bug rate comparison (critical features with vs without N-version)
- Time cost vs bug reduction benefit

### Debate Metrics

- Debate rounds needed to reach consensus
- Reversal rate (how often do we reverse debate decisions?)
- Perspective agreement patterns (which perspectives align?)
- Decision quality (subjective assessment after implementation)

### Cascade Metrics

- Fallback frequency (primary, secondary, tertiary usage %)
- Average response time by cascade level
- User impact of degradation (complaints, satisfaction)
- Optimization opportunities (timeout tuning)

## Conclusion

These three consensus workflows provide powerful patterns for:

1. **Risk Reduction** (N-Version): Multiple implementations catch critical errors
2. **Better Decisions** (Debate): Structured analysis surfaces trade-offs
3. **Resilience** (Cascade): Graceful degradation maintains availability

Use them judiciously - they add cost but provide significant value when applied to the right problems.

---

**Status**: Workflows complete, orchestrators pending implementation
**Next**: Build Python orchestrators to execute these workflows
**Owner**: To be assigned
**Priority**: High (enables consensus-based development)
