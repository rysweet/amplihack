"""Pattern-based request classifier for auto-ultrathink feature.

Analyzes user prompts to determine if they would benefit from UltraThink orchestration.
Returns classification with confidence score and reasoning.
"""

import re
import sys
from dataclasses import dataclass
from typing import Optional


@dataclass
class Classification:
    """Result of request classification."""

    needs_ultrathink: bool
    confidence: float  # 0.0 to 1.0
    reason: str
    matched_patterns: list[str]


# Compile regex patterns at module load for performance
SLASH_COMMAND_PATTERN = re.compile(r"^/")

# Trigger patterns - these suggest UltraThink would be helpful
TRIGGER_PATTERNS = [
    {
        "name": "multi_file_feature",
        "keywords": ["add feature", "implement", "create system", "build"],
        "indicators": ["API", "database", "frontend", "backend", "auth", "payment"],
        "base_confidence": 0.90,
        "reason": "Multi-file feature implementation",
    },
    {
        "name": "refactoring",
        "keywords": ["refactor", "redesign", "restructure", "reorganize"],
        "indicators": ["module", "layer", "architecture"],
        "base_confidence": 0.85,
        "reason": "Refactoring or redesign task",
    },
    {
        "name": "complex_bug_fix",
        "keywords": ["fix", "resolve", "debug"],
        "indicators": ["CI", "test", "async", "race condition", "multiple"],
        "base_confidence": 0.80,
        "reason": "Complex bug fix",
    },
    {
        "name": "testing_implementation",
        "keywords": ["test", "coverage", "TDD", "test-driven"],
        "indicators": ["implement", "add", "create"],
        "base_confidence": 0.85,
        "reason": "Testing and implementation",
    },
    {
        "name": "documentation_code",
        "keywords": ["document", "add docs", "documentation"],
        "indicators": ["implement", "API", "README"],
        "base_confidence": 0.80,
        "reason": "Documentation and code changes",
    },
]

# Skip patterns - these suggest UltraThink is NOT needed
SKIP_PATTERNS = [
    {
        "name": "slash_command",
        "regex": r"^/",
        "base_confidence": 0.99,
        "reason": "Existing slash command",
    },
    {
        "name": "question",
        "keywords": ["what", "how", "why", "explain", "tell me"],
        "base_confidence": 0.95,
        "reason": "Informational question",
    },
    {
        "name": "simple_edit",
        "keywords": ["change", "update"],
        "negative_indicators": ["multiple", "all", "refactor", "restructure"],
        "base_confidence": 0.90,
        "reason": "Simple edit operation",
    },
    {
        "name": "read_operation",
        "keywords": ["show", "display", "read", "list", "find", "view"],
        "base_confidence": 0.95,
        "reason": "Read-only operation",
    },
]


def classify_request(prompt: str) -> Classification:
    """
    Classify whether a user prompt needs UltraThink orchestration.

    Args:
        prompt: Raw user input string

    Returns:
        Classification with confidence score and reasoning

    Raises:
        Never raises - returns safe default on errors
    """
    try:
        # Handle None or invalid input
        if prompt is None:
            return Classification(
                needs_ultrathink=False,
                confidence=0.0,
                reason="Classification failed: invalid input (None)",
                matched_patterns=[],
            )

        # Handle non-string input
        if not isinstance(prompt, str):
            return Classification(
                needs_ultrathink=False,
                confidence=0.0,
                reason="Classification failed: invalid input type",
                matched_patterns=[],
            )

        # Quick checks for early exit
        prompt_stripped = prompt.strip()

        # Empty or whitespace-only prompt
        if not prompt_stripped:
            return Classification(
                needs_ultrathink=False,
                confidence=0.95,
                reason="Empty or whitespace-only prompt",
                matched_patterns=["empty_prompt"],
            )

        # Slash command
        if SLASH_COMMAND_PATTERN.match(prompt_stripped):
            return Classification(
                needs_ultrathink=False,
                confidence=0.99,
                reason="Existing slash command",
                matched_patterns=["slash_command"],
            )

        # Convert to lowercase for case-insensitive matching
        prompt_lower = prompt.lower()

        # Check skip patterns first (fail-fast)
        skip_result = _check_skip_patterns(prompt_lower, prompt)
        if skip_result:
            return skip_result

        # Check trigger patterns
        trigger_result = _check_trigger_patterns(prompt_lower, prompt)
        if trigger_result:
            return trigger_result

        # Check for very short prompts (only if no other pattern matched)
        word_count = len(prompt_stripped.split())
        if word_count < 3:
            return Classification(
                needs_ultrathink=False,
                confidence=0.85,
                reason="Very short prompt",
                matched_patterns=["short_prompt"],
            )

        # Default: no strong match, skip
        return Classification(
            needs_ultrathink=False,
            confidence=0.70,
            reason="No strong pattern match detected",
            matched_patterns=[],
        )

    except Exception as e:
        # Log error to stderr
        print(f"Classification error: {e}", file=sys.stderr)

        # Return safe default (fail-open)
        return Classification(
            needs_ultrathink=False,
            confidence=0.0,
            reason=f"Classification failed: {type(e).__name__}",
            matched_patterns=[],
        )


def _check_skip_patterns(prompt_lower: str, original_prompt: str) -> Optional[Classification]:
    """Check if prompt matches any skip patterns."""
    matched_patterns = []
    max_confidence = 0.0
    best_reason = ""

    for pattern in SKIP_PATTERNS:
        # Check regex pattern if present
        if "regex" in pattern:
            if re.search(pattern["regex"], original_prompt, re.IGNORECASE):
                matched_patterns.append(pattern["name"])
                if pattern["base_confidence"] > max_confidence:
                    max_confidence = pattern["base_confidence"]
                    best_reason = pattern["reason"]
                continue

        # Check keywords (match individual words in multi-word keywords)
        if "keywords" in pattern:
            keyword_matched = False
            for keyword in pattern["keywords"]:
                # Split multi-word keywords and check if any word matches
                keyword_words = keyword.split()
                for word in keyword_words:
                    if re.search(r'\b' + re.escape(word) + r'\b', prompt_lower):
                        keyword_matched = True
                        break
                if keyword_matched:
                    break

            if keyword_matched:
                # Check negative indicators
                if "negative_indicators" in pattern:
                    has_negative = False
                    for neg_indicator in pattern["negative_indicators"]:
                        if re.search(r'\b' + re.escape(neg_indicator) + r'\b', prompt_lower):
                            has_negative = True
                            break
                    if has_negative:
                        continue  # Skip this pattern if negative indicator found

                matched_patterns.append(pattern["name"])
                if pattern["base_confidence"] > max_confidence:
                    max_confidence = pattern["base_confidence"]
                    best_reason = pattern["reason"]

    # If we have skip patterns matched, return skip classification
    if matched_patterns:
        return Classification(
            needs_ultrathink=False,
            confidence=max_confidence,
            reason=best_reason,
            matched_patterns=matched_patterns,
        )

    return None


def _check_trigger_patterns(prompt_lower: str, original_prompt: str) -> Optional[Classification]:
    """Check if prompt matches any trigger patterns."""
    matched_patterns = []
    confidence_scores = []

    for pattern in TRIGGER_PATTERNS:
        # Check if any keyword matches (match individual words in multi-word keywords)
        keyword_matched = False
        for keyword in pattern["keywords"]:
            # Split multi-word keywords and check if any word matches
            keyword_words = keyword.split()
            for word in keyword_words:
                if re.search(r'\b' + re.escape(word) + r'\b', prompt_lower):
                    keyword_matched = True
                    break
            if keyword_matched:
                break

        if not keyword_matched:
            continue

        # Count indicator matches for confidence boosting
        indicator_count = 0
        for indicator in pattern["indicators"]:
            if re.search(r'\b' + re.escape(indicator.lower()) + r'\b', prompt_lower):
                indicator_count += 1

        # If we have keyword + at least one indicator, it's a match
        if indicator_count > 0:
            matched_patterns.append(pattern["name"])

            # Calculate confidence with boost for multiple indicators
            confidence = pattern["base_confidence"]
            if indicator_count > 1:
                confidence = min(0.98, confidence + (indicator_count - 1) * 0.03)

            confidence_scores.append(confidence)

    # If we have trigger patterns matched, return trigger classification
    if matched_patterns:
        # Use maximum confidence score
        max_confidence = max(confidence_scores)

        # Cap confidence at 0.98 (never 1.0)
        max_confidence = min(0.98, max_confidence)

        # Get reason from first matched pattern
        first_pattern_name = matched_patterns[0]
        reason = next(
            (p["reason"] for p in TRIGGER_PATTERNS if p["name"] == first_pattern_name),
            "Multi-step task detected",
        )

        return Classification(
            needs_ultrathink=True,
            confidence=max_confidence,
            reason=reason,
            matched_patterns=matched_patterns,
        )

    return None
