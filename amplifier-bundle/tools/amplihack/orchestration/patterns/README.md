# Fault-Tolerance Pattern Orchestrators

This directory contains three fault-tolerance pattern orchestrators that provide robust, reliable execution strategies for AI-powered development workflows.

## Overview

Each pattern addresses a different aspect of reliability:

1. **N-Version Programming** - Reduces errors through diversity
2. **Multi-Agent Debate** - Improves decisions through multiple perspectives
3. **Fallback Cascade** - Ensures completion through graceful degradation

## Patterns

### 1. N-Version Programming (`n_version.py`)

Generate N independent implementations in parallel, compare them, and select the best.

**When to use:**

- Critical security features (authentication, authorization)
- Complex algorithms with multiple valid approaches
- High-risk refactoring of core components
- When correctness is paramount

**Example:**

```python
from .n_version import run_n_version

result = run_n_version(
    task_prompt="Implement password hashing function",
    n=3,
    selection_criteria=["security", "correctness", "simplicity"],
    timeout=300,
)

print(f"Selected: {result['selected']}")
print(f"Rationale: {result['rationale']}")
```

**Based on:** `.claude/workflow/N_VERSION_WORKFLOW.md`

**Key Features:**

- Parallel execution of N implementations
- Diversity through different implementation profiles (conservative, pragmatic, minimalist, etc.)
- Automated comparison and selection using reviewer agent
- Support for hybrid synthesis (combining best parts)

**Returns:**

```python
{
    "versions": List[ProcessResult],      # All N implementation outputs
    "comparison": ProcessResult,          # Reviewer analysis
    "selected": str,                      # "version_1", "version_2", or "hybrid"
    "rationale": str,                     # Selection explanation
    "session_id": str,                    # For log tracking
    "success": bool,                      # Overall success
}
```

---

### 2. Multi-Agent Debate (`debate.py`)

Conduct structured debate with multiple perspectives to reach consensus on complex decisions.

**When to use:**

- Major architectural decisions
- Complex trade-offs with no clear winner
- Controversial changes affecting multiple teams
- Decisions that are expensive to reverse

**Example:**

```python
from .debate import run_debate

result = run_debate(
    decision_question="Should we use PostgreSQL or MongoDB?",
    perspectives=["security", "performance", "simplicity", "cost"],
    rounds=3,
    timeout=180,
)

print(f"Consensus: {result['synthesis'].output}")
print(f"Confidence: {result['confidence']}")
```

**Based on:** `.claude/workflow/DEBATE_WORKFLOW.md`

**Key Features:**

- Multiple perspectives (security, performance, simplicity, maintainability, etc.)
- Structured rounds: initial positions → challenges → synthesis
- Parallel execution within each round
- Facilitator synthesis with confidence levels
- Documents dissenting views

**Returns:**

```python
{
    "rounds": List[dict],                 # Each round's results
    "positions": Dict[str, List[str]],    # Position history per perspective
    "synthesis": ProcessResult,           # Final consensus
    "confidence": str,                    # "HIGH", "MEDIUM", or "LOW"
    "session_id": str,                    # For log tracking
    "success": bool,                      # Overall success
}
```

---

### 3. Fallback Cascade (`cascade.py`)

Graceful degradation through cascading fallback strategies.

**When to use:**

- External service dependencies
- Time-sensitive operations with acceptable degraded modes
- High-availability requirements
- When partial results are better than no results

**Example:**

```python
from .cascade import run_cascade

result = run_cascade(
    task_prompt="Generate API documentation",
    fallback_strategy="quality",      # or "service", "freshness", "completeness"
    timeout_strategy="balanced",      # or "aggressive", "patient"
    notification_level="explicit",
)

print(f"Succeeded at {result['cascade_level']} level")
if result['degradation']:
    print(f"Degradation: {result['degradation']}")
```

**Based on:** `.claude/workflow/CASCADE_WORKFLOW.md`

**Key Features:**

- Three levels: primary (optimal) → secondary (acceptable) → tertiary (minimal)
- Predefined strategies: quality, service, freshness, completeness, accuracy
- Timeout strategies: aggressive, balanced, patient
- Notification levels: silent, warning, explicit
- Custom cascade support via `create_custom_cascade()`

**Returns:**

```python
{
    "result": ProcessResult,              # Final successful result
    "cascade_level": str,                 # "primary", "secondary", "tertiary", or "failed"
    "degradation": str,                   # Degradation description (if any)
    "attempts": List[ProcessResult],      # All attempts made
    "session_id": str,                    # For log tracking
    "success": bool,                      # Whether any level succeeded
}
```

---

## Common Parameters

All patterns share these common parameters:

- `working_dir: Optional[Path]` - Working directory (default: current dir)
- `model: Optional[str]` - Claude model to use (default: CLI default)
- `timeout: Optional[int]` - Timeout per process in seconds

## Session Logs

All patterns create session logs in `.claude/runtime/logs/<session_id>/`:

- `session.log` - Overall session information
- `<process_id>.log` - Individual process logs

Session IDs are returned in results for traceability.

## Pattern Selection Guide

| Scenario                  | Pattern   | Why                                                |
| ------------------------- | --------- | -------------------------------------------------- |
| Critical security feature | N-Version | Multiple implementations catch vulnerabilities     |
| Architecture decision     | Debate    | Multiple perspectives surface trade-offs           |
| External API integration  | Cascade   | Graceful degradation when service slow/unavailable |
| Complex algorithm         | N-Version | Different approaches reveal design insights        |
| Controversial change      | Debate    | Structured discussion builds consensus             |
| Time-sensitive operation  | Cascade   | Acceptable degradation better than timeout         |

## Examples

See `PATTERN_EXAMPLES.py` for complete working examples of each pattern.

## Integration with Workflows

These patterns are designed to integrate with the default workflow (`.claude/workflow/DEFAULT_WORKFLOW.md`):

- **N-Version**: Replaces Steps 4-5 (Research/Design and Implementation)
- **Debate**: Replaces Step 4 (Research and Design)
- **Cascade**: Can be applied to any step with fallback options

## Architecture

All patterns are built on the orchestration infrastructure:

```
patterns/
├── n_version.py        # N-Version Programming orchestrator
├── debate.py           # Multi-Agent Debate orchestrator
├── cascade.py          # Fallback Cascade orchestrator
└── __init__.py         # Pattern exports

Uses:
../claude_process.py    # Subprocess wrapper
../execution.py         # Parallel/sequential/fallback helpers
../session.py           # Session management
```

## Philosophy Alignment

These patterns follow Amplihack's core principles:

- **Ruthless Simplicity** - Simple, direct implementations
- **Zero-BS** - No stubs, no placeholders, working code only
- **Fault Tolerance** - Graceful handling of failures
- **Transparency** - Clear logging and rationale
- **Evidence-Based** - Decisions backed by data and analysis

## Advanced Usage

### Custom Cascade Levels

```python
from .cascade import create_custom_cascade

result = create_custom_cascade(
    task_prompt="Analyze code",
    levels=[
        {
            "name": "deep_analysis",
            "timeout": 120,
            "constraint": "comprehensive analysis with all recommendations",
        },
        {
            "name": "quick_scan",
            "timeout": 30,
            "constraint": "identify major issues only",
        },
        {
            "name": "syntax_check",
            "timeout": 5,
            "constraint": "basic syntax validation",
        },
    ],
)
```

### Custom N-Version Profiles

```python
result = run_n_version(
    task_prompt="Implement feature",
    diversity_profiles=[
        {
            "name": "security_first",
            "traits": "Prioritize security over all else, defensive programming",
        },
        {
            "name": "performance_first",
            "traits": "Optimize for speed, minimize allocations",
        },
        {
            "name": "maintainability_first",
            "traits": "Optimize for readability and future changes",
        },
    ],
)
```

### Extended Debate Perspectives

```python
result = run_debate(
    decision_question="Which framework?",
    perspectives=[
        "security",
        "performance",
        "simplicity",
        "maintainability",
        "cost",
        "scalability",
        "user_experience",
    ],
    rounds=4,  # More rounds for complex decisions
)
```

## Contributing

When adding new patterns:

1. Create new file in `patterns/` directory
2. Implement using orchestration infrastructure
3. Add comprehensive docstrings
4. Update `__init__.py` exports
5. Add examples to `PATTERN_EXAMPLES.py`
6. Update this README

## References

- Orchestration Infrastructure: `../README.md`
- Workflows: `.claude/workflow/*.md`
- Core Philosophy: `.claude/context/PHILOSOPHY.md`
