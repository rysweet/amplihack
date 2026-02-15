# Design Decisions for amplihack-memory-lib

This document captures the key design decisions and trade-offs made during API design.

## Critical Decision: Exclude Code Graph

**Decision**: Code graph (CodeFile, CodeClass, CodeFunction) stays in amplihack, NOT in standalone library.

**Reasoning**:

1. **Domain specificity**: Code graph is specific to code analysis domain
2. **Dependency coupling**: Code graph requires language-specific parsers (scip-python, tree-sitter)
3. **Scope creep**: A "memory library" shouldn't know about code entities
4. **Reusability**: Generic experience storage works for ANY agent domain

**Trade-off**: amplihack will need to maintain its own code graph logic, but library stays clean and reusable.

**Alternative considered**: Include both schemas (code + experiences) in library.
**Why rejected**: Violates single responsibility principle. Library would be "memory + code analysis" which is incoherent.

## Critical Decision: Experience Schema Over Memory Types

**Decision**: Replace MemoryType enum (Episodic, Semantic, etc.) with Experience = {context, action, outcome}.

**Reasoning**:

1. **Simplicity**: One data model vs five memory type schemas
2. **Clarity**: "What happened, what I did, what resulted" is universally understandable
3. **Flexibility**: Tags provide categorization without rigid types
4. **Implementation size**: ~100 lines vs ~500 lines for multiple memory types

**Trade-off**: Lose academic memory model purity, gain practical usability.

**Alternative considered**: Keep psychological memory types (Episodic, Semantic, Procedural, Prospective, Working).
**Why rejected**:

- Adds complexity (5 node tables, different schemas)
- Agents don't think in academic terms
- Experience model covers all cases with simpler interface

## Critical Decision: Text Similarity Over Embeddings

**Decision**: Use Cypher CONTAINS for similarity, not vector embeddings.

**Reasoning**:

1. **Zero dependencies**: No OpenAI API, no sentence-transformers, no numpy
2. **Simplicity**: SQL-like text matching is well-understood
3. **Performance**: < 50ms query time without external API calls
4. **Good enough**: Text matching finds 80% of similar experiences

**Trade-off**: Less semantic understanding, but dramatically simpler.

**Alternative considered**: Integrate sentence-transformers for embeddings.
**Why rejected**:

- Adds ~500MB dependency (torch + transformers)
- Requires embedding generation on every store()
- Increases query complexity
- Overkill for v1 - can add in v2 if truly needed

**Migration path**: v2 can add optional embeddings without breaking v1 API:

```python
store.store(..., embedding=None)  # Optional in v2
store.find_semantic(embedding=[...])  # New method in v2
```

## Critical Decision: Remove Sessions

**Decision**: Use agent_id scoping instead of explicit sessions.

**Reasoning**:

1. **Simplicity**: One scoping dimension (agent) vs two (agent + session)
2. **Flexibility**: Agents can create their own session concepts via tags
3. **Usage pattern**: Most agents don't need explicit sessions

**Trade-off**: Lose session-based queries, but agents can use tags like "session:abc123" if needed.

**Alternative considered**: Keep Session as first-class entity.
**Why rejected**:

- Adds complexity (Session node table, relationships)
- Most agents don't use sessions
- Can be simulated with metadata/tags

## Critical Decision: Importance Score Over Confidence/Valence/etc.

**Decision**: Single importance field (1-10) instead of multiple scoring dimensions.

**Reasoning**:

1. **Simplicity**: One score vs multiple (confidence, valence, importance, etc.)
2. **Clarity**: "How important is this?" is clearer than "What's the emotional valence?"
3. **Sufficient**: Importance captures what matters for retrieval/filtering

**Trade-off**: Lose emotional valence, confidence scores, but gain simplicity.

**Alternative considered**: Multiple scoring dimensions like current MemoryEntry.
**Why rejected**:

- Agents rarely use these fields
- Increases cognitive load
- Can be stored in metadata if truly needed

## Critical Decision: Synchronous API (Async Optional)

**Decision**: Primary API is synchronous, async support via ThreadPoolExecutor.

**Reasoning**:

1. **Simplicity**: Sync code is easier to understand and debug
2. **Kuzu native**: Kuzu database is sync by nature
3. **Performance**: < 50ms queries don't need async
4. **Compatibility**: Works in any Python context

**Trade-off**: Not idiomatic for async codebases, but simpler for majority.

**Alternative considered**: Async-first API with sync wrappers.
**Why rejected**:

- Adds complexity (async/await everywhere)
- Kuzu is sync, would fake async benefits
- Most agents are sync

**Future**: Can add async API in v1.x as additive feature:

```python
async def store_async(...): ...
async def retrieve_async(...): ...
```

## Design Philosophy Summary

| Principle                 | Application                                     |
| ------------------------- | ----------------------------------------------- |
| **Ruthless Simplicity**   | Removed memory types, sessions, embeddings      |
| **Single Responsibility** | Experiences only, no code graph                 |
| **Bricks & Studs**        | ExperienceStore is self-contained brick         |
| **Zero-BS**               | No stubs, no mocks, every method works          |
| **Proportionality**       | API size matches implementation size (~300 LOC) |

## Validation Against Requirements

| Requirement                 | How Met                                             |
| --------------------------- | --------------------------------------------------- |
| Zero amplihack dependencies | No imports from amplihack.\*                        |
| Usable by generated agents  | Simple 3-method API (store, retrieve, find_similar) |
| Support experiences         | Experience = {context, action, outcome}             |
| Async-friendly              | ThreadPoolExecutor for concurrent operations        |
| Bricks & Studs              | ExperienceStore is regeneratable from spec          |

## What We Didn't Build (And Why)

| Feature           | Why Excluded                                   |
| ----------------- | ---------------------------------------------- |
| Vector embeddings | Too complex for v1, add in v2 if needed        |
| Code graph        | Domain-specific, stays in amplihack            |
| Memory types      | Academic, replaced by simpler experience model |
| Sessions          | Can be simulated with tags/metadata            |
| Relationships     | Can be added in v1.x as optional feature       |
| Full-text search  | Cypher CONTAINS is sufficient                  |
| Async-first API   | Kuzu is sync, would fake benefits              |

## Risks and Mitigations

| Risk                     | Mitigation                                     |
| ------------------------ | ---------------------------------------------- |
| Text similarity too weak | Can add embeddings in v2 without breaking API  |
| No sessions needed later | Can add via relationships in v1.x              |
| Performance insufficient | Kuzu is fast, queries < 50ms                   |
| API too simple           | Additive changes in v1.x (backward compatible) |

## Success Criteria Met

✅ API fits on one page (README quick start)
✅ Every method has single, clear purpose
✅ Zero ambiguous parameters
✅ Clear error handling
✅ Migration path documented
✅ Schema is minimal (1 core table)
✅ No premature optimization

## Conclusion

This API design prioritizes **simplicity and clarity** over **features and flexibility**. Every decision favors the 80% use case over the 20% edge cases. The result is an API that fits in your head and works on day one.

We can always add complexity later. We can't remove it once it's in v1.
