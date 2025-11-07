"""Learning extraction patterns for agent outputs.

This module contains pattern matchers that extract learnings from agent outputs.
Different patterns are used for different agent types and learning types.

Pattern Types:
- Decision patterns: Extract explicit decisions with reasoning
- Recommendation patterns: Extract best practices and advice
- Anti-pattern patterns: Extract warnings and things to avoid
- Error-solution patterns: Extract problem-solution pairs
- Implementation patterns: Extract code patterns and approaches
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def extract_learnings(
    output: str,
    agent_type: str,
    task_category: str,
) -> List[Dict[str, Any]]:
    """Extract all learnings from agent output using pattern matching.

    Args:
        output: Full agent output text
        agent_type: Type of agent (affects which patterns are used)
        task_category: Task category

    Returns:
        List of learning dictionaries with keys:
        - type: Learning type (decision, recommendation, anti_pattern, etc.)
        - content: Learning content
        - category: Task category
        - confidence: Confidence score (0-1)
        - reasoning: Optional reasoning/context
    """
    learnings = []

    # Apply all pattern extractors
    learnings.extend(_extract_decisions(output, task_category))
    learnings.extend(_extract_recommendations(output, task_category))
    learnings.extend(_extract_anti_patterns(output, task_category))
    learnings.extend(_extract_error_solutions(output, task_category))

    # Agent-specific patterns
    if agent_type in ["builder", "architect"]:
        learnings.extend(_extract_implementation_patterns(output, task_category))

    if agent_type in ["fix-agent", "reviewer", "tester"]:
        learnings.extend(_extract_diagnostic_patterns(output, task_category))

    # Filter out low-quality extractions
    learnings = [l for l in learnings if _is_substantial(l["content"])]

    logger.debug(
        f"Extracted {len(learnings)} learnings from {agent_type} output "
        f"(category: {task_category})"
    )

    return learnings


def _extract_decisions(output: str, category: str) -> List[Dict[str, Any]]:
    """Extract explicit decisions with reasoning.

    Patterns:
    - "## Decision: <title>\n**What**: <what>\n**Why**: <why>"
    - "Decision to <action> because <reason>"
    - "Decided to <action>. Rationale: <reason>"
    """
    learnings = []

    # Pattern 1: Structured decision format (from DECISIONS.md)
    decision_pattern = r"##\s+Decision\s*\d*:?\s*([^\n]+)\n\*\*What\*\*:([^\n]+)\n\*\*Why\*\*:([^\n]+)"
    for match in re.finditer(decision_pattern, output, re.IGNORECASE):
        title = match.group(1).strip()
        what = match.group(2).strip()
        why = match.group(3).strip()

        learnings.append({
            "type": "decision",
            "content": f"{title}: {what}",
            "reasoning": why,
            "category": category,
            "confidence": 0.85,  # High confidence - structured format
        })

    # Pattern 2: Inline decision statements
    inline_pattern = r"(?:Decision|Decided) to ([^.!?\n]{20,}?)(?:\.|because|since) ([^.!?\n]{20,})"
    for match in re.finditer(inline_pattern, output, re.IGNORECASE):
        decision = match.group(1).strip()
        reasoning = match.group(2).strip()

        learnings.append({
            "type": "decision",
            "content": f"Decided to {decision}",
            "reasoning": reasoning,
            "category": category,
            "confidence": 0.75,
        })

    return learnings


def _extract_recommendations(output: str, category: str) -> List[Dict[str, Any]]:
    """Extract recommendations and best practices.

    Patterns:
    - "## Recommendation:\n- <item>"
    - "Best practice: <advice>"
    - "Should always <action>"
    """
    learnings = []

    # Pattern 1: Bulleted recommendations
    rec_section_pattern = r"##\s+(?:Recommendation|Best Practice|Key Points?)s?:?\s*\n((?:[-*]\s+[^\n]+\n?)+)"
    for match in re.finditer(rec_section_pattern, output, re.IGNORECASE):
        items = re.findall(r"[-*]\s+([^\n]+)", match.group(1))
        for item in items:
            if len(item) > 20:  # Substantial content
                learnings.append({
                    "type": "recommendation",
                    "content": item.strip(),
                    "category": category,
                    "confidence": 0.75,
                })

    # Pattern 2: Inline recommendations
    inline_pattern = r"(?:Should always|Always|Recommend|Best practice:?)\s+([^.!?\n]{30,})"
    for match in re.finditer(inline_pattern, output, re.IGNORECASE):
        recommendation = match.group(1).strip()

        learnings.append({
            "type": "recommendation",
            "content": recommendation,
            "category": category,
            "confidence": 0.70,
        })

    return learnings


def _extract_anti_patterns(output: str, category: str) -> List[Dict[str, Any]]:
    """Extract anti-patterns and things to avoid.

    Patterns:
    - "⚠️ Warning: <warning>"
    - "Avoid <thing> because <reason>"
    - "Anti-pattern: <pattern>"
    - "Never <action>"
    """
    learnings = []

    # Pattern 1: Explicit warnings
    warning_pattern = r"(?:⚠️|Warning|Caution|Anti-pattern):?\s+([^\n]{30,})"
    for match in re.finditer(warning_pattern, output, re.IGNORECASE):
        warning = match.group(1).strip()

        learnings.append({
            "type": "anti_pattern",
            "content": warning,
            "category": category,
            "confidence": 0.85,  # High confidence - explicit warnings
        })

    # Pattern 2: Avoid/Never statements
    avoid_pattern = r"(?:Avoid|Never|Don't)\s+([^.!?\n]{30,}?)(?:\.|because) ([^.!?\n]{20,})"
    for match in re.finditer(avoid_pattern, output, re.IGNORECASE):
        action = match.group(1).strip()
        reasoning = match.group(2).strip()

        learnings.append({
            "type": "anti_pattern",
            "content": f"Avoid: {action}",
            "reasoning": reasoning,
            "category": category,
            "confidence": 0.80,
        })

    return learnings


def _extract_error_solutions(output: str, category: str) -> List[Dict[str, Any]]:
    """Extract error-solution pairs.

    Patterns:
    - "Error: <error>\nSolution: <solution>"
    - "Issue: <issue>\nFix: <fix>"
    - "Problem: <problem>\nResolution: <resolution>"
    """
    learnings = []

    # Pattern: Problem-solution pairs
    problem_solution_pattern = r"(?:Error|Issue|Problem|Bug):([^\n]{20,})\n+(?:Solution|Fix|Resolution):([^\n]{20,})"
    for match in re.finditer(problem_solution_pattern, output, re.IGNORECASE):
        problem = match.group(1).strip()
        solution = match.group(2).strip()

        learnings.append({
            "type": "error_solution",
            "content": f"Error: {problem} | Solution: {solution}",
            "category": "error_handling",  # Force category
            "confidence": 0.90,  # High confidence - structured format
        })

    return learnings


def _extract_implementation_patterns(output: str, category: str) -> List[Dict[str, Any]]:
    """Extract implementation patterns (for builder/architect agents).

    Patterns:
    - "Pattern: <pattern>"
    - "Approach: <approach>"
    - "Implementation strategy: <strategy>"
    """
    learnings = []

    # Pattern: Explicit patterns/approaches
    pattern_match = r"(?:Pattern|Approach|Strategy):?\s+([^\n]{30,})"
    for match in re.finditer(pattern_match, output, re.IGNORECASE):
        pattern = match.group(1).strip()

        learnings.append({
            "type": "pattern",
            "content": pattern,
            "category": category,
            "confidence": 0.75,
        })

    return learnings


def _extract_diagnostic_patterns(output: str, category: str) -> List[Dict[str, Any]]:
    """Extract diagnostic patterns (for fix-agent/reviewer/tester).

    Patterns:
    - Root cause analysis
    - Test strategies
    - Common mistakes
    """
    learnings = []

    # Pattern: Root cause findings
    root_cause_pattern = r"(?:Root cause|Cause):?\s+([^\n]{30,})"
    for match in re.finditer(root_cause_pattern, output, re.IGNORECASE):
        cause = match.group(1).strip()

        learnings.append({
            "type": "procedural",
            "content": f"Root cause: {cause}",
            "category": "error_handling",
            "confidence": 0.80,
        })

    # Pattern: Test strategies
    test_strategy_pattern = r"Test strategy:?\s+([^\n]{30,})"
    for match in re.finditer(test_strategy_pattern, output, re.IGNORECASE):
        strategy = match.group(1).strip()

        learnings.append({
            "type": "procedural",
            "content": f"Test strategy: {strategy}",
            "category": "testing",
            "confidence": 0.75,
        })

    return learnings


def _is_substantial(content: str) -> bool:
    """Check if content is substantial enough to store as a learning.

    Args:
        content: Learning content

    Returns:
        True if substantial, False otherwise

    Criteria:
    - At least 20 characters
    - Not just a URL
    - Not just a file path
    - Contains actual words (not just punctuation)
    """
    if len(content) < 20:
        return False

    # Check if it's just a URL
    if content.startswith("http://") or content.startswith("https://"):
        return False

    # Check if it's just a file path
    if "/" in content and content.count("/") > 2:
        return False

    # Check if it has actual words
    words = re.findall(r'\w+', content)
    if len(words) < 5:
        return False

    return True


def assess_learning_quality(learning: Dict[str, Any]) -> float:
    """Assess the quality of an extracted learning.

    Args:
        learning: Learning dictionary

    Returns:
        Quality score (0-1)

    Factors:
    - Has reasoning (+0.2)
    - Has outcome (+0.15)
    - Has concrete examples (+0.1)
    - Is anti-pattern (+0.2)
    - High confidence (+0.1)
    """
    score = 0.5  # Base score

    # Has reasoning/explanation
    if learning.get("reasoning"):
        score += 0.2

    # Has outcome/result
    if learning.get("metadata", {}).get("outcome"):
        score += 0.15

    # Has concrete examples
    content = learning.get("content", "")
    if any(marker in content.lower() for marker in ["example:", "e.g.", "for instance", "such as"]):
        score += 0.1

    # Is anti-pattern (high value)
    if learning.get("type") == "anti_pattern":
        score += 0.2

    # High confidence
    if learning.get("confidence", 0) >= 0.85:
        score += 0.1

    return min(score, 1.0)
