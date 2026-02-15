# Versioning Strategy for amplihack-memory-lib

## Version Philosophy

**Stability over features**: Stay on v1 as long as possible. Only v2 when breaking changes are unavoidable.

**Additive changes**: Prefer adding optional parameters and methods over breaking existing APIs.

**Clear contracts**: API is a promise. Breaking it damages trust.

## Version 1.0 (Current)

### Scope

**Core API**:

- MemoryConnector: Connection management
- ExperienceStore: Storage and retrieval
- Experience: Data model
- ExperienceStats: Statistics model
- QueryBuilder: Helper utilities

**Database Schema**:

- Experience node table
- Agent node table (optional)
- Basic indexes (agent_id, timestamp, importance)

### Stability Guarantees

**Stable (will NOT change)**:

- ExperienceStore.store() parameters
- ExperienceStore.retrieve() parameters
- Experience dataclass fields
- Error class hierarchy

**May add optional parameters** (backward compatible):

- ExperienceStore methods can gain new optional kwargs
- QueryBuilder can gain new helper methods
- MemoryConnector can gain connection options

**May change** (not part of public API):

- Internal implementation details
- Database query optimization
- Schema indexes (transparent to users)

## Version 1.x (Minor Releases)

### v1.1 - Experience Sequences (Optional)

**Add without breaking**:

```python
class ExperienceStore:
    def link_sequence(self, exp_id1: str, exp_id2: str) -> None:
        """Link two experiences as sequence (optional)."""

    def get_sequence(self, exp_id: str) -> list[Experience]:
        """Get experience sequence starting from exp_id."""
```

**Schema addition**:

```cypher
CREATE REL TABLE IF NOT EXISTS FOLLOWED_BY (
    FROM Experience TO Experience,
    time_delta INT64
)
```

**Backward compatible**: Existing code continues to work. New feature is opt-in.

### v1.2 - Bulk Operations (Optional)

**Add without breaking**:

```python
class ExperienceStore:
    def store_batch(self, experiences: list[dict]) -> list[str]:
        """Store multiple experiences in single transaction."""
```

**Backward compatible**: Existing store() method unchanged.

### v1.3 - Advanced Querying (Optional)

**Add without breaking**:

```python
class ExperienceStore:
    def search(
        self,
        agent_id: str,
        filters: dict[str, Any],  # Flexible filter dict
        sort_by: str = "timestamp",
        limit: int = 10
    ) -> list[Experience]:
        """Advanced search with flexible filters."""
```

**Backward compatible**: Existing retrieve() and find_similar() unchanged.

## Version 2.0 (Future - Breaking Changes Only)

### When to Release v2

**Only when absolutely necessary**:

1. Fundamental schema change required (e.g., switching from Kuzu to different DB)
2. Security issue requiring API redesign
3. Performance bottleneck requiring incompatible changes
4. User feedback indicating v1 API is fundamentally wrong

**NOT valid reasons for v2**:

- "It would be nice to rename this"
- "We could make this slightly more elegant"
- "I have a better idea now"

### Potential v2 Changes (If Needed)

**Example: Vector embeddings support**

```python
class ExperienceStore:
    def store(
        self,
        agent_id: str,
        context: str,
        action: str,
        outcome: str,
        embedding: list[float] | None = None,  # NEW
        ...
    ) -> str:
        """Store with optional embedding for semantic search."""

    def find_semantic(
        self,
        agent_id: str,
        query_embedding: list[float],  # NEW
        limit: int = 5
    ) -> list[Experience]:
        """Semantic similarity search via embeddings."""
```

**Breaking changes**:

- find_similar() might change behavior (use embeddings if available)
- Schema adds embedding column

**Migration path**:

```python
# v1 code (no embeddings)
store.find_similar(agent_id, context="...")

# v2 code (optional embeddings)
store.find_similar(agent_id, context="...")  # Still works, uses text
store.find_semantic(agent_id, embedding=[...])  # New capability
```

## Deprecation Policy

### How to Deprecate

1. **Announce**: Add deprecation warning to method docstring
2. **Warn**: Log warning when deprecated method is called
3. **Wait**: Minimum 6 months before removal
4. **Remove**: Only in next major version

**Example**:

```python
# v1.2
def old_method(self):
    """DEPRECATED: Use new_method() instead.

    This method will be removed in v2.0.
    """
    warnings.warn(
        "old_method() is deprecated, use new_method()",
        DeprecationWarning,
        stacklevel=2
    )
    return self.new_method()
```

### Migration Guide Template

````markdown
# Migration from v1.x to v2.0

## Breaking Changes

### 1. Method Renamed: old_method → new_method

**v1.x**:

```python
store.old_method()
```
````

**v2.0**:

```python
store.new_method()
```

**Migration script**:

```bash
# Automated find/replace
find . -name "*.py" -exec sed -i 's/old_method/new_method/g' {} +
```

## New Features

### Vector Embeddings Support

...

````

## Semantic Versioning Rules

**MAJOR.MINOR.PATCH** (e.g., 1.2.3)

### MAJOR (Breaking changes)
- Incompatible API changes
- Schema changes requiring migration
- Removed deprecated methods

**Example**: 1.9.5 → 2.0.0

### MINOR (New features)
- New methods added
- New optional parameters
- Schema additions (non-breaking)

**Example**: 1.2.5 → 1.3.0

### PATCH (Bug fixes)
- Bug fixes only
- Documentation updates
- Performance improvements (no API change)

**Example**: 1.2.3 → 1.2.4

## Release Process

### Pre-release Checklist

**For MAJOR releases**:
- [ ] All deprecated methods removed
- [ ] Migration guide complete with examples
- [ ] Breaking changes documented
- [ ] Test suite passes
- [ ] Performance benchmarks run
- [ ] User notification sent (email, blog post)

**For MINOR releases**:
- [ ] New features documented
- [ ] Test coverage ≥ 90%
- [ ] Backward compatibility verified
- [ ] CHANGELOG.md updated

**For PATCH releases**:
- [ ] Bug fix verified
- [ ] No API changes
- [ ] Quick smoke tests pass

### Version Tag Format

```bash
# Git tags
v1.0.0     # Initial release
v1.1.0     # Minor feature
v1.1.1     # Bug fix
v2.0.0     # Major breaking change

# Python package
amplihack-memory-lib==1.0.0
amplihack-memory-lib>=1.0.0,<2.0.0  # Compatible with v1.x
````

## Backward Compatibility Testing

### Compatibility Test Suite

```python
# tests/test_backward_compatibility.py

def test_v1_0_store_signature():
    """Ensure v1.0 store() signature still works."""
    store.store(
        agent_id="test",
        context="test",
        action="test",
        outcome="test"
    )

def test_v1_0_retrieve_signature():
    """Ensure v1.0 retrieve() signature still works."""
    store.retrieve(agent_id="test", limit=10)

def test_v1_1_new_features_optional():
    """Ensure v1.1 features are optional."""
    # Should work without using v1.1 features
    pass
```

### Compatibility Matrix

| Library Version | Python 3.9 | Python 3.10 | Python 3.11 | Python 3.12 |
| --------------- | ---------- | ----------- | ----------- | ----------- |
| 1.0.x           | ✓          | ✓           | ✓           | ✓           |
| 1.1.x           | ✓          | ✓           | ✓           | ✓           |
| 1.2.x           | ✗          | ✓           | ✓           | ✓           |
| 2.0.x           | ✗          | ✗           | ✓           | ✓           |

**Support policy**: Support last 3 minor versions of Python.

## Communication Strategy

### Release Notes Template

```markdown
# amplihack-memory-lib v1.2.0

Released: 2024-03-15

## New Features

- Bulk operations support (#42)
- Performance improvements for large databases (#45)

## Bug Fixes

- Fixed race condition in concurrent writes (#41)
- Corrected timestamp timezone handling (#43)

## Deprecations

None

## Breaking Changes

None

## Migration

No migration required - fully backward compatible with v1.x.

## Contributors

Thanks to @user1, @user2 for contributions.
```

### Deprecation Announcement Template

````markdown
# Deprecation Notice: old_method()

**Effective**: v1.3.0 (2024-04-01)
**Removal**: v2.0.0 (2025-04-01)

## What's Deprecated

`ExperienceStore.old_method()` is deprecated in favor of `new_method()`.

## Why

[Explanation of why the change is needed]

## Migration

**Before**:

```python
store.old_method(param1, param2)
```
````

**After**:

```python
store.new_method(param1, param2, new_param=default)
```

## Timeline

- **Now**: Start using new_method() in new code
- **v1.3.0**: Warning messages appear
- **v2.0.0**: old_method() removed

## Questions?

Open an issue or contact [maintainer].

```

## Version 1.0 Stability Commitment

**We commit to**:
1. No breaking changes in v1.x (only additions)
2. Minimum 6 months notice before any deprecation
3. Clear migration guides for v2.0+
4. Backward compatibility tests for every release

**Users can trust**:
- Code written for v1.0 works on all v1.x versions
- Upgrading v1.x is always safe (no breaking changes)
- Clear warning before anything is removed

## Conclusion

**Stay on v1 as long as possible**. Every version bump carries cognitive load and migration cost. Add features carefully, deprecate reluctantly, and only go to v2 when there's no other way.

Good APIs age like fine wine, not milk.
```
