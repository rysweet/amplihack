---
name: Q&A_WORKFLOW
version: 1.0.0
description: Minimal 3-step workflow for simple questions and informational requests
steps: 3
phases:
  - classification-confirmation
  - response
  - escalation-check
success_criteria:
  - "Question answered clearly"
  - "User satisfied with response"
  - "Escalated to proper workflow if needed"
philosophy_alignment:
  - principle: Ruthless Simplicity
    application: Minimal overhead for simple questions
  - principle: Right-Size Response
    application: Match effort to task complexity
customizable: true
---

# Q&A Workflow

Minimal workflow for simple questions that don't require code changes or exploration.

## When This Workflow Applies

Use Q&A_WORKFLOW when ALL are true:

1. **Single-turn answer**: Can be fully answered in one response
2. **No code changes**: Doesn't require creating/modifying files
3. **Information available**: Answer is in context or general knowledge
4. **No exploration**: Don't need to trace code paths or read many files

### Keywords Suggesting Q&A

- "What is..."
- "Explain briefly..."
- "Quick question..."
- "How do I run..."
- "What does X mean..."

### NOT Q&A (Escalate)

- "Help me understand X" -> INVESTIGATION (needs exploration)
- "What's wrong with this code?" -> INVESTIGATION (needs analysis)
- "Add/Fix/Create X" -> DEFAULT (needs implementation)

## The 3 Steps

### Step 1: Classification Confirmation

- [ ] Confirm this is truly Q&A (not disguised investigation/development)
- [ ] Verify single-response answer is possible
- [ ] Check if answer is available in current context

**If ANY doubt**: Escalate to INVESTIGATION_WORKFLOW or DEFAULT_WORKFLOW

### Step 2: Provide Response

- [ ] Answer directly and clearly
- [ ] Keep response appropriately concise
- [ ] Include code examples if helpful
- [ ] Reference relevant files if applicable

### Step 3: Escalation Check

- [ ] Verify answer fully addresses question
- [ ] Check if follow-up suggests different workflow needed
- [ ] If deeper understanding needed -> Offer INVESTIGATION_WORKFLOW
- [ ] If implementation needed -> Offer DEFAULT_WORKFLOW

## Escalation Examples

**Q&A to INVESTIGATION:**

```
User: "What does the cleanup agent do?"
[Answer provided]
User: "How does it integrate with the other hooks?"
-> "That requires code exploration. Switching to INVESTIGATION_WORKFLOW."
```

**Q&A to DEFAULT:**

```
User: "What's the recommended way to add a command?"
[Answer provided]
User: "Can you add a /status command for me?"
-> "That requires implementation. Switching to DEFAULT_WORKFLOW."
```

## Success Criteria

- Question fully answered
- Response appropriately sized
- Escalated if complexity emerged
