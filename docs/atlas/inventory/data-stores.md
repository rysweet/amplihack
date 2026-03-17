# Data Store Inventory

**Generated:** 2026-03-17

| Store | Type | Version | Location | Consumers | Migration Tool |
|-------|------|---------|----------|-----------|---------------|
| Kuzu | Embedded Graph DB | >=0.11 | ~/.amplihack/memory/ | memory/ | - (schema-less) |
| Filesystem (runtime) | File System | - | ~/.claude/runtime/ | hooks, session | - |
| Filesystem (logs) | File System | - | ~/.claude/runtime/logs/ | session, hooks | - |
| Filesystem (metrics) | File System | - | ~/.claude/runtime/metrics/ | hooks | - |
| Filesystem (locks) | File System | - | ~/.claude/runtime/locks/ | hooks | - |
| Settings | JSON File | - | ~/.claude/settings.json | settings.py | - |
| Manifest | JSON File | - | ~/.claude/install/amplihack-manifest.json | install.py, uninstall.py | - |
| Recipe Output | File System | - | .recipe-output/ | recipes/ | - |

## Graph Databases (via vendor/blarify)

These are used by the vendored blarify code intelligence system, not by the core amplihack application:

| Store | Type | Version | Purpose |
|-------|------|---------|---------|
| FalkorDB | Graph DB | >=1.0.10 | Blarify code graph storage (optional) |
| Neo4j | Graph DB | >=5.25 | Blarify code graph storage (optional) |
