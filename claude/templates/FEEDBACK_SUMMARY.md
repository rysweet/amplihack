# Feedback Summary Template

Use this template to document session outcomes and learning opportunities.

## Task Summary

[Brief description of what was accomplished - 2-3 sentences]

## Implementation Details

[Key changes made, files created/modified, etc. - Be specific with file paths and line numbers when relevant]

## KEY FINDINGS

### What Worked Well

[VERBOSE: List 3-5 specific things that worked effectively. Include:

- Specific tool usage that was effective
- Agent deployments that were successful
- Communication patterns that resonated with user
- Workflow steps that were executed well
  Be detailed and specific with examples from the session]

### Areas for Improvement

[VERBOSE: List 3-5 specific areas that could be improved. Include:

- Specific inefficiencies identified (with message numbers if relevant)
- Tool usage that could be optimized
- Communication patterns that could be clearer
- Workflow adherence issues
- User frustration points or confusion
  Be detailed and specific with examples from the session]

### User Interactions Analysis

- **Corrections & Clarifications:** [List any user corrections with context]
- **Satisfaction Indicators:** [Positive feedback, task completion acknowledgment]
- **Friction Points:** [Moments of user frustration, confusion, or repeated clarification needs]
- **Communication Style Match:** [Did Claude's communication style align with user preferences?]

### Workflow Performance

- **Task Complexity:** [1-13 scale based on actual experience - explain the rating]
- **Iterations Required:** [Number with explanation of why iterations were needed]
- **Time Investment:** [Message count and approximate duration]
- **Workflow Adherence:** [Detailed analysis: Which DEFAULT_WORKFLOW.md steps were followed? Which were skipped? Why?]
- **Subagent Usage:** [Comprehensive list: Which agents were used? Were they used effectively? Which agents should have been used but weren't?]

## RECOMMENDATIONS FOR IMPROVEMENT

### High Priority

[VERBOSE: 2-3 high-impact improvements with:

- Specific problem they address
- Proposed solution with implementation details
- Expected impact
- Difficulty estimate]

### Medium Priority

[VERBOSE: 2-3 moderate-impact improvements following same format]

### Low Priority / Future Enhancements

[1-2 nice-to-have improvements]

## PRESENTATION STRUCTURE

When presenting these findings to the user, organize as follows:

**1. Executive Summary** (2-3 sentences)
[One sentence on what was accomplished, one on key insight]

**2. Key Findings Breakdown**

- Lead with 2-3 most important findings (what worked well + top improvement area)
- Use specific examples from the session
- Be verbose - include context and reasoning

**3. Recommendations Summary**

- Present top 3-5 recommendations in priority order
- For each: Problem → Solution → Impact
- Be verbose - explain WHY each recommendation matters

**4. Action Options**
Present these specific options to the user:

a) **Create GitHub Issues**

- For high-priority recommendations
- Option to work on them NOW or LATER
- List which recommendations warrant issues

b) **Start Auto Mode**

- If there are concrete improvements that can be implemented immediately
- Describe what would be automated

c) **Discuss Specific Improvements**

- If user wants to explore certain recommendations in detail
- List which ones are good candidates for discussion

d) **Just Stop**

- If user is satisfied and wants to end session
- Remind that next stop will succeed (semaphore prevents re-run)

## Next Steps

[Specific, actionable follow-up items with priority]

---

**Usage Instructions:**

1. **When to Use:** End of significant sessions (not trivial tasks)
2. **Who Fills It:** Reflection system or manual session review
3. **Where to Save:** `~/.amplihack/.claude/runtime/logs/<session_id>/feedback_summary.md`
4. **Purpose:** Capture learning opportunities for continuous improvement

**Integration with Reflection:**

This template will be automatically populated by the reflection system during BLOCKING stop hook execution:

- Reflection runs synchronously when session ends
- User sees findings and can interact
- System fills this template with observations
- User can approve GitHub issue creation
- Template saved before stop is allowed
