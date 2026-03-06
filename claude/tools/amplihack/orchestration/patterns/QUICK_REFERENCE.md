# Pattern Orchestrators Quick Reference

## Import

```python
from .claude.tools.amplihack.orchestration.patterns import (
    run_n_version,
    run_debate,
    run_cascade,
    create_custom_cascade,
)
```

## N-Version Programming

**Use when:** Critical implementations requiring multiple attempts

```python
result = run_n_version(
    task_prompt="Implement feature X",
    n=3,                          # Number of versions
    selection_criteria=[          # Optional
        "correctness",
        "security",
        "simplicity"
    ],
    timeout=300                   # Per version
)

# Access results
print(result['selected'])         # "version_1", "version_2", etc.
print(result['rationale'])        # Why selected
print(result['versions'])         # All ProcessResult objects
print(result['comparison'])       # Reviewer analysis
```

## Multi-Agent Debate

**Use when:** Complex decisions needing multiple viewpoints

```python
result = run_debate(
    decision_question="Which database?",
    perspectives=[                # Optional
        "security",
        "performance",
        "simplicity"
    ],
    rounds=3,                     # Number of debate rounds
    timeout=180                   # Per perspective
)

# Access results
print(result['synthesis'])        # Final consensus
print(result['confidence'])       # "HIGH", "MEDIUM", "LOW"
print(result['rounds'])           # Each round's results
print(result['positions'])        # History per perspective
```

## Fallback Cascade

**Use when:** Need guaranteed completion with degradation

```python
result = run_cascade(
    task_prompt="Generate documentation",
    fallback_strategy="quality", # quality, service, freshness, completeness, accuracy
    timeout_strategy="balanced", # aggressive, balanced, patient
    notification_level="warning", # silent, warning, explicit
)

# Access results
print(result['cascade_level'])    # "primary", "secondary", "tertiary"
print(result['degradation'])      # Degradation description
print(result['result'])           # Final ProcessResult
print(result['attempts'])         # All attempts
```

## Custom Cascade

**Use when:** Need specific cascade behavior

```python
result = create_custom_cascade(
    task_prompt="Analyze code",
    levels=[
        {
            "name": "comprehensive",
            "timeout": 120,
            "constraint": "full analysis",
            "model": None,        # Optional
        },
        {
            "name": "quick",
            "timeout": 30,
            "constraint": "basic analysis",
        },
        {
            "name": "minimal",
            "timeout": 5,
            "constraint": "syntax check only",
        },
    ],
)
```

## Common Parameters

All patterns support:

| Parameter     | Type   | Default     | Description                       |
| ------------- | ------ | ----------- | --------------------------------- |
| `working_dir` | `Path` | current dir | Working directory                 |
| `model`       | `str`  | None        | Claude model (None = CLI default) |
| `timeout`     | `int`  | None        | Timeout per process (seconds)     |

## Return Structure

All patterns return `Dict[str, Any]` with:

| Key                                 | Type   | Description                 |
| ----------------------------------- | ------ | --------------------------- |
| `session_id`                        | `str`  | Session identifier for logs |
| `success`                           | `bool` | Whether operation succeeded |
| Additional keys specific to pattern |        | See pattern docs            |

## Session Logs

Find logs at: `~/.amplihack/.claude/runtime/logs/<session_id>/`

- `session.log` - Session overview
- `<process_id>.log` - Individual process logs

## Error Handling

All patterns handle errors gracefully:

```python
result = run_n_version(task_prompt="...")
if not result['success']:
    print("Failed:", result['rationale'])
    # Check individual attempts
    for version in result['versions']:
        if version.exit_code != 0:
            print(f"Error: {version.stderr}")
```

## Timeout Strategies

For `run_cascade()`:

| Strategy     | Primary | Secondary | Tertiary |
| ------------ | ------- | --------- | -------- |
| `aggressive` | 5s      | 2s        | 1s       |
| `balanced`   | 30s     | 10s       | 5s       |
| `patient`    | 120s    | 30s       | 10s      |

## Fallback Strategies

For `run_cascade()`:

| Strategy       | Primary       | Secondary   | Tertiary   |
| -------------- | ------------- | ----------- | ---------- |
| `quality`      | comprehensive | standard    | minimal    |
| `service`      | optimal API   | cached      | defaults   |
| `freshness`    | real-time     | recent      | historical |
| `completeness` | full dataset  | sample      | summary    |
| `accuracy`     | precise       | approximate | estimate   |

## Perspective Profiles

For `run_debate()`:

| Perspective       | Focus                       | Questions                   |
| ----------------- | --------------------------- | --------------------------- |
| `security`        | Vulnerabilities, protection | What could go wrong?        |
| `performance`     | Speed, scalability          | Will this scale?            |
| `simplicity`      | Minimal complexity          | Is this the simplest?       |
| `maintainability` | Long-term evolution         | Can future devs understand? |
| `user_experience` | API design, usability       | Is this intuitive?          |

## Diversity Profiles

For `run_n_version()`:

| Profile               | Approach                |
| --------------------- | ----------------------- |
| `conservative`        | Proven patterns, safety |
| `pragmatic`           | Balanced trade-offs     |
| `minimalist`          | Ruthless simplicity     |
| `innovative`          | Novel approaches        |
| `performance_focused` | Speed optimization      |

## Pattern Selection

Quick decision guide:

```
Need multiple implementations?
├─ Yes → N-Version Programming
└─ No
   ├─ Need to make decision?
   │  ├─ Yes → Multi-Agent Debate
   │  └─ No → Continue
   └─ Need guaranteed completion?
      ├─ Yes → Fallback Cascade
      └─ No → Use standard execution
```

## Examples

See `PATTERN_EXAMPLES.py` for complete working examples.

## Full Documentation

See `README.md` for comprehensive documentation.
