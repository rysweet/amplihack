# Original Request Preservation

Rules for maintaining fidelity to user intent during context compaction and multi-turn conversations.

---

## The Problem

As conversations grow long:
- Context windows fill up
- Earlier messages get summarized or dropped
- Original user intent can be lost or distorted
- Agent behavior drifts from what user actually wanted

**Result**: Agent solves the wrong problem or makes unwanted changes.

---

## Core Principle

**The original user request is sacred.**

No matter how many turns pass or how much context is compacted, the agent must be able to answer: "What did the user originally ask for?"

---

## Preservation Rules

### Rule 1: Anchor to Original Request

At the start of any multi-step task, explicitly capture the original request:

```markdown
## Original Request
User asked: "Add authentication to the API endpoints using JWT tokens"

## Interpretation
- Add JWT-based auth to existing API
- Protect all endpoints (or specify which)
- Follow existing patterns in codebase
```

### Rule 2: Reference Original in Every Step

Each step should connect back to the original:

```markdown
## Current Step: Implementing token validation middleware

**Connection to original**: This middleware will check JWT tokens on
protected endpoints, fulfilling the "authentication" part of the request.
```

### Rule 3: Preserve, Don't Paraphrase

When summarizing context, keep the original request verbatim:

```markdown
# WRONG - Paraphrasing loses nuance
Original: "Make the API secure"

# RIGHT - Preserve exact words
Original: "Add authentication to the API endpoints using JWT tokens"
```

### Rule 4: Flag Scope Creep

If work starts to extend beyond original request, explicitly flag it:

```markdown
**Note**: Adding refresh token support. This extends beyond the original
request ("JWT tokens") but is standard practice. Proceeding unless you
want basic JWT only.
```

### Rule 5: Verify Before Major Changes

Before any irreversible or significant change, verify alignment:

```markdown
**Verification**: About to modify 15 endpoint files to add auth middleware.
This matches original request: "Add authentication to the API endpoints"
Proceeding with changes.
```

---

## Context Compaction Guidelines

When context must be reduced, follow this priority:

### Must Preserve (Never Remove)

1. **Original user request** - Exact words
2. **Key constraints** - "must use PostgreSQL", "keep backward compatible"
3. **Explicit decisions** - User choices during conversation
4. **Current task status** - What's done, what's pending

### Can Summarize (Keep Essence)

1. **Exploration results** - Summarize findings, keep conclusions
2. **Alternative approaches** - Note what was rejected and why
3. **Technical details** - Keep interface, summarize implementation

### Can Remove (If Needed)

1. **Intermediate reasoning** - Keep conclusion, drop derivation
2. **Verbose output** - Keep summary, drop raw logs
3. **Superseded information** - If user changed direction

---

## Compaction Template

When compacting context, use this structure:

```markdown
# Conversation Summary

## Original Request (PRESERVED VERBATIM)
"[Exact user request from first message]"

## Key Constraints
- [Constraint 1 from user]
- [Constraint 2 from user]

## Decisions Made
1. [Decision]: [Rationale]
2. [Decision]: [Rationale]

## Current Status
- Completed: [List]
- In Progress: [Current task]
- Remaining: [List]

## Important Context
- [Critical information for continuing work]
```

---

## Multi-Turn Conversation Patterns

### Pattern 1: Explicit Anchoring

At start of complex task:

```markdown
I understand you want me to: "Add authentication to the API endpoints using JWT tokens"

I'll break this into steps:
1. [Step 1]
2. [Step 2]
3. [Step 3]

I'll reference this original request as I work. Let me know if I've misunderstood anything.
```

### Pattern 2: Progress Checkpoints

Every few steps:

```markdown
## Progress Update

**Original request**: "Add authentication to the API endpoints using JWT tokens"

**Completed**:
- ✅ Created JWT utility module
- ✅ Added auth middleware

**Current**:
- 🔄 Updating endpoint handlers

**Remaining**:
- ⏳ Adding tests
- ⏳ Updating documentation

Still aligned with original request. Continuing...
```

### Pattern 3: Drift Detection

If direction seems to shift:

```markdown
**Checking alignment**: The current task (adding rate limiting) wasn't in
the original request ("Add authentication using JWT"). 

Options:
1. Complete auth first, then discuss rate limiting
2. Add rate limiting as part of auth work
3. Switch focus to rate limiting

Which would you prefer?
```

---

## Anti-Patterns

### Don't: Let Scope Silently Expand

```markdown
# BAD
User: "Add JWT auth"
Agent: *adds auth, then rate limiting, then logging, then caching...*

# GOOD
User: "Add JWT auth"
Agent: *adds auth*
Agent: "Auth complete. I noticed the API could benefit from rate limiting.
       Want me to add that as a separate task?"
```

### Don't: Lose Original in Technical Details

```markdown
# BAD - Original buried in implementation details
...the RSA key size should be 2048 bits for the JWT signing algorithm
which uses RS256 as specified in RFC 7519 section 3.1...

# GOOD - Original stays visible
## Implementing JWT Signing (for: "Add authentication using JWT tokens")
Using RS256 algorithm with 2048-bit keys...
```

### Don't: Paraphrase Away Precision

```markdown
# BAD - Lost specificity
Original: "Make login faster, it takes 3 seconds"
Compacted: "Improve login performance"

# GOOD - Preserved specificity  
Original: "Make login faster, it takes 3 seconds"
Compacted: "Improve login performance (currently 3s, needs to be faster)"
```

### Don't: Assume Implicit Extension

```markdown
# BAD - Assumed user wanted more
User: "Add dark mode to settings page"
Agent: *adds dark mode to entire app*

# GOOD - Stick to request
User: "Add dark mode to settings page"
Agent: *adds dark mode to settings page only*
Agent: "Dark mode added to settings page. Want me to extend it to the
       rest of the app?"
```

---

## Recovery Procedures

### When Original Request is Unclear

```markdown
I want to make sure I understand correctly. You asked to "[quote request]".

I interpret this as:
- [Interpretation point 1]
- [Interpretation point 2]

Is this correct, or should I adjust my understanding?
```

### When Conversation Has Drifted

```markdown
Let me re-anchor to your original request: "[quote request]"

Current state:
- [What's done]
- [What we're currently doing]
- [How it relates to original]

Are we still on track, or has the goal changed?
```

### When Context Was Lost

```markdown
I notice we may have lost some context. Based on our conversation:

Your original request was: "[best reconstruction]"
Key decisions made: [list]
Current task: [description]

Please correct anything I've misremembered.
```

---

## Checklist for Long Conversations

Every 5-10 turns, verify:

- [ ] Can I state the original request verbatim?
- [ ] Is current work aligned with that request?
- [ ] Have I flagged any scope extensions?
- [ ] Are key constraints still being honored?
- [ ] Would user recognize this as what they asked for?
