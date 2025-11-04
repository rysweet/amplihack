# Feedback Summary Template

Use this template to document session outcomes and learning opportunities.

## Task Summary
[Brief description of what was accomplished]

## Implementation Details
[Key changes made, files created/modified, etc.]

## Feedback Summary

**User Interactions Observed:**
- [Any user corrections, clarifications, or guidance]
- [Expressions of satisfaction or frustration]
- [Requests for different approaches]

**Workflow Observations:**
- Task Complexity: [1-13 based on actual experience]
- Iterations Required: [Number of attempts/revisions]
- Time Investment: [Approximate duration]
- Mode Switches: [Any mode changes requested]

**Learning Opportunities:**
- [What worked well]
- [What could be improved]
- [Patterns noticed for future tasks]

**Recommendations for Improvement:**
- [Specific suggestions for mode enhancements to the root rules that will improve future sessions]
- [Process improvements identified]
- [Tool or automation opportunities]

## Next Steps
[Any follow-up actions or recommendations]

---

**Usage Instructions:**

1. **When to Use:** End of significant sessions (not trivial tasks)
2. **Who Fills It:** Reflection system or manual session review
3. **Where to Save:** `.claude/runtime/logs/<session_id>/feedback_summary.md`
4. **Purpose:** Capture learning opportunities for continuous improvement

**Integration with Reflection:**

This template will be automatically populated by the reflection system during BLOCKING stop hook execution:
- Reflection runs synchronously when session ends
- User sees findings and can interact
- System fills this template with observations
- User can approve GitHub issue creation
- Template saved before stop is allowed
