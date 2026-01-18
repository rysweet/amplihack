# PM Architect Reference

This document contains detailed algorithms, formulas, patterns, and technical specifications for PM Architect operations.

## Table of Contents

- [Multi-Criteria Scoring Algorithm](#multi-criteria-scoring-algorithm)
- [Complexity Estimation](#complexity-estimation)
- [Dependency Analysis](#dependency-analysis)
- [Coordination Patterns](#coordination-patterns)
- [Autopilot Decision Logic](#autopilot-decision-logic)
- [Learning Algorithms](#learning-algorithms)
- [State File Schemas](#state-file-schemas)

## Multi-Criteria Scoring Algorithm

### Overview

The recommendation engine uses weighted multi-criteria scoring to rank backlog items:

```
Total Score = (P × 0.40) + (B × 0.30) + (E × 0.20) + (G × 0.10)

Where:
  P = Priority Score (0.0-1.0)
  B = Blocking Score (0.0-1.0)
  E = Ease Score (0.0-1.0)
  G = Goal Alignment Score (0.0-1.0)

Final score multiplied by 100 for readability (0-100 scale)
```

### Component Calculations

#### Priority Score (40% weight)

Maps user-set priority to normalized score:

```python
def priority_score(priority: str) -> float:
    return {
        "HIGH": 1.0,
        "MEDIUM": 0.6,
        "LOW": 0.3
    }.get(priority, 0.5)  # Default to 0.5 if unspecified
```

**Rationale**: Priority is highest weight because it reflects user intent. HIGH priority items get maximum score, LOW priority gets 30% to avoid being ignored.

#### Blocking Score (30% weight)

Measures how many other items this item would unblock:

```python
def blocking_score(item: BacklogItem, all_items: List[BacklogItem]) -> float:
    """Calculate blocking impact score."""
    blocking_count = count_items_blocked_by(item, all_items)
    total_items = len(all_items)

    if total_items == 0:
        return 0.0

    # Normalize: if item blocks 30% of backlog, score = 1.0
    max_expected = total_items * 0.3
    return min(blocking_count / max(max_expected, 1), 1.0)
```

**Rationale**: Unblocking work creates velocity. 30% weight balances strategic value of clearing blockers.

#### Ease Score (20% weight)

Inverse of complexity—simpler tasks score higher:

```python
def ease_score(complexity: str) -> float:
    return {
        "simple": 1.0,    # < 2 hours
        "medium": 0.6,    # 2-6 hours
        "complex": 0.3    # > 6 hours
    }.get(complexity, 0.5)
```

**Rationale**: Quick wins build momentum. 20% weight prevents always choosing easiest tasks (balanced with priority).

#### Goal Alignment Score (10% weight)

Measures alignment with project primary goals:

```python
def goal_alignment_score(item: BacklogItem, config: PMConfig) -> float:
    """Calculate business value based on goal alignment."""
    # Start with priority-based value
    base_score = priority_score(item.priority)

    # Check if item text mentions any primary goals
    text = (item.title + " " + item.description).lower()
    goal_matches = 0

    for goal in config.primary_goals:
        goal_words = set(goal.lower().split())
        if any(word in text for word in goal_words):
            goal_matches += 1

    # +10% per matching goal
    bonus = min(goal_matches * 0.1, 0.3)  # Cap at +30%

    # Category adjustments
    category = categorize_item(item)
    if category == "bug":
        bonus += 0.15  # Bugs get priority boost
    elif category == "documentation":
        bonus -= 0.05  # Docs slightly lower

    return min(base_score + bonus, 1.0)
```

**Rationale**: Ensures work aligns with strategic goals. 10% weight keeps it influential without overriding tactical priorities.

### Example Scoring

Given:

- BL-001: "Implement config parser" (HIGH priority, blocks 2 items, medium complexity, matches "config system" goal)

```
P = 1.0 (HIGH)
B = 0.67 (blocks 2 of 10 items = 0.2, normalized to ~0.67 assuming 30% threshold)
E = 0.6 (medium complexity)
G = 0.85 (HIGH=1.0 base, +10% goal match, -5% rounded)

Score = (1.0 × 0.40) + (0.67 × 0.30) + (0.6 × 0.20) + (0.85 × 0.10)
      = 0.40 + 0.20 + 0.12 + 0.085
      = 0.805 × 100
      = 80.5/100
```

### Confidence Scoring

Rate confidence in recommendation (0.0-1.0):

```python
def estimate_confidence(item: BacklogItem) -> float:
    confidence = 0.5  # Neutral baseline

    # Detailed description increases confidence
    if len(item.description) > 100:
        confidence += 0.2
    elif len(item.description) > 50:
        confidence += 0.1

    # Explicit priority (not default MEDIUM)
    if item.priority in ["HIGH", "LOW"]:
        confidence += 0.1

    # Tags provide context
    if item.tags:
        confidence += 0.1

    # Estimated hours explicitly set (not default)
    if item.estimated_hours != 4:  # 4 is default
        confidence += 0.1

    return min(confidence, 1.0)
```

**Usage**: Show confidence to user with recommendations. Low confidence (< 0.6) → ask clarifying questions.

## Complexity Estimation

### Complexity Categories

- **Simple** (< 2 hours): Single function, clear requirements, no integration
- **Medium** (2-6 hours): Multiple functions, some integration, moderate scope
- **Complex** (> 6 hours): Multiple files, significant integration, large scope

### Estimation Algorithm

```python
def estimate_complexity(item: BacklogItem) -> str:
    # Start with estimated hours
    if item.estimated_hours < 2:
        base = "simple"
    elif item.estimated_hours <= 6:
        base = "medium"
    else:
        base = "complex"

    # Check technical signals
    signals = extract_technical_signals(item)
    complexity_count = sum(1 for v in signals.values() if v)

    # Multiple technical areas increase complexity
    if complexity_count >= 3:
        if base == "simple":
            base = "medium"
        elif base == "medium":
            base = "complex"

    return base

def extract_technical_signals(item: BacklogItem) -> dict:
    text = (item.title + " " + item.description).lower()

    return {
        "has_api_changes": any(kw in text for kw in ["api", "endpoint", "route"]),
        "has_db_changes": any(kw in text for kw in ["database", "db", "schema", "migration"]),
        "has_ui_changes": any(kw in text for kw in ["ui", "interface", "frontend", "view"]),
        "mentions_testing": any(kw in text for kw in ["test", "coverage", "verify"]),
        "mentions_security": any(kw in text for kw in ["security", "auth", "permission", "encryption"])
    }
```

### Category Detection

Categorize items to adjust scoring and delegation:

```python
def categorize_item(item: BacklogItem) -> str:
    """Categorize as feature, bug, refactor, doc, test, or other."""
    text = (item.title + " " + item.description).lower()

    KEYWORDS = {
        "bug": {"fix", "bug", "issue", "error", "broken"},
        "test": {"test", "coverage", "verify", "validate"},
        "documentation": {"document", "docs", "readme", "comment", "explain"},
        "refactor": {"refactor", "clean", "improve", "optimize", "restructure"},
        "feature": {"add", "implement", "create", "new", "feature"}
    }

    for category, keywords in KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category

    return "other"
```

## Dependency Analysis

### Dependency Detection

Identify dependencies between backlog items:

```python
def detect_dependencies(item: BacklogItem, all_items: List[BacklogItem]) -> List[str]:
    """Return list of backlog IDs this item depends on."""
    dependencies = []
    text = (item.title + " " + item.description).lower()

    # 1. Explicit ID references (BL-001, BL-002)
    import re
    id_pattern = r'bl-\d{3}'
    matches = re.findall(id_pattern, text, re.IGNORECASE)
    dependencies.extend(m.upper() for m in matches if m.upper() in all_items)

    # 2. Check for blocking relationships in other items
    for other_item in all_items:
        if other_item.id == item.id:
            continue

        other_text = (other_item.title + " " + other_item.description).lower()

        # Does other item mention this item as blocking?
        if item.id.lower() in other_text:
            if any(kw in other_text for kw in ["blocks", "required for", "prerequisite"]):
                if other_item.id not in dependencies:
                    dependencies.append(other_item.id)

    return list(set(dependencies))  # Remove duplicates
```

### Blocking Count

Count how many items this item would unblock:

```python
def count_blocking(item: BacklogItem, all_items: List[BacklogItem]) -> int:
    """Count items that depend on this item."""
    count = 0

    for other_item in all_items:
        if other_item.id == item.id:
            continue

        deps = detect_dependencies(other_item, all_items)
        if item.id in deps:
            count += 1

    return count
```

### Dependency Validation

Before starting work, verify dependencies are met:

```python
def has_unmet_dependencies(item: BacklogItem, all_items: List[BacklogItem]) -> bool:
    """Check if item has dependencies not yet completed."""
    dependencies = detect_dependencies(item, all_items)

    for dep_id in dependencies:
        dep_item = next((i for i in all_items if i.id == dep_id), None)
        if dep_item and dep_item.status != "DONE":
            return True

    return False
```

## Coordination Patterns

### Concurrent Workstream Management (Phase 3)

**Goal**: Manage up to 5 concurrent workstreams safely.

#### Capacity Check

```python
def can_start_workstream(active_count: int, max_concurrent: int = 5) -> tuple[bool, str]:
    """Check if new workstream can be started."""
    if active_count >= max_concurrent:
        return False, f"Maximum {max_concurrent} concurrent workstreams (currently: {active_count})"

    return True, f"Capacity available ({active_count}/{max_concurrent})"
```

#### Conflict Detection

```python
def detect_conflicts(workstreams: List[WorkstreamState], backlog_items: List[BacklogItem]) -> List[dict]:
    """Detect conflicts between active workstreams."""
    conflicts = []

    # Check for dependency conflicts
    for ws in workstreams:
        item = next((i for i in backlog_items if i.id == ws.backlog_id), None)
        if not item:
            continue

        deps = detect_dependencies(item, backlog_items)

        # Check if any dependency is also active
        for other_ws in workstreams:
            if other_ws.id == ws.id:
                continue

            if other_ws.backlog_id in deps:
                conflicts.append({
                    "type": "dependency",
                    "workstream": ws.id,
                    "blocks": other_ws.id,
                    "reason": f"{ws.id} depends on {other_ws.backlog_id} which is in progress"
                })

    return conflicts
```

#### Stall Detection

```python
from datetime import datetime, timedelta

def detect_stalled_workstreams(workstreams: List[WorkstreamState], threshold_hours: int = 2) -> List[dict]:
    """Identify workstreams with no progress for threshold period."""
    stalled = []
    now = datetime.utcnow()

    for ws in workstreams:
        if ws.status != "RUNNING":
            continue

        last_activity = datetime.fromisoformat(ws.last_activity.replace("Z", "+00:00"))
        hours_idle = (now - last_activity).total_seconds() / 3600

        if hours_idle > threshold_hours:
            stalled.append({
                "workstream": ws.id,
                "title": ws.title,
                "idle_hours": round(hours_idle, 1),
                "recommendation": "Investigate or pause"
            })

    return stalled
```

### Resource Allocation

Suggest optimal agent for work based on category:

```python
def suggest_agent(item: BacklogItem) -> str:
    """Suggest best agent for backlog item."""
    category = categorize_item(item)

    AGENT_MAP = {
        "feature": "builder",
        "bug": "builder",  # Builder can fix and test
        "refactor": "optimizer",
        "test": "tester",
        "documentation": "builder"  # Builder handles docs with code
    }

    return AGENT_MAP.get(category, "builder")
```

## Autopilot Decision Logic

### Decision Cycle (Phase 4)

Autonomous PM operation when user grants permission:

```python
def autopilot_cycle(state_manager: PMStateManager, dry_run: bool = True) -> dict:
    """Execute one autopilot decision cycle."""
    decisions = []
    actions = []

    # 1. Check active workstreams
    active = state_manager.get_active_workstreams()
    can_start, reason = state_manager.can_start_workstream()

    # 2. Detect stalled workstreams
    stalled = detect_stalled_workstreams(active)
    for ws in stalled:
        decision = {
            "type": "pause_stalled",
            "workstream": ws["workstream"],
            "reason": f"No activity for {ws['idle_hours']} hours",
            "confidence": 0.8
        }
        decisions.append(decision)

        if not dry_run:
            state_manager.update_workstream(ws["workstream"], status="PAUSED")
            actions.append(decision)

    # 3. Start new work if capacity available
    if can_start:
        recommendations = generate_recommendations(state_manager)

        if recommendations:
            top = recommendations[0]

            # Decision rule: Start if HIGH priority and high confidence
            if top.backlog_item.priority == "HIGH" and top.confidence > 0.7:
                decision = {
                    "type": "start_work",
                    "backlog_id": top.backlog_item.id,
                    "score": top.score,
                    "rationale": top.rationale,
                    "confidence": top.confidence
                }
                decisions.append(decision)

                if not dry_run:
                    agent = suggest_agent(top.backlog_item)
                    ws = state_manager.create_workstream(top.backlog_item.id, agent)
                    actions.append(decision)

    # 4. Complete finished workstreams
    for ws in active:
        # Check if workstream is actually complete
        # (This would integrate with ClaudeProcess to check completion)
        if is_workstream_complete(ws):
            decision = {
                "type": "complete_work",
                "workstream": ws.id,
                "backlog_id": ws.backlog_id,
                "confidence": 0.9
            }
            decisions.append(decision)

            if not dry_run:
                state_manager.complete_workstream(ws.id)
                actions.append(decision)

    return {
        "decisions": decisions,
        "actions": actions if not dry_run else [],
        "dry_run": dry_run
    }
```

### Decision Rules

**Rule 1: Priority Threshold**

- Only auto-start HIGH priority items with confidence > 0.7
- MEDIUM/LOW require explicit user approval

**Rule 2: Capacity Management**

- Never exceed max concurrent workstreams (default: 5)
- Pause stalled workstreams to free capacity

**Rule 3: Dependency Safety**

- Never start work with unmet dependencies
- Complete blocking items first

**Rule 4: Quality Gates**

- Always apply quality checks before marking complete
- Flag quality issues for user review

### Logging Decisions

All autopilot decisions must be logged:

```yaml
# .pm/logs/autopilot_YYYYMMDD_HHMMSS.yaml
timestamp: "2025-11-21T15:30:00Z"
cycle: 42
decisions:
  - type: start_work
    backlog_id: BL-003
    score: 87.5
    rationale: HIGH priority, unblocks 2 items, medium complexity
    confidence: 0.85
    action_taken: true
  - type: pause_stalled
    workstream: ws-005
    reason: No activity for 3.2 hours
    confidence: 0.80
    action_taken: true
summary: Started 1 workstream, paused 1 stalled
```

## Learning Algorithms

### Outcome Tracking (Phase 4)

Learn from completed workstreams to improve recommendations:

```python
def record_outcome(ws: WorkstreamState, success: bool, notes: str):
    """Record workstream outcome for learning."""
    outcome = {
        "workstream_id": ws.id,
        "backlog_id": ws.backlog_id,
        "agent": ws.agent,
        "estimated_hours": ws.backlog_item.estimated_hours,
        "actual_minutes": ws.elapsed_minutes,
        "complexity": estimate_complexity(ws.backlog_item),
        "success": success,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # Append to learning log
    log_path = Path(".pm/logs/outcomes.yaml")
    outcomes = load_yaml(log_path).get("outcomes", [])
    outcomes.append(outcome)
    save_yaml(log_path, {"outcomes": outcomes})
```

### Estimation Improvement

Use historical data to improve estimates:

```python
def improve_estimate(item: BacklogItem, outcomes: List[dict]) -> int:
    """Improve estimate based on historical outcomes."""
    category = categorize_item(item)
    complexity = estimate_complexity(item)

    # Find similar completed items
    similar = [
        o for o in outcomes
        if o["complexity"] == complexity
        and categorize_item_from_id(o["backlog_id"]) == category
        and o["success"]
    ]

    if not similar:
        return item.estimated_hours  # Use original estimate

    # Average actual time for similar items
    avg_minutes = sum(o["actual_minutes"] for o in similar) / len(similar)
    improved_hours = int(avg_minutes / 60) + 1  # Round up

    return improved_hours
```

### Agent Performance

Track agent effectiveness by category:

```python
def analyze_agent_performance(outcomes: List[dict]) -> dict:
    """Analyze which agents perform best for which categories."""
    perf = {}

    for outcome in outcomes:
        agent = outcome["agent"]
        category = categorize_item_from_id(outcome["backlog_id"])
        success = outcome["success"]

        key = f"{agent}:{category}"
        if key not in perf:
            perf[key] = {"successes": 0, "total": 0}

        perf[key]["total"] += 1
        if success:
            perf[key]["successes"] += 1

    # Calculate success rates
    rates = {}
    for key, stats in perf.items():
        agent, category = key.split(":")
        rate = stats["successes"] / stats["total"]
        rates[key] = {
            "agent": agent,
            "category": category,
            "success_rate": round(rate, 2),
            "sample_size": stats["total"]
        }

    return rates
```

## State File Schemas

### Config Schema (config.yaml)

```yaml
project_name: string # Required
project_type: enum # cli-tool, web-service, library, other
primary_goals: list[string] # 3-5 concrete goals
quality_bar: enum # strict, balanced, relaxed
initialized_at: ISO8601 # UTC timestamp with Z suffix
version: string # Schema version (1.0)
```

### Backlog Schema (backlog/items.yaml)

```yaml
items:
  - id: string # BL-XXX format (BL-001, BL-002, ...)
    title: string # Brief title
    description: string # Detailed description
    priority: enum # HIGH, MEDIUM, LOW
    estimated_hours: int # Estimated effort
    status: enum # READY, IN_PROGRESS, DONE, BLOCKED
    created_at: ISO8601 # UTC timestamp with Z suffix
    tags: list[string] # Optional categorization tags
```

### Workstream Schema (workstreams/ws-XXX.yaml)

```yaml
id: string # ws-XXX format (ws-001, ws-002, ...)
backlog_id: string # BL-XXX reference
title: string # Copied from backlog item
status: enum # RUNNING, PAUSED, COMPLETED, FAILED
agent: string # builder, reviewer, tester, etc.
started_at: ISO8601 # UTC timestamp with Z suffix
completed_at: ISO8601 | null # UTC timestamp or null if not complete
process_id: string | null # ClaudeProcess ID if using orchestration
elapsed_minutes: int # Total elapsed time
progress_notes: list[string] # Progress updates
dependencies: list[string] # List of BL-XXX this depends on
last_activity: ISO8601 # Last progress update timestamp
```

### Context Schema (context.yaml)

```yaml
project_name: string # Project name
initialized_at: ISO8601 # When PM initialized
version: string # Schema version
```

## Integration Patterns

### ClaudeProcess Integration

```python
from orchestration.claude_process import ClaudeProcess
from pathlib import Path

def start_workstream_with_process(
    backlog_id: str,
    agent: str,
    delegation_package: dict
) -> WorkstreamState:
    """Start workstream using ClaudeProcess orchestration."""

    # Create process
    process = ClaudeProcess(
        agent_path=f".claude/agents/amplihack/core/{agent}.md",
        context=delegation_package,
        project_root=Path.cwd()
    )

    # Start execution
    process_id = process.start()

    # Create workstream tracking
    ws = state_manager.create_workstream(
        backlog_id=backlog_id,
        agent=agent
    )

    # Link process to workstream
    state_manager.update_workstream(
        ws.id,
        process_id=process_id
    )

    return ws
```

### File Utility Integration

Use resilient file operations:

```python
from session.file_utils import retry_file_operation, FileOperationError

@retry_file_operation(max_retries=3, delay=0.1)
def save_state(path: Path, data: dict):
    """Save state with retries."""
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
```

## Performance Considerations

### Token Efficiency

- **SKILL.md**: ~2,500 tokens (main guidance)
- **REFERENCE.md**: ~4,000 tokens (this file, loaded as needed)
- **EXAMPLES.md**: ~2,000 tokens (loaded as needed)
- **Scripts**: External Python, no token cost until executed

Total pre-load: ~50 tokens (YAML frontmatter only)

### File I/O Optimization

- Batch reads when possible
- Use Read → Edit → Write pattern for updates
- Avoid re-reading unchanged files
- Cache config in memory during operation

### Recommendation Generation

- Only score READY items (skip IN_PROGRESS, DONE, BLOCKED)
- Skip items with unmet dependencies early
- Limit to top N recommendations (default: 3)
- Cache complexity estimates for session

## Error Handling

### Common Error Cases

1. **PM Not Initialized**: Return helpful error with initialization instructions
2. **Backlog Item Not Found**: Suggest listing backlog or checking ID
3. **Workstream Capacity Full**: Explain limit and suggest pausing stalled
4. **Unmet Dependencies**: List blocking items and their status
5. **Invalid YAML**: Catch parse errors, suggest schema validation

### Recovery Strategies

```python
def safe_load_backlog(state_manager: PMStateManager) -> List[BacklogItem]:
    """Load backlog with error recovery."""
    try:
        return state_manager.get_backlog_items()
    except FileNotFoundError:
        # Backlog file missing - create empty
        state_manager._write_yaml(
            state_manager.pm_dir / "backlog" / "items.yaml",
            {"items": []}
        )
        return []
    except yaml.YAMLError as e:
        # Invalid YAML - report and suggest fix
        raise ValueError(f"Backlog file corrupted: {e}. Check .pm/backlog/items.yaml")
```

## Philosophy Compliance

### Ruthless Simplicity

- File-based state (no database)
- YAML for human readability
- Simple scoring formulas
- Standard library only (Python)

### Single Responsibility

- PM Architect: coordination and prioritization
- Coding agents: implementation
- ClaudeProcess: orchestration
- Scripts: complex calculations

### Zero-BS Implementation

- All formulas are working (no stubs)
- All state files are valid YAML
- All recommendations have clear rationale
- All decisions are logged

### Trust in Emergence

- User controls when to delegate
- User approves autonomous actions
- PM suggests, user directs
- Learning adapts to outcomes

---

This reference provides complete technical specifications for PM Architect operations. Use it when you need detailed algorithm logic, precise scoring formulas, or implementation patterns.
