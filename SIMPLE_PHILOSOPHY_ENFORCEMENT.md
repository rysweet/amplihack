# Simple Philosophy Enforcement (Hook-Based)

**Philosophy:** No dashboards, no complex tooling - just simple hooks like user_prompt_submit.

---

## THE SIMPLE WAY: Hooks at Key Moments

### Hook 1: `architect_design_submit.py`

**When:** Architect agent completes design spec
**What:** Quick YAGNI check before builder starts
**How:** Inject questions into context

```python
#!/usr/bin/env python3
"""
Hook when architect submits design spec.
Adds philosophy validation questions to context.
"""

def architect_design_submit(design_spec: str) -> dict:
    """Add YAGNI questions to context before implementation."""

    # Simple heuristics - no complex analysis
    red_flags = []

    # Check for future-oriented language
    future_words = ['future', 'might', 'could', 'eventually', 'scalable', 'flexible']
    if any(word in design_spec.lower() for word in future_words):
        red_flags.append("future-oriented")

    # Check for "Phase N" without "Phase N-1" validation
    if 'Phase 2' in design_spec and 'Phase 1 validation' not in design_spec:
        red_flags.append("skipping-validation")

    # Check LOC estimate
    if 'estimated' in design_spec.lower():
        # Parse rough number
        import re
        numbers = re.findall(r'(\d+)\s*(?:lines|LOC)', design_spec, re.I)
        if numbers and int(numbers[0]) > 500:
            red_flags.append("high-complexity")

    if not red_flags:
        return {"decision": "approve"}

    # Inject philosophy questions into context
    questions = """

📋 PHILOSOPHY VALIDATION (Quick Check)

The design shows some patterns worth questioning:
""" + "\n".join(f"- {flag}" for flag in red_flags) + """

Before implementing, please confirm:

1. **Need Evidence:** What proves we need this NOW?
   (User reports? Data showing gaps? Real failures?)

2. **Simpler Alternative:** What's the simplest version that could work?
   (Could we start smaller and grow?)

3. **Wait Cost:** What's the risk of waiting to build this?
   (Can we validate need first?)

If you can answer these, proceed. If not, consider deferring or simplifying.
"""

    return {
        "decision": "block",
        "reason": questions
    }
```

**Result:** Claude sees questions, discusses with user BEFORE coding.

---

### Hook 2: `pre_tool_use.py` Enhancement

**When:** Before ANY file write to src/
**What:** Fast AST check for TODOs, stubs
**How:** Simple regex patterns

```python
#!/usr/bin/env python3
"""
Enhanced pre-tool-use hook with philosophy checks.
"""

def pre_tool_use(tool_name: str, tool_args: dict) -> dict:
    """Quick philosophy check before writing code."""

    # Only check file writes to production code
    if tool_name != "Write":
        return {"decision": "approve"}

    file_path = tool_args.get("file_path", "")
    if "/tests/" in file_path or "/examples/" in file_path:
        return {"decision": "approve"}

    content = tool_args.get("content", "")

    # Fast checks (no AST parsing - just regex)
    violations = []

    # Check 1: TODOs
    if any(marker in content for marker in ['TODO', 'FIXME', 'XXX', 'HACK']):
        # Allow in comments explaining patterns, not action items
        for line in content.split('\n'):
            if any(marker in line for marker in ['TODO:', 'FIXME:', 'XXX:']):
                violations.append("Action item comment found (TODO/FIXME)")

    # Check 2: NotImplementedError
    if 'NotImplementedError' in content:
        violations.append("Stub function (NotImplementedError)")

    # Check 3: Fake data patterns
    fake_patterns = [
        'return [  # fake',
        'return {  # fake',
        'fake_data =',
        'mock_response =',
        'dummy_result =',
    ]
    if any(pattern in content.lower() for pattern in fake_patterns):
        violations.append("Fake data detected")

    # Check 4: Functions with only pass
    if re.search(r'def \w+\([^)]*\):\s*"""[^"]*"""\s*pass\s*$', content, re.MULTILINE):
        violations.append("Empty function (only docstring + pass)")

    if not violations:
        return {"decision": "approve"}

    # Block and show violations
    message = f"""
⚠️ PHILOSOPHY CHECK FAILED

File: {file_path}

Violations found:
""" + "\n".join(f"- {v}" for v in violations) + """

Philosophy: Zero-BS Implementation
- No stubs (NotImplementedError)
- No TODOs (action items must be resolved)
- No fake data (real implementations only)
- No empty functions (every function works)

Please fix these issues before writing the file.
"""

    return {
        "decision": "block",
        "reason": message
    }
```

**Result:** Blocks fake data at write time, not review time.

---

### Hook 3: `post_tool_use.py` Enhancement

**When:** After builder completes implementation
**What:** Count LOC and compare to estimate
**How:** Simple file stats

```python
#!/usr/bin/env python3
"""
Post-tool-use hook - track complexity growth.
"""

import json
from pathlib import Path

def post_tool_use(tool_name: str, tool_args: dict, result: dict) -> dict:
    """Track complexity metrics after code changes."""

    if tool_name not in ["Write", "Edit"]:
        return {"decision": "approve"}

    # Update simple metrics file
    metrics_file = Path(".claude/runtime/simple_metrics.json")

    try:
        if metrics_file.exists():
            metrics = json.loads(metrics_file.read_text())
        else:
            metrics = {"total_loc": 0, "features_added": 0}

        # Count new lines
        if tool_name == "Write":
            content = tool_args.get("content", "")
            new_lines = len([l for l in content.split('\n') if l.strip()])
            metrics["total_loc"] += new_lines

        # Save
        metrics_file.parent.mkdir(parents=True, exist_ok=True)
        metrics_file.write_text(json.dumps(metrics, indent=2))

    except Exception:
        pass  # Don't block on metrics failure

    return {"decision": "approve"}
```

---

## THE SIMPLE PHILOSOPHY CHECK: 3 Questions

Forget complex calculators. Just ask:

### Question 1: Evidence?
"What proves we need this now? (data, users, failures)"

### Question 2: Simpler?
"What's the simplest version that could work?"

### Question 3: Wait?
"What's the risk of building this later instead?"

**If can't answer → Defer**

---

## Implementation: Dead Simple

### Add to Workflow (Step 4)

```markdown
## Step 4: Research and Design

After architect creates design, INJECT THIS into context:

---
**PHILOSOPHY CHECK (3 Questions):**

Before implementing, confirm:

1. Evidence? (What data shows we need this?)
2. Simpler? (What's the minimal version?)
3. Wait risk? (Why not defer until validated?)

If unclear → Ask user
---
```

### Add Single File

`.claude/tools/amplihack/philosophy_check.py` (< 100 lines total)

```python
"""
Simple philosophy validation.
No complex metrics, no dashboards - just questions.
"""

QUESTIONS = """
PHILOSOPHY CHECK (Answer before implementing):

1. Evidence of need? (user reports, data, failures)
2. Simplest version? (minimal that could work)
3. Risk of waiting? (why build now vs later)

Can't answer? → Defer or ask user
"""

def check_design(design_text: str) -> str:
    """Return questions if red flags found, else empty string."""

    red_flags = [
        'future', 'might', 'could', 'phase 2', 'phase 3',
        'scalable', 'flexible', 'extensible'
    ]

    if any(flag in design_text.lower() for flag in red_flags):
        return QUESTIONS

    return ""  # No concerns

def inject_if_needed(context: str, design: str) -> str:
    """Inject questions into context if needed."""
    check = check_design(design)
    if check:
        return context + "\n\n" + check
    return context
```

That's it. 30 lines. No AST parsing, no metrics, no dashboard.

---

## Usage

### In user_prompt_submit hook

```python
# When user submits "implement Phase 2", inject questions:

from philosophy_check import inject_if_needed

new_context = inject_if_needed(
    current_context,
    user_message
)

# Claude sees questions before designing
```

### In architect agent

```markdown
When creating designs, check for:
- "future", "might", "could" → Flag as speculative
- "Phase N" without "Phase N-1 validation" → Flag as premature
- Estimated > 500 LOC → Flag as complex

If flagged → Inject 3 questions
```

---

## Why This Works

**Simple:**
- No complex tools
- No metrics tracking
- No dashboard
- Just questions at right time

**Effective:**
- Catches speculation early
- Forces evidence-based decisions
- User makes final call
- Transparent process

**Maintainable:**
- < 100 lines total
- No dependencies
- Easy to understand
- Easy to modify

---

## Comparison

### Complex Approach (Rejected)
- PhilosophyMetrics class (300 lines)
- ComplexityChecker (200 lines)
- Dashboard generator (150 lines)
- AST parsing
- Database tracking
- **Total: 650+ lines of meta-infrastructure**

### Simple Approach (This)
- 3 questions (3 lines)
- Simple keyword check (20 lines)
- Hook integration (50 lines)
- **Total: 73 lines**

**89% simpler!**

---

## Implementation Plan

1. Add `philosophy_check.py` (30 lines)
2. Update `user_prompt_submit.py` hook (add 10 lines)
3. Update architect agent instructions (add 5 lines)
4. Test with speculative feature request

**Total effort:** 2 hours
**Total code:** < 100 lines
**Effectiveness:** Catches Phase 2-4 type issues early

---

**This embodies ruthless simplicity: minimum code, maximum impact.**
