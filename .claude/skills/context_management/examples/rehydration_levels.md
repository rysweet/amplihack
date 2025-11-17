# Rehydration Level Guide

Comprehensive guide for choosing the right detail level when restoring context.

## Three Levels Overview

| Level         | Token Cost | Contains                  | Use When             |
| ------------- | ---------- | ------------------------- | -------------------- |
| Essential     | ~200       | Requirements + State      | Quick refresh needed |
| Standard      | ~800       | + Decisions + Open Items  | Normal restoration   |
| Comprehensive | ~1250      | + Full Details + Metadata | Need everything      |

## Level 1: Essential

### What's Included

- Original user requirements
- Current implementation state

### What's NOT Included

- Key decisions and rationales
- Open items and questions
- Tools used
- Metadata

### When to Use

1. **Quick refresh after short break**
   - "What was I working on?"
   - Just need the basics to remember context

2. **Starting point after compaction**
   - Get essentials first
   - Upgrade later if needed

3. **Token budget is tight**
   - Already high token usage
   - Only need minimal context

4. **Continuing straightforward work**
   - Implementation is clear
   - No complex decisions needed

### Example Output

```markdown
# Restored Context: auth-feature

_Snapshot created: 2025-11-16 14:35:22_

## Original Requirements

Build a JWT authentication system for API endpoints with user login,
token generation, and validation. Support refresh tokens.

## Current State

Tools invoked: 8
Files modified: jwt_handler.py, middleware.py, auth_service.py
```

### Code Example

```python
from context_management import rehydrate_context

# Quick refresh - just need the basics
context = rehydrate_context(
    snapshot_id='20251116_143522',
    level='essential'
)

print(context['context'])
# Output: Requirements + State (~200 tokens)
```

## Level 2: Standard (Recommended)

### What's Included

- Original user requirements
- Current implementation state
- Key decisions and rationales
- Open items and blockers

### What's NOT Included

- Full decision details with alternatives
- Complete tool usage list
- Metadata and timestamps

### When to Use

1. **Normal context restoration** (Most common)
   - Default choice for most situations
   - Balanced token cost vs information

2. **Need to understand decisions made**
   - Why we chose approach X?
   - What trade-offs were considered?

3. **Have open questions or blockers**
   - Need to know what's pending
   - Want to see blockers

4. **Resuming work after compaction**
   - Good balance of context
   - Usually sufficient for continuation

### Example Output

```markdown
# Restored Context: auth-feature

_Snapshot created: 2025-11-16 14:35:22_

## Original Requirements

Build a JWT authentication system for API endpoints with user login,
token generation, and validation. Support refresh tokens.

## Current State

Tools invoked: 8
Files modified: jwt_handler.py, middleware.py, auth_service.py

## Key Decisions

1. Use RS256 encryption instead of HS256
   - Rationale: Better security for distributed systems

2. 15-minute token expiry with refresh tokens
   - Rationale: Balance between security and UX

## Open Items

- Implement refresh token rotation
- Add error handling for expired tokens
- Decide on token storage strategy
```

### Code Example

```python
from context_management import rehydrate_context

# Standard restoration - most common choice
context = rehydrate_context(
    snapshot_id='20251116_143522',
    level='standard'
)

print(context['context'])
# Output: Requirements + State + Decisions + Open Items (~800 tokens)
```

## Level 3: Comprehensive

### What's Included

- Original user requirements
- Current implementation state
- Full key decisions with:
  - What was decided
  - Why (rationale)
  - Alternatives considered
- Open items and questions
- Complete tools used list
- Metadata (timestamp, token count)

### When to Use

1. **Complex debugging needed**
   - Need full context for diagnosis
   - Want to see all decisions and tools

2. **Team handoffs**
   - Transferring work to another developer
   - Need complete picture

3. **After long break**
   - Haven't worked on this in days/weeks
   - Need to fully rebuild mental model

4. **Critical decision point**
   - Making architectural changes
   - Need full history to decide

5. **Documentation or review**
   - Writing docs about the work
   - Explaining implementation to others

### Example Output

```markdown
# Restored Context: auth-feature

_Snapshot created: 2025-11-16 14:35:22_
_Estimated tokens: 1250_

## Original Requirements

Build a JWT authentication system for API endpoints with user login,
token generation, and validation. Support refresh tokens.

## Current State

Tools invoked: 8
Files modified: jwt_handler.py, middleware.py, auth_service.py

## Key Decisions

### Decision 1

**What:** Use RS256 asymmetric encryption
**Why:** Better security for distributed systems, public key verification
**Alternatives:** HS256 (symmetric), ES256 (elliptic curve)

### Decision 2

**What:** 15-minute access token expiry with refresh tokens
**Why:** Balance between security (short-lived) and UX (not constant re-auth)
**Alternatives:** 1-hour expiry, 5-minute expiry, no expiry

## Open Items & Questions

- Implement refresh token rotation (security requirement)
- Add error handling for expired tokens
- Decide on token storage strategy (Redis vs database?)
- How to handle token revocation?

## Tools Used

- Write
- Edit
- Read
- Bash
```

### Code Example

```python
from context_management import rehydrate_context

# Comprehensive - need everything
context = rehydrate_context(
    snapshot_id='20251116_143522',
    level='comprehensive'
)

print(context['context'])
# Output: Everything (~1250 tokens)
```

## Decision Flow

```
Need context?
│
├─ Just checking what task was? → Essential
├─ Resuming normal work? → Standard
├─ Need full picture? → Comprehensive
│
├─ Token budget tight? → Essential, upgrade if needed
├─ Not sure? → Start with Standard
└─ Team handoff or documentation? → Comprehensive
```

## Progressive Upgrade Pattern

Start minimal, upgrade as needed:

```python
from context_management import rehydrate_context

snapshot_id = '20251116_143522'

# Phase 1: Start essential
context = rehydrate_context(snapshot_id, level='essential')
# "Hmm, I need to know why we chose RS256..."

# Phase 2: Upgrade to standard
context = rehydrate_context(snapshot_id, level='standard')
# "Now I see the decision, but need more details..."

# Phase 3: Get comprehensive
context = rehydrate_context(snapshot_id, level='comprehensive')
# "Perfect, now I have everything"
```

## Token Cost Comparison

### Scenario: Same Snapshot, Different Levels

```python
snapshot_id = '20251116_143522'

# Essential: ~200 tokens
essential = rehydrate_context(snapshot_id, level='essential')
print(f"Essential tokens: ~200")

# Standard: ~800 tokens (4x essential)
standard = rehydrate_context(snapshot_id, level='standard')
print(f"Standard tokens: ~800 (4x essential)")

# Comprehensive: ~1250 tokens (6x essential, 1.5x standard)
comprehensive = rehydrate_context(snapshot_id, level='comprehensive')
print(f"Comprehensive tokens: ~1250 (6x essential)")
```

### Token Budget Planning

If you have 900,000 tokens used and need context:

```python
# Current usage: 900k / 1M (90%)
# Remaining: 100k tokens

# Essential: 200 tokens → 90.02% after restoration
# Safe choice, leaves room for work

# Standard: 800 tokens → 90.08% after restoration
# Acceptable, still has breathing room

# Comprehensive: 1250 tokens → 90.125% after restoration
# Risky, approaching limit again
```

## Use Case Examples

### Use Case 1: Quick Task Continuation

**Scenario:** Working on feature, took lunch break, coming back

**Level:** Essential

**Why:** Just need to remember what I was doing, task is straightforward

```python
context = rehydrate_context(snapshot_id, level='essential')
# Quick refresh, back to work
```

### Use Case 2: After Weekend

**Scenario:** Haven't worked on project since Friday, need to resume Monday

**Level:** Standard

**Why:** Need to rebuild mental model, remember decisions and open items

```python
context = rehydrate_context(snapshot_id, level='standard')
# Good context refresh for new week
```

### Use Case 3: Debugging Complex Issue

**Scenario:** Production bug, need to understand all implementation details

**Level:** Comprehensive

**Why:** Need complete picture including all decisions and tools used

```python
context = rehydrate_context(snapshot_id, level='comprehensive')
# Full context for debugging
```

### Use Case 4: Code Review Prep

**Scenario:** Need to explain implementation to reviewer

**Level:** Comprehensive

**Why:** Reviewer needs full context including rationales and alternatives

```python
context = rehydrate_context(snapshot_id, level='comprehensive')
# Complete picture for review
```

### Use Case 5: Token Budget Crisis

**Scenario:** Already at 950k tokens, need some context

**Level:** Essential

**Why:** Can't afford more tokens, get minimum needed

```python
context = rehydrate_context(snapshot_id, level='essential')
# Minimal tokens, essential info only
```

## Common Patterns

### Pattern 1: Start Small, Grow

```python
# Always start with essential
context = rehydrate_context(snapshot_id, level='essential')

# Work with that...
# If need more, upgrade to standard
if need_decisions:
    context = rehydrate_context(snapshot_id, level='standard')

# Still need more? Go comprehensive
if need_everything:
    context = rehydrate_context(snapshot_id, level='comprehensive')
```

### Pattern 2: Match Use Case

```python
def choose_level(use_case):
    """Helper to choose appropriate level."""
    if use_case in ['quick_refresh', 'short_break']:
        return 'essential'
    elif use_case in ['normal_work', 'resume_session', 'after_compaction']:
        return 'standard'
    elif use_case in ['debugging', 'handoff', 'review', 'long_break']:
        return 'comprehensive'
    else:
        return 'standard'  # Default

level = choose_level('debugging')
context = rehydrate_context(snapshot_id, level=level)
```

### Pattern 3: Token Budget Aware

```python
def safe_rehydrate(snapshot_id, current_tokens, max_tokens=1_000_000):
    """Choose level based on available token budget."""
    remaining = max_tokens - current_tokens

    if remaining > 50_000:
        # Plenty of room, use standard
        return rehydrate_context(snapshot_id, level='standard')
    elif remaining > 10_000:
        # Some room, use essential
        return rehydrate_context(snapshot_id, level='essential')
    else:
        # Very tight, warn user
        print("Warning: Token budget very tight!")
        return rehydrate_context(snapshot_id, level='essential')

context = safe_rehydrate(snapshot_id, current_tokens=950_000)
```

## Summary

- **Essential (200 tokens)**: Quick refresh, tight budget, simple tasks
- **Standard (800 tokens)**: Default choice, normal work, balanced context
- **Comprehensive (1250 tokens)**: Full picture, debugging, handoffs, reviews

**Default recommendation: Start with `standard`, adjust as needed.**

## Next Steps

- See `basic_usage.md` for code examples
- See `proactive_workflow.md` for workflow patterns
- See `SKILL.md` for complete documentation
