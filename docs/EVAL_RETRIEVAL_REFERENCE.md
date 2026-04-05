# Eval Retrieval Methods Reference

**Type**: Reference (Information-Oriented)
**Last Updated**: 2026-02-28
**Source Files**:

- `src/amplihack/agents/goal_seeking/learning_agent.py`
- `src/amplihack/eval/long_horizon_memory.py`

## Overview

This reference documents the retrieval methods added to the amplihack evaluation system for improved fact retrieval accuracy. These methods address specific retrieval patterns that standard context-based search misses.

## Retrieval Method Comparison

| Method                     | Use Case              | ID Pattern            | Context Scope  | Multi-Entity | Performance                       |
| -------------------------- | --------------------- | --------------------- | -------------- | ------------ | --------------------------------- |
| `_entity_linked_retrieval` | Structured entity IDs | INC-_, CVE-_, PROJ-\* | All contexts   | No           | O(n×e) where n=facts, e=entities  |
| `_multi_entity_retrieval`  | Multi-hop reasoning   | Named entities        | Per entity     | Yes          | O(n×e×k) where k=facts per entity |
| `_standard_retrieval`      | General questions     | N/A                   | Single context | No           | O(n)                              |

## Entity-Linked Retrieval

### Method Signature

```python
def _entity_linked_retrieval(
    self,
    question: str,
    limit_per_entity: int = 10
) -> list[Fact]:
    """
    Retrieves all facts containing structured entity IDs found in the question.

    Args:
        question: The question text containing entity IDs
        limit_per_entity: Max facts to retrieve per entity ID (default: 10)

    Returns:
        List of deduplicated facts containing the entity IDs

    Entity ID Patterns Supported:
        - INC-YYYY-NNN: Incident identifiers
        - CVE-YYYY-NNNNN: Common Vulnerabilities and Exposures
        - PROJ-NNN: Project identifiers
        - SRV-NNN: Server/service identifiers
    """
```

### Entity ID Patterns

The method recognizes these structured ID formats:

| Pattern          | Description      | Example        | Use Case                    |
| ---------------- | ---------------- | -------------- | --------------------------- |
| `INC-YYYY-NNN`   | Incident reports | INC-2024-089   | Security incidents, outages |
| `CVE-YYYY-NNNNN` | CVE identifiers  | CVE-2024-12345 | Vulnerability tracking      |
| `PROJ-NNN`       | Project codes    | PROJ-456       | Project management          |
| `SRV-NNN`        | Server IDs       | SRV-789        | Infrastructure inventory    |

### Algorithm

```
1. Extract entity IDs from question using regex patterns
2. For each entity ID:
   a. Search memory for facts containing the entity ID text
   b. Search across ALL contexts (not limited to single context)
   c. Retrieve up to limit_per_entity facts
3. Aggregate all retrieved facts
4. Deduplicate based on fact ID
5. Return deduplicated fact list
```

### Example Usage

```python
# Question containing incident ID
question = "What was the root cause of INC-2024-089?"

# Retrieves facts from:
# - incidents context: "INC-2024-089: Authentication service outage..."
# - security_logs context: "INC-2024-089 logged at 14:32..."
# - post_mortems context: "INC-2024-089 post-mortem: Database deadlock..."

facts = agent._entity_linked_retrieval(question)
# Returns ~8-10 facts containing "INC-2024-089" from multiple contexts
```

### Performance Characteristics

- **Time Complexity**: O(n × e) where n = total facts, e = entity IDs
- **Space Complexity**: O(e × k) where k = limit_per_entity
- **Index Requirements**: Text search on fact content
- **Recommended Use**: Questions with 1-3 entity IDs

### When to Use

✅ **Use entity-linked retrieval when:**

- Question contains structured entity IDs
- Facts are distributed across multiple context tags
- Standard retrieval misses related information
- Entity ID is more reliable than semantic similarity

❌ **Don't use when:**

- Question has no structured IDs
- All facts are in a single context
- Entity IDs are ambiguous or non-unique

## Multi-Entity Retrieval

### Method Signature

```python
def _multi_entity_retrieval(
    self,
    question: str,
    min_entities: int = 2,
    facts_per_entity: int = 5
) -> list[Fact]:
    """
    Detects questions with multiple entities and retrieves facts for each independently.

    Args:
        question: The question text
        min_entities: Minimum entities required to trigger this method (default: 2)
        facts_per_entity: Max facts to retrieve per entity (default: 5)

    Returns:
        List of deduplicated facts for all detected entities

    Entity Detection Methods:
        - Quoted terms: "Alpine Lodge"
        - Capitalized phrases: Alpine Lodge Project
        - Named entity patterns: proper nouns, locations
    """
```

### Entity Extraction

The method detects entities using these patterns:

| Pattern Type        | Regex                              | Example             | Priority |
| ------------------- | ---------------------------------- | ------------------- | -------- |
| Quoted terms        | `"([^"]+)"`                        | "Snowfall incident" | High     |
| Capitalized phrases | `[A-Z][a-z]+(?: [A-Z][a-z]+){1,3}` | Alpine Lodge        | Medium   |
| Structured IDs      | Entity ID patterns                 | INC-2024-089        | High     |

### Algorithm

```
1. Extract entities from question:
   a. Extract quoted terms (highest priority)
   b. Extract capitalized multi-word phrases
   c. Extract structured entity IDs
2. Filter to unique entities (deduplicate)
3. If fewer than min_entities detected, return empty list
4. For each entity:
   a. Retrieve top facts_per_entity facts via semantic search
   b. Use entity as query term
5. Aggregate all facts from all entities
6. Deduplicate based on fact ID
7. Return merged fact list
```

### Example Usage

```python
# Multi-entity question
question = "How did the Snowfall incident affect the Alpine Lodge project?"

# Extracts entities:
# 1. "Snowfall incident" (quoted term)
# 2. "Alpine Lodge project" (capitalized phrase)

facts = agent._multi_entity_retrieval(question)

# Returns facts about:
# - Snowfall incident: "Snowfall caused power outage..."
# - Alpine Lodge project: "Alpine Lodge delayed by 2 weeks..."
# - Both: "Alpine Lodge impacted by Snowfall incident"
```

### Performance Characteristics

- **Time Complexity**: O(n × e × k) where n = facts, e = entities, k = facts per entity
- **Space Complexity**: O(e × k)
- **Index Requirements**: Semantic similarity search
- **Recommended Use**: Questions with 2-4 entities

### When to Use

✅ **Use multi-entity retrieval when:**

- Question mentions 2+ distinct entities
- Question asks about relationships or comparisons
- Facts about entities are stored separately
- Need comprehensive coverage for multi-hop reasoning

❌ **Don't use when:**

- Question has only 1 entity
- All facts are about a single topic
- Entities are too generic ("system", "process")

## Retrieval Strategy Selection

### Decision Algorithm

```python
def _select_retrieval_strategy(self, question: str) -> str:
    """
    Selects the most appropriate retrieval strategy for a question.

    Returns: "entity_linked", "multi_entity", or "standard"
    """
    # Priority 1: Structured entity IDs
    entity_ids = self._extract_entity_ids(question)
    if entity_ids:
        return "entity_linked"

    # Priority 2: Multiple named entities
    entities = self._extract_entities(question)
    if len(entities) >= 2:
        return "multi_entity"

    # Priority 3: Standard context-based retrieval
    return "standard"
```

### Strategy Flow Chart

```
┌─────────────────────────────────────────────────────────────┐
│ Question: "What was the impact of INC-2024-089 on PROJ-456?"│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │ Extract Entity IDs      │
                  │ Pattern: INC-*, PROJ-*  │
                  └─────────────────────────┘
                              │
                    Found: INC-2024-089, PROJ-456
                              │
                              ▼
                  ┌─────────────────────────┐
                  │ Use Entity-Linked       │
                  │ Retrieval               │
                  └─────────────────────────┘
                              │
                              ▼
           ┌──────────────────────────────────────┐
           │ Search for "INC-2024-089" (all ctx)  │
           │ Search for "PROJ-456" (all ctx)      │
           └──────────────────────────────────────┘
                              │
                              ▼
                  ┌─────────────────────────┐
                  │ Merge & Deduplicate     │
                  │ Return ~15 facts        │
                  └─────────────────────────┘
```

### Example Selection

| Question                                   | Detected Pattern | Strategy      | Rationale                         |
| ------------------------------------------ | ---------------- | ------------- | --------------------------------- |
| "What was the root cause of INC-2024-089?" | INC-2024-089     | entity_linked | Structured ID detected            |
| "How did Snowfall affect Alpine Lodge?"    | 2 entities       | multi_entity  | Multiple named entities           |
| "What's the project budget?"               | No patterns      | standard      | Generic question                  |
| "Compare CVE-2024-001 and CVE-2024-002"    | 2 CVE IDs        | entity_linked | Structured IDs (not multi-entity) |

## Combined Retrieval Pattern

### Recommended Implementation

```python
def answer_question(self, question: str) -> str:
    """
    Answers a question using intelligent retrieval strategy selection.
    """
    # Step 1: Select primary strategy
    strategy = self._select_retrieval_strategy(question)

    # Step 2: Execute primary retrieval
    if strategy == "entity_linked":
        facts = self._entity_linked_retrieval(question)
    elif strategy == "multi_entity":
        facts = self._multi_entity_retrieval(question)
    else:
        facts = self._standard_retrieval(question)

    # Step 3: If insufficient coverage, try fallback strategies
    if len(facts) < 3:
        if strategy != "entity_linked":
            facts.extend(self._entity_linked_retrieval(question))
        if strategy != "multi_entity":
            facts.extend(self._multi_entity_retrieval(question))
        if strategy != "standard":
            facts.extend(self._standard_retrieval(question))

        facts = self._deduplicate_facts(facts)

    # Step 4: Synthesize answer
    return self._synthesize_with_llm(question, facts)
```

### Fallback Chain

```
Primary Strategy
      │
      ├─ Success (≥3 facts) → Synthesize Answer
      │
      └─ Insufficient (<3 facts)
            │
            ▼
      Try All Other Strategies
            │
            ▼
      Merge & Deduplicate
            │
            ▼
      Synthesize Answer
```

## Deduplication

### Implementation

```python
def _deduplicate_facts(self, facts: list[Fact]) -> list[Fact]:
    """
    Removes duplicate facts based on fact ID or content hash.

    Deduplication keys (in priority order):
    1. fact.id (if available)
    2. hash(fact.content)
    3. (fact.source, fact.timestamp) tuple
    """
    seen = set()
    unique = []

    for fact in facts:
        # Try fact ID first
        if fact.id:
            key = fact.id
        # Fall back to content hash
        else:
            key = hash(fact.content)

        if key not in seen:
            seen.add(key)
            unique.append(fact)

    return unique
```

### Why Deduplication Matters

Multiple retrieval strategies can return the same facts:

```python
# Question: "What's the status of INC-2024-089?"

# Entity-linked retrieval finds:
# - Fact A: "INC-2024-089: Resolved"
# - Fact B: "INC-2024-089: Root cause identified"

# Multi-entity retrieval also finds:
# - Fact A: "INC-2024-089: Resolved" (duplicate!)

# After deduplication:
# - Fact A: "INC-2024-089: Resolved" (kept)
# - Fact B: "INC-2024-089: Root cause identified" (kept)
```

## Performance Tuning

### Recommended Parameters

| Scenario    | Method        | limit_per_entity | facts_per_entity | min_entities |
| ----------- | ------------- | ---------------- | ---------------- | ------------ |
| Low memory  | entity_linked | 5                | 3                | 2            |
| Balanced    | entity_linked | 10               | 5                | 2            |
| High recall | entity_linked | 20               | 10               | 2            |
| Multi-hop   | multi_entity  | N/A              | 8                | 2            |

### Memory vs Accuracy Trade-off

```
Retrieval Limit (facts per entity)
    │
  20│                                    ╔═══ Max Accuracy
    │                              ╔════╝
  15│                        ╔════╝
    │                  ╔════╝
  10│            ╔════╝  ← Sweet Spot (recommended)
    │      ╔════╝
   5│ ╔═══╝  ← Min Viable
    │
    └────────────────────────────────────────────────
     Low                                         High
                Memory Usage / Latency
```

## Error Handling

### Missing Entity Patterns

```python
def _entity_linked_retrieval(self, question: str) -> list[Fact]:
    try:
        entity_ids = self._extract_entity_ids(question)
        if not entity_ids:
            logger.debug("No entity IDs found, returning empty list")
            return []

        facts = []
        for entity_id in entity_ids:
            entity_facts = self.memory.search(query=entity_id, limit=10)
            facts.extend(entity_facts)

        return self._deduplicate_facts(facts)

    except Exception as e:
        logger.error(f"Entity-linked retrieval failed: {e}")
        return []  # Graceful degradation
```

### Ambiguous Entities

```python
def _multi_entity_retrieval(self, question: str) -> list[Fact]:
    entities = self._extract_entities(question)

    # Filter out generic/ambiguous terms
    filtered_entities = [
        e for e in entities
        if not self._is_generic_term(e)
    ]

    if len(filtered_entities) < 2:
        return []

    # Proceed with filtered entities...
```

## Testing

### Unit Test Example

```python
def test_entity_linked_retrieval():
    agent = LearningAgent("test")

    # Learn facts with entity IDs
    agent.learn("INC-2024-089 was caused by database deadlock")
    agent.learn("INC-2024-089 resolved after 2 hours")

    # Question with entity ID
    question = "What caused INC-2024-089?"
    facts = agent._entity_linked_retrieval(question)

    assert len(facts) == 2
    assert all("INC-2024-089" in f.content for f in facts)
```

### Integration Test Example

```python
def test_combined_retrieval_strategy():
    agent = LearningAgent("test")

    # Learn diverse facts
    agent.learn("INC-2024-089: Auth service outage")
    agent.learn("Alpine Lodge project delayed")
    agent.learn("Snowfall incident caused power loss")

    # Multi-entity question with ID
    question = "How did INC-2024-089 affect Alpine Lodge?"

    answer = agent.answer_question(question)

    # Should retrieve facts using entity-linked (INC-*) and multi-entity (Alpine Lodge)
    assert "INC-2024-089" in answer
    assert "Alpine Lodge" in answer or "delayed" in answer
```

## Related Documentation

- [EVAL_GRADING_IMPROVEMENTS.md](./EVAL_GRADING_IMPROVEMENTS.md) - Tutorial on using these methods
- [EVAL_SYSTEM_ARCHITECTURE.md](./EVAL_SYSTEM_ARCHITECTURE.md) - Complete eval system overview
- [learning_agent.py](../src/amplihack/agents/goal_seeking/learning_agent.py) - Source implementation
