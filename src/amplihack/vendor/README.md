# Vendored Dependencies

This directory contains forked/modified versions of third-party packages.

## blarify (Modified Fork)

**Version**: 1.3.0 (forked)
**Original**: https://github.com/blarApp/blarify
**Modifications**: Added Kuzu database support

### Why Vendored?

Blarify natively supports Neo4j and FalkorDB, but not Kuzu. We've added a `KuzuManager`
implementing the `AbstractDbManager` interface to enable direct Kuzu integration without
requiring Neo4j.

### Key Changes

1. **Added `kuzu_manager.py`**: New database manager for Kuzu
2. **Modified `cli/commands/create.py`**: Added `--db-type kuzu` option
3. **Modified `__init__.py`**: Export KuzuManager

### Upstream Integration

If/when blarify adds official Kuzu support upstream, this fork can be removed and
replaced with the official blarify package.

### License

Blarify is licensed under its original license. See `blarify/LICENSE` for details.
