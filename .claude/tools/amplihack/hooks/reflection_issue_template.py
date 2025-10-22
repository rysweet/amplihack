#!/usr/bin/env python3
"""
GitHub Issue Template Generator for Reflection Patterns

Generates well-formatted GitHub issue titles, bodies, and labels
for different types of improvement patterns detected during reflection.
"""

from typing import Any, Dict


def generate_issue(pattern: Dict[str, Any], session_id: str = "") -> Dict[str, str]:
    """Generate GitHub issue content from a reflection pattern.

    Args:
        pattern: Pattern dictionary from SessionReflector
        session_id: Optional session identifier for linking

    Returns:
        Dictionary with 'title', 'body', and 'labels' keys
    """
    pattern_type = pattern.get("type", "unknown")
    generator = _get_generator_for_type(pattern_type)

    issue_data = generator(pattern, session_id)

    # Add common labels
    base_labels = ["reflection", "improvement"]
    pattern_labels = issue_data.get("labels", [])

    issue_data["labels"] = base_labels + pattern_labels

    return issue_data


def _get_generator_for_type(pattern_type: str):
    """Get the appropriate template generator function for a pattern type."""
    generators = {
        "repeated_tool_use": _generate_repeated_tool_issue,
        "error_patterns": _generate_error_pattern_issue,
        "long_session": _generate_long_session_issue,
        "user_frustration": _generate_frustration_issue,
        "repeated_commands": _generate_repeated_commands_issue,
        "error_retry": _generate_error_retry_issue,
        "repeated_reads": _generate_repeated_reads_issue,
        "automation": _generate_automation_issue,
        "workflow": _generate_workflow_issue,
        "error_handling": _generate_error_handling_issue,
    }

    return generators.get(pattern_type, _generate_generic_issue)


def _generate_repeated_tool_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for repeated tool usage pattern."""
    tool = pattern.get("tool", "unknown")
    count = pattern.get("count", 0)

    title = f"Optimize repeated {tool} usage ({count} occurrences)"

    body = f"""## Pattern Detected

**Type**: Repeated Tool Usage
**Tool**: `{tool}`
**Occurrences**: {count}
**Session**: {session_id or "N/A"}

## Description

The `{tool}` tool was used {count} times in a single session, suggesting a potential opportunity for optimization.

## Suggestion

{pattern.get("suggestion", "Consider creating a reusable script or automation for this pattern.")}

## Action Items

- [ ] Analyze the specific use cases for `{tool}` in session {session_id}
- [ ] Determine if a custom script or tool would be beneficial
- [ ] Implement automation if appropriate
- [ ] Update documentation with the new approach

## Priority

This issue was automatically generated from session reflection analysis.
"""

    labels = ["automation", "tooling", "efficiency"]
    if count >= 10:
        labels.append("high-priority")

    return {"title": title, "body": body, "labels": labels}


def _generate_error_pattern_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for error pattern detection."""
    count = pattern.get("count", 0)
    samples = pattern.get("samples", [])

    title = f"Investigate recurring errors ({count} occurrences)"

    # Format error samples
    samples_text = ""
    if samples:
        samples_text = "\n### Error Samples\n\n"
        for i, sample in enumerate(samples[:3], 1):
            samples_text += f"{i}. `{sample[:150]}...`\n"

    body = f"""## Pattern Detected

**Type**: Error Pattern
**Occurrences**: {count}
**Session**: {session_id or "N/A"}

## Description

Multiple errors were encountered during this session, suggesting a potential systemic issue or missing error handling.

{samples_text}

## Suggestion

{pattern.get("suggestion", "Investigate root cause and add better error handling.")}

## Action Items

- [ ] Review error occurrences in session {session_id}
- [ ] Identify root cause(s)
- [ ] Add appropriate error handling
- [ ] Add tests to prevent regression
- [ ] Update documentation if needed

## Priority

High - Errors impact user experience and system reliability.
"""

    labels = ["bug", "error-handling", "high-priority"]

    return {"title": title, "body": body, "labels": labels}


def _generate_long_session_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for long session pattern."""
    message_count = pattern.get("message_count", 0)

    title = f"Task decomposition opportunity (session: {message_count} messages)"

    body = f"""## Pattern Detected

**Type**: Long Session
**Message Count**: {message_count}
**Session**: {session_id or "N/A"}

## Description

This session was unusually long ({message_count} messages), suggesting that the task could benefit from better decomposition.

## Suggestion

{pattern.get("suggestion", "Consider breaking into smaller, focused tasks.")}

## Action Items

- [ ] Review session {session_id} to understand task complexity
- [ ] Identify natural breakpoints or sub-tasks
- [ ] Create TodoWrite templates for similar complex tasks
- [ ] Document task decomposition best practices

## Benefits

- Clearer progress tracking
- Better context management
- Easier debugging and recovery
- Improved parallel execution opportunities

## Priority

Medium - Improves workflow efficiency and reduces cognitive load.
"""

    labels = ["workflow", "productivity", "task-management"]

    return {"title": title, "body": body, "labels": labels}


def _generate_frustration_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for user frustration pattern."""
    indicators = pattern.get("indicators", 0)

    title = f"User experience issue detected ({indicators} frustration indicators)"

    body = f"""## Pattern Detected

**Type**: User Frustration
**Indicators**: {indicators}
**Session**: {session_id or "N/A"}

## Description

Multiple frustration indicators were detected during this session, suggesting the user encountered difficulties or confusion.

## Suggestion

{pattern.get("suggestion", "Review approach and consider alternative solution.")}

## Action Items

- [ ] **URGENT**: Review session {session_id} to understand user's difficulties
- [ ] Identify specific pain points or blockers
- [ ] Evaluate if architect agent should be consulted for redesign
- [ ] Improve documentation or guidance for similar scenarios
- [ ] Consider adding proactive help or suggestions

## Impact

High - User frustration directly impacts productivity and satisfaction.

## Next Steps

This issue should be prioritized for immediate investigation to prevent similar experiences in the future.
"""

    labels = ["user-experience", "high-priority", "needs-investigation"]

    return {"title": title, "body": body, "labels": labels}


def _generate_repeated_commands_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for repeated commands pattern."""
    title = "Create automation for repeated commands"

    body = f"""## Pattern Detected

**Type**: Repeated Commands
**Session**: {session_id or "N/A"}

## Description

The same commands or actions were repeated multiple times during this session.

## Suggestion

{pattern.get("suggestion", "Consider creating a tool or script for this repeated action.")}

## Action Items

- [ ] Analyze repeated command patterns in session {session_id}
- [ ] Determine if a scenario tool would be appropriate
- [ ] Create script or tool following the Progressive Maturity Model
- [ ] Test in `.claude/ai_working/` before promoting to `.claude/scenarios/`
- [ ] Add Makefile integration when ready

## Priority

Medium - Reduces repetitive work and improves consistency.
"""

    labels = ["automation", "enhancement", "productivity"]

    return {"title": title, "body": body, "labels": labels}


def _generate_error_retry_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for error retry pattern."""
    title = "Improve error handling and retry logic"

    body = f"""## Pattern Detected

**Type**: Error Retry
**Session**: {session_id or "N/A"}

## Description

Multiple retry attempts were needed to complete operations, suggesting missing or inadequate error handling.

## Suggestion

{pattern.get("suggestion", "Investigate root cause and add better error handling.")}

## Action Items

- [ ] Review error retry patterns in session {session_id}
- [ ] Identify which operations need better error handling
- [ ] Add appropriate try/catch blocks and recovery logic
- [ ] Implement exponential backoff where appropriate
- [ ] Add logging for better debugging
- [ ] Create tests for error scenarios

## Priority

High - Better error handling improves reliability and user experience.
"""

    labels = ["error-handling", "reliability", "high-priority"]

    return {"title": title, "body": body, "labels": labels}


def _generate_repeated_reads_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for repeated file reads pattern."""
    title = "Optimize repeated file read operations"

    body = f"""## Pattern Detected

**Type**: Repeated File Reads
**Session**: {session_id or "N/A"}

## Description

The same files were read multiple times during this session, suggesting an opportunity for caching or better data flow.

## Suggestion

{pattern.get("suggestion", "Consider caching or extracting relevant parts once.")}

## Action Items

- [ ] Analyze file read patterns in session {session_id}
- [ ] Identify frequently accessed files
- [ ] Implement caching strategy if appropriate
- [ ] Use more targeted search (Grep) instead of full file reads
- [ ] Extract and pass relevant data between steps

## Benefits

- Reduced I/O operations
- Faster execution
- Better context management

## Priority

Medium - Performance optimization.
"""

    labels = ["performance", "optimization", "efficiency"]

    return {"title": title, "body": body, "labels": labels}


def _generate_automation_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for automation opportunity."""
    title = "Automation opportunity for frequent tool combinations"

    body = f"""## Pattern Detected

**Type**: Automation Opportunity
**Session**: {session_id or "N/A"}

## Description

Frequent tool combinations were detected, suggesting an opportunity for automation.

## Suggestion

{pattern.get("suggestion", "Consider automating frequent tool combinations.")}

## Action Items

- [ ] Analyze tool usage patterns in session {session_id}
- [ ] Identify common tool sequences
- [ ] Create specialized agent or scenario tool
- [ ] Document the automation pattern
- [ ] Add to agent catalog or Makefile

## Priority

Medium - Improves workflow efficiency.
"""

    labels = ["automation", "workflow", "enhancement"]

    return {"title": title, "body": body, "labels": labels}


def _generate_workflow_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for workflow improvement."""
    title = "Streamline workflow to reduce repetitive actions"

    body = f"""## Pattern Detected

**Type**: Workflow Inefficiency
**Session**: {session_id or "N/A"}

## Description

Repetitive actions or rework were detected, suggesting the workflow could be streamlined.

## Suggestion

{pattern.get("suggestion", "Streamline workflow to reduce repetitive actions.")}

## Action Items

- [ ] Review workflow in session {session_id}
- [ ] Identify repetitive steps or rework
- [ ] Update DEFAULT_WORKFLOW.md if needed
- [ ] Create specialized agents for common patterns
- [ ] Document improved workflow

## Priority

Medium - Improves productivity and reduces frustration.
"""

    labels = ["workflow", "productivity", "process-improvement"]

    return {"title": title, "body": body, "labels": labels}


def _generate_error_handling_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate issue for error handling improvement."""
    title = "Improve error handling based on session failures"

    body = f"""## Pattern Detected

**Type**: Error Handling
**Session**: {session_id or "N/A"}

## Description

Errors were encountered during this session, suggesting areas for improved error handling.

## Suggestion

{pattern.get("suggestion", "Improve error handling based on session failures.")}

## Action Items

- [ ] Review error cases in session {session_id}
- [ ] Add better error messages
- [ ] Implement graceful fallbacks
- [ ] Add validation before operations
- [ ] Update tests to cover error cases

## Priority

High - Better error handling improves reliability.
"""

    labels = ["error-handling", "reliability", "enhancement"]

    return {"title": title, "body": body, "labels": labels}


def _generate_generic_issue(pattern: Dict, session_id: str) -> Dict:
    """Generate generic issue for unknown pattern types."""
    pattern_type = pattern.get("type", "unknown")
    title = f"Reflection: {pattern_type.replace('_', ' ').title()}"

    body = f"""## Pattern Detected

**Type**: {pattern_type}
**Session**: {session_id or "N/A"}

## Description

An improvement opportunity was detected during reflection analysis.

## Suggestion

{pattern.get("suggestion", "Review session and determine appropriate action.")}

## Details

```json
{pattern}
```

## Action Items

- [ ] Review session {session_id}
- [ ] Understand the pattern and its implications
- [ ] Determine and implement appropriate improvements
- [ ] Document learnings

## Priority

Medium - Requires investigation to determine priority.
"""

    labels = ["needs-investigation"]

    return {"title": title, "body": body, "labels": labels}


def main():
    """CLI interface for testing template generation."""

    # Example patterns for testing
    test_patterns = [
        {
            "type": "repeated_tool_use",
            "tool": "bash",
            "count": 15,
            "suggestion": "Consider creating a script",
        },
        {
            "type": "error_patterns",
            "count": 5,
            "samples": ["Error: file not found", "Exception: timeout"],
            "suggestion": "Improve error handling",
        },
        {"type": "user_frustration", "indicators": 3, "suggestion": "Review approach"},
    ]

    print("Testing issue template generation:\n")

    for pattern in test_patterns:
        issue = generate_issue(pattern, session_id="20251020_test")
        print(f"Pattern: {pattern['type']}")
        print(f"Title: {issue['title']}")
        print(f"Labels: {', '.join(issue['labels'])}")
        print(f"Body length: {len(issue['body'])} chars")
        print("-" * 70)


if __name__ == "__main__":
    main()
