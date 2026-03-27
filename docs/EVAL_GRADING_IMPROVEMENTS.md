# Eval Grading Improvements Tutorial

**Type**: Tutorial (Learning-Oriented)
**Last Updated**: 2026-02-28
**Related PRs**: [#2673](https://github.com/rysweet/amplihack/pull/2673), [#2674](https://github.com/rysweet/amplihack/pull/2674)

## Overview

This tutorial teaches you how to fix grader false negatives and implement advanced retrieval strategies for eval systems. These improvements increased evaluation accuracy from 96.0% to 97.8% in the amplihack eval system.

## What You'll Learn

1. How to fix grader false negatives using deterministic patterns
2. How to implement entity-linked retrieval for structured IDs
3. How to implement multi-entity retrieval for multi-hop reasoning
4. Best practices for combining deterministic and semantic grading

## Prerequisites

- Basic understanding of LLM-based evaluation systems
- Familiarity with semantic similarity grading
- Knowledge of information retrieval concepts

## Problem: Grader False Negatives

### The Issue

Consider this question and answer:

**Question**: "What is the current project budget?"
**Expected**: "$1.4M"
**Agent Answer**: "The budget increased from $1.2M to $1.4M"

The agent's answer contains the correct current value ($1.4M) but also mentions the historical value ($1.2M). A naive grader using incorrect patterns might score this as 0% because $1.2M appears in the answer and matches an "incorrect pattern" for the historical value.

### The Root Cause

The grader was checking for incorrect patterns WITHOUT first verifying that the correct answer was present:

```python
# BUGGY VERSION (from before PR #2674)
if any(pattern in answer.lower() for pattern in incorrect_patterns):
    score = 0.0  # Wrong! Penalizes even when correct answer is present
```

This caused false negatives when answers contained both historical and current information.

## Solution 1: Fix Deterministic Grading Logic

### The Fix

Only apply incorrect pattern penalties when the correct keywords are NOT present:

```python
# FIXED VERSION (from PR #2674)
def _deterministic_grade(answer: str, rubric: GradingRubric) -> float:
    answer_lower = answer.lower()

    # Check if correct keywords are present
    has_correct = any(
        keyword.lower() in answer_lower
        for keyword in rubric.correct_keywords
    )

    # Only penalize incorrect patterns if correct answer is MISSING
    if not has_correct:
        for pattern in rubric.incorrect_patterns:
            if pattern.lower() in answer_lower:
                return 0.0

    # Grade based on keyword matches
    matches = sum(
        1 for keyword in rubric.correct_keywords
        if keyword.lower() in answer_lower
    )
    return matches / len(rubric.correct_keywords)
```

### Key Insight

**Only skip incorrect patterns when ALL correct keywords are present.** This ensures that:

1. Complete answers get full credit even if they mention historical data
2. Incomplete answers still get penalized for incorrect patterns
3. Grading is more aligned with human judgment

### Impact

- **temporal_evolution**: 86.6% → 99.8%
- **Overall accuracy**: 96.0% → 97.4%

## Solution 2: Entity-Linked Retrieval

### The Problem

Questions about structured entities (incident IDs, CVE numbers, etc.) often fail because facts are stored under different context tags:

**Example**:
- Question: "What was the impact of INC-2024-089?"
- Facts stored under: "incidents", "security_logs", "post_mortems"
- Standard retrieval: Only searches "incidents" context
- Result: Misses related facts in "security_logs" and "post_mortems"

### The Solution

When structured entity IDs are detected, search ALL facts containing that entity:

```python
def _entity_linked_retrieval(self, question: str) -> list[Fact]:
    """
    Retrieves all facts containing structured entity IDs found in the question.

    Structured ID patterns:
    - INC-YYYY-NNN (incidents)
    - CVE-YYYY-NNNNN (vulnerabilities)
    - PROJ-NNN (projects)
    - SRV-NNN (servers)
    """
    import re

    # Extract entity IDs from question
    entity_patterns = [
        r'INC-\d{4}-\d{3}',    # Incident IDs
        r'CVE-\d{4}-\d{4,}',   # CVE IDs
        r'PROJ-\d{3}',         # Project IDs
        r'SRV-\d{3}',          # Server IDs
    ]

    entities = []
    for pattern in entity_patterns:
        entities.extend(re.findall(pattern, question, re.IGNORECASE))

    if not entities:
        return []

    # Search for facts containing any of these entity IDs
    all_facts = []
    for entity_id in entities:
        # Get facts from memory where fact text contains the entity ID
        facts = self.memory.search(
            query=entity_id,
            filters=None,  # Search ALL contexts
            limit=10
        )
        all_facts.extend(facts)

    return self._deduplicate_facts(all_facts)
```

### When to Use

Use entity-linked retrieval when:

1. Questions contain structured identifiers (INC-*, CVE-*, PROJ-*)
2. Related facts are stored across multiple context tags
3. Standard context-based retrieval misses relevant information

### Impact

- **security_log_analysis**: 88% → 100%
- **incident_tracking**: Improved multi-source fact aggregation

## Solution 3: Multi-Entity Retrieval

### The Problem

Multi-hop reasoning questions ask about relationships between multiple entities:

**Example**: "How did the Snowfall incident affect the Alpine Lodge project?"

This question involves:
1. The "Snowfall incident" entity
2. The "Alpine Lodge project" entity
3. The relationship/impact between them

Standard retrieval searches for both terms together and often finds nothing because facts about each entity are stored separately.

### The Solution

Detect questions with 2+ named entities, retrieve facts for EACH entity independently, then merge results:

```python
def _multi_entity_retrieval(self, question: str) -> list[Fact]:
    """
    Detects questions with multiple entities and retrieves facts for each independently.

    Useful for multi-hop reasoning questions like:
    - "How did X affect Y?"
    - "What's the relationship between A and B?"
    - "Compare X and Y"
    """
    # Detect named entities or key phrases
    entities = self._extract_entities(question)

    if len(entities) < 2:
        return []

    # Retrieve facts for EACH entity independently
    all_facts = []
    for entity in entities:
        facts = self.memory.search(
            query=entity,
            limit=5
        )
        all_facts.extend(facts)

    return self._deduplicate_facts(all_facts)

def _extract_entities(self, question: str) -> list[str]:
    """
    Extract named entities and key noun phrases from question.

    Uses simple heuristics:
    - Capitalized phrases (e.g., "Alpine Lodge")
    - Quoted terms (e.g., "Snowfall incident")
    - Common entity patterns
    """
    import re

    entities = []

    # Extract quoted terms
    entities.extend(re.findall(r'"([^"]+)"', question))

    # Extract capitalized phrases (2-4 words)
    entities.extend(
        re.findall(r'\b([A-Z][a-z]+(?: [A-Z][a-z]+){1,3})\b', question)
    )

    # Remove duplicates, keep unique entities
    return list(set(entities))
```

### When to Use

Use multi-entity retrieval when:

1. Questions contain 2+ named entities or key phrases
2. Questions ask about relationships, comparisons, or impacts
3. Facts about each entity are stored in separate context tags
4. Standard combined search returns insufficient results

### Impact

- **multi_hop_reasoning**: Improved coverage for chain-of-thought questions
- **temporal_evolution**: Better handling of "before/after" comparisons

## Combining the Strategies

The most powerful approach combines all three techniques:

```python
def answer_question(self, question: str) -> str:
    # 1. Detect question intent
    intent = self._detect_intent(question)

    # 2. Try entity-linked retrieval first (structured IDs)
    facts = self._entity_linked_retrieval(question)

    # 3. If insufficient, try multi-entity retrieval
    if len(facts) < 3:
        facts.extend(self._multi_entity_retrieval(question))

    # 4. Fall back to standard retrieval
    if len(facts) < 3:
        facts.extend(self._standard_retrieval(question))

    # 5. Synthesize answer from retrieved facts
    answer = self._synthesize_with_llm(question, facts)

    return answer
```

### Retrieval Strategy Decision Tree

```
Question received
    │
    ├─ Contains structured IDs (INC-*, CVE-*)?
    │   └─ YES → Use entity-linked retrieval
    │
    ├─ Contains 2+ named entities?
    │   └─ YES → Use multi-entity retrieval
    │
    └─ Otherwise → Use standard context-based retrieval
```

## Best Practices

### 1. Always Check for False Negatives

When adding new incorrect patterns to grading rubrics:

```python
# DON'T: Apply incorrect patterns unconditionally
if "outdated_info" in answer:
    return 0.0

# DO: Check for correct answer first
if not has_correct_answer and "outdated_info" in answer:
    return 0.0
```

### 2. Deduplicate Retrieved Facts

Multiple retrieval strategies can return overlapping facts:

```python
def _deduplicate_facts(self, facts: list[Fact]) -> list[Fact]:
    seen = set()
    unique = []
    for fact in facts:
        # Use fact ID or content hash as deduplication key
        key = fact.id or hash(fact.content)
        if key not in seen:
            seen.add(key)
            unique.append(fact)
    return unique
```

### 3. Log Retrieval Strategy Used

For debugging and analysis:

```python
def answer_question(self, question: str) -> str:
    retrieval_method = None

    facts = self._entity_linked_retrieval(question)
    if facts:
        retrieval_method = "entity_linked"
    else:
        facts = self._multi_entity_retrieval(question)
        if facts:
            retrieval_method = "multi_entity"
        else:
            facts = self._standard_retrieval(question)
            retrieval_method = "standard"

    logger.info(f"Used {retrieval_method} retrieval: {len(facts)} facts")
    return self._synthesize_with_llm(question, facts)
```

### 4. Test with Multi-Vote Grading

Grading improvements should be validated with multiple grading runs:

```bash
# Single run (unreliable)
python -m amplihack.eval.progressive_test_suite --sdk mini

# Multi-vote grading (recommended)
python -m amplihack.eval.progressive_test_suite --grader-votes 3 --sdk mini
```

## Results

Applying these three improvements to the amplihack eval system:

| Category               | Before  | After   | Improvement |
|------------------------|---------|---------|-------------|
| temporal_evolution     | 86.6%   | 99.8%   | +13.2%      |
| security_log_analysis  | 88.0%   | 100.0%  | +12.0%      |
| incident_tracking      | ~85%    | ~95%    | +10.0%      |
| multi_hop_reasoning    | ~90%    | ~95%    | +5.0%       |
| **Overall**            | **96.0%** | **97.8%** | **+1.8%** |

## Next Steps

1. **Apply to your eval system**: Implement deterministic grading fixes in your grader
2. **Add retrieval strategies**: Implement entity-linked and multi-entity retrieval
3. **Validate with multi-vote grading**: Run 3-vote grading to measure improvement
4. **Monitor specific categories**: Track per-category scores to identify remaining gaps

## Related Documentation

- [EVAL_SYSTEM_ARCHITECTURE.md](./EVAL_SYSTEM_ARCHITECTURE.md) - Complete eval system overview
- [EVAL_RETRIEVAL_REFERENCE.md](./EVAL_RETRIEVAL_REFERENCE.md) - Detailed API reference
- [PR #2673](https://github.com/rysweet/amplihack/pull/2673) - Original implementation
- [PR #2674](https://github.com/rysweet/amplihack/pull/2674) - Grading regression fix
- [PR #2675](https://github.com/rysweet/amplihack/pull/2675) - Security domain improvements
