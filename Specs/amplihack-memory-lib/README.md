# amplihack-memory-lib API Specification

**Version**: 1.0.0
**Status**: Design Complete
**Purpose**: Standalone graph-based memory library for autonomous agents

## Overview

This specification defines a **minimal, standalone memory library** extracted from amplihack.memory.kuzu. The library provides persistent graph-based memory storage for goal-seeking agents with zero amplihack dependencies.

## Key Design Decisions

### 1. Single Responsibility: Agent Experiences ONLY

**In scope**: Agent memory (experiences, learnings, outcomes)
**Out of scope**: Code graph indexing (stays in amplihack)

**Why**: A standalone library should be domain-agnostic. Code graph is domain-specific and belongs in the application that uses it, not in a general-purpose memory library.

### 2. Experience-Centric Schema

**New schema**:

- Experience = {context, action, outcome, timestamp, agent_id}
- Simple, clear, applicable to any agent domain

**Replaces**:

- Complex memory types (Episodic, Semantic, Procedural, etc.)
- Code-specific entities (CodeFile, CodeClass, CodeFunction)

**Why**: Experiences are universal. Every agent has context, takes actions, and observes outcomes. This works for code analysis agents, chatbots, robotics, etc.

### 3. Text Similarity, Not Embeddings

**Choice**: Cypher CONTAINS for text similarity
**Not chosen**: Vector embeddings (OpenAI, sentence-transformers)

**Why**:

- Zero dependencies (no external models)
- Fast enough (< 50ms)
- Good enough for 80% of use cases
- Can add embeddings in v2 if truly needed

### 4. Ruthless Simplicity

**What we included**:

- 1 core node type (Experience)
- 3 core methods (store, retrieve, find_similar)
- 5 required fields (context, action, outcome, agent_id, timestamp)

**What we rejected**:

- Sessions (use agent_id scoping instead)
- Memory types (use tags instead)
- Hierarchical memories (use relationships later if needed)
- Complex querying (use QueryBuilder helpers)

**Why**: Start minimal. Every abstraction must justify its existence. Users can build complexity on top of simple primitives.

## Files in This Specification

### [API.md](./API.md)

Complete API specification with:

- Class definitions and method signatures
- Error handling patterns
- Basic usage examples
- Design rationale

### [SCHEMA.md](./SCHEMA.md)

Database schema design:

- Experience node structure
- Optional relationship tables
- Query patterns and performance
- Comparison with current amplihack schema

### [EXAMPLES.md](./EXAMPLES.md)

Common usage scenarios:

- Basic agent memory
- Context manager patterns
- Learning from experiences
- Multi-agent coordination
- Error handling
- Migration guide

### [VERSIONING.md](./VERSIONING.md)

Version strategy:

- v1 stability commitment
- Backward compatibility policy
- Deprecation process
- Future v2 considerations

## Quick Start

```python
from amplihack_memory import MemoryConnector, ExperienceStore

# Initialize
with MemoryConnector("./memory.db") as conn:
    store = ExperienceStore(conn)

    # Store experience
    store.store(
        agent_id="agent_01",
        context="User requested code analysis",
        action="Analyzed src/ directory structure",
        outcome="Found 142 Python files, identified 2 test gaps",
        importance=7
    )

    # Find similar experiences
    similar = store.find_similar(
        agent_id="agent_01",
        context="User requested analysis"
    )
```

## Core Principles

### Bricks & Studs Philosophy

**Brick**: ExperienceStore is a self-contained module
**Stud**: Public API (store, retrieve, find_similar) is the contract
**Regeneratable**: Can rebuild implementation from this spec

### Zero-BS Implementation

- No stubs or placeholders
- No fake data or mock services
- Every method works or doesn't exist
- Clear, actionable errors

### Ruthless Simplicity

- Every class, method, field must justify existence
- Complexity is guilty until proven necessary
- Prefer explicit over clever
- Documentation IS the specification

## Migration from amplihack.memory.kuzu

### What Changes

**API simplification**:

- `KuzuConnector` → `MemoryConnector` (renamed for clarity)
- `KuzuBackend` → `ExperienceStore` (experience-centric)
- `MemoryEntry` → `Experience` (simpler model)

**Schema changes**:

- Code graph moved out (stays in amplihack)
- Memory types replaced by tags
- Sessions replaced by agent_id scoping

### Migration Path

1. **Phase 1**: Build amplihack-memory-lib separately
2. **Phase 2**: New agents use standalone library
3. **Phase 3**: Gradual migration of existing agents
4. **Phase 4**: Deprecate old amplihack.memory.kuzu (6+ months)

### Backward Compatibility

**Not compatible**: This is a new library, not a version bump

**Reason**: Breaking changes required:

- Different schema (experiences vs memory types)
- Different API surface (simplified)
- Different philosophy (domain-agnostic)

**Coexistence**: Both libraries can coexist during migration:

- amplihack.memory.kuzu: Used by existing amplihack code
- amplihack-memory-lib: Used by new standalone agents

## Review Checklist

When reviewing this specification, check for:

- [ ] Unnecessary complexity that can be removed
- [ ] Methods that don't justify their existence
- [ ] Inconsistent patterns needing standardization
- [ ] Missing error handling
- [ ] Unclear documentation
- [ ] Premature optimization or versioning

## Anti-Patterns Avoided

✅ **No over-engineering**: Rejected complex memory type hierarchies
✅ **No premature features**: Embeddings deferred to v2 if needed
✅ **No ambiguity**: Every method has single, clear purpose
✅ **No inconsistency**: All methods follow same patterns
✅ **No hidden complexity**: Schema is visible and documented

## Success Metrics

**How we measure success**:

1. Generated agents can use API without human help
2. Zero confusion about method purposes
3. < 10 minutes from reading docs to working code
4. < 50ms average query performance
5. Zero breaking changes in v1.x releases

## Next Steps

### Implementation Phase

1. **Create repo**: `amplihack-memory-lib` as standalone package
2. **Implement core**: MemoryConnector, ExperienceStore, Experience
3. **Write tests**: Comprehensive test coverage (≥90%)
4. **Document**: README, examples, API reference
5. **Publish**: PyPI package for easy installation

### Integration Phase

1. **Prototype agent**: Build one agent using new library
2. **Gather feedback**: Does API work as expected?
3. **Iterate**: Fix issues found in real usage
4. **Stabilize**: Lock v1.0 API (no more changes)

### Migration Phase

1. **Coexistence**: Both libraries available
2. **New code**: Use amplihack-memory-lib by default
3. **Migration guide**: Help existing agents migrate
4. **Deprecation**: Announce timeline for old library
5. **Sunset**: Remove old library after 6+ months

## Questions and Answers

### Why not just improve amplihack.memory.kuzu?

Because it has amplihack dependencies and code-specific schema. A standalone library must be dependency-free and domain-agnostic.

### Why remove memory types (Episodic, Semantic, etc.)?

They're academic concepts that add complexity without proportional value. Tags provide equivalent functionality with more flexibility.

### Why not support code graph in this library?

Code graph is domain-specific. This library is for general agent memory. Mixing concerns leads to bloat and coupling.

### What about backward compatibility?

This is a NEW library, not a version bump. Old code continues to use amplihack.memory.kuzu. Migration is gradual and optional.

### When will embeddings be supported?

In v2, IF usage shows text similarity isn't sufficient. Don't add features speculatively.

## Conclusion

This specification defines a **minimal viable memory library** for autonomous agents. Every design decision favors simplicity over features, clarity over cleverness, and utility over elegance.

The API is a promise. We will not break it lightly.

---

**Specification Authors**: API Designer Agent
**Date**: 2026-02-14
**Review Status**: Pending Review
